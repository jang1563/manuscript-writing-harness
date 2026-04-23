#!/usr/bin/env python3
"""Validate repo-maturity nightly artifacts and their companion outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from figures_common import REPO_ROOT
from harness_benchmark import (
    build_public_benchmark_runs_manifest,
    render_public_benchmark_runs_markdown,
)
from repo_maturity_acceptance_summary import load_json_payload
from run_repo_maturity_nightly import NIGHTLY_STEP_IDS


ALLOWED_NIGHTLY_STATUSES = {"running", "ready", "blocked", "error", "unknown"}
ALLOWED_STEP_STATUSES = {"ready", "blocked", "error"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="submission-framework",
        choices=["demo", "submission-framework", "submission-ready"],
        help="Repo maturity profile whose nightly artifact should be checked.",
    )
    parser.add_argument(
        "--nightly-json",
        type=Path,
        help="Optional explicit nightly artifact JSON path.",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        help="Optional explicit nightly summary markdown path.",
    )
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


def _default_nightly_path(profile: str) -> Path:
    return (
        REPO_ROOT
        / "workflows"
        / "release"
        / "reports"
        / f"repo_maturity_{profile}_nightly"
        / "repo-maturity-nightly.json"
    )


def _default_summary_path(profile: str) -> Path:
    return (
        REPO_ROOT
        / "workflows"
        / "release"
        / "reports"
        / f"repo_maturity_{profile}_nightly"
        / "repo-maturity-nightly-summary.md"
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


def _load_nightly_payload(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    payload, error = load_json_payload(path)
    if error is not None:
        return None, error
    if not isinstance(payload, dict):
        return None, f"{path.name} must contain a JSON object"
    return payload, None


def _derive_nightly_status(payload: dict[str, Any]) -> str:
    current_step_id = payload.get("current_step_id")
    if current_step_id:
        return "running"
    steps = payload.get("steps", {})
    if not isinstance(steps, dict):
        return "unknown"
    present_steps = [steps[step_id] for step_id in NIGHTLY_STEP_IDS if step_id in steps]
    if len(present_steps) < len(NIGHTLY_STEP_IDS):
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


def evaluate_nightly_artifact(
    nightly_payload: dict[str, Any],
    *,
    nightly_path: Path,
    summary_markdown: str | None = None,
    summary_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []

    profile = str(nightly_payload.get("profile", "")).strip()
    session_id = str(nightly_payload.get("session_id", "")).strip()
    explicit_status = str(nightly_payload.get("status", "")).strip()
    derived_status = _derive_nightly_status(nightly_payload)
    current_step_id = nightly_payload.get("current_step_id")
    last_completed_step_id = nightly_payload.get("last_completed_step_id")
    steps = nightly_payload.get("steps", {})

    if not profile:
        issues.append("`profile` is required")
    if not session_id:
        issues.append("`session_id` is required")
    if explicit_status not in ALLOWED_NIGHTLY_STATUSES:
        issues.append("`status` must be one of running, ready, blocked, error, or unknown")
    elif explicit_status != derived_status:
        issues.append(f"`status` is `{explicit_status}` but the artifact contents imply `{derived_status}`")

    if not isinstance(steps, dict):
        issues.append("`steps` must be an object")
        steps = {}

    for step_id in steps:
        if step_id not in NIGHTLY_STEP_IDS:
            issues.append(f"unexpected step id `{step_id}`")

    step_log_paths: list[tuple[str, str, Path]] = []
    for step_id in NIGHTLY_STEP_IDS:
        if step_id not in steps:
            if explicit_status in {"ready", "blocked", "error"}:
                issues.append(f"final nightly artifact is missing step `{step_id}`")
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
            elif str(raw_path or "").strip():
                candidate = _resolve_from_repo_root(str(raw_path), repo_root)
                step_log_paths.append((step_id, path_field, candidate))
                if explicit_status in {"ready", "blocked", "error"} and not candidate.exists():
                    issues.append(f"step `{step_id}` expects `{path_field}` to exist")

    if current_step_id is not None and current_step_id not in NIGHTLY_STEP_IDS:
        issues.append("`current_step_id` must name a known nightly step or be null")
    if last_completed_step_id is not None and last_completed_step_id not in NIGHTLY_STEP_IDS:
        issues.append("`last_completed_step_id` must name a known nightly step or be null")

    if explicit_status in {"ready", "blocked", "error"}:
        if current_step_id is not None:
            issues.append("final nightly artifacts must set `current_step_id` to null")
        if last_completed_step_id != NIGHTLY_STEP_IDS[-1]:
            issues.append(
                "final nightly artifacts must set `last_completed_step_id` to `public_benchmark_runs_summary`"
            )
        if _parse_iso_timestamp(nightly_payload.get("finished_at_utc"), "finished_at_utc", issues) is None:
            issues.append("final nightly artifacts must include `finished_at_utc`")
        duration = nightly_payload.get("duration_seconds")
        if duration is None:
            issues.append("final nightly artifacts must include `duration_seconds`")
        else:
            try:
                if float(duration) < 0:
                    issues.append("`duration_seconds` must be non-negative")
            except (TypeError, ValueError):
                issues.append("`duration_seconds` must be numeric")
    elif explicit_status == "running":
        if nightly_payload.get("finished_at_utc") not in (None, ""):
            issues.append("running nightly artifacts must not set `finished_at_utc`")
        if nightly_payload.get("duration_seconds") not in (None, ""):
            issues.append("running nightly artifacts must not set `duration_seconds`")

    _parse_iso_timestamp(nightly_payload.get("started_at_utc"), "started_at_utc", issues)
    _parse_iso_timestamp(nightly_payload.get("last_updated_at_utc"), "last_updated_at_utc", issues)

    environment = nightly_payload.get("environment", {})
    if not isinstance(environment, dict):
        issues.append("`environment` must be an object")
        environment = {}
    required_environment_keys = (
        "controller_python_version",
        "controller_python_implementation",
        "requested_python_executable",
        "requested_rscript_executable",
        "platform",
        "machine",
    )
    if explicit_status in {"ready", "blocked", "error"}:
        for key in required_environment_keys:
            if not str(environment.get(key, "")).strip():
                issues.append(f"`environment.{key}` is required")

    artifacts = nightly_payload.get("artifacts", {})
    if not isinstance(artifacts, dict):
        issues.append("`artifacts` must be an object")
        artifacts = {}
    required_artifacts = (
        "manifest_json",
        "summary_md",
        "repo_maturity_acceptance_manifest",
        "repo_maturity_acceptance_summary_md",
        "repo_maturity_report_json",
        "repo_maturity_report_md",
        "benchmark_matrix_report_json",
        "benchmark_matrix_report_md",
        "benchmark_matrix_manifest",
        "public_run_check_json",
        "public_run_report_json",
        "public_run_report_md",
        "public_run_manifest",
        "public_run_metadata_json",
        "public_runs_summary_report_json",
        "public_runs_summary_report_md",
        "public_runs_summary_manifest",
        "public_runs_dir",
    )
    for key in required_artifacts:
        if not str(artifacts.get(key, "")).strip():
            issues.append(f"`artifacts.{key}` is required")

    output_dir_raw = str(nightly_payload.get("output_dir", "")).strip()
    if not output_dir_raw:
        issues.append("`output_dir` is required")
    resolved_output_dir = _resolve_from_repo_root(output_dir_raw, repo_root) if output_dir_raw else None
    resolved_artifact_paths = {
        key: _resolve_from_repo_root(str(value), repo_root)
        for key, value in artifacts.items()
        if isinstance(value, str) and value.strip()
    }
    if "manifest_json" in resolved_artifact_paths:
        if resolved_artifact_paths["manifest_json"].resolve() != nightly_path.resolve():
            issues.append("`artifacts.manifest_json` does not match the checked manifest path")
    if summary_path is not None and "summary_md" in resolved_artifact_paths:
        if resolved_artifact_paths["summary_md"].resolve() != summary_path.resolve():
            issues.append("`artifacts.summary_md` does not match the checked summary path")
    if explicit_status in {"ready", "blocked", "error"}:
        for key in required_artifacts:
            path = resolved_artifact_paths.get(key)
            if path is None or not path.exists():
                issues.append(f"final nightly artifact expects `{key}` to exist")

    resolved_public_runs_dir = resolved_artifact_paths.get("public_runs_dir")
    if session_id and resolved_public_runs_dir is not None:
        expected_session_dir_name = f"nightly_session_{session_id}"
        if resolved_public_runs_dir.name != expected_session_dir_name:
            issues.append("`artifacts.public_runs_dir` does not match `session_id`")
    if resolved_output_dir is not None and resolved_public_runs_dir is not None:
        if not _is_within(resolved_public_runs_dir, resolved_output_dir):
            issues.append("`artifacts.public_runs_dir` must live under `output_dir`")
    if resolved_output_dir is not None:
        expected_output_artifacts = (
            "manifest_json",
            "summary_md",
            "repo_maturity_acceptance_manifest",
            "repo_maturity_acceptance_summary_md",
            "repo_maturity_report_json",
            "repo_maturity_report_md",
            "benchmark_matrix_report_json",
            "benchmark_matrix_report_md",
            "benchmark_matrix_manifest",
            "public_run_check_json",
        )
        for key in expected_output_artifacts:
            path = resolved_artifact_paths.get(key)
            if path is not None and not _is_within(path, resolved_output_dir):
                issues.append(f"`artifacts.{key}` must live under `output_dir`")
        for step_id, path_field, candidate in step_log_paths:
            if not _is_within(candidate, resolved_output_dir):
                issues.append(f"step `{step_id}` has `{path_field}` outside `output_dir`")
    if resolved_public_runs_dir is not None:
        public_run_artifacts = (
            "public_run_report_json",
            "public_run_report_md",
            "public_run_manifest",
            "public_run_metadata_json",
            "public_runs_summary_report_json",
            "public_runs_summary_report_md",
            "public_runs_summary_manifest",
        )
        for key in public_run_artifacts:
            path = resolved_artifact_paths.get(key)
            if path is not None and not _is_within(path, resolved_public_runs_dir):
                issues.append(f"`artifacts.{key}` must live under `artifacts.public_runs_dir`")

    public_run_check_path = resolved_artifact_paths.get("public_run_check_json")
    if explicit_status in {"ready", "blocked", "error"} and public_run_check_path is not None:
        public_run_check_payload, public_run_check_error = load_json_payload(public_run_check_path)
        if public_run_check_error is not None:
            issues.append(f"`artifacts.public_run_check_json` is invalid: {public_run_check_error}")
        elif not isinstance(public_run_check_payload, dict):
            issues.append("`artifacts.public_run_check_json` must contain a JSON object")
        else:
            if not public_run_check_payload.get("passed", False):
                issues.append("`artifacts.public_run_check_json` must report `passed: true`")
            if str(public_run_check_payload.get("readiness", "")).strip() != "ready":
                issues.append("`artifacts.public_run_check_json` must report `readiness: ready`")

    public_runs_summary_report_path = resolved_artifact_paths.get("public_runs_summary_report_json")
    public_runs_summary_manifest_path = resolved_artifact_paths.get("public_runs_summary_manifest")
    public_runs_summary_md_path = resolved_artifact_paths.get("public_runs_summary_report_md")
    if (
        explicit_status in {"ready", "blocked", "error"}
        and public_runs_summary_report_path is not None
        and public_runs_summary_manifest_path is not None
        and public_runs_summary_md_path is not None
    ):
        public_runs_summary_report_payload, public_runs_summary_report_error = load_json_payload(
            public_runs_summary_report_path
        )
        if public_runs_summary_report_error is not None:
            issues.append(
                "`artifacts.public_runs_summary_report_json` is invalid: "
                f"{public_runs_summary_report_error}"
            )
        elif not isinstance(public_runs_summary_report_payload, dict):
            issues.append("`artifacts.public_runs_summary_report_json` must contain a JSON object")
        else:
            report_runs_dir_raw = str(public_runs_summary_report_payload.get("runs_dir", "")).strip()
            if not report_runs_dir_raw:
                issues.append("`artifacts.public_runs_summary_report_json` must include `runs_dir`")
            elif resolved_public_runs_dir is not None:
                resolved_report_runs_dir = _resolve_from_repo_root(report_runs_dir_raw, repo_root)
                if resolved_report_runs_dir != resolved_public_runs_dir.resolve():
                    issues.append(
                        "`artifacts.public_runs_summary_report_json.runs_dir` does not match "
                        "`artifacts.public_runs_dir`"
                    )

            public_runs_summary_manifest_payload, public_runs_summary_manifest_error = load_json_payload(
                public_runs_summary_manifest_path
            )
            if public_runs_summary_manifest_error is not None:
                issues.append(
                    "`artifacts.public_runs_summary_manifest` is invalid: "
                    f"{public_runs_summary_manifest_error}"
                )
            elif not isinstance(public_runs_summary_manifest_payload, dict):
                issues.append("`artifacts.public_runs_summary_manifest` must contain a JSON object")
            else:
                expected_public_runs_manifest = build_public_benchmark_runs_manifest(
                    public_runs_summary_report_payload
                )
                if public_runs_summary_manifest_payload != expected_public_runs_manifest:
                    issues.append(
                        "`artifacts.public_runs_summary_manifest` does not match the public-runs summary report"
                    )

            public_runs_summary_markdown = public_runs_summary_md_path.read_text(encoding="utf-8")
            expected_public_runs_markdown = render_public_benchmark_runs_markdown(
                public_runs_summary_report_payload
            )
            if public_runs_summary_markdown != expected_public_runs_markdown:
                issues.append(
                    "`artifacts.public_runs_summary_report_md` does not match the public-runs summary report"
                )

    if summary_markdown is not None:
        expected_snippets = [
            f"- nightly_status: `{explicit_status}`",
            f"- current_step_id: `{current_step_id or 'none'}`",
            f"- last_completed_step_id: `{last_completed_step_id or 'none'}`",
            f"- session_id: `{session_id or 'unknown'}`",
        ]
        if explicit_status in {"ready", "blocked", "error"}:
            expected_snippets.extend(
                [
                    "- public_run_artifact_passed: `True`",
                    "- public_run_artifact_readiness: `ready`",
                ]
            )
        for snippet in expected_snippets:
            if snippet not in summary_markdown:
                issues.append(f"nightly summary is missing expected line: {snippet}")
    elif explicit_status in {"ready", "blocked", "error"}:
        issues.append("final nightly artifact is missing the companion nightly summary")

    return {
        "nightly_path": _relative(nightly_path, repo_root),
        "profile": profile,
        "status": explicit_status or derived_status,
        "derived_status": derived_status,
        "current_step_id": current_step_id,
        "last_completed_step_id": last_completed_step_id,
        "session_id": session_id,
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        "Repo Maturity Nightly Check",
        "",
        f"Artifact: {result['nightly_path']}",
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
    nightly_path = (args.nightly_json or _default_nightly_path(args.profile)).resolve()
    summary_path = (args.summary_md or _default_summary_path(args.profile)).resolve()

    nightly_payload, nightly_error = _load_nightly_payload(nightly_path)
    if nightly_error is not None:
        if args.json:
            print(json.dumps({"error": nightly_error}, indent=2))
        else:
            print(f"Error: {nightly_error}", file=sys.stderr)
        return 2

    summary_markdown = summary_path.read_text(encoding="utf-8") if summary_path.exists() else None
    result = evaluate_nightly_artifact(
        nightly_payload,
        nightly_path=nightly_path,
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
