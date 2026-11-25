#!/usr/bin/env python3
"""Compare live-query embeddings with answerable golden-question embeddings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml  # type: ignore[import-untyped]

HERE = Path(__file__).resolve().parent
ALLOWED_OLLAMA_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "host.docker.internal",
    "host.minikube.internal",
    "ollama",
    "ollama.rahbar.svc",
    "ollama.rahbar.svc.cluster.local",
})


def resolve_eval_path(path: Path, root: Path = HERE) -> Path:
    allowed_root = root.resolve()
    resolved = path.expanduser().resolve()
    if resolved == allowed_root or not resolved.is_relative_to(allowed_root):
        raise ValueError(f"path must be inside {allowed_root}")
    return resolved


def read_jsonl(path: Path) -> list[dict]:
    path = resolve_eval_path(path)
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"{path}:{line_number}: expected a JSON object")
                records.append(record)
    if not records:
        raise ValueError(f"no records in {path}")
    return records


def load_answerable_golden(path: Path) -> list[dict]:
    path = resolve_eval_path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = [
        question for question in data.get("questions", [])
        if not question.get("must_abstain", False) and question.get("relevant")
    ]
    if not questions:
        raise ValueError(f"no answerable questions in {path}")
    return questions


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("embedding dimensions must match and be non-empty")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        raise ValueError("zero-length embedding vector")
    return dot / (left_norm * right_norm)


def percentile(values: list[float], percentage: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    low = math.floor(position)
    high = math.ceil(position)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def evaluate_coverage(
    live: list[dict], golden: list[dict], live_vectors: list[list[float]],
    golden_vectors: list[list[float]], threshold: float,
) -> dict:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if len(live) != len(live_vectors) or len(golden) != len(golden_vectors):
        raise ValueError("one embedding is required per query")

    details = []
    for query, vector in zip(live, live_vectors, strict=True):
        matches = [
            (cosine(vector, candidate), question)
            for question, candidate in zip(golden, golden_vectors, strict=True)
        ]
        similarity, nearest = max(matches, key=lambda match: match[0])
        details.append({
            "id": query["id"],
            "query": query["query"],
            "domain": query["domain"],
            "topic": query["topic"],
            "nearest_golden_id": nearest["id"],
            "similarity": similarity,
            "covered": similarity >= threshold,
        })

    covered = sum(item["covered"] for item in details)
    scores = sorted(item["similarity"] for item in details)
    return {
        "threshold": threshold,
        "total": len(details),
        "covered": covered,
        "uncovered": len(details) - covered,
        "coverage": covered / len(details),
        "uncovered_topics": sorted({
            item["topic"] for item in details if not item["covered"]
        }),
        "similarity_distribution": {
            "min": scores[0],
            "max": scores[-1],
            "mean": sum(scores) / len(scores),
            "p50": percentile(scores, 50),
            "p95": percentile(scores, 95),
        },
        "queries": details,
    }


def validate_ollama_url(url: str) -> str:
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").casefold()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid Ollama URL port") from exc
    if (
        parsed.scheme != "http"
        or hostname not in ALLOWED_OLLAMA_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port not in (None, 11434)
    ):
        raise ValueError("Ollama URL must use an approved host and port 11434")
    formatted_host = f"[{hostname}]" if ":" in hostname else hostname
    return f"http://{formatted_host}:11434"


def embed(texts: list[str], model: str, url: str) -> list[list[float]]:
    vectors = []
    base_url = validate_ollama_url(url)
    with httpx.Client(timeout=120) as client:
        for start in range(0, len(texts), 32):
            batch = texts[start:start + 32]
            response = client.post(
                f"{base_url}/api/embed",
                json={"model": model, "input": batch},
            )
            response.raise_for_status()
            payload = response.json()
            batch_vectors = payload.get("embeddings")
            if not isinstance(batch_vectors, list) or len(batch_vectors) != len(batch):
                raise ValueError("embedding service returned an unexpected response")
            vectors.extend([[float(value) for value in vector] for vector in batch_vectors])
    return vectors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--live", type=Path, default=HERE / "live_queries.jsonl")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--model", default=os.environ.get("EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument(
        "--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434")
    )
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--minimum-coverage", type=float, default=0.85)
    args = parser.parse_args()
    if not 0 <= args.minimum_coverage <= 1:
        parser.error("--minimum-coverage must be between 0 and 1")
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")

    try:
        live_path = resolve_eval_path(args.live)
        golden_path = resolve_eval_path(args.golden)
        output_path = resolve_eval_path(args.out or HERE / "results" / (
            "coverage_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".json"
        ))
        ollama_url = validate_ollama_url(args.ollama_url)
    except ValueError as exc:
        parser.error(str(exc))

    live = read_jsonl(live_path)
    golden = load_answerable_golden(golden_path)
    vectors = embed(
        [item["query"] for item in live] + [item["question"] for item in golden],
        args.model,
        ollama_url,
    )
    live_vectors = vectors[:len(live)]
    golden_vectors = vectors[len(live):]
    result = evaluate_coverage(
        live, golden, live_vectors, golden_vectors, args.threshold
    )
    result.update({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model": args.model,
        "golden_sha256": hashlib.sha256(golden_path.read_bytes()).hexdigest(),
        "live_sha256": hashlib.sha256(live_path.read_bytes()).hexdigest(),
        "minimum_coverage": args.minimum_coverage,
        "gate": "PASS" if result["coverage"] >= args.minimum_coverage else "FAIL",
    })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "queries"}, indent=2))
    return 0 if result["coverage"] >= args.minimum_coverage else 1


if __name__ == "__main__":
    sys.exit(main())
