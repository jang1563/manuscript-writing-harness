from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_repo_maturity_acceptance
import repo_maturity


def _write_ready_acceptance_fixture(tmp_path: Path) -> tuple[Path, dict[str, object], dict[str, object], str]:
    logs_dir = tmp_path / "acceptance_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    report_path = tmp_path / "repo_maturity_submission-framework.json"
    report_md_path = tmp_path / "repo_maturity_submission-framework.md"
    report_manifest_path = tmp_path / "repo_maturity_submission-framework.manifest.json"
    report_payload = {
        "profile": "submission-framework",
        "readiness": "ready",
        "blocking_issues": [],
        "deferred_submission_blockers": [],
        "strict_requirement_issues": [],
        "warnings": [],
        "package_paths": [],
        "target_venue_ids": [],
        "evidence": {
            "manuscript_scope": {"status": "provisional"},
            "pre_submission_audit": {
                "readiness": "ready",
                "manuscript_scope_gate": {"status": "blocked"},
                "bibliography_scope_gate": {"status": "blocked"},
                "submission_gate": {"status": "blocked"},
            },
            "release_bundle": {"readiness": "ready"},
            "project_release": {"readiness": "provisional"},
            "project_handoff": {"readiness": "provisional"},
            "benchmark_matrix": {"readiness": "ready"},
            "reference_integrity": {"readiness": "ready"},
            "external_validation": {
                "artifact_path": str(tmp_path / "repo_maturity_submission-framework_acceptance.json"),
                "steps": {
                    "runtime_support": {"status": "ready"},
                    "scaffold": {"status": "ready"},
                    "python_suite": {"status": "ready"},
                    "r_figure_suite": {"status": "ready"},
                },
            },
        },
    }
    report_path.write_text(json.dumps(report_payload, indent=2) + "\n", encoding="utf-8")
    report_md_path.write_text(repo_maturity.render_repo_maturity_markdown(report_payload), encoding="utf-8")
    report_manifest_path.write_text(
        json.dumps(repo_maturity.build_repo_maturity_manifest(report_payload), indent=2) + "\n",
        encoding="utf-8",
    )

    summary_path = logs_dir / "summary.md"
    summary_markdown = """# Repo Maturity Acceptance Summary

- acceptance_status: `ready`
- current_step_id: `none`
- last_completed_step_id: `repo_maturity`
"""
    summary_path.write_text(summary_markdown, encoding="utf-8")

    acceptance_path = tmp_path / "repo_maturity_submission-framework_acceptance.json"
    acceptance_payload: dict[str, object] = {
        "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
        "profile": "submission-framework",
        "venue": "",
        "generated_at_utc": "2026-04-22T06:00:00Z",
        "repo_root": ".",
        "status": "ready",
        "current_step_id": None,
        "last_completed_step_id": "repo_maturity",
        "last_updated_at_utc": "2026-04-22T06:10:00Z",
        "started_at_utc": "2026-04-22T06:00:00Z",
        "finished_at_utc": "2026-04-22T06:10:00Z",
        "duration_seconds": 600.0,
        "environment": {},
        "outputs": {
            "acceptance_manifest": str(acceptance_path),
            "acceptance_logs_dir": str(logs_dir),
            "report_json": str(report_path),
            "report_md": str(report_md_path),
            "report_manifest": str(report_manifest_path),
            "acceptance_summary_md": str(summary_path),
        },
        "steps": {
            step_id: {
                "status": "ready",
                "started_at_utc": "2026-04-22T06:00:00Z",
                "finished_at_utc": "2026-04-22T06:00:01Z",
                "duration_seconds": 1.0,
                "stdout_path": str((logs_dir / f"{step_id}.stdout").resolve()),
                "stderr_path": str((logs_dir / f"{step_id}.stderr").resolve()),
            }
            for step_id in (
                "runtime_support",
                "scaffold",
                "python_suite",
                "r_figure_suite",
                "repo_maturity",
            )
        },
    }
    for step in acceptance_payload["steps"].values():
        stdout_path = Path(step["stdout_path"])
        stderr_path = Path(step["stderr_path"])
        stdout_path.write_text("{}\n", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
    acceptance_path.write_text(json.dumps(acceptance_payload, indent=2) + "\n", encoding="utf-8")
    return acceptance_path, acceptance_payload, report_payload, summary_markdown


def test_evaluate_acceptance_artifact_passes_for_ready_fixture(tmp_path: Path) -> None:
    acceptance_path, acceptance_payload, report_payload, summary_markdown = _write_ready_acceptance_fixture(
        tmp_path
    )

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        acceptance_payload,
        acceptance_path=acceptance_path,
        report_payload=report_payload,
        summary_markdown=summary_markdown,
        repo_root=tmp_path,
    )

    assert result["passed"] is True
    assert result["status"] == "ready"
    assert result["derived_status"] == "ready"


