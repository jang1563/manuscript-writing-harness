from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_repo_maturity_nightly


def test_parse_args_defaults() -> None:
    args = run_repo_maturity_nightly.parse_args([])

    assert args.profile == "submission-framework"
    assert args.output_dir is None
    assert args.public_runs_dir is None
    assert args.sample_package_dir == run_repo_maturity_nightly.DEFAULT_SAMPLE_PACKAGE_DIR
    assert args.sample_run_id == "nightly_public_package_sample"
    assert args.python == run_repo_maturity_nightly._default_python_executable()
    assert args.rscript == "Rscript"
    assert args.write_step_summary is False


def test_default_python_executable_prefers_repo_venv_when_controller_python_is_unsupported(
    tmp_path: Path, monkeypatch
) -> None:
    venv_python = tmp_path / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.write_text("", encoding="utf-8")

    monkeypatch.setattr(run_repo_maturity_nightly, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(run_repo_maturity_nightly.sys, "version_info", (3, 8, 8))
    monkeypatch.setattr(run_repo_maturity_nightly.sys, "executable", "/usr/bin/python3")

    assert run_repo_maturity_nightly._default_python_executable(tmp_path) == str(venv_python)


def test_run_repo_maturity_nightly_writes_artifacts_and_summary(
    tmp_path: Path, monkeypatch
) -> None:
    step_summary = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary))
    commands: list[list[str]] = []
    monkeypatch.setattr(
        run_repo_maturity_nightly,
        "_collect_environment_metadata",
        lambda **_: {
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
    )

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        assert cwd == REPO_ROOT
        assert check is False
        assert capture_output is True
        assert text is True
        commands.append(list(command))
        joined = " ".join(command)
        if "run_repo_maturity_acceptance.py" in joined:
            return subprocess.CompletedProcess(command, 0, stdout="acceptance ok\n", stderr="")
        if "check_repo_maturity_acceptance.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"passed": True, "status": "ready"}, indent=2) + "\n",
                stderr="",
            )
        if "check_harness_benchmark_matrix.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    json.dumps(
                        {
                            "report": {
                                "readiness": "ready",
                                "overall_score": 100.0,
                                "total_case_count": 9,
                            }
                        },
                        indent=2,
                    )
                    + "\n"
                ),
                stderr="",
            )
        if "run_public_benchmark_package.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    json.dumps(
                        {
                            "report": {
                                "readiness": "ready",
                                "overall_score": 100.0,
                                "case_count": 2,
                            },
                            "run_metadata": {
                                "run_id": "nightly_public_package_sample",
                            },
                        },
                        indent=2,
                    )
                    + "\n"
                ),
                stderr="",
            )
        if "check_public_benchmark_run.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    json.dumps(
                        {
                            "run_id": "nightly_public_package_sample",
                            "readiness": "ready",
                            "passed": True,
                            "issues": [],
                            "warnings": [],
                        },
                        indent=2,
                    )
                    + "\n"
                ),
                stderr="",
            )
        if "check_public_benchmark_runs.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=(
                    json.dumps(
                        {
                            "report": {
                                "readiness": "ready",
                                "run_count": 1,
                                "overall_score": 100.0,
                                "total_case_count": 2,
                            }
                        },
                        indent=2,
                    )
                    + "\n"
                ),
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(run_repo_maturity_nightly.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_nightly.run_repo_maturity_nightly(
        profile="submission-framework",
        output_dir=tmp_path,
        public_runs_dir=tmp_path / "public_runs",
        sample_package_dir=REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1",
        sample_run_id="nightly_public_package_sample",
        python_executable="python3",
        rscript_executable="Rscript",
        write_step_summary=True,
    )

    assert exit_code == 0
    manifest_path = tmp_path / "repo-maturity-nightly.json"
    summary_path = tmp_path / "repo-maturity-nightly-summary.md"
    assert manifest_path.exists()
    assert summary_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ready"
    assert payload["profile"] == "submission-framework"
    assert payload["current_step_id"] is None
    assert payload["last_completed_step_id"] == "public_benchmark_runs_summary"
    assert payload["session_id"]
    assert payload["last_updated_at_utc"]
    assert payload["output_dir"] == "."
    assert payload["public_runs_dir"].startswith("public_runs/nightly_session_")
    assert payload["environment"]["git_commit"] == "abc123"
    assert payload["artifacts"]["repo_maturity_acceptance_manifest"].endswith(
        "repo_maturity_manifests/repo_maturity_submission-framework_acceptance.json"
    )
    assert payload["artifacts"]["repo_maturity_acceptance_summary_md"].endswith(
        "repo_maturity_reports/repo_maturity_submission-framework_acceptance/summary.md"
    )
    assert payload["artifacts"]["benchmark_matrix_report_json"].endswith(
        "benchmark_reports/harness_benchmark_matrix.json"
    )
    assert payload["artifacts"]["benchmark_matrix_manifest"].endswith(
        "benchmark_manifests/harness_benchmark_matrix.json"
    )
    assert payload["artifacts"]["public_run_check_json"].endswith(
        "repo-maturity-public-run-check.json"
    )
    assert "public_runs/nightly_session_" in payload["artifacts"]["public_run_report_json"]
    assert payload["artifacts"]["public_run_report_json"].endswith(
        "/nightly_public_package_sample/report.json"
    )
    assert "public_runs/nightly_session_" in payload["artifacts"]["public_run_metadata_json"]
    assert payload["artifacts"]["public_run_metadata_json"].endswith(
        "/nightly_public_package_sample/run_metadata.json"
    )
    assert "public_runs/nightly_session_" in payload["artifacts"]["public_runs_summary_report_json"]
    assert payload["artifacts"]["public_runs_summary_report_json"].endswith(
        "/public_benchmark_runs_summary.json"
    )
    assert "public_runs/nightly_session_" in payload["artifacts"]["public_runs_summary_manifest"]
    assert payload["artifacts"]["public_runs_summary_manifest"].endswith(
        "/public_benchmark_runs_summary_manifest.json"
    )
    assert payload["steps"]["repo_maturity_acceptance"]["status"] == "ready"
    assert payload["steps"]["public_benchmark_runs_summary"]["status"] == "ready"

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "# Repo Maturity Nightly Summary" in summary_text
    assert "- nightly_status: `ready`" in summary_text
    assert "- current_step_id: `none`" in summary_text
    assert "- last_completed_step_id: `public_benchmark_runs_summary`" in summary_text
    assert f"- session_id: `{payload['session_id']}`" in summary_text
    assert "- acceptance_artifact_passed: `True`" in summary_text
    assert "- benchmark_matrix_score: `100.0`" in summary_text
    assert "- benchmark_matrix_total_case_count: `9`" in summary_text
    assert "- public_run_id: `nightly_public_package_sample`" in summary_text
    assert "- public_run_case_count: `2`" in summary_text
    assert "- public_run_artifact_passed: `True`" in summary_text
    assert "- public_run_artifact_readiness: `ready`" in summary_text
    assert "- public_runs_summary_run_count: `1`" in summary_text
    assert "- public_runs_summary_total_case_count: `2`" in summary_text
    assert "- controller_python_version: `3.11.2`" in summary_text
    assert step_summary.read_text(encoding="utf-8") == summary_text
    payload_text = json.dumps(payload)
    assert str(tmp_path) not in payload_text
    assert "/Users/" not in payload_text
    for step in payload["steps"].values():
        assert all(not Path(token).is_absolute() for token in step["command"])
    acceptance_command = next(
        command for command in commands if any("run_repo_maturity_acceptance.py" in part for part in command)
    )
    assert "--reports-dir" in acceptance_command
    assert "--manifests-dir" in acceptance_command
    acceptance_check_command = next(
        command for command in commands if any("check_repo_maturity_acceptance.py" in part for part in command)
    )
    assert "--acceptance-json" in acceptance_check_command
    assert "--report-json" in acceptance_check_command
    assert "--summary-md" in acceptance_check_command
    benchmark_command = next(
        command for command in commands if any("check_harness_benchmark_matrix.py" in part for part in command)
    )
    assert "--reports-dir" in benchmark_command
    assert "--manifests-dir" in benchmark_command
    public_run_command = next(
        command for command in commands if any("run_public_benchmark_package.py" in part for part in command)
    )
    public_run_output_dir = Path(public_run_command[public_run_command.index("--output-dir") + 1])
    assert public_run_output_dir.parent == tmp_path / "public_runs"
    assert public_run_output_dir.name.startswith("nightly_session_")
    public_run_check_command = next(
        command for command in commands if any("check_public_benchmark_run.py" in part for part in command)
    )
    public_run_check_dir = Path(public_run_check_command[public_run_check_command.index("--run-dir") + 1])
    assert public_run_check_dir == public_run_output_dir / "nightly_public_package_sample"
    public_summary_command = next(
        command for command in commands if any("check_public_benchmark_runs.py" in part for part in command)
    )
    public_summary_runs_dir = Path(public_summary_command[public_summary_command.index("--runs-dir") + 1])
    assert public_summary_runs_dir == public_run_output_dir


def test_run_repo_maturity_nightly_returns_blocked_when_a_step_blocks(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        run_repo_maturity_nightly,
        "_collect_environment_metadata",
        lambda **_: {
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
    )

    def fake_run(command, cwd=None, check=None, capture_output=None, text=None, **kwargs):
        joined = " ".join(command)
        if "check_harness_benchmark_matrix.py" in joined:
            return subprocess.CompletedProcess(
                command,
                1,
                stdout=json.dumps({"report": {"readiness": "blocked"}}, indent=2) + "\n",
                stderr="benchmark blocked\n",
            )
        if "check_repo_maturity_acceptance.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"passed": True, "status": "ready"}, indent=2) + "\n",
                stderr="",
            )
        if "run_public_benchmark_package.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {"report": {"readiness": "ready"}, "run_metadata": {"run_id": "sample"}},
                    indent=2,
                )
                + "\n",
                stderr="",
            )
        if "check_public_benchmark_run.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"passed": True, "readiness": "ready"}, indent=2) + "\n",
                stderr="",
            )
        if "check_public_benchmark_runs.py" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"report": {"readiness": "ready", "run_count": 1}}, indent=2)
                + "\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(run_repo_maturity_nightly.subprocess, "run", fake_run)

    exit_code = run_repo_maturity_nightly.run_repo_maturity_nightly(
        profile="submission-framework",
        output_dir=tmp_path,
        public_runs_dir=tmp_path / "public_runs",
        sample_package_dir=REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1",
        sample_run_id="nightly_public_package_sample",
        python_executable="python3",
        rscript_executable="Rscript",
    )

    payload = json.loads((tmp_path / "repo-maturity-nightly.json").read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["status"] == "blocked"
    assert payload["current_step_id"] is None
    assert payload["last_completed_step_id"] == "public_benchmark_runs_summary"
    assert payload["steps"]["harness_benchmark_matrix"]["status"] == "blocked"
