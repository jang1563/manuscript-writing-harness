#!/usr/bin/env python3
"""Import a local benchmark package into the tracked benchmark-bundle format."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness_benchmark import BUNDLES_DIR, import_benchmark_package, import_benchmark_package_archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-dir",
        type=Path,
        help="Path to a local benchmark package directory containing package_manifest.json.",
    )
    parser.add_argument(
        "--package-archive",
        type=Path,
        help="Path to a local .zip benchmark package archive.",
    )
    parser.add_argument("--bundle-id", help="Optional override for the imported bundle id.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BUNDLES_DIR,
        help="Directory to write the imported bundle into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing bundle with the same id.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing the bundle.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like text.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def main() -> int:
    args = parse_args()
    if bool(args.package_dir) == bool(args.package_archive):
        message = "Specify exactly one of --package-dir or --package-archive."
        if args.json:
            _emit_error_json(message)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    try:
        if args.package_archive:
            result = import_benchmark_package_archive(
                args.package_archive,
                bundle_id=args.bundle_id,
                output_dir=args.output_dir,
                dry_run=args.dry_run,
                force=args.force,
            )
        else:
            result = import_benchmark_package(
                args.package_dir,
                bundle_id=args.bundle_id,
                output_dir=args.output_dir,
                dry_run=args.dry_run,
                force=args.force,
            )
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("# Imported Benchmark Bundle")
        print()
        print(f"- bundle_id: `{result['bundle_id']}`")
        print(f"- case_count: `{result['case_count']}`")
        print(f"- dry_run: `{str(result['dry_run']).lower()}`")
        print(f"- package_manifest: `{result['package_manifest']}`")
        if result.get("package_archive"):
            print(f"- package_archive: `{result['package_archive']}`")
        print(f"- output_path: `{result['output_path']}`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
