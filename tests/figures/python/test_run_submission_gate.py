from __future__ import annotations

import subprocess
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_submission_gate


def test_parse_args_defaults() -> None:
    args = run_submission_gate.parse_args(["--venue", "neurips"])

    assert args.venue == "neurips"
    assert args.output_dir == Path(".")
    assert args.python == sys.executable
    assert args.write_step_summary is False


def test_run_submission_gate_writes_artifacts_and_returns_max_status(tmp_path: Path, monkeypatch) -> None:
    step_summary = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary))

    def fake_run(command: list[str], cwd: Path, check: bool, capture_output: bool, text: bool):
        assert cwd == REPO_ROOT
        assert check is False
        assert capture_output is True
        assert text is True
        if any("check_venue_readiness.py" in part for part in command):
            return subprocess.CompletedProcess(
                command,
                1,
                stdout='{"submission_gate":{"status":"blocked","failed_count":1,"failed_venues":[{"display_name":"NeurIPS","venue":"neurips","verification_status":"needs_submission_confirmation"}]}}\n',
                stderr="venue stderr\n",
            )
        if any("check_pre_submission_audit.py" in part for part in command):
            return subprocess.CompletedProcess(
                command,
                2,
                stdout='{"report":{"audit_id":"pre_submission_audit_neurips_v1","readiness":"ready","bibliography_scope_gate":{"status":"blocked","current_manuscript_scope_status":"unconfirmed"},"submission_gate":{"status":"blocked","failed_count":0,"failed_venues":[]}}}\n',
                stderr="audit stderr\n",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(run_submission_gate.subprocess, "run", fake_run)

    exit_code = run_submission_gate.run_submission_gate(
        "neurips",
        output_dir=tmp_path,
        python_executable="python3",
        write_step_summary=True,
    )

    assert exit_code == 2
    assert (tmp_path / "submission-gate-venue.json").exists()
    assert (tmp_path / "submission-gate-audit.json").exists()
    assert (tmp_path / "submission-gate-venue.exit").read_text(encoding="utf-8").strip() == "1"
    assert (tmp_path / "submission-gate-audit.exit").read_text(encoding="utf-8").strip() == "2"
    summary = (tmp_path / "submission-gate-summary.md").read_text(encoding="utf-8")
    assert "- venue_gate_exit: `1`" in summary
    assert "- audit_gate_exit: `2`" in summary
    assert "- bibliography_scope_gate: `blocked`" in summary
    assert "- stderr: `venue stderr`" in summary
    assert "- stderr: `audit stderr`" in summary
    assert step_summary.read_text(encoding="utf-8") == summary
