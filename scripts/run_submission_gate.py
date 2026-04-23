#!/usr/bin/env python3
"""Run the end-to-end submission gate sequence used by GitHub Actions."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from submission_gate_summary import (
    load_json_payload,
    load_optional_text,
    render_markdown,
    resolve_step_summary_path,
)


REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", required=True, help="Tracked venue id to gate.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory where gate artifacts should be written.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to use for the gate commands.",
    )
    parser.add_argument(
        "--write-step-summary",
        action="store_true",
        help="Write the rendered gate summary to $GITHUB_STEP_SUMMARY if it is available.",
    )
    return parser.parse_args(argv)


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "venue_json": output_dir / "submission-gate-venue.json",
        "venue_stderr": output_dir / "submission-gate-venue.stderr",
        "venue_exit": output_dir / "submission-gate-venue.exit",
        "audit_json": output_dir / "submission-gate-audit.json",
        "audit_stderr": output_dir / "submission-gate-audit.stderr",
        "audit_exit": output_dir / "submission-gate-audit.exit",
        "summary": output_dir / "submission-gate-summary.md",
    }


def run_json_command(command: list[str], *, stdout_path: Path, stderr_path: Path) -> int:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed.returncode


def write_summary(
    *,
    venue: str,
    paths: dict[str, Path],
    write_step_summary: bool,
) -> str:
    venue_payload, venue_payload_error = load_json_payload(paths["venue_json"])
    audit_payload, audit_payload_error = load_json_payload(paths["audit_json"])
    markdown = render_markdown(
        venue_input=venue,
        venue_status=paths["venue_exit"].read_text(encoding="utf-8").strip(),
        audit_status=paths["audit_exit"].read_text(encoding="utf-8").strip(),
        venue_payload=venue_payload,
        audit_payload=audit_payload,
        venue_payload_error=venue_payload_error,
        audit_payload_error=audit_payload_error,
        venue_stderr=load_optional_text(paths["venue_stderr"]),
        audit_stderr=load_optional_text(paths["audit_stderr"]),
    )
    paths["summary"].write_text(markdown, encoding="utf-8")
    if write_step_summary and (step_summary_path := resolve_step_summary_path(None)):
        step_summary_path.write_text(markdown, encoding="utf-8")
    return markdown


def run_submission_gate(
    venue: str,
    *,
    output_dir: Path,
    python_executable: str,
    write_step_summary: bool = False,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)

    venue_command = [
        python_executable,
        "scripts/check_venue_readiness.py",
        "--venue",
        venue,
        "--json",
        "--strict",
        "--require-current-verification",
    ]
    audit_command = [
        python_executable,
        "scripts/check_pre_submission_audit.py",
        "--venue",
        venue,
        "--json",
        "--strict",
        "--require-current-venue-verification",
        "--require-confirmed-manuscript-bibliography",
    ]

    print(f"[submission-gate] venue gate for `{venue}`", flush=True)
    venue_status = run_json_command(
        venue_command,
        stdout_path=paths["venue_json"],
        stderr_path=paths["venue_stderr"],
    )
    paths["venue_exit"].write_text(f"{venue_status}\n", encoding="utf-8")

    print(f"[submission-gate] pre-submission audit for `{venue}`", flush=True)
    audit_status = run_json_command(
        audit_command,
        stdout_path=paths["audit_json"],
        stderr_path=paths["audit_stderr"],
    )
    paths["audit_exit"].write_text(f"{audit_status}\n", encoding="utf-8")

    print(f"[submission-gate] render summary for `{venue}`", flush=True)
    markdown = write_summary(
        venue=venue,
        paths=paths,
        write_step_summary=write_step_summary,
    )
    print(markdown, end="" if markdown.endswith("\n") else "\n")

    print(f"[submission-gate] venue JSON: {paths['venue_json']}", flush=True)
    print(f"[submission-gate] audit JSON: {paths['audit_json']}", flush=True)
    print(f"[submission-gate] summary markdown: {paths['summary']}", flush=True)
    return max(venue_status, audit_status)


def main() -> int:
    args = parse_args()
    return run_submission_gate(
        args.venue,
        output_dir=args.output_dir,
        python_executable=args.python,
        write_step_summary=args.write_step_summary,
    )


if __name__ == "__main__":
    raise SystemExit(main())
