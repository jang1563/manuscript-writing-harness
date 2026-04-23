#!/usr/bin/env python3
"""Validate one local public benchmark run directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness_benchmark import validate_public_benchmark_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Public benchmark run directory containing report.json, report.md, manifest.json, and run_metadata.json.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the run is valid and ready.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def render_text(result: dict[str, object]) -> str:
    lines = [
        "# Public Benchmark Run Check",
        "",
        f"- run_dir: `{result['run_dir']}`",
        f"- run_id: `{result['run_id']}`",
        f"- readiness: `{result['readiness']}`",
        f"- passed: `{result['passed']}`",
        f"- suite_id: `{result['suite_id'] or 'unknown'}`",
        f"- overall_score: `{result['overall_score']}`",
        f"- case_count: `{result['case_count']}`",
        "",
    ]
    issues = result.get("issues", [])
    if issues:
        lines.extend(["## Issues", ""])
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    warnings = result.get("warnings", [])
    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")
    lines.extend(["## Artifacts", ""])
    artifacts = result.get("artifacts", {})
    if isinstance(artifacts, dict):
        for key, value in artifacts.items():
            lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    try:
        result = validate_public_benchmark_run(args.run_dir)
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result), end="")

    if args.strict:
        return 0 if result["passed"] and result["readiness"] == "ready" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
