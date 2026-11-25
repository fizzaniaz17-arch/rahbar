#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

The runner talks to the API, reads a golden set, writes machine-readable results,
and returns a non-zero exit code when the configured release gate fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml  # type: ignore[import-untyped]

HERE = Path(__file__).resolve().parent


def resolve_cli_path(path: Path, allowed_roots: tuple[Path, ...]) -> Path:
    resolved = path.expanduser().resolve()
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed_roots):
        raise ValueError("CLI path must be under an approved directory")
    return resolved


@dataclass(frozen=True)
class GateThresholds:
    max_recall5_drop: float = 0.05
    min_citation_validity: float = 0.95
    required_abstention_correctness: float = 1.0


def load_gate_thresholds(
    path: Path, allowed_roots: tuple[Path, ...] = (HERE.parent,)
) -> GateThresholds:
    path = resolve_cli_path(path, allowed_roots)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    thresholds = GateThresholds(**data)
    if not 0 <= thresholds.max_recall5_drop <= 1:
        raise ValueError("max_recall5_drop must be between 0 and 1")
    if not 0 <= thresholds.min_citation_validity <= 1:
        raise ValueError("min_citation_validity must be between 0 and 1")
    if not 0 <= thresholds.required_abstention_correctness <= 1:
        raise ValueError("required_abstention_correctness must be between 0 and 1")
    return thresholds


def load_golden(
    path: Path, allowed_roots: tuple[Path, ...] = (HERE.parent,)
) -> list[dict]:
    path = resolve_cli_path(path, allowed_roots)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of the relevant (source, section) pairs found in the top k retrieved.
    Return None when the question has no relevant passages (must-abstain questions)."""
    def pairs(passages: list[dict]) -> set[tuple[str, str]]:
        return {(item["source"], " ".join(item["section"].split()).casefold())
                for item in passages}

    expected = pairs(relevant)
    return len(expected & pairs(retrieved[:k])) / len(expected) if expected else None


def citation_validity(response: dict) -> float | None:
    citations = response.get("citations", [])
    if not citations:
        return None
    retrieved = {(item["source"], item["section"], item["page"])
                 for item in response.get("retrieved", [])}
    return sum((item["source"], item["section"], item["page"]) in retrieved
               for item in citations) / len(citations)


def percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile must be between 0 and 100")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def reciprocal_rank(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Return reciprocal rank of the first matching source/section pair."""
    expected = {(item["source"], " ".join(item["section"].split()).casefold())
                for item in relevant}
    if not expected:
        return None
    for rank, item in enumerate(retrieved[:k], 1):
        pair = (item["source"], " ".join(item["section"].split()).casefold())
        if pair in expected:
            return 1 / rank
    return 0.0


