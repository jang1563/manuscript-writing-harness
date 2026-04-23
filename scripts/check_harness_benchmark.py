#!/usr/bin/env python3
"""Run the tracked benchmark suite for the multi-agent manuscript system."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness_benchmark import (
    DEFAULT_SUITE_ID,
    build_harness_benchmark_report,
    build_harness_benchmark_report_from_package,
    build_harness_benchmark_report_from_package_archive,
    list_benchmark_bundles,
    list_benchmark_suites,
    load_benchmark_bundle,
    load_benchmark_suite,
    render_harness_benchmark_markdown,
    write_harness_benchmark_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default=None, help="Benchmark suite id to run.")
    parser.add_argument("--bundle", default=None, help="Benchmark bundle id to run through the adapter layer.")
    parser.add_argument("--package-dir", type=Path, help="Benchmark package directory to evaluate directly.")
    parser.add_argument("--package-archive", type=Path, help="Benchmark package .zip archive to evaluate directly.")
    parser.add_argument("--write", action="store_true", help="Write benchmark markdown/json outputs and manifest.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every benchmark case passes.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--list-suites", action="store_true", help="List available benchmark suites and exit.")
    parser.add_argument("--list-bundles", action="store_true", help="List available benchmark bundles and exit.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def main() -> int:
    args = parse_args()
    source_flags = [
        bool(args.suite),
        bool(args.bundle),
        bool(args.package_dir),
        bool(args.package_archive),
    ]
    if sum(source_flags) > 1:
        message = "Specify at most one of --suite, --bundle, --package-dir, or --package-archive."
        if args.json:
            _emit_error_json(message)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    if args.list_suites:
        for suite_id in list_benchmark_suites():
            print(suite_id)
        return 0
    if args.list_bundles:
        for bundle_id in list_benchmark_bundles():
            print(bundle_id)
        return 0

    if args.write and (args.package_dir or args.package_archive):
        message = (
            "--write is only supported for tracked suites and bundles. "
            "Import the package first if you want tracked benchmark report files."
        )
        if args.json:
            _emit_error_json(message)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    suite_id = args.suite or DEFAULT_SUITE_ID
    bundle_id = args.bundle

    try:
        if args.package_dir:
            report = build_harness_benchmark_report_from_package(
                args.package_dir,
                repo_root=Path.cwd(),
            )
        elif args.package_archive:
            report = build_harness_benchmark_report_from_package_archive(
                args.package_archive,
                repo_root=Path.cwd(),
            )
        else:
            if bundle_id:
                load_benchmark_bundle(bundle_id)
            else:
                load_benchmark_suite(suite_id)
            report = build_harness_benchmark_report(suite_id=suite_id, bundle_id=bundle_id)
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    writes = {}
    if not args.package_dir and not args.package_archive and args.write:
        writes = write_harness_benchmark_outputs(suite_id=suite_id, bundle_id=bundle_id)

    if args.json:
        print(json.dumps({"report": report, "writes": writes}, indent=2))
    else:
        print(render_harness_benchmark_markdown(report), end="")
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
