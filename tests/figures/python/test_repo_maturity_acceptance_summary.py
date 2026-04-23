from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import repo_maturity_acceptance_summary


def test_render_markdown_includes_steps_and_repo_maturity() -> None:
    markdown = repo_maturity_acceptance_summary.render_markdown(
        acceptance_payload={
            "profile": "submission-framework",
            "venue": "",
            "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
            "status": "ready",
            "current_step_id": None,
            "last_completed_step_id": "repo_maturity",
            "last_updated_at_utc": "2026-04-21T20:05:00Z",
            "started_at_utc": "2026-04-21T20:00:00Z",
            "finished_at_utc": "2026-04-21T20:05:00Z",
            "duration_seconds": 300.0,
            "environment": {
                "controller_python_version": "3.11.2",
                "controller_python_implementation": "CPython",
                "controller_python_executable": "/tmp/python",
                "requested_python_executable": "/tmp/python",
                "requested_rscript_executable": "Rscript",
                "platform": "macOS-13",
                "machine": "arm64",
                "git_commit": "abc123",
                "git_branch": "main",
                "git_dirty": False,
            },
            "steps": {
                "runtime_support": {
                    "status": "ready",
                    "exit_code": 0,
                    "stdout_path": "runtime.stdout",
                    "stderr_path": "runtime.stderr",
                    "duration_seconds": 1.25,
                },
                "scaffold": {
                    "status": "ready",
                    "exit_code": 0,
                    "stdout_path": "scaffold.stdout",
                    "stderr_path": "scaffold.stderr",
                    "duration_seconds": 0.5,
                },
                "python_suite": {
                    "status": "ready",
                    "exit_code": 0,
                    "stdout_path": "pytest.stdout",
                    "stderr_path": "pytest.stderr",
                    "duration_seconds": 120.0,
                },
                "r_figure_suite": {
                    "status": "ready",
                    "exit_code": 0,
                    "stdout_path": "r.stdout",
                    "stderr_path": "r.stderr",
                    "duration_seconds": 30.0,
                },
                "repo_maturity": {
                    "status": "ready",
                    "exit_code": 0,
                    "stdout_path": "maturity.stdout",
                    "stderr_path": "maturity.stderr",
                    "duration_seconds": 0.25,
                },
            },
        },
        report_payload={
            "profile": "submission-framework",
            "readiness": "ready",
            "blocking_issues": [],
            "deferred_submission_blockers": [
                {"gate": "manuscript_scope_gate", "summary": "manuscript scope must be `real`"}
            ],
            "strict_requirement_issues": [],
            "warnings": ["example warning"],
            "package_paths": ["a", "b"],
        },
    )

    assert "Repo Maturity Acceptance Summary" in markdown
    assert "- acceptance_status: `ready`" in markdown
    assert "- current_step_id: `none`" in markdown
    assert "- last_completed_step_id: `repo_maturity`" in markdown
    assert "- duration_seconds: `300.0`" in markdown
    assert "- `python_suite`: `ready` (exit `0`), duration `120.0`s" in markdown
    assert "## Environment" in markdown
    assert "- controller_python_version: `3.11.2`" in markdown
    assert "- readiness: `ready`" in markdown
    assert "- `manuscript_scope_gate`: manuscript scope must be `real`" in markdown


def test_render_markdown_uses_all_for_unscoped_multi_venue_report() -> None:
    markdown = repo_maturity_acceptance_summary.render_markdown(
        acceptance_payload={
            "profile": "submission-framework",
            "venue": "",
            "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
            "steps": {},
        },
        report_payload={
            "profile": "submission-framework",
            "readiness": "ready",
            "blocking_issues": [],
            "deferred_submission_blockers": [],
            "strict_requirement_issues": [],
            "warnings": [],
            "package_paths": [],
            "target_venue_ids": ["neurips", "nature"],
        },
    )

    assert "- venue: `all`" in markdown


def test_render_markdown_reports_running_state_and_current_step() -> None:
    markdown = repo_maturity_acceptance_summary.render_markdown(
        acceptance_payload={
            "profile": "submission-framework",
            "venue": "",
            "acceptance_id": "repo_maturity_submission-framework_acceptance_v1",
            "status": "running",
            "current_step_id": "python_suite",
            "last_completed_step_id": "scaffold",
            "last_updated_at_utc": "2026-04-22T06:00:00Z",
            "steps": {
                "runtime_support": {"status": "ready", "exit_code": 0},
                "scaffold": {"status": "ready", "exit_code": 0},
            },
        },
        report_payload={},
    )

    assert "- acceptance_status: `running`" in markdown
    assert "- current_step_id: `python_suite`" in markdown
    assert "- last_completed_step_id: `scaffold`" in markdown


def test_cli_handles_missing_report_json(tmp_path: Path) -> None:
    acceptance_path = tmp_path / "acceptance.json"
    acceptance_path.write_text(
        json.dumps(
            {
                "acceptance_id": "demo",
                "profile": "submission-framework",
                "venue": "",
                "steps": {},
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "summary.md"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/repo_maturity_acceptance_summary.py",
            "--acceptance-json",
            str(acceptance_path),
            "--report-json",
            str(tmp_path / "missing_report.json"),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.exists()
    assert "payload_error" in output_path.read_text(encoding="utf-8")
    assert "Repo Maturity Acceptance Summary" in completed.stdout
