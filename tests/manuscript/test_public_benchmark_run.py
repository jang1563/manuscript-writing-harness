from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_benchmark


HELDOUT_SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1"


def _run_public_package(command: list[str]) -> None:
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_validate_public_benchmark_run_passes_for_ready_run(tmp_path: Path) -> None:
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_ready_run",
            "--json",
            "--strict",
        ]
    )

    result = harness_benchmark.validate_public_benchmark_run(tmp_path / "heldout_ready_run")

    assert result["passed"] is True
    assert result["readiness"] == "ready"
    assert result["run_id"] == "heldout_ready_run"
    assert result["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert result["artifacts"]["report_json"].endswith("heldout_ready_run/report.json")
    report_markdown = (tmp_path / "heldout_ready_run" / "report.md").read_text(encoding="utf-8")
    assert report_markdown.startswith("# Agent Evaluation Benchmark")


def test_cli_check_public_benchmark_run_non_strict_reports_invalid_run(tmp_path: Path) -> None:
    broken_run_dir = tmp_path / "broken_run"
    broken_run_dir.mkdir()
    (broken_run_dir / "run_metadata.json").write_text(
        json.dumps({"run_id": "broken_run", "created_at_utc": "2026-04-21T00:00:00Z"}, indent=2) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_public_benchmark_run.py",
            "--run-dir",
            str(broken_run_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["passed"] is False
    assert payload["readiness"] == "invalid"
    assert any("missing `report_json`" in issue for issue in payload["issues"])


def test_cli_check_public_benchmark_run_strict_fails_for_invalid_run(tmp_path: Path) -> None:
    broken_run_dir = tmp_path / "broken_run"
    broken_run_dir.mkdir()
    (broken_run_dir / "run_metadata.json").write_text(
        json.dumps({"run_id": "broken_run", "created_at_utc": "2026-04-21T00:00:00Z"}, indent=2) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_public_benchmark_run.py",
            "--run-dir",
            str(broken_run_dir),
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["passed"] is False
    assert payload["readiness"] == "invalid"
