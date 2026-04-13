#!/usr/bin/env python3
"""Run the deterministic short-soak acceptance sequence used by CI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports" / "overnight"
DEFAULT_WORKSPACE_ROOT = Path("/tmp/manuscript_overnight_ci")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-hours", type=float, default=0.1)
    parser.add_argument("--light-interval-min", type=int, default=1)
    parser.add_argument("--full-interval-min", type=int, default=2)
    parser.add_argument("--myst-interval-min", type=int, default=3)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument(
        "--no-keep-workspace",
        action="store_true",
        help="Delete the sandbox workspace after the soak run completes",
    )
    parser.add_argument(
        "--write-step-summary",
        action="store_true",
        help="Write the rendered CI soak markdown to $GITHUB_STEP_SUMMARY if it is set",
    )
    return parser.parse_args(argv)


def run_step(label: str, command: list[str]) -> None:
    print(f"[ci-soak] {label}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> int:
    args = parse_args()
    python = sys.executable

    soak_command = [
        python,
        "scripts/run_overnight_validation.py",
        "--max-hours",
        str(args.max_hours),
        "--light-interval-min",
        str(args.light_interval_min),
        "--full-interval-min",
        str(args.full_interval_min),
        "--myst-interval-min",
        str(args.myst_interval_min),
        "--workspace-root",
        str(args.workspace_root),
        "--report-root",
        str(args.report_root),
    ]
    if not args.no_keep_workspace:
        soak_command.append("--keep-workspace")

    run_step("deterministic short soak", soak_command)

    report_json_path = args.report_root / "latest-report-check.json"
    summary_md_path = args.report_root / "latest-ci-summary.md"

    with report_json_path.open("w", encoding="utf-8") as handle:
        print("[ci-soak] check report health", flush=True)
        subprocess.run(
            [python, "scripts/check_overnight_report.py", "--json"],
            cwd=REPO_ROOT,
            check=True,
            stdout=handle,
        )

    print("[ci-soak] render CI summary", flush=True)
    rendered = subprocess.run(
        [python, "scripts/render_ci_soak_summary.py"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    summary_md_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="" if rendered.endswith("\n") else "\n")

    if args.write_step_summary:
        step_summary_raw = os.environ.get("GITHUB_STEP_SUMMARY")
        if step_summary_raw:
            step_summary = Path(step_summary_raw)
            with step_summary.open("a", encoding="utf-8") as handle:
                handle.write(rendered)

    print(f"[ci-soak] report JSON: {report_json_path}", flush=True)
    print(f"[ci-soak] summary markdown: {summary_md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
