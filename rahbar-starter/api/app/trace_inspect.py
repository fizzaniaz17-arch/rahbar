"""Reconstruct a saved query trace without re-running the query."""

from __future__ import annotations

import argparse
import json
import sys

from .config import get_settings
from .services.tracing import read_traces


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-id", required=True)
    parser.add_argument("--path", default=get_settings().trace_path)
    args = parser.parse_args()

    matches = [
        item for item in read_traces(args.path)
        if item.get("trace_id") == args.trace_id
    ]
    if not matches:
        print(f"trace not found: {args.trace_id}", file=sys.stderr)
        return 1
    print(json.dumps(matches[-1], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
