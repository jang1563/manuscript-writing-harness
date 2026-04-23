#!/usr/bin/env python3
"""Run the nightly repo-maturity monitoring sequence and write one summary bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import time
from typing import Any
from uuid import uuid4

from repo_maturity_acceptance_summary import resolve_step_summary_path
from repo_maturity import _maturity_stem


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_PACKAGE_DIR = (
    REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1"
)
MIN_SUPPORTED_PYTHON = (3, 10)
NIGHTLY_STEP_IDS = (
    "repo_maturity_acceptance",
    "repo_maturity_acceptance_check",
    "harness_benchmark_matrix",
    "public_benchmark_run",
    "public_benchmark_run_check",
    "public_benchmark_runs_summary",
)


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


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _default_output_dir(profile: str) -> Path:
    stem = f"repo_maturity_{profile}_nightly"
    return REPO_ROOT / "workflows" / "release" / "reports" / stem


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        default="submission-framework",
        choices=["demo", "submission-framework", "submission-ready"],
        help="Repo maturity profile to exercise in the nightly sequence.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory where nightly artifacts should be written.",
    )
    parser.add_argument(
        "--public-runs-dir",
        type=Path,
        help="Optional directory for ephemeral public benchmark runs.",
    )
    parser.add_argument(
        "--sample-package-dir",
        type=Path,
        default=DEFAULT_SAMPLE_PACKAGE_DIR,
        help="Tracked sample public benchmark package directory to evaluate.",
    )
    parser.add_argument(
        "--sample-run-id",
        default="nightly_public_package_sample",
        help="Run id to use for the nightly sample public benchmark package evaluation.",
    )
    parser.add_argument(
        "--python",
        default=_default_python_executable(),
        help="Python interpreter to use for the nightly commands.",
    )
    parser.add_argument(
        "--rscript",
        default="Rscript",
        help="Rscript executable to use for the repo-maturity acceptance step.",
    )
    parser.add_argument(
        "--write-step-summary",
        action="store_true",
        help="Write the rendered nightly summary to $GITHUB_STEP_SUMMARY when available.",
    )
    return parser.parse_args(argv)


def artifact_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "acceptance_stdout": output_dir / "repo-maturity-acceptance.stdout",
        "acceptance_stderr": output_dir / "repo-maturity-acceptance.stderr",
        "acceptance_exit": output_dir / "repo-maturity-acceptance.exit",
        "acceptance_check_json": output_dir / "repo-maturity-acceptance-check.json",
        "acceptance_check_stderr": output_dir / "repo-maturity-acceptance-check.stderr",
        "acceptance_check_exit": output_dir / "repo-maturity-acceptance-check.exit",
        "benchmark_matrix_json": output_dir / "repo-maturity-benchmark-matrix.json",
        "benchmark_matrix_stderr": output_dir / "repo-maturity-benchmark-matrix.stderr",
        "benchmark_matrix_exit": output_dir / "repo-maturity-benchmark-matrix.exit",
        "public_run_json": output_dir / "repo-maturity-public-run.json",
        "public_run_stderr": output_dir / "repo-maturity-public-run.stderr",
        "public_run_exit": output_dir / "repo-maturity-public-run.exit",
        "public_run_check_json": output_dir / "repo-maturity-public-run-check.json",
        "public_run_check_stderr": output_dir / "repo-maturity-public-run-check.stderr",
        "public_run_check_exit": output_dir / "repo-maturity-public-run-check.exit",
        "public_runs_summary_json": output_dir / "repo-maturity-public-runs-summary.json",
        "public_runs_summary_stderr": output_dir / "repo-maturity-public-runs-summary.stderr",
        "public_runs_summary_exit": output_dir / "repo-maturity-public-runs-summary.exit",
        "summary": output_dir / "repo-maturity-nightly-summary.md",
        "manifest": output_dir / "repo-maturity-nightly.json",
    }


def _acceptance_reports_dir(output_dir: Path) -> Path:
    return output_dir / "repo_maturity_reports"


def _acceptance_manifests_dir(output_dir: Path) -> Path:
    return output_dir / "repo_maturity_manifests"


def _benchmark_reports_dir(output_dir: Path) -> Path:
    return output_dir / "benchmark_reports"


def _benchmark_manifests_dir(output_dir: Path) -> Path:
    return output_dir / "benchmark_manifests"


def _session_public_runs_dir(public_runs_root_dir: Path, session_id: str) -> Path:
    return public_runs_root_dir / f"nightly_session_{session_id}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp-{uuid4().hex}"
    tmp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp-{uuid4().hex}"
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def _step_status(exit_code: int) -> str:
    if exit_code == 0:
        return "ready"
    if exit_code == 1:
        return "blocked"
    return "error"


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


def _refresh_state(payload: dict[str, Any], *, status: str | None = None) -> None:
    if status is not None:
        payload["status"] = status
    payload["last_updated_at_utc"] = _utc_iso(_utc_now())


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
    return {
        "step_id": step_id,
        "status": _step_status(completed.returncode),
        "command": command,
        "exit_code": completed.returncode,
        "stdout_path": _relative(stdout_path),
        "stderr_path": _relative(stderr_path),
        "started_at_utc": _utc_iso(started),
        "finished_at_utc": _utc_iso(finished),
        "duration_seconds": round(time.monotonic() - started_monotonic, 3),
    }


def _load_json_payload(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"{path.name} was not created"
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None, f"{path.name} was empty"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"{path.name} contained invalid JSON: {exc}"


def _coerce_write_path(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return _relative(Path(text))


def _record_optional_artifact(payload: dict[str, Any], key: str, value: Any) -> None:
    coerced = _coerce_write_path(value)
    if coerced is not None:
        payload["artifacts"][key] = coerced


def _setdefault_artifact_path(payload: dict[str, Any], key: str, path: Path) -> None:
    payload["artifacts"].setdefault(key, _relative(path))


def _summary_line(lines: list[str], label: str, value: Any) -> None:
    lines.append(f"- {label}: `{value}`")


def render_summary(
    *,
    payload: dict[str, Any],
    acceptance_check_payload: Any | None,
    acceptance_check_error: str | None,
    benchmark_payload: Any | None,
    benchmark_error: str | None,
    public_run_payload: Any | None,
    public_run_error: str | None,
    public_run_check_payload: Any | None,
    public_run_check_error: str | None,
    public_runs_summary_payload: Any | None,
    public_runs_summary_error: str | None,
) -> str:
    lines = [
        "# Repo Maturity Nightly Summary",
        "",
    ]
    _summary_line(lines, "profile", payload["profile"])
    _summary_line(lines, "nightly_status", payload["status"])
    _summary_line(lines, "current_step_id", payload.get("current_step_id") or "none")
    _summary_line(lines, "last_completed_step_id", payload.get("last_completed_step_id") or "none")
    _summary_line(lines, "session_id", payload.get("session_id", "unknown"))
    _summary_line(lines, "last_updated_at_utc", payload.get("last_updated_at_utc", "unknown"))
    _summary_line(lines, "started_at_utc", payload["started_at_utc"])
    _summary_line(lines, "finished_at_utc", payload["finished_at_utc"])
    _summary_line(lines, "duration_seconds", payload["duration_seconds"])
    _summary_line(lines, "sample_package_dir", payload["sample_package_dir"])
    _summary_line(lines, "public_runs_dir", payload["public_runs_dir"])
    lines.append("")

    lines.append("## Steps")
    lines.append("")
    for step_id in NIGHTLY_STEP_IDS:
        step = payload["steps"][step_id]
        exit_suffix = f" (exit `{step['exit_code']}`)"
        duration_suffix = f", duration `{step['duration_seconds']}`s"
        lines.append(f"- `{step_id}`: `{step['status']}`{exit_suffix}{duration_suffix}")
        lines.append(f"- `{step_id}_stdout`: `{step['stdout_path']}`")
        lines.append(f"- `{step_id}_stderr`: `{step['stderr_path']}`")
    lines.append("")

    lines.append("## Parsed Results")
    lines.append("")
    if acceptance_check_error:
        lines.append(f"- acceptance_check_error: `{acceptance_check_error}`")
    elif isinstance(acceptance_check_payload, dict):
        _summary_line(lines, "acceptance_artifact_passed", acceptance_check_payload.get("passed"))
        _summary_line(lines, "acceptance_artifact_status", acceptance_check_payload.get("status"))
    if benchmark_error:
        lines.append(f"- benchmark_matrix_error: `{benchmark_error}`")
    elif isinstance(benchmark_payload, dict):
        report = benchmark_payload.get("report", {})
        _summary_line(lines, "benchmark_matrix_readiness", report.get("readiness", "unknown"))
        _summary_line(lines, "benchmark_matrix_score", report.get("overall_score", "unknown"))
        _summary_line(
            lines,
            "benchmark_matrix_total_case_count",
            report.get("total_case_count", report.get("case_count", "unknown")),
        )
    if public_run_error:
        lines.append(f"- public_run_error: `{public_run_error}`")
    elif isinstance(public_run_payload, dict):
        report = public_run_payload.get("report", {})
        metadata = public_run_payload.get("run_metadata", {})
        _summary_line(lines, "public_run_id", metadata.get("run_id", "unknown"))
        _summary_line(lines, "public_run_readiness", report.get("readiness", "unknown"))
        _summary_line(lines, "public_run_score", report.get("overall_score", "unknown"))
        _summary_line(lines, "public_run_case_count", report.get("case_count", "unknown"))
    if public_run_check_error:
        lines.append(f"- public_run_check_error: `{public_run_check_error}`")
    elif isinstance(public_run_check_payload, dict):
        _summary_line(lines, "public_run_artifact_passed", public_run_check_payload.get("passed"))
        _summary_line(lines, "public_run_artifact_readiness", public_run_check_payload.get("readiness", "unknown"))
    if public_runs_summary_error:
        lines.append(f"- public_runs_summary_error: `{public_runs_summary_error}`")
    elif isinstance(public_runs_summary_payload, dict):
        report = public_runs_summary_payload.get("report", {})
        _summary_line(lines, "public_runs_summary_readiness", report.get("readiness", "unknown"))
        _summary_line(lines, "public_runs_summary_run_count", report.get("run_count", "unknown"))
        _summary_line(lines, "public_runs_summary_score", report.get("overall_score", "unknown"))
        _summary_line(
            lines,
            "public_runs_summary_total_case_count",
            report.get("total_case_count", "unknown"),
        )
    lines.append("")

    environment = payload.get("environment", {})
    if isinstance(environment, dict) and environment:
        lines.append("## Environment")
        lines.append("")
        _summary_line(lines, "controller_python_version", environment.get("controller_python_version", "unknown"))
        _summary_line(
            lines,
            "controller_python_implementation",
            environment.get("controller_python_implementation", "unknown"),
        )
        _summary_line(lines, "requested_python_executable", environment.get("requested_python_executable", "unknown"))
        _summary_line(lines, "requested_rscript_executable", environment.get("requested_rscript_executable", "unknown"))
        _summary_line(lines, "platform", environment.get("platform", "unknown"))
        _summary_line(lines, "machine", environment.get("machine", "unknown"))
        _summary_line(lines, "git_commit", environment.get("git_commit", "unknown"))
        _summary_line(lines, "git_branch", environment.get("git_branch", "unknown"))
        _summary_line(lines, "git_dirty", environment.get("git_dirty"))
        lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    for key, value in payload["artifacts"].items():
        _summary_line(lines, key, value)
    lines.append("")

    return "\n".join(lines)


def run_repo_maturity_nightly(
    *,
    profile: str,
    output_dir: Path,
    public_runs_dir: Path,
    sample_package_dir: Path,
    sample_run_id: str,
    python_executable: str | None,
    rscript_executable: str,
    write_step_summary: bool = False,
) -> int:
    python_executable = python_executable or _default_python_executable()
    started = _utc_now()
    started_monotonic = time.monotonic()
    session_id = started.strftime("%Y%m%dt%H%M%SZ").lower() + f"_{uuid4().hex[:8]}"

    output_dir.mkdir(parents=True, exist_ok=True)
    public_runs_root_dir = public_runs_dir
    public_runs_dir = _session_public_runs_dir(public_runs_root_dir, session_id)
    public_runs_dir.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(output_dir)
    acceptance_reports_dir = _acceptance_reports_dir(output_dir)
    acceptance_manifests_dir = _acceptance_manifests_dir(output_dir)
    benchmark_reports_dir = _benchmark_reports_dir(output_dir)
    benchmark_manifests_dir = _benchmark_manifests_dir(output_dir)
    acceptance_stem = _maturity_stem(profile)
    acceptance_manifest_path = acceptance_manifests_dir / f"{acceptance_stem}_acceptance.json"
    acceptance_report_json_path = acceptance_reports_dir / f"{acceptance_stem}.json"
    acceptance_report_md_path = acceptance_reports_dir / f"{acceptance_stem}.md"
    acceptance_summary_path = acceptance_reports_dir / f"{acceptance_stem}_acceptance" / "summary.md"
    benchmark_report_json_path = benchmark_reports_dir / "harness_benchmark_matrix.json"
    benchmark_report_md_path = benchmark_reports_dir / "harness_benchmark_matrix.md"
    benchmark_manifest_path = benchmark_manifests_dir / "harness_benchmark_matrix.json"

    payload: dict[str, Any] = {
        "run_id": f"repo_maturity_{profile}_nightly_v1",
        "session_id": session_id,
        "profile": profile,
        "started_at_utc": _utc_iso(started),
        "finished_at_utc": None,
        "duration_seconds": None,
        "status": "running",
        "current_step_id": None,
        "last_completed_step_id": None,
        "last_updated_at_utc": _utc_iso(started),
        "output_dir": _relative(output_dir),
        "public_runs_dir": _relative(public_runs_dir),
        "sample_package_dir": _relative(sample_package_dir.resolve()),
        "sample_run_id": sample_run_id,
        "invocation": " ".join(shlex.quote(arg) for arg in sys.argv),
        "environment": _collect_environment_metadata(
            repo_root=REPO_ROOT,
            python_executable=python_executable,
            rscript_executable=rscript_executable,
        ),
        "steps": {},
        "artifacts": {
            "manifest_json": _relative(paths["manifest"]),
            "summary_md": _relative(paths["summary"]),
            "repo_maturity_acceptance_manifest": _relative(acceptance_manifest_path),
            "repo_maturity_acceptance_summary_md": _relative(acceptance_summary_path),
            "repo_maturity_report_json": _relative(acceptance_report_json_path),
            "repo_maturity_report_md": _relative(acceptance_report_md_path),
            "benchmark_matrix_report_json": _relative(benchmark_report_json_path),
            "benchmark_matrix_report_md": _relative(benchmark_report_md_path),
            "benchmark_matrix_manifest": _relative(benchmark_manifest_path),
            "public_run_check_json": _relative(paths["public_run_check_json"]),
            "public_runs_dir": _relative(public_runs_dir),
        },
    }
    _write_json(paths["manifest"], payload)

    acceptance_command = [
        python_executable,
        "scripts/run_repo_maturity_acceptance.py",
        "--profile",
        profile,
        "--python",
        python_executable,
        "--rscript",
        rscript_executable,
        "--strict",
        "--reports-dir",
        str(acceptance_reports_dir.resolve()),
        "--manifests-dir",
        str(acceptance_manifests_dir.resolve()),
    ]
    acceptance_check_command = [
        python_executable,
        "scripts/check_repo_maturity_acceptance.py",
        "--acceptance-json",
        str(acceptance_manifest_path.resolve()),
        "--report-json",
        str(acceptance_report_json_path.resolve()),
        "--summary-md",
        str(acceptance_summary_path.resolve()),
        "--json",
    ]
    benchmark_matrix_command = [
        python_executable,
        "scripts/check_harness_benchmark_matrix.py",
        "--write",
        "--json",
        "--strict",
        "--reports-dir",
        str(benchmark_reports_dir.resolve()),
        "--manifests-dir",
        str(benchmark_manifests_dir.resolve()),
    ]
    public_run_command = [
        python_executable,
        "scripts/run_public_benchmark_package.py",
        "--package-dir",
        str(sample_package_dir.resolve()),
        "--output-dir",
        str(public_runs_dir.resolve()),
        "--run-id",
        sample_run_id,
        "--force",
        "--json",
        "--strict",
    ]
    public_run_check_command = [
        python_executable,
        "scripts/check_public_benchmark_run.py",
        "--run-dir",
        str((public_runs_dir / sample_run_id).resolve()),
        "--json",
        "--strict",
    ]
    public_runs_summary_command = [
        python_executable,
        "scripts/check_public_benchmark_runs.py",
        "--runs-dir",
        str(public_runs_dir.resolve()),
        "--write",
        "--json",
        "--strict",
    ]

    step_specs = (
        ("repo_maturity_acceptance", acceptance_command, paths["acceptance_stdout"], paths["acceptance_stderr"], paths["acceptance_exit"]),
        ("repo_maturity_acceptance_check", acceptance_check_command, paths["acceptance_check_json"], paths["acceptance_check_stderr"], paths["acceptance_check_exit"]),
        ("harness_benchmark_matrix", benchmark_matrix_command, paths["benchmark_matrix_json"], paths["benchmark_matrix_stderr"], paths["benchmark_matrix_exit"]),
        ("public_benchmark_run", public_run_command, paths["public_run_json"], paths["public_run_stderr"], paths["public_run_exit"]),
        ("public_benchmark_run_check", public_run_check_command, paths["public_run_check_json"], paths["public_run_check_stderr"], paths["public_run_check_exit"]),
        ("public_benchmark_runs_summary", public_runs_summary_command, paths["public_runs_summary_json"], paths["public_runs_summary_stderr"], paths["public_runs_summary_exit"]),
    )

    exit_codes: list[int] = []
    for step_id, command, stdout_path, stderr_path, exit_path in step_specs:
        print(f"[repo-maturity-nightly] {step_id}", flush=True)
        payload["current_step_id"] = step_id
        _refresh_state(payload, status="running")
        _write_json(paths["manifest"], payload)
        step = _run_step(step_id, command, stdout_path=stdout_path, stderr_path=stderr_path)
        payload["steps"][step_id] = step
        payload["current_step_id"] = None
        payload["last_completed_step_id"] = step_id
        _refresh_state(payload, status="running")
        exit_path.write_text(f"{step['exit_code']}\n", encoding="utf-8")
        exit_codes.append(int(step["exit_code"]))
        _write_json(paths["manifest"], payload)

    acceptance_check_payload, acceptance_check_error = _load_json_payload(paths["acceptance_check_json"])
    benchmark_payload, benchmark_error = _load_json_payload(paths["benchmark_matrix_json"])
    public_run_payload, public_run_error = _load_json_payload(paths["public_run_json"])
    public_run_check_payload, public_run_check_error = _load_json_payload(paths["public_run_check_json"])
    public_runs_summary_payload, public_runs_summary_error = _load_json_payload(paths["public_runs_summary_json"])

    if isinstance(public_run_payload, dict):
        public_run_writes = public_run_payload.get("writes", {})
        if isinstance(public_run_writes, dict):
            _record_optional_artifact(payload, "public_run_report_json", public_run_writes.get("report_json"))
            _record_optional_artifact(payload, "public_run_report_md", public_run_writes.get("report_md"))
            _record_optional_artifact(payload, "public_run_manifest", public_run_writes.get("manifest"))
            _record_optional_artifact(payload, "public_run_metadata_json", public_run_writes.get("run_metadata"))
        public_run_metadata = public_run_payload.get("run_metadata", {})
        public_run_id = (
            public_run_metadata.get("run_id")
            if isinstance(public_run_metadata, dict)
            else None
        ) or sample_run_id
        if isinstance(public_run_id, str) and public_run_id.strip():
            public_run_dir = public_runs_dir / public_run_id.strip()
            _setdefault_artifact_path(payload, "public_run_report_json", public_run_dir / "report.json")
            _setdefault_artifact_path(payload, "public_run_report_md", public_run_dir / "report.md")
            _setdefault_artifact_path(payload, "public_run_manifest", public_run_dir / "manifest.json")
            _setdefault_artifact_path(
                payload,
                "public_run_metadata_json",
                public_run_dir / "run_metadata.json",
            )
    if isinstance(public_runs_summary_payload, dict):
        public_summary_writes = public_runs_summary_payload.get("writes", {})
        if isinstance(public_summary_writes, dict):
            _record_optional_artifact(
                payload,
                "public_runs_summary_report_json",
                public_summary_writes.get("report_json"),
            )
            _record_optional_artifact(
                payload,
                "public_runs_summary_report_md",
                public_summary_writes.get("report_md"),
            )
            _record_optional_artifact(
                payload,
                "public_runs_summary_manifest",
                public_summary_writes.get("manifest"),
            )
        _setdefault_artifact_path(
            payload,
            "public_runs_summary_report_json",
            public_runs_dir / "public_benchmark_runs_summary.json",
        )
        _setdefault_artifact_path(
            payload,
            "public_runs_summary_report_md",
            public_runs_dir / "public_benchmark_runs_summary.md",
        )
        _setdefault_artifact_path(
            payload,
            "public_runs_summary_manifest",
            public_runs_dir / "public_benchmark_runs_summary_manifest.json",
        )

    finished = _utc_now()
    payload["finished_at_utc"] = _utc_iso(finished)
    payload["duration_seconds"] = round(time.monotonic() - started_monotonic, 3)
    if any(code > 1 for code in exit_codes):
        _refresh_state(payload, status="error")
    elif any(code == 1 for code in exit_codes):
        _refresh_state(payload, status="blocked")
    else:
        _refresh_state(payload, status="ready")

    summary_markdown = render_summary(
        payload=payload,
        acceptance_check_payload=acceptance_check_payload,
        acceptance_check_error=acceptance_check_error,
        benchmark_payload=benchmark_payload,
        benchmark_error=benchmark_error,
        public_run_payload=public_run_payload,
        public_run_error=public_run_error,
        public_run_check_payload=public_run_check_payload,
        public_run_check_error=public_run_check_error,
        public_runs_summary_payload=public_runs_summary_payload,
        public_runs_summary_error=public_runs_summary_error,
    )
    _write_text(paths["summary"], summary_markdown)
    _write_json(paths["manifest"], payload)

    if write_step_summary and (step_summary_path := resolve_step_summary_path(None)):
        _write_text(step_summary_path, summary_markdown)

    print(summary_markdown, end="" if summary_markdown.endswith("\n") else "\n")
    return max(exit_codes) if exit_codes else 0


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir or _default_output_dir(args.profile)
    public_runs_dir = args.public_runs_dir or (output_dir / "public_runs")
    return run_repo_maturity_nightly(
        profile=args.profile,
        output_dir=output_dir,
        public_runs_dir=public_runs_dir,
        sample_package_dir=args.sample_package_dir,
        sample_run_id=args.sample_run_id,
        python_executable=args.python,
        rscript_executable=args.rscript,
        write_step_summary=args.write_step_summary,
    )


if __name__ == "__main__":
    raise SystemExit(main())
