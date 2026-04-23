from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_benchmark


SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_demo_v1"
HELDOUT_SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1"


def _write_package_archive(source_dir: Path, archive_path: Path, *, root_prefix: str | None = None) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            relative_path = path.relative_to(source_dir)
            arcname = (Path(root_prefix) / relative_path) if root_prefix else relative_path
            archive.write(path, arcname.as_posix())


def _run_public_package(command: list[str]) -> None:
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_build_public_benchmark_runs_report_is_ready(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_demo_v1.zip"
    _write_package_archive(
        SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=SOURCE_PACKAGE_DIR.name,
    )
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
            "--strict",
        ]
    )
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-archive",
            str(archive_path),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "demo_archive_run",
            "--json",
            "--strict",
        ]
    )

    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    assert report["readiness"] == "ready"
    assert report["run_count"] == 2
    assert report["ready_run_count"] == 2
    assert report["invalid_run_count"] == 0
    assert report["total_case_count"] == 4
    assert report["overall_score"] == 100.0
    assert report["latest_run_id"] == report["runs"][0]["run_id"]
    assert report["latest_ready_run_id"] == report["runs"][0]["run_id"]
    assert report["best_run_id"] in {"heldout_dir_run", "demo_archive_run"}
    assert report["duplicate_source_count"] == 0
    assert all(run["source_sha256"] for run in report["runs"])
    assert all(run["python_version"] for run in report["runs"])
    assert all("git_commit" in run for run in report["runs"])


def test_build_public_benchmark_runs_report_marks_invalid_run(tmp_path) -> None:
    broken_run_dir = tmp_path / "broken_run"
    broken_run_dir.mkdir()
    (broken_run_dir / "run_metadata.json").write_text(
        json.dumps({"run_id": "broken_run", "created_at_utc": "2026-04-21T00:00:00Z"}, indent=2) + "\n",
        encoding="utf-8",
    )
    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    assert report["readiness"] == "blocked"
    assert report["run_count"] == 1
    assert report["invalid_run_count"] == 1
    assert report["runs"][0]["readiness"] == "invalid"
    assert any("missing `report_json`" in issue for issue in report["runs"][0]["errors"])
    assert report["latest_run_id"] == "broken_run"
    assert report["latest_ready_run_id"] == ""
    assert report["best_run_id"] == ""
    assert report["duplicate_source_count"] == 0
    assert report["runs"][0]["python_version"] == ""


def test_build_public_benchmark_runs_report_marks_generation_mismatch_invalid(tmp_path) -> None:
    mismatched_run_dir = tmp_path / "mismatched_run"
    mismatched_run_dir.mkdir()
    report_payload = {
        "suite_id": "paperwritingbench_style_demo_v1",
        "readiness": "ready",
        "overall_score": 100.0,
        "case_count": 2,
        "passed_case_count": 2,
        "failed_case_count": 0,
        "run_generation_id": "report-generation",
    }
    manifest_payload = {
        "suite_id": "paperwritingbench_style_demo_v1",
        "readiness": "ready",
        "overall_score": 100.0,
        "case_count": 2,
        "passed_case_count": 2,
        "failed_case_count": 0,
        "run_generation_id": "report-generation",
    }
    metadata_payload = {
        "run_id": "mismatched_run",
        "created_at_utc": "2026-04-21T00:00:00Z",
        "generation_id": "metadata-generation",
        "source_type": "package_dir",
        "source_path": str(HELDOUT_SOURCE_PACKAGE_DIR),
        "source_sha256": "abc123",
        "suite_id": "paperwritingbench_style_demo_v1",
        "environment": {},
    }
    (mismatched_run_dir / "report.json").write_text(
        json.dumps(report_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (mismatched_run_dir / "manifest.json").write_text(
        json.dumps(manifest_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (mismatched_run_dir / "run_metadata.json").write_text(
        json.dumps(metadata_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    assert report["readiness"] == "blocked"
    assert report["invalid_run_count"] == 1
    assert report["runs"][0]["readiness"] == "invalid"
    assert any("inconsistent run generation markers" in issue for issue in report["runs"][0]["errors"])


def test_build_public_benchmark_runs_report_detects_duplicate_sources(tmp_path) -> None:
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run_a",
            "--json",
            "--strict",
        ]
    )
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run_b",
            "--json",
            "--strict",
        ]
    )

    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    assert report["duplicate_source_count"] == 1
    duplicate_source = report["duplicate_sources"][0]
    assert duplicate_source["source_type"] == "package_dir"
    assert duplicate_source["run_count"] == 2
    assert set(duplicate_source["run_ids"]) == {"heldout_dir_run_a", "heldout_dir_run_b"}


def test_build_public_benchmark_runs_report_uses_strict_run_validation(tmp_path) -> None:
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
            "--strict",
        ]
    )
    (tmp_path / "heldout_dir_run" / "report.md").write_text(
        "# Corrupted Report\n\n- readiness: `ready`\n",
        encoding="utf-8",
    )

    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    assert report["readiness"] == "blocked"
    assert report["invalid_run_count"] == 1
    assert report["runs"][0]["readiness"] == "invalid"
    assert any("report.md" in issue for issue in report["runs"][0]["errors"])


def test_write_public_benchmark_runs_outputs_can_be_redirected(tmp_path) -> None:
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
            "--strict",
        ]
    )
    report = harness_benchmark.build_public_benchmark_runs_report(tmp_path)
    writes = harness_benchmark.write_public_benchmark_runs_outputs(tmp_path, report=report)
    assert Path(writes["report_json"]) == tmp_path / "public_benchmark_runs_summary.json"
    assert Path(writes["report_md"]) == tmp_path / "public_benchmark_runs_summary.md"
    assert Path(writes["manifest"]) == tmp_path / "public_benchmark_runs_summary_manifest.json"
    written_report = json.loads((tmp_path / "public_benchmark_runs_summary.json").read_text(encoding="utf-8"))
    assert written_report == report


def test_cli_check_public_benchmark_runs_json_strict(tmp_path) -> None:
    _run_public_package(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
            "--strict",
        ]
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_public_benchmark_runs.py",
            "--runs-dir",
            str(tmp_path),
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["run_count"] == 1
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["duplicate_source_count"] == 0
    assert payload["report"]["runs"][0]["python_version"]


def test_cli_check_public_benchmark_runs_non_strict_returns_zero_for_invalid_runs(tmp_path) -> None:
    broken_run_dir = tmp_path / "broken_run"
    broken_run_dir.mkdir()
    (broken_run_dir / "run_metadata.json").write_text(
        json.dumps({"run_id": "broken_run", "created_at_utc": "2026-04-21T00:00:00Z"}, indent=2) + "\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_public_benchmark_runs.py",
            "--runs-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "blocked"
    assert payload["report"]["invalid_run_count"] == 1


def test_cli_check_public_benchmark_runs_empty_dir_returns_json_error(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_public_benchmark_runs.py",
            "--runs-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "No public benchmark runs found" in payload["error"]
