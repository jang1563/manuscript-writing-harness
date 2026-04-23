#!/usr/bin/env python3
"""Run the aggregate benchmark matrix for the multi-agent manuscript system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from harness_benchmark import (
    MANIFESTS_DIR,
    REPORTS_DIR,
    build_harness_benchmark_matrix_report,
    render_harness_benchmark_matrix_markdown,
    write_harness_benchmark_matrix_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write matrix markdown/json outputs and manifest.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every tracked benchmark is ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--suites-only", action="store_true", help="Only include tracked suites in the matrix.")
    parser.add_argument("--bundles-only", action="store_true", help="Only include tracked bundles in the matrix.")
    parser.add_argument("--reports-dir", type=Path, help="Optional override directory for written matrix reports.")
    parser.add_argument("--manifests-dir", type=Path, help="Optional override directory for written matrix manifests.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def main() -> int:
    args = parse_args()
    if args.suites_only and args.bundles_only:
        message = "Specify at most one of --suites-only or --bundles-only."
        if args.json:
            _emit_error_json(message)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    include_suites = not args.bundles_only
    include_bundles = not args.suites_only

    try:
        report = build_harness_benchmark_matrix_report(
            include_suites=include_suites,
            include_bundles=include_bundles,
        )
        writes = (
            write_harness_benchmark_matrix_outputs(
                include_suites=include_suites,
                include_bundles=include_bundles,
                reports_dir=args.reports_dir or REPORTS_DIR,
                manifests_dir=args.manifests_dir or MANIFESTS_DIR,
            )
            if args.write
            else {}
        )
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"report": report, "writes": writes}, indent=2))
    else:
        print(render_harness_benchmark_matrix_markdown(report), end="")
        if writes:
            print("Generated outputs:")
            print(f"- `{writes['report_json']}`")
            print(f"- `{writes['report_md']}`")
            print(f"- `{writes['manifest']}`")

    if args.strict:
        return 0 if report["readiness"] == "ready" else 1
    return 0 if report["readiness"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
