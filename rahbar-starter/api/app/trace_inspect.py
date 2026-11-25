"""Reconstruct a saved query trace without re-running the query."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import get_settings
from .services.tracing import read_traces


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-id", required=True)
    settings = get_settings()
    parser.add_argument("--path", default=settings.trace_path)
    args = parser.parse_args()

    try:
        traces = read_traces(args.path, allowed_directory=Path(settings.trace_path).parent)
    except ValueError as exc:
        parser.error(str(exc))
    matches = [item for item in traces if item.get("trace_id") == args.trace_id]
    if not matches:
        print(f"trace not found: {args.trace_id}", file=sys.stderr)
        return 1
    print(json.dumps(matches[-1], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
