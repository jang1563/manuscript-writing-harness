#!/usr/bin/env python3
"""Render a concise markdown summary for CI soak-validation results."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from check_overnight_report import evaluate_payload
from overnight_digest import summary_snapshot
from overnight_status import choose_run_dir, REPORT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--run-id", help="Explicit overnight run directory name")
    return parser.parse_args()


def render_markdown(result: dict[str, object], payload: dict[str, object]) -> str:
    snapshot = payload["status_snapshot"]
    summary_status = snapshot.get("summary_status") or {}
    lines = [
        "## Soak Acceptance",
        "",
        f"- run: `{result['run_dir']}`",
        f"- passed: `{result['passed']}`",
        f"- health: `{result['health']}`",
        f"- baseline: `{result['baseline']}`",
        f"- completed: `{result['completed']}`",
    ]
    artifact_mode = summary_status.get("MyST artifact mode")
    if artifact_mode is not None:
        lines.append(f"- MyST artifact mode: `{artifact_mode}`")

    phase_counts = snapshot.get("phase_counts") or {}
    if phase_counts:
        lines.extend(["", "### Phase Counts"])
        for phase, count in sorted(phase_counts.items()):
            lines.append(f"- `{phase}`: `{count}`")

    lines.extend(["", "### Gate Result"])
    if result["failures"]:
        for failure in result["failures"]:
            lines.append(f"- fail: `{failure}`")
    else:
        lines.append("- fail: `none`")

    unexpected_warnings = payload.get("unexpected_warning_lines") or []
    drift_items = payload.get("drift_items") or []
    lines.extend(["", "### Warnings And Drift"])
    if unexpected_warnings:
        for line in unexpected_warnings:
            lines.append(f"- unexpected warning: `{line}`")
    else:
        lines.append("- unexpected warning: `none`")
    if drift_items and any(item != "- `none`" for item in drift_items):
        for item in drift_items:
            lines.append(item)
    else:
        lines.append("- artifact drift: `none`")

    lines.extend(["", "### Morning Paths"])
    expected_paths = result.get("expected_paths") or {}
    if expected_paths:
        for label in ("review", "index", "results"):
            value = expected_paths.get(label)
            if value:
                lines.append(f"- {label}: `{value}`")
    else:
        lines.append("- unavailable")

    figure_qa = payload.get("figure_qa")
    if isinstance(figure_qa, dict):
        lines.extend(["", "### Figure QA"])
        lines.append(f"- figures covered: `{figure_qa.get('figure_count', 0)}`")
        font_counts = figure_qa.get("font_status_counts") or {}
        clipping_counts = figure_qa.get("clipping_risk_counts") or {}
        for status, count in sorted(font_counts.items()):
            lines.append(f"- font `{status}`: `{count}`")
        for status, count in sorted(clipping_counts.items()):
            lines.append(f"- clipping `{status}`: `{count}`")

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
    print(render_markdown(result, payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
