#!/usr/bin/env python3
"""Render a markdown summary for the submission-gate workflow artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", required=True, help="Submitted venue input to describe in the summary.")
    parser.add_argument("--venue-json", type=Path, required=True, help="Venue gate JSON payload path.")
    parser.add_argument("--audit-json", type=Path, required=True, help="Pre-submission audit JSON payload path.")
    parser.add_argument("--venue-exit", type=Path, required=True, help="Venue gate exit-status file path.")
    parser.add_argument("--audit-exit", type=Path, required=True, help="Audit gate exit-status file path.")
    parser.add_argument("--venue-stderr", type=Path, help="Venue gate stderr file path.")
    parser.add_argument("--audit-stderr", type=Path, help="Audit gate stderr file path.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("submission-gate-summary.md"),
        help="Markdown file to write.",
    )
    parser.add_argument(
        "--github-step-summary",
        type=Path,
        help="Optional GitHub step summary path. Defaults to $GITHUB_STEP_SUMMARY when available.",
    )
    return parser.parse_args()


def load_json_payload(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"{path.name} was not created"
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None, f"{path.name} was empty"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"{path.name} contained invalid JSON: {exc}"


def load_optional_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    return raw or None


def load_required_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def render_markdown(
    *,
    venue_input: str,
    venue_status: str,
    audit_status: str,
    venue_payload: Any | None,
    audit_payload: Any | None,
    venue_payload_error: str | None = None,
    audit_payload_error: str | None = None,
    venue_stderr: str | None = None,
    audit_stderr: str | None = None,
) -> str:
    lines = [
        "# Submission Gate Summary",
        "",
        f"- venue_input: `{venue_input}`",
        f"- venue_gate_exit: `{venue_status}`",
        f"- audit_gate_exit: `{audit_status}`",
        "",
    ]

    if venue_payload is not None:
        gate = venue_payload.get("submission_gate", {}) if isinstance(venue_payload, dict) else {}
        lines.extend(
            [
                "## Venue Gate",
                "",
                f"- status: `{gate.get('status', 'unknown')}`",
                f"- failed_count: `{gate.get('failed_count', 0)}`",
                "",
            ]
        )
        for item in gate.get("failed_venues", []):
            lines.append(f"- `{item['display_name']}` (`{item['venue']}`): `{item['verification_status']}`")
        if isinstance(venue_payload, dict) and "error" in venue_payload:
            lines.append(f"- error: `{venue_payload['error']}`")
    elif venue_payload_error:
        lines.extend(["## Venue Gate", "", f"- payload_error: `{venue_payload_error}`", ""])

    if venue_stderr:
        lines.append(f"- stderr: `{venue_stderr}`")

    if audit_payload is not None:
        report = audit_payload.get("report", {}) if isinstance(audit_payload, dict) else {}
        gate = report.get("submission_gate", {}) if isinstance(report, dict) else {}
        bibliography_scope_gate = report.get("bibliography_scope_gate", {}) if isinstance(report, dict) else {}
        lines.extend(
            [
                "",
                "## Audit Gate",
                "",
                f"- audit_id: `{report.get('audit_id', 'unknown')}`",
                f"- readiness: `{report.get('readiness', 'unknown')}`",
                f"- status: `{gate.get('status', 'unknown')}`",
                f"- failed_count: `{gate.get('failed_count', 0)}`",
                "",
            ]
        )
        if bibliography_scope_gate:
            lines.append(f"- bibliography_scope_gate: `{bibliography_scope_gate.get('status', 'unknown')}`")
            lines.append(
                "- bibliography_scope_status: "
                f"`{bibliography_scope_gate.get('current_manuscript_scope_status', 'unknown')}`"
            )
        for item in gate.get("failed_venues", []):
            lines.append(f"- `{item['display_name']}` (`{item['venue']}`): `{item['verification_status']}`")
        if isinstance(audit_payload, dict) and "error" in audit_payload:
            lines.append(f"- error: `{audit_payload['error']}`")
    elif audit_payload_error:
        lines.extend(["", "## Audit Gate", "", f"- payload_error: `{audit_payload_error}`", ""])

    if audit_stderr:
        lines.append(f"- stderr: `{audit_stderr}`")

    return "\n".join(lines).rstrip() + "\n"


def resolve_step_summary_path(cli_value: Path | None) -> Path | None:
    if cli_value is not None:
        return cli_value
    env_value = Path(value) if (value := os.environ.get("GITHUB_STEP_SUMMARY")) else None
    return env_value


def main() -> int:
    args = parse_args()
    venue_payload, venue_payload_error = load_json_payload(args.venue_json)
    audit_payload, audit_payload_error = load_json_payload(args.audit_json)
    markdown = render_markdown(
        venue_input=args.venue,
        venue_status=load_required_text(args.venue_exit),
        audit_status=load_required_text(args.audit_exit),
        venue_payload=venue_payload,
        audit_payload=audit_payload,
        venue_payload_error=venue_payload_error,
        audit_payload_error=audit_payload_error,
        venue_stderr=load_optional_text(args.venue_stderr),
        audit_stderr=load_optional_text(args.audit_stderr),
    )
    args.output.write_text(markdown, encoding="utf-8")
    if step_summary_path := resolve_step_summary_path(args.github_step_summary):
        step_summary_path.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