def ndcg_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Compute binary-relevance normalized discounted cumulative gain."""
    expected = {(item["source"], " ".join(item["section"].split()).casefold())
                for item in relevant}
    if not expected:
        return None
    seen: set[tuple[str, str]] = set()
    actual = []
    for item in retrieved[:k]:
        pair = (item["source"], " ".join(item["section"].split()).casefold())
        actual.append(pair in expected and pair not in seen)
        seen.add(pair)
    dcg = sum(int(is_relevant) / math.log2(rank + 1)
              for rank, is_relevant in enumerate(actual, 1))
    ideal_count = min(len(expected), k)
    ideal_dcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def summarise(rows: list[dict]) -> dict:
    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None

    by_type: dict[str, dict] = {}
    results: dict = {"by_type": by_type}
    for k in (3, 5):
        key = f"recall@{k}"
        scored = [(row["type"], score) for row in rows
                  if (score := recall_at_k(row["relevant"],
                                           row["response"]["retrieved"], k)) is not None]
        results[key] = mean([score for _, score in scored])
        for kind in sorted({kind for kind, _ in scored}):
            by_type.setdefault(kind, {})[key] = mean(
                [score for row_type, score in scored if row_type == kind])
    valid_total = 0.0
    citation_total = 0
    abstentions = []
    for row in rows:
        response = row["response"]
        count = len(response.get("citations", []))
        valid_total += (citation_validity(response) or 0) * count
        citation_total += count
        if row["must_abstain"]:
            abstentions.append(float(response.get("answered_from_context") is False))
    results["citation_count"] = citation_total
    results["citation_validity"] = valid_total / citation_total if citation_total else None
    results["abstention_correctness"] = mean(abstentions)
    scored_mrr = [reciprocal_rank(row["relevant"], row["response"]["retrieved"], 5)
                  for row in rows]
    scored_ndcg = [ndcg_at_k(row["relevant"], row["response"]["retrieved"], 5)
                   for row in rows]
    results["mrr@5"] = mean([value for value in scored_mrr if value is not None])
    results["ndcg@5"] = mean([value for value in scored_ndcg if value is not None])
    latencies = [float(row["seconds"]) for row in rows if "seconds" in row]
    results["latency_p50_seconds"] = percentile(latencies, 50)
    results["latency_p95_seconds"] = percentile(latencies, 95)
    return results


def gate(
    results: dict,
    baseline: dict | None,
    thresholds: GateThresholds = GateThresholds(),
) -> list[str]:
    failures = []
    recall = results["recall@5"]
    previous = baseline.get("recall@5") if baseline else None
    if recall is None or (
        previous is not None
        and previous - recall > thresholds.max_recall5_drop + 1e-12
    ):
        failures.append(
            "recall@5 missing or more than "
            f"{thresholds.max_recall5_drop:.1%} below baseline"
        )
    validity = results["citation_validity"]
    if validity is None:
        failures.append("the API returned zero citations across the evaluation set")
    elif validity < thresholds.min_citation_validity:
        failures.append(
            f"citation validity must be at least {thresholds.min_citation_validity:.1%}"
        )
    abstention = results["abstention_correctness"]
    if (abstention is None
            or abstention < thresholds.required_abstention_correctness):
        failures.append("abstention correctness is below the configured minimum")
    return failures


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--gate-config", type=Path, default=HERE / "gate.yaml")
    parser.add_argument("--responses", type=Path,
                        help="optional per-question responses for manual review")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="HTTP timeout in seconds")
    parser.add_argument("--min-recall5", type=float, default=0,
                        help="optional absolute recall@5 floor for CI fixtures")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    try:
        args.golden = resolve_cli_path(args.golden, (HERE.parent,))
        args.baseline = resolve_cli_path(args.baseline, (HERE.parent,))
        args.gate_config = resolve_cli_path(args.gate_config, (HERE.parent,))
        output_roots = (HERE.parent, Path(tempfile.gettempdir()))
        args.out = resolve_cli_path(args.out, output_roots)
        if args.responses is not None:
            args.responses = resolve_cli_path(args.responses, output_roots)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def collect_responses(args: argparse.Namespace, questions: list[dict]) -> list[dict]:
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=args.timeout, headers=headers) as client:
        for question in questions:
            started = time.perf_counter()
            try:
                response = ask(client, args.api, question["question"])
            except httpx.TimeoutException as exc:
                sys.exit(
                    f"{question['id']}: request timed out ({type(exc).__name__})"
                )
            row = {
                "id": question["id"],
                "type": question.get("type", "ordinary"),
                "must_abstain": bool(question.get("must_abstain", False)),
                "relevant": question.get("relevant") or [],
                "expect": question.get("expect"),
                "response": response,
                "seconds": round(time.perf_counter() - started, 2),
            }
            rows.append(row)
            print(
                f"  {question['id']:<5} {row['seconds']:>6.2f}s  "
                f"{question['question'][:60]}"
            )
            if args.responses:
                args.responses.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def finish_evaluation(args: argparse.Namespace, rows: list[dict]) -> int:
    results = summarise(rows)
    baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
    thresholds = load_gate_thresholds(args.gate_config)
    failures = gate(results, baseline, thresholds)
    recall5 = results["recall@5"]
    if recall5 is not None and recall5 < args.min_recall5:
        failures.append(f"recall@5 {recall5:.3f} is below the {args.min_recall5:.3f} floor")

    results["golden"] = str(args.golden)
    results["golden_sha256"] = hashlib.sha256(args.golden.read_bytes()).hexdigest()
    results["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    results["gate_thresholds"] = {
        "max_recall5_drop": thresholds.max_recall5_drop,
        "min_citation_validity": thresholds.min_citation_validity,
        "required_abstention_correctness": thresholds.required_abstention_correctness,
    }
    results["questions"] = len(rows)
    results["per_question"] = [
        {
            "id": row["id"],
            "answered_from_context": row["response"]["answered_from_context"],
            "citation_count": len(row["response"].get("citations", [])),
            "citation_validity": citation_validity(row["response"]),
            "recall@5": recall_at_k(row["relevant"], row["response"]["retrieved"], 5),
        }
        for row in rows
    ]
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline and not failures:
        args.baseline.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


def main() -> int:
    args = parse_arguments()
    questions = load_golden(args.golden)
    rows = collect_responses(args, questions)
    return finish_evaluation(args, rows)


if __name__ == "__main__":
    sys.exit(main())
