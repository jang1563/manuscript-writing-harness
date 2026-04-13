#!/usr/bin/env python3
"""Validate that an overnight soak-validation run finished in a healthy state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

from overnight_digest import summary_snapshot
from overnight_status import choose_run_dir, REPORT_ROOT
from run_overnight_validation import morning_check_paths


STATUS_LINE_RE = re.compile(r"^- status: `(?P<status>[^`]+)`$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--run-id", help="Explicit overnight run directory name")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of plain text",
    )
    return parser.parse_args()


def parse_digest_status(path: Path) -> str | None:
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = STATUS_LINE_RE.match(raw_line.strip())
        if match:
            return match.group("status")
    return None


def evaluate_payload(run_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    snapshot = payload["status_snapshot"]
    summary_status = snapshot.get("summary_status") or {}
    digest_path = run_dir / "morning_digest.md"
    digest_status = parse_digest_status(digest_path)

    if not payload["completed"]:
        failures.append("summary.md missing or run still in progress")
    if payload["health"] != "healthy":
        failures.append(f"run health is {payload['health']!r}, expected 'healthy'")
    if summary_status.get("baseline") != "passed":
        failures.append("baseline did not pass")
    if payload["unexpected_warning_lines"]:
        failures.append("unexpected warnings were recorded")
    if any(line != "- `none`" for line in payload["drift_items"]):
        failures.append("artifact drift was recorded")
    if summary_status.get("first failure", "none") != "none":
        failures.append("first failure is not none")
    if summary_status.get("latest failure", "none") != "none":
        failures.append("latest failure is not none")
    if not digest_path.is_file():
        failures.append("morning_digest.md is missing")
    elif digest_status != "healthy":
        failures.append(f"morning digest status is {digest_status!r}, expected 'healthy'")

    workspace_value = payload.get("workspace")
    workspace = Path(workspace_value) if workspace_value else None
    expected_paths: dict[str, str] = {}
    missing_paths: list[str] = []
    if workspace is None or not workspace.exists():
        failures.append("workspace path is missing from the report or does not exist")
    else:
        expected_paths = morning_check_paths(workspace)
        for label in ("review", "index", "results"):
            candidate = Path(expected_paths[label])
            if not candidate.is_file():
                missing_paths.append(str(candidate))
        if missing_paths:
            failures.append("one or more morning check paths are missing")

    return {
        "run_dir": str(run_dir),
        "passed": not failures,
        "failures": failures,
        "health": payload["health"],
        "completed": payload["completed"],
        "baseline": summary_status.get("baseline"),
        "digest_path": str(digest_path),
        "digest_status": digest_status,
        "workspace": str(workspace) if workspace is not None else None,
        "expected_paths": expected_paths,
        "missing_paths": missing_paths,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        "Overnight Report Check",
        "",
        f"Run: {result['run_dir']}",
        f"Passed: {'yes' if result['passed'] else 'no'}",
        f"Health: {result['health']}",
        f"Completed: {result['completed']}",
        f"Baseline: {result['baseline']}",
        f"Morning digest: {result['digest_status'] or 'missing'}",
    ]
    if result["failures"]:
        lines.append("Failures:")
        for failure in result["failures"]:
            lines.append(f"  - {failure}")
    else:
        lines.append("Failures: none")
    if result["expected_paths"]:
        lines.append("Morning paths:")
        for label in ("review", "index", "results"):
            lines.append(f"  - {label}: {result['expected_paths'][label]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        run_dir = choose_run_dir(args.report_root, args.run_id)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = summary_snapshot(run_dir)
    result = evaluate_payload(run_dir, payload)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result), end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
