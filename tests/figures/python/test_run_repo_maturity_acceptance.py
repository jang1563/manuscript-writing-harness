from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import repo_maturity
import run_repo_maturity_acceptance


def test_parse_args_defaults() -> None:
    args = run_repo_maturity_acceptance.parse_args(["--profile", "submission-framework"])
    assert args.profile == "submission-framework"
    assert args.python == run_repo_maturity_acceptance._default_python_executable()
    assert args.rscript == "Rscript"
    assert args.strict is False


def test_default_python_executable_prefers_repo_venv_when_controller_python_is_unsupported(
    tmp_path: Path, monkeypatch
) -> None:
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(run_repo_maturity_acceptance, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(run_repo_maturity_acceptance.sys, "version_info", (3, 8, 8))
    monkeypatch.setattr(run_repo_maturity_acceptance.sys, "executable", "/usr/bin/python3")

    assert run_repo_maturity_acceptance._default_python_executable(tmp_path) == str(venv_python)


def test_run_repo_maturity_acceptance_writes_manifest_and_repo_step(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_repo_maturity_acceptance, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(run_repo_maturity_acceptance, "MANIFESTS_DIR", tmp_path / "manifests")

    commands: list[list[str]] = []
    report_json_path = tmp_path / "reports" / "repo_maturity_submission-framework.json"

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        commands.append(list(command))
        if "check_repo_maturity.py" in " ".join(command):
            report_json_path.parent.mkdir(parents=True, exist_ok=True)
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
                        "artifact_path": "repo_maturity_submission-framework_acceptance.json",
                        "steps": {
                            "runtime_support": {"status": "ready"},
                            "scaffold": {"status": "ready"},
                            "python_suite": {"status": "ready"},
                            "r_figure_suite": {"status": "ready"},
                        },
                    },
                },
            }
            report_json_path.write_text(
                json.dumps(report_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            (tmp_path / "reports" / "repo_maturity_submission-framework.md").write_text(
                repo_maturity.render_repo_maturity_markdown(report_payload),
                encoding="utf-8",
            )
            (tmp_path / "manifests" / "repo_maturity_submission-framework.json").write_text(
                json.dumps(repo_maturity.build_repo_maturity_manifest(report_payload), indent=2) + "\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(command, 0, stdout='{"ok": true}\n', stderr="")

    monkeypatch.setattr(run_repo_maturity_acceptance.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_acceptance.run_repo_maturity_acceptance(
        "submission-framework",
        strict=True,
    )

    manifest_path = tmp_path / "manifests" / "repo_maturity_submission-framework_acceptance.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_path = tmp_path / "reports" / "repo_maturity_submission-framework_acceptance" / "summary.md"

    assert exit_code == 0
    assert payload["profile"] == "submission-framework"
    assert payload["environment"]["controller_python_version"]
    assert (
        payload["environment"]["requested_python_executable"]
        == run_repo_maturity_acceptance._default_python_executable()
    )
    assert payload["environment"]["requested_rscript_executable"] == "Rscript"
    assert payload["status"] == "ready"
    assert payload["current_step_id"] is None
    assert payload["last_completed_step_id"] == "repo_maturity"
    assert payload["last_updated_at_utc"]
    assert payload["started_at_utc"]
    assert payload["finished_at_utc"]
    assert payload["duration_seconds"] is not None
    assert report_json_path.exists()
    assert summary_path.exists()
    assert payload["outputs"]["acceptance_manifest"].endswith(
        "repo_maturity_submission-framework_acceptance.json"
    )
    assert payload["outputs"]["report_json"].endswith(
        "repo_maturity_submission-framework.json"
    )
    assert payload["outputs"]["report_manifest"].endswith(
        "repo_maturity_submission-framework.json"
    )
    assert payload["outputs"]["acceptance_summary_md"].endswith(
        "repo_maturity_submission-framework_acceptance/summary.md"
    )
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "Repo Maturity Acceptance Summary" in summary_text
    assert "- acceptance_status: `ready`" in summary_text
    assert "- current_step_id: `none`" in summary_text
    assert "- last_completed_step_id: `repo_maturity`" in summary_text
    assert "- finished_at_utc: `" in summary_text
    assert "- duration_seconds: `" in summary_text
    assert set(payload["steps"]) == {
        "runtime_support",
        "scaffold",
        "python_suite",
        "r_figure_suite",
        "repo_maturity",
    }
    assert payload["steps"]["runtime_support"]["started_at_utc"]
    assert payload["steps"]["runtime_support"]["finished_at_utc"]
    assert payload["steps"]["runtime_support"]["duration_seconds"] is not None
    assert payload["steps"]["repo_maturity"]["status"] == "ready"
    assert any("scripts/check_repo_maturity.py" in " ".join(command) for command in commands)


def test_run_repo_maturity_acceptance_returns_nonzero_when_step_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_repo_maturity_acceptance, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(run_repo_maturity_acceptance, "MANIFESTS_DIR", tmp_path / "manifests")

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        joined = " ".join(command)
        if "pytest" in joined or "check_repo_maturity.py" in joined:
            return subprocess.CompletedProcess(command, 1, stdout="{}", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(run_repo_maturity_acceptance.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_acceptance.run_repo_maturity_acceptance(
        "submission-framework",
        strict=True,
    )

    manifest_path = tmp_path / "manifests" / "repo_maturity_submission-framework_acceptance.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["status"] == "blocked"
    assert payload["current_step_id"] is None
    assert payload["last_completed_step_id"] == "repo_maturity"
    assert payload["steps"]["python_suite"]["status"] == "blocked"
    assert payload["steps"]["repo_maturity"]["status"] == "blocked"


def test_run_repo_maturity_acceptance_marks_nonstandard_exit_as_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(run_repo_maturity_acceptance, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(run_repo_maturity_acceptance, "MANIFESTS_DIR", tmp_path / "manifests")

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        joined = " ".join(command)
        if "check_repo_maturity.py" in joined:
            return subprocess.CompletedProcess(command, 2, stdout="{}", stderr="bad input")
        return subprocess.CompletedProcess(command, 0, stdout="{}", stderr="")

    monkeypatch.setattr(run_repo_maturity_acceptance.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_acceptance.run_repo_maturity_acceptance(
        "submission-framework",
        strict=True,
    )

    manifest_path = tmp_path / "manifests" / "repo_maturity_submission-framework_acceptance.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["status"] == "error"
    assert payload["current_step_id"] is None
    assert payload["last_completed_step_id"] == "repo_maturity"
    assert payload["steps"]["repo_maturity"]["status"] == "error"


def test_run_repo_maturity_acceptance_writes_step_summary_when_requested(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(run_repo_maturity_acceptance, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(run_repo_maturity_acceptance, "MANIFESTS_DIR", tmp_path / "manifests")

    step_summary_path = tmp_path / "github_step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary_path))

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout='{"report": {"profile": "submission-framework", "readiness": "ready", "blocking_issues": [], "deferred_submission_blockers": [], "strict_requirement_issues": [], "warnings": [], "package_paths": []}}\n', stderr="")

    monkeypatch.setattr(run_repo_maturity_acceptance.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_acceptance.run_repo_maturity_acceptance(
        "submission-framework",
        write_step_summary=True,
        strict=True,
    )

    assert exit_code == 0
    summary_text = step_summary_path.read_text(encoding="utf-8")
    assert "Repo Maturity Acceptance Summary" in summary_text
    assert "`python_suite`: `ready`" in summary_text
