from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_repo_maturity_nightly
import harness_benchmark


def _write_ready_nightly_fixture(tmp_path: Path) -> tuple[Path, dict[str, object], str]:
    session_id = "20260422t070000z_fixture"
    public_runs_dir = tmp_path / "public_runs" / f"nightly_session_{session_id}"
    public_runs_dir.mkdir(parents=True, exist_ok=True)

    artifacts = {
        "manifest_json": tmp_path / "repo-maturity-nightly.json",
        "summary_md": tmp_path / "repo-maturity-nightly-summary.md",
        "repo_maturity_acceptance_manifest": tmp_path / "repo_maturity_acceptance.json",
        "repo_maturity_acceptance_summary_md": tmp_path / "repo_maturity_acceptance_summary.md",
        "repo_maturity_report_json": tmp_path / "repo_maturity_submission-framework.json",
        "repo_maturity_report_md": tmp_path / "repo_maturity_submission-framework.md",
        "benchmark_matrix_report_json": tmp_path / "harness_benchmark_matrix.json",
        "benchmark_matrix_report_md": tmp_path / "harness_benchmark_matrix.md",
        "benchmark_matrix_manifest": tmp_path / "harness_benchmark_matrix_manifest.json",
        "public_run_check_json": tmp_path / "repo-maturity-public-run-check.json",
        "public_run_report_json": public_runs_dir / "nightly_public_package_sample" / "report.json",
        "public_run_report_md": public_runs_dir / "nightly_public_package_sample" / "report.md",
        "public_run_manifest": public_runs_dir / "nightly_public_package_sample" / "manifest.json",
        "public_run_metadata_json": public_runs_dir / "nightly_public_package_sample" / "run_metadata.json",
        "public_runs_summary_report_json": public_runs_dir / "public_benchmark_runs_summary.json",
        "public_runs_summary_report_md": public_runs_dir / "public_benchmark_runs_summary.md",
        "public_runs_summary_manifest": public_runs_dir / "public_benchmark_runs_summary_manifest.json",
        "public_runs_dir": public_runs_dir,
    }
    for path in artifacts.values():
        if isinstance(path, Path):
            if path.suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.name == "repo-maturity-public-run-check.json":
                    path.write_text(
                        json.dumps({"passed": True, "readiness": "ready"}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                else:
                    path.write_text("{}\n", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)

    public_runs_summary_report = {
        "runs_dir": str(public_runs_dir),
        "readiness": "ready",
        "run_count": 1,
        "ready_run_count": 1,
        "blocked_run_count": 0,
        "invalid_run_count": 0,
        "total_case_count": 2,
        "overall_score": 100.0,
        "latest_run_id": "nightly_public_package_sample",
        "latest_ready_run_id": "nightly_public_package_sample",
        "best_run_id": "nightly_public_package_sample",
        "duplicate_source_count": 0,
        "duplicate_sources": [],
        "runs": [
            {
                "run_id": "nightly_public_package_sample",
                "created_at_utc": "2026-04-22T07:00:00Z",
                "source_type": "package_dir",
                "source_path": "benchmarks/packages/paperwritingbench_style_source_heldout_v1",
                "source_sha256": "abc123",
                "suite_id": "paperwritingbench_style_heldout_v1",
                "python_version": "3.11.2",
                "python_implementation": "CPython",
                "git_commit": "abc123",
                "git_branch": "main",
                "git_dirty": False,
                "readiness": "ready",
                "overall_score": 100.0,
                "case_count": 2,
                "passed_case_count": 2,
                "failed_case_count": 0,
                "run_dir": str(public_runs_dir / "nightly_public_package_sample"),
                "passed": True,
                "errors": [],
                "warnings": [],
                "artifacts": {
                    "report_json": str(artifacts["public_run_report_json"]),
                    "report_md": str(artifacts["public_run_report_md"]),
                    "manifest_json": str(artifacts["public_run_manifest"]),
                    "run_metadata_json": str(artifacts["public_run_metadata_json"]),
                },
            }
        ],
    }
    public_runs_summary_report_path = artifacts["public_runs_summary_report_json"]
    public_runs_summary_report_md_path = artifacts["public_runs_summary_report_md"]
    public_runs_summary_manifest_path = artifacts["public_runs_summary_manifest"]
    assert isinstance(public_runs_summary_report_path, Path)
    assert isinstance(public_runs_summary_report_md_path, Path)
    assert isinstance(public_runs_summary_manifest_path, Path)
    public_runs_summary_report_path.write_text(
        json.dumps(public_runs_summary_report, indent=2) + "\n",
        encoding="utf-8",
    )
    public_runs_summary_report_md_path.write_text(
        harness_benchmark.render_public_benchmark_runs_markdown(public_runs_summary_report),
        encoding="utf-8",
    )
    public_runs_summary_manifest_path.write_text(
        json.dumps(harness_benchmark.build_public_benchmark_runs_manifest(public_runs_summary_report), indent=2)
        + "\n",
        encoding="utf-8",
    )

    step_paths: dict[str, tuple[Path, Path]] = {}
    steps = {}
    for step_id in (
        "repo_maturity_acceptance",
        "repo_maturity_acceptance_check",
        "harness_benchmark_matrix",
        "public_benchmark_run",
        "public_benchmark_run_check",
        "public_benchmark_runs_summary",
    ):
        stdout_path = tmp_path / f"{step_id}.stdout"
        stderr_path = tmp_path / f"{step_id}.stderr"
        stdout_path.write_text("{}\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        step_paths[step_id] = (stdout_path, stderr_path)
        steps[step_id] = {
            "status": "ready",
            "started_at_utc": "2026-04-22T07:00:00Z",
            "finished_at_utc": "2026-04-22T07:00:01Z",
            "duration_seconds": 1.0,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }

    payload: dict[str, object] = {
        "run_id": "repo_maturity_submission-framework_nightly_v1",
        "session_id": session_id,
        "profile": "submission-framework",
        "status": "ready",
        "current_step_id": None,
        "last_completed_step_id": "public_benchmark_runs_summary",
        "last_updated_at_utc": "2026-04-22T07:10:00Z",
        "started_at_utc": "2026-04-22T07:00:00Z",
        "finished_at_utc": "2026-04-22T07:10:00Z",
        "duration_seconds": 600.0,
        "output_dir": str(tmp_path),
        "public_runs_dir": str(public_runs_dir),
        "sample_package_dir": str(tmp_path / "sample_package"),
        "sample_run_id": "nightly_public_package_sample",
        "invocation": "python3 scripts/run_repo_maturity_nightly.py",
        "environment": {
            "controller_python_version": "3.11.2",
            "controller_python_implementation": "CPython",
            "requested_python_executable": "python3",
            "requested_rscript_executable": "Rscript",
            "platform": "Darwin-24.0.0",
            "machine": "arm64",
            "git_commit": "abc123",
            "git_branch": "main",
            "git_dirty": False,
        },
        "steps": steps,
        "artifacts": {key: str(value) for key, value in artifacts.items()},
    }
    nightly_path = artifacts["manifest_json"]
    assert isinstance(nightly_path, Path)
    nightly_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary_markdown = """# Repo Maturity Nightly Summary

- nightly_status: `ready`
- current_step_id: `none`
- last_completed_step_id: `public_benchmark_runs_summary`
- session_id: `20260422t070000z_fixture`
- public_run_artifact_passed: `True`
- public_run_artifact_readiness: `ready`
"""
    summary_path = artifacts["summary_md"]
    assert isinstance(summary_path, Path)
    summary_path.write_text(summary_markdown, encoding="utf-8")

    return nightly_path, payload, summary_markdown


def test_evaluate_nightly_artifact_passes_for_ready_fixture(tmp_path: Path) -> None:
    nightly_path, payload, summary_markdown = _write_ready_nightly_fixture(tmp_path)

    result = check_repo_maturity_nightly.evaluate_nightly_artifact(
        payload,
        nightly_path=nightly_path,
        summary_markdown=summary_markdown,
        repo_root=tmp_path,
    )

    assert result["passed"] is True
    assert result["status"] == "ready"
    assert result["derived_status"] == "ready"


def test_evaluate_nightly_artifact_accepts_running_partial_state(tmp_path: Path) -> None:
    nightly_path = tmp_path / "repo-maturity-nightly.json"
    payload = {
        "run_id": "repo_maturity_submission-framework_nightly_v1",
        "session_id": "20260422t070000z_running",
        "profile": "submission-framework",
        "status": "running",
        "current_step_id": "harness_benchmark_matrix",
        "last_completed_step_id": "repo_maturity_acceptance_check",
        "last_updated_at_utc": "2026-04-22T07:02:00Z",
        "started_at_utc": "2026-04-22T07:00:00Z",
        "finished_at_utc": None,
        "duration_seconds": None,
        "output_dir": ".",
        "public_runs_dir": "public_runs/nightly_session_20260422t070000z_running",
        "sample_package_dir": "sample_package",
        "sample_run_id": "nightly_public_package_sample",
        "invocation": "python3 scripts/run_repo_maturity_nightly.py",
        "environment": {},
        "steps": {
            "repo_maturity_acceptance": {
                "status": "ready",
                "started_at_utc": "2026-04-22T07:00:00Z",
                "finished_at_utc": "2026-04-22T07:00:01Z",
                "duration_seconds": 1.0,
                "stdout_path": "acceptance.stdout",
                "stderr_path": "acceptance.stderr",
            },
            "repo_maturity_acceptance_check": {
                "status": "ready",
                "started_at_utc": "2026-04-22T07:00:01Z",
                "finished_at_utc": "2026-04-22T07:00:02Z",
                "duration_seconds": 1.0,
                "stdout_path": "acceptance-check.stdout",
                "stderr_path": "acceptance-check.stderr",
            },
        },
        "artifacts": {
            "manifest_json": str(nightly_path),
            "summary_md": str(tmp_path / "repo-maturity-nightly-summary.md"),
            "repo_maturity_acceptance_manifest": str(tmp_path / "repo_maturity_acceptance.json"),
            "repo_maturity_acceptance_summary_md": str(tmp_path / "repo_maturity_acceptance_summary.md"),
            "repo_maturity_report_json": str(tmp_path / "repo_maturity_submission-framework.json"),
            "repo_maturity_report_md": str(tmp_path / "repo_maturity_submission-framework.md"),
            "benchmark_matrix_report_json": str(tmp_path / "harness_benchmark_matrix.json"),
            "benchmark_matrix_report_md": str(tmp_path / "harness_benchmark_matrix.md"),
            "benchmark_matrix_manifest": str(tmp_path / "harness_benchmark_matrix_manifest.json"),
            "public_run_check_json": str(tmp_path / "repo-maturity-public-run-check.json"),
            "public_run_report_json": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "nightly_public_package_sample" / "report.json"),
            "public_run_report_md": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "nightly_public_package_sample" / "report.md"),
            "public_run_manifest": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "nightly_public_package_sample" / "manifest.json"),
            "public_run_metadata_json": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "nightly_public_package_sample" / "run_metadata.json"),
            "public_runs_summary_report_json": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "public_benchmark_runs_summary.json"),
            "public_runs_summary_report_md": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "public_benchmark_runs_summary.md"),
            "public_runs_summary_manifest": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running" / "public_benchmark_runs_summary_manifest.json"),
            "public_runs_dir": str(tmp_path / "public_runs" / "nightly_session_20260422t070000z_running"),
        },
    }

    result = check_repo_maturity_nightly.evaluate_nightly_artifact(
        payload,
        nightly_path=nightly_path,
        summary_markdown=None,
        repo_root=tmp_path,
    )

    assert result["passed"] is True
    assert result["status"] == "running"
    assert result["derived_status"] == "running"


