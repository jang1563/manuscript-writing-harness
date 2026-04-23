#!/usr/bin/env python3
"""Validate repo-maturity acceptance artifacts and their companion outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from figures_common import REPO_ROOT
from repo_maturity import build_repo_maturity_manifest, render_repo_maturity_markdown
from repo_maturity_acceptance_summary import load_json_payload
from run_repo_maturity_acceptance import FINAL_ACCEPTANCE_STEP_IDS


ALLOWED_ACCEPTANCE_STATUSES = {"running", "ready", "blocked", "error", "unknown"}
ALLOWED_STEP_STATUSES = {"ready", "blocked", "error"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="submission-framework",
        choices=["demo", "submission-framework", "submission-ready"],
        help="Repo maturity profile whose acceptance artifact should be checked.",
    )
    parser.add_argument("--acceptance-json", type=Path, help="Optional explicit acceptance artifact path.")
    parser.add_argument("--report-json", type=Path, help="Optional explicit repo-maturity report JSON path.")
    parser.add_argument("--summary-md", type=Path, help="Optional explicit acceptance summary markdown path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text.")
    return parser.parse_args()


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _resolve_from_repo_root(value: str, repo_root: Path) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path.resolve()
    return (repo_root / raw_path).resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _default_acceptance_path(profile: str) -> Path:
    return REPO_ROOT / "workflows" / "release" / "manifests" / f"repo_maturity_{profile}_acceptance.json"


def _default_report_path(profile: str) -> Path:
    return REPO_ROOT / "workflows" / "release" / "reports" / f"repo_maturity_{profile}.json"


def _default_summary_path(profile: str) -> Path:
    return (
        REPO_ROOT
        / "workflows"
        / "release"
        / "reports"
        / f"repo_maturity_{profile}_acceptance"
        / "summary.md"
    )


def _parse_iso_timestamp(raw: Any, field_name: str, issues: list[str]) -> str | None:
    if raw in (None, ""):
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        from datetime import datetime

        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"`{field_name}` must be an ISO-8601 timestamp")
        return None
    return text


def _load_acceptance_payload(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    payload, error = load_json_payload(path)
    if error is not None:
        return None, error
    if not isinstance(payload, dict):
        return None, f"{path.name} must contain a JSON object"
    return payload, None


def _extract_report_payload(report_payload: Any | None) -> dict[str, Any]:
    if not isinstance(report_payload, dict):
        return {}
    wrapped = report_payload.get("report")
    if isinstance(wrapped, dict):
        return wrapped
    if "readiness" in report_payload and "profile" in report_payload:
        return report_payload
    return {}


def _derive_acceptance_status(payload: dict[str, Any]) -> str:
    current_step_id = payload.get("current_step_id")
    if current_step_id:
        return "running"
    steps = payload.get("steps", {})
    if not isinstance(steps, dict):
        return "unknown"
    present_steps = [steps[step_id] for step_id in FINAL_ACCEPTANCE_STEP_IDS if step_id in steps]
    if len(present_steps) < len(FINAL_ACCEPTANCE_STEP_IDS):
        return "running"
    statuses = [
        str(step.get("status", "unknown"))
        for step in present_steps
        if isinstance(step, dict)
    ]
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if statuses and all(status == "ready" for status in statuses):
        return "ready"
    return "unknown"


def evaluate_acceptance_artifact(
    acceptance_payload: dict[str, Any],
    *,
    acceptance_path: Path,
    report_payload: dict[str, Any] | None = None,
    report_path: Path | None = None,
    summary_markdown: str | None = None,
    summary_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    profile = str(acceptance_payload.get("profile", "")).strip()
    explicit_status = str(acceptance_payload.get("status", "")).strip()
    derived_status = _derive_acceptance_status(acceptance_payload)
    current_step_id = acceptance_payload.get("current_step_id")
    last_completed_step_id = acceptance_payload.get("last_completed_step_id")
    steps = acceptance_payload.get("steps", {})

    if not profile:
        issues.append("`profile` is required")
    if explicit_status not in ALLOWED_ACCEPTANCE_STATUSES:
        issues.append(
            "`status` must be one of running, ready, blocked, error, or unknown"
        )
    elif explicit_status != derived_status:
        issues.append(
            f"`status` is `{explicit_status}` but the artifact contents imply `{derived_status}`"
        )

    if not isinstance(steps, dict):
        issues.append("`steps` must be an object")
        steps = {}

    for step_id in steps:
        if step_id not in FINAL_ACCEPTANCE_STEP_IDS:
            issues.append(f"unexpected step id `{step_id}`")

    step_log_paths: list[tuple[str, str, Path]] = []
    for step_id in FINAL_ACCEPTANCE_STEP_IDS:
        if step_id not in steps:
            if explicit_status in {"ready", "blocked", "error"}:
                issues.append(f"final acceptance artifact is missing step `{step_id}`")
            continue
        step = steps[step_id]
        if not isinstance(step, dict):
            issues.append(f"step `{step_id}` must be an object")
            continue
        step_status = str(step.get("status", "")).strip()
        if step_status not in ALLOWED_STEP_STATUSES:
            issues.append(f"step `{step_id}` has invalid status `{step_status}`")
        _parse_iso_timestamp(step.get("started_at_utc"), f"steps.{step_id}.started_at_utc", issues)
        _parse_iso_timestamp(step.get("finished_at_utc"), f"steps.{step_id}.finished_at_utc", issues)
        duration = step.get("duration_seconds")
        if duration is None:
            issues.append(f"step `{step_id}` is missing `duration_seconds`")
        else:
            try:
                if float(duration) < 0:
                    issues.append(f"step `{step_id}` has negative `duration_seconds`")
            except (TypeError, ValueError):
                issues.append(f"step `{step_id}` has invalid `duration_seconds`")
        for path_field in ("stdout_path", "stderr_path"):
            raw_path = step.get(path_field)
            if explicit_status in {"ready", "blocked", "error"} and not str(raw_path or "").strip():
                issues.append(f"step `{step_id}` is missing `{path_field}`")
                continue
            if not str(raw_path or "").strip():
                continue
            candidate = _resolve_from_repo_root(str(raw_path), repo_root)
            step_log_paths.append((step_id, path_field, candidate))
            if explicit_status in {"ready", "blocked", "error"} and not candidate.exists():
                issues.append(f"step `{step_id}` expects `{path_field}` to exist")

    if current_step_id is not None and current_step_id not in FINAL_ACCEPTANCE_STEP_IDS:
        issues.append("`current_step_id` must name a known acceptance step or be null")
    if last_completed_step_id is not None and last_completed_step_id not in FINAL_ACCEPTANCE_STEP_IDS:
        issues.append("`last_completed_step_id` must name a known acceptance step or be null")

    if explicit_status in {"ready", "blocked", "error"}:
        if current_step_id is not None:
            issues.append("final acceptance artifacts must set `current_step_id` to null")
        if last_completed_step_id != "repo_maturity":
            issues.append("final acceptance artifacts must set `last_completed_step_id` to `repo_maturity`")
        if _parse_iso_timestamp(acceptance_payload.get("finished_at_utc"), "finished_at_utc", issues) is None:
            issues.append("final acceptance artifacts must include `finished_at_utc`")
        duration = acceptance_payload.get("duration_seconds")
        if duration is None:
            issues.append("final acceptance artifacts must include `duration_seconds`")
        else:
            try:
                if float(duration) < 0:
                    issues.append("`duration_seconds` must be non-negative")
            except (TypeError, ValueError):
                issues.append("`duration_seconds` must be numeric")
    elif explicit_status == "running":
        if acceptance_payload.get("finished_at_utc") not in (None, ""):
            issues.append("running acceptance artifacts must not set `finished_at_utc`")
        if acceptance_payload.get("duration_seconds") not in (None, ""):
            issues.append("running acceptance artifacts must not set `duration_seconds`")

    _parse_iso_timestamp(acceptance_payload.get("generated_at_utc"), "generated_at_utc", issues)
    _parse_iso_timestamp(acceptance_payload.get("started_at_utc"), "started_at_utc", issues)
    _parse_iso_timestamp(acceptance_payload.get("last_updated_at_utc"), "last_updated_at_utc", issues)

    outputs = acceptance_payload.get("outputs", {})
    if not isinstance(outputs, dict):
        issues.append("`outputs` must be an object")
        outputs = {}
    required_outputs = (
        "acceptance_manifest",
        "acceptance_logs_dir",
        "report_json",
        "report_md",
        "report_manifest",
        "acceptance_summary_md",
    )
    for key in required_outputs:
        if not str(outputs.get(key, "")).strip():
            issues.append(f"`outputs.{key}` is required")

    resolved_output_paths = {
        key: _resolve_from_repo_root(str(value), repo_root)
        for key, value in outputs.items()
        if isinstance(value, str) and value.strip()
    }
    if "acceptance_manifest" in resolved_output_paths:
        if resolved_output_paths["acceptance_manifest"].resolve() != acceptance_path.resolve():
            issues.append("`outputs.acceptance_manifest` does not match the checked manifest path")
    logs_dir = resolved_output_paths.get("acceptance_logs_dir")
    if explicit_status in {"ready", "blocked", "error"}:
        for key in ("acceptance_logs_dir", "report_json", "report_md", "report_manifest", "acceptance_summary_md"):
            path = resolved_output_paths.get(key)
            if path is None or not path.exists():
                issues.append(f"final acceptance artifact expects `{key}` to exist")
        if logs_dir is not None and not logs_dir.is_dir():
            issues.append("`outputs.acceptance_logs_dir` must point to a directory")

    if logs_dir is not None:
        for step_id, path_field, candidate in step_log_paths:
            if not _is_within(candidate, logs_dir):
                issues.append(
                    f"step `{step_id}` has `{path_field}` outside `outputs.acceptance_logs_dir`"
                )
        summary_output = resolved_output_paths.get("acceptance_summary_md")
        if summary_output is not None and not _is_within(summary_output, logs_dir):
            issues.append("`outputs.acceptance_summary_md` must live under `outputs.acceptance_logs_dir`")

    if report_path is not None:
        expected_report_path = resolved_output_paths.get("report_json")
        if expected_report_path is not None and expected_report_path.resolve() != report_path.resolve():
            issues.append("`outputs.report_json` does not match the checked report path")
    if summary_path is not None:
        expected_summary_path = resolved_output_paths.get("acceptance_summary_md")
        if expected_summary_path is not None and expected_summary_path.resolve() != summary_path.resolve():
            issues.append("`outputs.acceptance_summary_md` does not match the checked summary path")

    normalized_report_payload = _extract_report_payload(report_payload)
    if report_payload is not None:
        report_profile = str(normalized_report_payload.get("profile", "")).strip()
        if report_profile and profile and report_profile != profile:
            issues.append("acceptance artifact profile does not match report profile")
        if explicit_status in {"ready", "blocked", "error"} and "readiness" not in normalized_report_payload:
            issues.append("repo maturity report is missing `readiness`")
        report_manifest_path = resolved_output_paths.get("report_manifest")
        if report_manifest_path is not None and normalized_report_payload:
            report_manifest_payload, report_manifest_error = load_json_payload(report_manifest_path)
            if report_manifest_error is not None:
                issues.append(f"`outputs.report_manifest` is invalid: {report_manifest_error}")
            elif not isinstance(report_manifest_payload, dict):
                issues.append("`outputs.report_manifest` must contain a JSON object")
            else:
                expected_report_manifest = build_repo_maturity_manifest(normalized_report_payload)
                if report_manifest_payload != expected_report_manifest:
                    issues.append("`outputs.report_manifest` does not match the repo-maturity report")
        report_markdown_path = resolved_output_paths.get("report_md")
        if report_markdown_path is not None and normalized_report_payload:
            report_markdown = report_markdown_path.read_text(encoding="utf-8")
            expected_report_markdown = render_repo_maturity_markdown(normalized_report_payload)
            if report_markdown != expected_report_markdown:
                issues.append("`outputs.report_md` does not match the repo-maturity report")
    elif explicit_status in {"ready", "blocked", "error"}:
        issues.append("final acceptance artifact is missing the companion repo-maturity report")

    if summary_markdown is not None:
        expected_snippets = [
            f"- acceptance_status: `{explicit_status}`",
            f"- current_step_id: `{current_step_id or 'none'}`",
            f"- last_completed_step_id: `{last_completed_step_id or 'none'}`",
        ]
        for snippet in expected_snippets:
            if snippet not in summary_markdown:
                issues.append(f"acceptance summary is missing expected line: {snippet}")
    elif explicit_status in {"ready", "blocked", "error"}:
        issues.append("final acceptance artifact is missing the companion acceptance summary")

    return {
        "acceptance_path": _relative(acceptance_path, repo_root),
        "profile": profile,
        "status": explicit_status or derived_status,
        "derived_status": derived_status,
        "current_step_id": current_step_id,
        "last_completed_step_id": last_completed_step_id,
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        "Repo Maturity Acceptance Check",
        "",
        f"Artifact: {result['acceptance_path']}",
        f"Profile: {result['profile'] or 'unknown'}",
        f"Status: {result['status']}",
        f"Derived status: {result['derived_status']}",
        f"Passed: {'yes' if result['passed'] else 'no'}",
        f"Current step: {result['current_step_id'] or 'none'}",
        f"Last completed step: {result['last_completed_step_id'] or 'none'}",
    ]
    if result["issues"]:
        lines.append("Issues:")
        for issue in result["issues"]:
            lines.append(f"  - {issue}")
    else:
        lines.append("Issues: none")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    acceptance_path = (args.acceptance_json or _default_acceptance_path(args.profile)).resolve()
    report_path = (args.report_json or _default_report_path(args.profile)).resolve()
    summary_path = (args.summary_md or _default_summary_path(args.profile)).resolve()

    acceptance_payload, acceptance_error = _load_acceptance_payload(acceptance_path)
    if acceptance_error is not None:
        if args.json:
            print(json.dumps({"error": acceptance_error}, indent=2))
        else:
            print(f"Error: {acceptance_error}", file=sys.stderr)
        return 2

    report_payload, _ = load_json_payload(report_path)
    report_payload = report_payload if isinstance(report_payload, dict) else None
    summary_markdown = summary_path.read_text(encoding="utf-8") if summary_path.exists() else None

    result = evaluate_acceptance_artifact(
        acceptance_payload,
        acceptance_path=acceptance_path,
        report_payload=report_payload,
        report_path=report_path,
        summary_markdown=summary_markdown,
        summary_path=summary_path,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result), end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
