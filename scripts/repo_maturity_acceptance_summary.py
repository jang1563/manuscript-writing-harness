#!/usr/bin/env python3
"""Render a markdown summary for repo-maturity acceptance artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ACCEPTANCE_STEP_ORDER = (
    "runtime_support",
    "scaffold",
    "python_suite",
    "r_figure_suite",
    "repo_maturity",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--acceptance-json",
        type=Path,
        required=True,
        help="Repo-maturity acceptance artifact JSON path.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        required=True,
        help="Repo-maturity report JSON path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("repo-maturity-acceptance-summary.md"),
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


def resolve_step_summary_path(cli_value: Path | None) -> Path | None:
    if cli_value is not None:
        return cli_value
    env_value = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    return Path(env_value) if env_value else None


def _overall_acceptance_status(acceptance_payload: Any | None) -> str:
    if not isinstance(acceptance_payload, dict):
        return "unknown"
    explicit_status = str(acceptance_payload.get("status", "")).strip()
    if explicit_status:
        return explicit_status
    steps = acceptance_payload.get("steps", {})
    if not isinstance(steps, dict) or not steps:
        return "unknown"
    statuses = [
        str(step.get("status", "unknown"))
        for step in steps.values()
        if isinstance(step, dict)
    ]
    if not statuses:
        return "unknown"
    if all(status == "ready" for status in statuses):
        return "ready"
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    return "unknown"


def _extract_report_payload(report_payload: Any | None) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        return {}
    wrapped = report_payload.get("report")
    if isinstance(wrapped, dict):
        return wrapped
    if "readiness" in report_payload and "profile" in report_payload:
        return report_payload
    return {}


def _render_venue_label(acceptance: dict[str, Any], report: dict[str, Any]) -> str:
    acceptance_venue = str(acceptance.get("venue", "")).strip()
    if acceptance_venue:
        return acceptance_venue
    target_venue_ids = report.get("target_venue_ids", [])
    if isinstance(target_venue_ids, list) and len(target_venue_ids) == 1:
        return str(target_venue_ids[0])
    return "all"


def render_markdown(
    *,
    acceptance_payload: Any | None,
    report_payload: Any | None,
    acceptance_payload_error: str | None = None,
    report_payload_error: str | None = None,
) -> str:
    acceptance = acceptance_payload if isinstance(acceptance_payload, dict) else {}
    report = _extract_report_payload(report_payload)
    lines = [
        "# Repo Maturity Acceptance Summary",
        "",
        f"- profile: `{acceptance.get('profile', report.get('profile', 'unknown'))}`",
        f"- venue: `{_render_venue_label(acceptance, report)}`",
        f"- acceptance_id: `{acceptance.get('acceptance_id', 'unknown')}`",
        f"- acceptance_status: `{_overall_acceptance_status(acceptance_payload)}`",
        f"- current_step_id: `{acceptance.get('current_step_id') or 'none'}`",
        f"- last_completed_step_id: `{acceptance.get('last_completed_step_id') or 'none'}`",
        f"- last_updated_at_utc: `{acceptance.get('last_updated_at_utc') or 'unknown'}`",
        f"- started_at_utc: `{acceptance.get('started_at_utc') or 'unknown'}`",
        f"- finished_at_utc: `{acceptance.get('finished_at_utc') or 'unknown'}`",
        f"- duration_seconds: `{acceptance.get('duration_seconds', 'unknown')}`",
        f"- repo_maturity_readiness: `{report.get('readiness', 'unknown')}`",
        f"- blocking_issue_count: `{len(report.get('blocking_issues', [])) if isinstance(report, dict) else 0}`",
        (
            f"- deferred_submission_blocker_count: "
            f"`{len(report.get('deferred_submission_blockers', [])) if isinstance(report, dict) else 0}`"
        ),
        f"- strict_requirement_issue_count: `{len(report.get('strict_requirement_issues', [])) if isinstance(report, dict) else 0}`",
        "",
    ]

    if acceptance_payload_error:
        lines.extend(["## Acceptance Artifact", "", f"- payload_error: `{acceptance_payload_error}`", ""])
    else:
        lines.extend(["## Acceptance Steps", ""])
        steps = acceptance.get("steps", {}) if isinstance(acceptance, dict) else {}
        for step_id in ACCEPTANCE_STEP_ORDER:
            step = steps.get(step_id)
            if not isinstance(step, dict):
                lines.append(f"- `{step_id}`: `missing`")
                continue
            exit_code = step.get("exit_code")
            exit_suffix = f" (exit `{exit_code}`)" if exit_code not in (None, "") else ""
            duration_suffix = ""
            if step.get("duration_seconds") is not None:
                duration_suffix = f", duration `{step['duration_seconds']}`s"
            lines.append(
                f"- `{step_id}`: `{step.get('status', 'unknown')}`{exit_suffix}{duration_suffix}"
            )
            if step.get("stdout_path"):
                lines.append(f"- `{step_id}_stdout`: `{step['stdout_path']}`")
            if step.get("stderr_path"):
                lines.append(f"- `{step_id}_stderr`: `{step['stderr_path']}`")
        lines.append("")

    environment = acceptance.get("environment", {}) if isinstance(acceptance, dict) else {}
    if isinstance(environment, dict) and environment:
        lines.extend(
            [
                "## Environment",
                "",
                f"- controller_python_version: `{environment.get('controller_python_version', 'unknown')}`",
                (
                    f"- controller_python_implementation: "
                    f"`{environment.get('controller_python_implementation', 'unknown')}`"
                ),
                f"- controller_python_executable: `{environment.get('controller_python_executable', 'unknown')}`",
                f"- requested_python_executable: `{environment.get('requested_python_executable', 'unknown')}`",
                f"- requested_rscript_executable: `{environment.get('requested_rscript_executable', 'unknown')}`",
                f"- platform: `{environment.get('platform', 'unknown')}`",
                f"- machine: `{environment.get('machine', 'unknown')}`",
                f"- git_commit: `{environment.get('git_commit', 'unknown')}`",
                f"- git_branch: `{environment.get('git_branch', 'unknown')}`",
                f"- git_dirty: `{environment.get('git_dirty')}`",
                "",
            ]
        )

    if report_payload_error:
        lines.extend(["## Repo Maturity", "", f"- payload_error: `{report_payload_error}`", ""])
    else:
        lines.extend(
            [
                "## Repo Maturity",
                "",
                f"- readiness: `{report.get('readiness', 'unknown')}`",
                f"- warning_count: `{len(report.get('warnings', [])) if isinstance(report, dict) else 0}`",
                f"- package_path_count: `{len(report.get('package_paths', [])) if isinstance(report, dict) else 0}`",
                "",
            ]
        )
        if isinstance(report, dict) and report.get("blocking_issues"):
            lines.append("### Blocking Issues")
            lines.append("")
            for issue in report["blocking_issues"]:
                lines.append(f"- {issue}")
            lines.append("")
        if isinstance(report, dict) and report.get("deferred_submission_blockers"):
            lines.append("### Deferred Submission Blockers")
            lines.append("")
            for blocker in report["deferred_submission_blockers"]:
                if isinstance(blocker, dict):
                    lines.append(f"- `{blocker.get('gate', 'unknown')}`: {blocker.get('summary', 'unknown')}")
            lines.append("")
        if isinstance(report, dict) and report.get("strict_requirement_issues"):
            lines.append("### Strict Requirement Issues")
            lines.append("")
            for issue in report["strict_requirement_issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_outputs(markdown: str, *, output_path: Path, github_step_summary: Path | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    if github_step_summary is not None:
        github_step_summary.parent.mkdir(parents=True, exist_ok=True)
        with github_step_summary.open("a", encoding="utf-8") as handle:
            handle.write(markdown)


def main() -> int:
    args = parse_args()
    acceptance_payload, acceptance_payload_error = load_json_payload(args.acceptance_json)
    report_payload, report_payload_error = load_json_payload(args.report_json)
    markdown = render_markdown(
        acceptance_payload=acceptance_payload,
        report_payload=report_payload,
        acceptance_payload_error=acceptance_payload_error,
        report_payload_error=report_payload_error,
    )
    write_outputs(
        markdown,
        output_path=args.output,
        github_step_summary=resolve_step_summary_path(args.github_step_summary),
    )
    print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
