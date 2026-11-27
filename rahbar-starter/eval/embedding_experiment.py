#!/usr/bin/env python3
"""Run real embedding similarity, noise, and determinism experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml

try:
    from .coverage import cosine, embed, resolve_eval_path, validate_ollama_url
except ImportError:
    from coverage import cosine, embed, resolve_eval_path, validate_ollama_url

HERE = Path(__file__).resolve().parent


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, default=HERE / "embedding_pairs.yaml")
    parser.add_argument("--model", default=os.environ.get("EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://localhost:11434"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    pairs_path = resolve_eval_path(args.pairs)
    data = yaml.safe_load(pairs_path.read_text(encoding="utf-8")) or {}
    paraphrases = data.get("paraphrase_pairs", [])
    unrelated = data.get("unrelated_pairs", [])
    if len(paraphrases) < 15 or len(unrelated) < 15:
        parser.error("at least 15 paraphrase pairs and 15 unrelated pairs are required")

    ollama_url = validate_ollama_url(args.ollama_url)
    texts = [text for pair in paraphrases + unrelated for text in pair]
    vectors = embed(texts, args.model, ollama_url)
    repeated = embed(texts, args.model, ollama_url)

    paraphrase_scores = []
    unrelated_scores = []
    offset = 0
    for pair in paraphrases:
        left = vectors[offset]
        right = vectors[offset + 1]
        paraphrase_scores.append(cosine(left, right))
        offset += 2
    for pair in unrelated:
        left = vectors[offset]
        right = vectors[offset + 1]
        unrelated_scores.append(cosine(left, right))
        offset += 2

    noisy_texts = [text + " This sentence does not change the topic." for text in texts]
    noisy_vectors = embed(noisy_texts, args.model, ollama_url)
    noise_scores = [
        cosine(original, noisy)
        for original, noisy in zip(vectors, noisy_vectors, strict=True)
    ]
    determinism = [
        cosine(vector, repeated_vector)
        for vector, repeated_vector in zip(vectors, repeated, strict=True)
    ]
    gap = mean(paraphrase_scores) - mean(unrelated_scores)
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "embedding_model": args.model,
        "pairs_sha256": hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
        "paraphrase_pair_count": len(paraphrases),
        "unrelated_pair_count": len(unrelated),
        "paraphrase_mean_similarity": mean(paraphrase_scores),
        "unrelated_mean_similarity": mean(unrelated_scores),
        "similarity_gap": gap,
        "noise_mean_similarity": mean(noise_scores),
        "determinism_mean_similarity": mean(determinism),
        "noise_pass": mean(noise_scores) >= 0.85,
        "determinism_pass": mean(determinism) >= 0.999,
    }
    out = args.out or HERE / "results" / (
        "embedding-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
    )
    out = resolve_eval_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
