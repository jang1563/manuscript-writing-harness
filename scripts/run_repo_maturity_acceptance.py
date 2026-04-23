#!/usr/bin/env python3
"""Run the full repo-maturity acceptance sequence and write a single evidence artifact."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
import platform
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4

from repo_maturity import REPORTS_DIR, MANIFESTS_DIR, _relative, _maturity_stem
from repo_maturity_acceptance_summary import (
    load_json_payload,
    render_markdown as render_acceptance_summary_markdown,
    resolve_step_summary_path,
    write_outputs as write_acceptance_summary_outputs,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
ACCEPTANCE_STEP_IDS = ("runtime_support", "scaffold", "python_suite", "r_figure_suite")
FINAL_ACCEPTANCE_STEP_IDS = (*ACCEPTANCE_STEP_IDS, "repo_maturity")
MIN_SUPPORTED_PYTHON = (3, 10)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_python_executable(repo_root: Path = REPO_ROOT) -> str:
    if tuple(sys.version_info[:2]) >= MIN_SUPPORTED_PYTHON and sys.executable:
        return sys.executable

    candidate_paths = (
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        required=True,
        choices=["demo", "submission-framework", "submission-ready"],
        help="Repo maturity profile to validate with the full acceptance sequence.",
    )
    parser.add_argument("--venue", help="Optional target venue id for scoped maturity evaluation.")
    parser.add_argument(
        "--python",
        default=_default_python_executable(),
        help="Python interpreter to use.",
    )
    parser.add_argument("--rscript", default="Rscript", help="Rscript executable to use.")
    parser.add_argument(
        "--write-step-summary",
        action="store_true",
        help="Write the generated repo-maturity markdown to $GITHUB_STEP_SUMMARY when available.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Pass --strict through to check_repo_maturity.py.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        help="Optional override directory for repo-maturity reports and acceptance logs.",
    )
    parser.add_argument(
        "--manifests-dir",
        type=Path,
        help="Optional override directory for repo-maturity and acceptance manifests.",
    )
    return parser.parse_args(argv)


def _acceptance_logs_dir(profile: str, reports_dir: Path) -> Path:
    return reports_dir / f"{_maturity_stem(profile)}_acceptance"


def _acceptance_manifest_path(profile: str, manifests_dir: Path) -> Path:
    return manifests_dir / f"{_maturity_stem(profile)}_acceptance.json"


def _run_step(
    step_id: str,
    command: list[str],
    *,
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    started = _utc_now()
    started_monotonic = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    finished = _utc_now()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    status = "ready"
    if completed.returncode == 1:
        status = "blocked"
    elif completed.returncode != 0:
        status = "error"
    return {
        "step_id": step_id,
        "status": status,
        "command": command,
        "exit_code": completed.returncode,
        "stdout_path": _relative(stdout_path),
        "stderr_path": _relative(stderr_path),
        "started_at_utc": _utc_iso(started),
        "finished_at_utc": _utc_iso(finished),
        "duration_seconds": round(time.monotonic() - started_monotonic, 3),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp-{uuid4().hex}"
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _base_acceptance_payload(profile: str, venue: str | None) -> dict[str, Any]:
    return {
        "acceptance_id": f"{_maturity_stem(profile)}_acceptance_v1",
        "profile": profile,
        "venue": venue or "",
        "generated_at_utc": _utc_iso(_utc_now()),
        "repo_root": _relative(REPO_ROOT),
        "steps": {},
        "outputs": {},
        "environment": {},
        "status": "running",
        "current_step_id": None,
        "last_completed_step_id": None,
        "last_updated_at_utc": _utc_iso(_utc_now()),
        "started_at_utc": None,
        "finished_at_utc": None,
        "duration_seconds": None,
    }


def _git_output(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def _collect_environment_metadata(
    *,
    repo_root: Path,
    python_executable: str,
    rscript_executable: str,
) -> dict[str, Any]:
    git_commit = _git_output(repo_root, "rev-parse", "HEAD")
    git_branch = _git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    git_status = _git_output(repo_root, "status", "--porcelain")
    system = platform.system()
    release = platform.release()
    platform_label = "-".join(part for part in (system, release) if part) or "unknown"
    return {
        "controller_python_version": platform.python_version(),
        "controller_python_implementation": platform.python_implementation(),
        "controller_python_executable": sys.executable,
        "requested_python_executable": python_executable,
        "requested_rscript_executable": rscript_executable,
        "platform": platform_label,
        "machine": platform.machine(),
        "repo_root": str(repo_root.resolve()),
        "invocation": " ".join(shlex.quote(arg) for arg in sys.argv),
        "git_commit": git_commit,
        "git_branch": git_branch,
        "git_dirty": bool(git_status) if git_commit else None,
    }


def _acceptance_summary_path(profile: str, reports_dir: Path) -> Path:
    return _acceptance_logs_dir(profile, reports_dir) / "summary.md"


def _acceptance_outputs(
    profile: str,
    manifest_path: Path,
    logs_dir: Path,
    *,
    reports_dir: Path,
    manifests_dir: Path,
) -> dict[str, str]:
    return {
        "acceptance_manifest": _relative(manifest_path),
        "acceptance_logs_dir": _relative(logs_dir),
        "report_json": _relative(reports_dir / f"{_maturity_stem(profile)}.json"),
        "report_md": _relative(reports_dir / f"{_maturity_stem(profile)}.md"),
        "report_manifest": _relative(manifests_dir / f"{_maturity_stem(profile)}.json"),
        "acceptance_summary_md": _relative(_acceptance_summary_path(profile, reports_dir)),
    }


def _acceptance_status(payload: dict[str, Any]) -> str:
    current_step_id = payload.get("current_step_id")
    if current_step_id:
        return "running"

    steps = payload.get("steps", {})
    if not isinstance(steps, dict):
        return "running"

    step_statuses = [
        str(step.get("status", "unknown"))
        for step in steps.values()
        if isinstance(step, dict)
    ]
    if len(steps) < len(FINAL_ACCEPTANCE_STEP_IDS):
        return "running"
    if any(status == "error" for status in step_statuses):
        return "error"
    if any(status == "blocked" for status in step_statuses):
        return "blocked"
    if step_statuses and all(status == "ready" for status in step_statuses):
        return "ready"
    return "unknown"


def _refresh_acceptance_state(payload: dict[str, Any]) -> None:
    payload["status"] = _acceptance_status(payload)
    payload["last_updated_at_utc"] = _utc_iso(_utc_now())


def run_repo_maturity_acceptance(
    profile: str,
    *,
    venue: str | None = None,
    python_executable: str | None = None,
    rscript_executable: str = "Rscript",
    write_step_summary: bool = False,
    strict: bool = False,
    reports_dir: Path | None = None,
    manifests_dir: Path | None = None,
) -> int:
    reports_dir = reports_dir or REPORTS_DIR
    manifests_dir = manifests_dir or MANIFESTS_DIR
    python_executable = python_executable or _default_python_executable()
    logs_dir = _acceptance_logs_dir(profile, reports_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = _acceptance_manifest_path(profile, manifests_dir)
    started = _utc_now()
    acceptance_payload = _base_acceptance_payload(profile, venue)
    acceptance_payload["started_at_utc"] = _utc_iso(started)
    acceptance_payload["environment"] = _collect_environment_metadata(
        repo_root=REPO_ROOT,
        python_executable=python_executable,
        rscript_executable=rscript_executable,
    )
    acceptance_payload["outputs"] = _acceptance_outputs(
        profile,
        manifest_path,
        logs_dir,
        reports_dir=reports_dir,
        manifests_dir=manifests_dir,
    )
    _refresh_acceptance_state(acceptance_payload)
    _write_json(manifest_path, acceptance_payload)

    step_commands = {
        "runtime_support": [python_executable, "scripts/check_runtime_support.py"],
        "scaffold": [python_executable, "scripts/check_scaffold.py"],
        "python_suite": [python_executable, "-m", "pytest", "-p", "no:capture", "tests"],
        "r_figure_suite": [rscript_executable, "tests/figures/r/testthat.R"],
    }

    for step_id in ACCEPTANCE_STEP_IDS:
        print(f"[repo-maturity] {step_id}", flush=True)
        acceptance_payload["current_step_id"] = step_id
        _refresh_acceptance_state(acceptance_payload)
        _write_json(manifest_path, acceptance_payload)
        acceptance_payload["steps"][step_id] = _run_step(
            step_id,
            step_commands[step_id],
            stdout_path=logs_dir / f"{step_id}.stdout",
            stderr_path=logs_dir / f"{step_id}.stderr",
        )
        acceptance_payload["current_step_id"] = None
        acceptance_payload["last_completed_step_id"] = step_id
        _refresh_acceptance_state(acceptance_payload)
        _write_json(manifest_path, acceptance_payload)

    print("[repo-maturity] repo_maturity", flush=True)
    repo_maturity_command = [
        python_executable,
        "scripts/check_repo_maturity.py",
        "--profile",
        profile,
        "--acceptance-json",
        str(manifest_path),
        "--write",
        "--json",
    ]
    if venue:
        repo_maturity_command.extend(["--venue", venue])
    if strict:
        repo_maturity_command.append("--strict")
    if reports_dir != REPORTS_DIR:
        repo_maturity_command.extend(["--reports-dir", str(reports_dir)])
    if manifests_dir != MANIFESTS_DIR:
        repo_maturity_command.extend(["--manifests-dir", str(manifests_dir)])

    acceptance_payload["current_step_id"] = "repo_maturity"
    _refresh_acceptance_state(acceptance_payload)
    _write_json(manifest_path, acceptance_payload)
    repo_maturity_step = _run_step(
        "repo_maturity",
        repo_maturity_command,
        stdout_path=logs_dir / "repo_maturity.stdout",
        stderr_path=logs_dir / "repo_maturity.stderr",
    )
    acceptance_payload["steps"]["repo_maturity"] = repo_maturity_step
    acceptance_payload["current_step_id"] = None
    acceptance_payload["last_completed_step_id"] = "repo_maturity"
    _refresh_acceptance_state(acceptance_payload)
    _write_json(manifest_path, acceptance_payload)

    report_json_path = reports_dir / f"{_maturity_stem(profile)}.json"
    acceptance_payload["outputs"] = _acceptance_outputs(
        profile,
        manifest_path,
        logs_dir,
        reports_dir=reports_dir,
        manifests_dir=manifests_dir,
    )
    finished = _utc_now()
    acceptance_payload["finished_at_utc"] = _utc_iso(finished)
    acceptance_payload["duration_seconds"] = round((finished - started).total_seconds(), 3)
    _refresh_acceptance_state(acceptance_payload)
    _write_json(manifest_path, acceptance_payload)
    report_payload, report_payload_error = load_json_payload(report_json_path)
    acceptance_summary_markdown = render_acceptance_summary_markdown(
        acceptance_payload=acceptance_payload,
        report_payload=report_payload,
        report_payload_error=report_payload_error,
    )
    write_acceptance_summary_outputs(
        acceptance_summary_markdown,
        output_path=_acceptance_summary_path(profile, reports_dir),
        github_step_summary=resolve_step_summary_path(None) if write_step_summary else None,
    )

    overall_ready = all(
        acceptance_payload["steps"][step_id]["status"] == "ready"
        for step_id in (*ACCEPTANCE_STEP_IDS, "repo_maturity")
    )
    return 0 if overall_ready else 1


def main() -> int:
    args = parse_args()
    return run_repo_maturity_acceptance(
        args.profile,
        venue=args.venue,
        python_executable=args.python,
        rscript_executable=args.rscript,
        write_step_summary=args.write_step_summary,
        strict=args.strict,
        reports_dir=args.reports_dir or REPORTS_DIR,
        manifests_dir=args.manifests_dir or MANIFESTS_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
