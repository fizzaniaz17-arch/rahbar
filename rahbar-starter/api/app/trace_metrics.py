"""Summarize persisted query traces over a configurable recent time window."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import get_settings
from .services.tracing import read_traces


def percentile(values: list[float], value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * value / 100
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] * (1 - (position - low)) + ordered[high] * (position - low)


def summarize(traces: list[dict], hours: float) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = [
        trace for trace in traces
        if datetime.fromisoformat(trace["timestamp_utc"]) >= cutoff
    ]
    total = len(recent)
    top_scores = [
        float(trace["retrieved"][0]["score"])
        for trace in recent if trace.get("retrieved")
    ]
    stages: dict[str, list[float]] = {}
    for trace in recent:
        for stage, seconds in trace.get("stage_seconds", {}).items():
            stages.setdefault(stage, []).append(float(seconds))
    return {
        "window_hours": hours,
        "trace_count": total,
        "top1_similarity": {
            "count": len(top_scores),
            "mean": sum(top_scores) / len(top_scores) if top_scores else None,
            "p50": percentile(top_scores, 50),
            "p95": percentile(top_scores, 95),
        },
        "abstention_rate": (
            sum(not trace["response"]["answered_from_context"] for trace in recent) / total
            if total else None
        ),
        "cache_hit_rate": (
            sum(bool(trace["cache_hit"]) for trace in recent) / total if total else None
        ),
        "stage_p95_seconds": {
            stage: percentile(values, 95) for stage, values in sorted(stages.items())
        },
        "prompt_injection_attempts": sum(
            bool(trace.get("guardrails", {}).get("injection_detected")) for trace in recent
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=24)
    settings = get_settings()
    parser.add_argument("--path", default=settings.trace_path)
    args = parser.parse_args()
    if args.hours <= 0:
        parser.error("--hours must be greater than zero")
    try:
        traces = read_traces(
            args.path, allowed_directory=Path(settings.trace_path).parent
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(summarize(traces, args.hours), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