def test_evaluate_acceptance_artifact_accepts_running_partial_state(tmp_path: Path) -> None:
    acceptance_path = tmp_path / "acceptance.json"
    payload = {
        "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
        "profile": "submission-framework",
        "venue": "",
        "generated_at_utc": "2026-04-22T06:00:00Z",
        "repo_root": ".",
        "status": "running",
        "current_step_id": "python_suite",
        "last_completed_step_id": "scaffold",
        "last_updated_at_utc": "2026-04-22T06:02:00Z",
        "started_at_utc": "2026-04-22T06:00:00Z",
        "finished_at_utc": None,
        "duration_seconds": None,
        "environment": {},
        "outputs": {
            "acceptance_manifest": str(acceptance_path.relative_to(tmp_path)),
            "acceptance_logs_dir": "logs",
            "report_json": "report.json",
            "report_md": "report.md",
            "report_manifest": "report.manifest.json",
            "acceptance_summary_md": "logs/summary.md",
        },
        "steps": {
            "runtime_support": {
                "status": "ready",
                "started_at_utc": "2026-04-22T06:00:00Z",
                "finished_at_utc": "2026-04-22T06:00:01Z",
                "duration_seconds": 1.0,
            },
            "scaffold": {
                "status": "ready",
                "started_at_utc": "2026-04-22T06:00:01Z",
                "finished_at_utc": "2026-04-22T06:00:03Z",
                "duration_seconds": 2.0,
            },
        },
    }

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        payload,
        acceptance_path=acceptance_path,
        report_payload=None,
        summary_markdown=None,
        repo_root=tmp_path,
    )

    assert result["passed"] is True
    assert result["status"] == "running"
    assert result["derived_status"] == "running"


def test_evaluate_acceptance_artifact_rejects_inconsistent_final_state(tmp_path: Path) -> None:
    acceptance_path = tmp_path / "acceptance.json"
    payload = {
        "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
        "profile": "submission-framework",
        "venue": "",
        "generated_at_utc": "2026-04-22T06:00:00Z",
        "repo_root": ".",
        "status": "ready",
        "current_step_id": "python_suite",
        "last_completed_step_id": "scaffold",
        "last_updated_at_utc": "2026-04-22T06:02:00Z",
        "started_at_utc": "2026-04-22T06:00:00Z",
        "finished_at_utc": None,
        "duration_seconds": None,
        "environment": {},
        "outputs": {},
        "steps": {},
    }

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        payload,
        acceptance_path=acceptance_path,
        report_payload=None,
        summary_markdown=None,
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("imply `running`" in issue for issue in result["issues"])


def test_evaluate_acceptance_artifact_rejects_missing_step_logs(tmp_path: Path) -> None:
    acceptance_path, acceptance_payload, report_payload, summary_markdown = _write_ready_acceptance_fixture(
        tmp_path
    )
    step = acceptance_payload["steps"]["runtime_support"]
    assert isinstance(step, dict)
    step.pop("stdout_path", None)

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        acceptance_payload,
        acceptance_path=acceptance_path,
        report_payload=report_payload,
        report_path=tmp_path / "repo_maturity_submission-framework.json",
        summary_markdown=summary_markdown,
        summary_path=tmp_path / "summary.md",
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("runtime_support" in issue and "stdout_path" in issue for issue in result["issues"])


def test_evaluate_acceptance_artifact_rejects_step_logs_outside_logs_dir(tmp_path: Path) -> None:
    acceptance_path, acceptance_payload, report_payload, summary_markdown = _write_ready_acceptance_fixture(
        tmp_path
    )
    outside_log = tmp_path / "outside.stdout"
    outside_log.write_text("{}\n", encoding="utf-8")
    step = acceptance_payload["steps"]["runtime_support"]
    assert isinstance(step, dict)
    step["stdout_path"] = str(outside_log)

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        acceptance_payload,
        acceptance_path=acceptance_path,
        report_payload=report_payload,
        report_path=tmp_path / "repo_maturity_submission-framework.json",
        summary_markdown=summary_markdown,
        summary_path=tmp_path / "summary.md",
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("outside `outputs.acceptance_logs_dir`" in issue for issue in result["issues"])


def test_evaluate_acceptance_artifact_rejects_inconsistent_report_manifest(tmp_path: Path) -> None:
    acceptance_path, acceptance_payload, report_payload, summary_markdown = _write_ready_acceptance_fixture(
        tmp_path
    )
    report_manifest_path = tmp_path / "repo_maturity_submission-framework.manifest.json"
    broken_manifest = json.loads(report_manifest_path.read_text(encoding="utf-8"))
    broken_manifest["readiness"] = "blocked"
    report_manifest_path.write_text(json.dumps(broken_manifest, indent=2) + "\n", encoding="utf-8")

    result = check_repo_maturity_acceptance.evaluate_acceptance_artifact(
        acceptance_payload,
        acceptance_path=acceptance_path,
        report_payload=report_payload,
        report_path=tmp_path / "repo_maturity_submission-framework.json",
        summary_markdown=summary_markdown,
        summary_path=tmp_path / "acceptance_logs" / "summary.md",
        repo_root=tmp_path,
    )

    assert result["passed"] is False
    assert any("report_manifest" in issue for issue in result["issues"])


def test_cli_check_repo_maturity_acceptance_reports_ready_fixture(tmp_path: Path) -> None:
    acceptance_path, _, _, _ = _write_ready_acceptance_fixture(tmp_path)
    report_path = tmp_path / "repo_maturity_submission-framework.json"
    summary_path = tmp_path / "acceptance_logs" / "summary.md"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity_acceptance.py",
            "--acceptance-json",
            str(acceptance_path),
            "--report-json",
            str(report_path),
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
