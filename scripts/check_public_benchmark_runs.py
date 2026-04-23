#!/usr/bin/env python3
"""Summarize local public benchmark package runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness_benchmark import (
    PUBLIC_RUNS_DIR,
    build_public_benchmark_runs_report,
    render_public_benchmark_runs_markdown,
    write_public_benchmark_runs_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=PUBLIC_RUNS_DIR,
        help="Directory containing public benchmark run subdirectories.",
    )
    parser.add_argument("--write", action="store_true", help="Write summary markdown/json outputs into the runs directory.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every discovered run is ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def main() -> int:
    args = parse_args()
    try:
        report = build_public_benchmark_runs_report(args.runs_dir)
        writes = write_public_benchmark_runs_outputs(args.runs_dir, report=report) if args.write else {}
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"report": report, "writes": writes}, indent=2))
    else:
        print(render_public_benchmark_runs_markdown(report), end="")
        if writes:
            print("Generated outputs:")
            print(f"- `{writes['report_json']}`")
            print(f"- `{writes['report_md']}`")
            print(f"- `{writes['manifest']}`")

    if args.strict:
        return 0 if report["readiness"] == "ready" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
