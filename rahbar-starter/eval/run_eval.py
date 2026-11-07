#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

Given: talking to the API, reading the golden set, writing results.json, the exit
code. Yours: the four functions marked STARTER-TODO. They are the evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
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
    return results


def gate(results: dict, baseline: dict | None) -> list[str]:
    failures = []
    recall = results["recall@5"]
    previous = baseline.get("recall@5") if baseline else None
    if recall is None or (previous is not None and previous - recall > MAX_RECALL5_DROP + 1e-12):
        failures.append("recall@5 missing or more than five percentage points below baseline")
    validity = results["citation_validity"]
    if validity is None:
        failures.append("the API returned zero citations across the evaluation set")
    elif validity < MIN_CITATION_VALIDITY:
        failures.append("citation validity must be at least 95%")
    if results["abstention_correctness"] != REQUIRED_ABSTENTION:
        failures.append("every must-abstain question must be declined")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--min-recall5", type=float, default=0,
                        help="optional absolute recall@5 floor for CI fixtures")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    rows = []
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(timeout=120.0, headers=headers) as client:
        for q in questions:
            started = time.perf_counter()
            response = ask(client, args.api, q["question"])
            rows.append({
                "id": q["id"], "type": q.get("type", "ordinary"),
                "must_abstain": bool(q.get("must_abstain", False)),
                "relevant": q.get("relevant") or [],
                "expect": q.get("expect"),
                "response": response,
                "seconds": round(time.perf_counter() - started, 2),
            })
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")

    results = summarise(rows)
    baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
    failures = gate(results, baseline)
    recall5 = results["recall@5"]
    if recall5 is not None and recall5 < args.min_recall5:
        failures.append(f"recall@5 {recall5:.3f} is below the {args.min_recall5:.3f} floor")

    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    results["per_question"] = [
        {"id": row["id"], "answered_from_context": row["response"]["answered_from_context"],
         "citation_count": len(row["response"].get("citations", [])),
         "citation_validity": citation_validity(row["response"]),
         "recall@5": recall_at_k(row["relevant"], row["response"]["retrieved"], 5)}
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


if __name__ == "__main__":
    sys.exit(main())