def test_evaluate_nightly_artifact_rejects_inconsistent_final_state(tmp_path: Path) -> None:
    nightly_path = tmp_path / "repo-maturity-nightly.json"
    payload = {
        "run_id": "repo_maturity_submission-framework_nightly_v1",
        "session_id": "20260422t070000z_broken",
        "profile": "submission-framework",
        "status": "ready",
        "current_step_id": "harness_benchmark_matrix",
        "last_completed_step_id": "repo_maturity_acceptance_check",
        "last_updated_at_utc": "2026-04-22T07:02:00Z",
        "started_at_utc": "2026-04-22T07:00:00Z",
        "finished_at_utc": None,
        "duration_seconds": None,
        "output_dir": ".",
        "public_runs_dir": "public_runs/nightly_session_20260422t070000z_broken",
        "sample_package_dir": "sample_package",
        "sample_run_id": "nightly_public_package_sample",
        "invocation": "python3 scripts/run_repo_maturity_nightly.py",
        "environment": {},
        "steps": {},
        "artifacts": {},
    }

    result = check_repo_maturity_nightly.evaluate_nightly_artifact(
        payload,
        nightly_path=nightly_path,
        summary_markdown=None,
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("imply `running`" in issue for issue in result["issues"])


def test_evaluate_nightly_artifact_rejects_public_artifacts_outside_public_runs_dir(tmp_path: Path) -> None:
    nightly_path, payload, summary_markdown = _write_ready_nightly_fixture(tmp_path)
    outside_report = tmp_path / "outside_public_run_report.json"
    outside_report.write_text("{}\n", encoding="utf-8")
    payload["artifacts"]["public_run_report_json"] = str(outside_report)

    result = check_repo_maturity_nightly.evaluate_nightly_artifact(
        payload,
        nightly_path=nightly_path,
        summary_markdown=summary_markdown,
        summary_path=tmp_path / "repo-maturity-nightly-summary.md",
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("public_run_report_json" in issue and "public_runs_dir" in issue for issue in result["issues"])


def test_evaluate_nightly_artifact_rejects_inconsistent_public_runs_summary_artifacts(tmp_path: Path) -> None:
    nightly_path, payload, summary_markdown = _write_ready_nightly_fixture(tmp_path)
    summary_report_path = Path(payload["artifacts"]["public_runs_summary_report_json"])
    broken_report = json.loads(summary_report_path.read_text(encoding="utf-8"))
    broken_report["readiness"] = "blocked"
    summary_report_path.write_text(json.dumps(broken_report, indent=2) + "\n", encoding="utf-8")

    result = check_repo_maturity_nightly.evaluate_nightly_artifact(
        payload,
        nightly_path=nightly_path,
        summary_markdown=summary_markdown,
        summary_path=tmp_path / "repo-maturity-nightly-summary.md",
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("public_runs_summary_manifest" in issue for issue in result["issues"])


def test_cli_check_repo_maturity_nightly_reports_ready_fixture(tmp_path: Path) -> None:
    nightly_path, _, _ = _write_ready_nightly_fixture(tmp_path)
    summary_path = tmp_path / "repo-maturity-nightly-summary.md"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity_nightly.py",
            "--nightly-json",
            str(nightly_path),
            "--summary-md",
            str(summary_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["passed"] is True
    assert payload["status"] == "ready"
