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


def test_build_harness_benchmark_report_is_ready_for_tracked_suite() -> None:
    report = harness_benchmark.build_harness_benchmark_report()
    assert report["suite_id"] == harness_benchmark.DEFAULT_SUITE_ID
    assert report["reference_benchmark"] == "PaperWritingBench"
    assert report["readiness"] == "ready"
    assert report["case_count"] == 3
    assert report["passed_case_count"] == 3
    assert report["failed_case_ids"] == []
    assert report["overall_score"] == 100.0


def test_build_harness_benchmark_report_is_ready_for_demo_bundle() -> None:
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="paperwritingbench_style_demo_v1")
    assert report["suite_id"] == "paperwritingbench_style_demo_v1"
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "paperwritingbench_style_bundle"
    assert report["reference_benchmark"] == "PaperWritingBench"
    assert report["readiness"] == "ready"
    assert report["case_count"] == 2
    assert report["passed_case_count"] == 2
    assert report["overall_score"] == 100.0
    first_case = report["cases"][0]
    assert first_case["source_materials"]["idea_summary"]["title"] == "Therapy response trajectories in a multimodal benchmark"
    assert first_case["metrics"]["topic"] == "Therapy response trajectories in a multimodal benchmark"


def test_build_harness_benchmark_report_is_ready_for_heldout_bundle() -> None:
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="paperwritingbench_style_heldout_v1")
    assert report["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "paperwritingbench_style_bundle"
    assert report["reference_benchmark"] == "PaperWritingBench"
    assert report["readiness"] == "ready"
    assert report["case_count"] == 2
    assert report["passed_case_count"] == 2
    assert report["overall_score"] == 100.0
    first_case = report["cases"][0]
    assert first_case["source_materials"]["idea_summary"]["title"] == "Calibration-aware foundation model ranking for imbalanced disease states"
    assert first_case["metrics"]["topic"] == "Calibration-aware foundation model ranking for imbalanced disease states"


def test_build_harness_benchmark_report_is_ready_for_generic_author_input_bundle() -> None:
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="generic_author_input_demo_v1")
    assert report["suite_id"] == "generic_author_input_demo_v1"
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "generic_author_input_bundle"
    assert report["readiness"] == "ready"
    assert report["case_count"] == 2
    assert report["passed_case_count"] == 2
    assert report["overall_score"] == 100.0
    first_case = report["cases"][0]
    assert first_case["metrics"]["topic"] == "Direct author input benchmark for therapeutic response"


def test_build_harness_benchmark_report_from_package_dir_is_ready() -> None:
    report = harness_benchmark.build_harness_benchmark_report_from_package(SOURCE_PACKAGE_DIR)
    assert report["suite_id"] == "paperwritingbench_style_demo_v1"
    assert report["definition_type"] == "bundle"
    assert report["readiness"] == "ready"
    assert report["suite_path"].endswith("package_manifest.json")


def test_build_harness_benchmark_report_from_package_archive_is_ready(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_heldout_v1.zip"
    _write_package_archive(
        HELDOUT_SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=HELDOUT_SOURCE_PACKAGE_DIR.name,
    )
    report = harness_benchmark.build_harness_benchmark_report_from_package_archive(archive_path)
    assert report["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert report["definition_type"] == "bundle"
    assert report["readiness"] == "ready"
    assert report["suite_path"].endswith(".zip")


def test_write_harness_benchmark_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(harness_benchmark, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_benchmark, "MANIFESTS_DIR", manifests_dir)

    writes = harness_benchmark.write_harness_benchmark_outputs()
    report_json = reports_dir / f"{harness_benchmark.DEFAULT_SUITE_ID}.json"
    report_md = reports_dir / f"{harness_benchmark.DEFAULT_SUITE_ID}.md"
    manifest = manifests_dir / f"{harness_benchmark.DEFAULT_SUITE_ID}.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["suite_id"] == harness_benchmark.DEFAULT_SUITE_ID
    assert payload["overall_score"] == 100.0


def test_render_harness_benchmark_markdown_uses_agent_evaluation_title() -> None:
    report = harness_benchmark.build_harness_benchmark_report()
    markdown = harness_benchmark.render_harness_benchmark_markdown(report)
    assert markdown.startswith("# Agent Evaluation Benchmark")


def test_write_harness_benchmark_bundle_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(harness_benchmark, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_benchmark, "MANIFESTS_DIR", manifests_dir)

    writes = harness_benchmark.write_harness_benchmark_outputs(bundle_id="paperwritingbench_style_demo_v1")
    report_json = reports_dir / "paperwritingbench_style_demo_v1.json"
    report_md = reports_dir / "paperwritingbench_style_demo_v1.md"
    manifest = manifests_dir / "paperwritingbench_style_demo_v1.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["definition_type"] == "bundle"
    assert payload["adapter_type"] == "paperwritingbench_style_bundle"


def test_write_generic_author_input_bundle_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(harness_benchmark, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_benchmark, "MANIFESTS_DIR", manifests_dir)

    writes = harness_benchmark.write_harness_benchmark_outputs(bundle_id="generic_author_input_demo_v1")
    report_json = reports_dir / "generic_author_input_demo_v1.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert writes["report_json"].endswith("generic_author_input_demo_v1.json")
    assert payload["definition_type"] == "bundle"
    assert payload["adapter_type"] == "generic_author_input_bundle"


def test_write_heldout_bundle_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(harness_benchmark, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_benchmark, "MANIFESTS_DIR", manifests_dir)

    writes = harness_benchmark.write_harness_benchmark_outputs(bundle_id="paperwritingbench_style_heldout_v1")
    report_json = reports_dir / "paperwritingbench_style_heldout_v1.json"
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert writes["report_json"].endswith("paperwritingbench_style_heldout_v1.json")
    assert payload["definition_type"] == "bundle"
    assert payload["adapter_type"] == "paperwritingbench_style_bundle"


def test_cli_check_harness_benchmark_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == harness_benchmark.DEFAULT_SUITE_ID
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["overall_score"] == 100.0


def test_cli_check_harness_benchmark_bundle_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--bundle",
            "paperwritingbench_style_demo_v1",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == "paperwritingbench_style_demo_v1"
    assert payload["report"]["definition_type"] == "bundle"
    assert payload["report"]["adapter_type"] == "paperwritingbench_style_bundle"
    assert payload["report"]["overall_score"] == 100.0


def test_cli_check_harness_benchmark_generic_bundle_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--bundle",
            "generic_author_input_demo_v1",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == "generic_author_input_demo_v1"
    assert payload["report"]["adapter_type"] == "generic_author_input_bundle"
    assert payload["report"]["overall_score"] == 100.0


def test_cli_check_harness_benchmark_heldout_bundle_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--bundle",
            "paperwritingbench_style_heldout_v1",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert payload["report"]["adapter_type"] == "paperwritingbench_style_bundle"
    assert payload["report"]["overall_score"] == 100.0


def test_cli_check_harness_benchmark_package_dir_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == "paperwritingbench_style_demo_v1"
    assert payload["report"]["suite_path"].endswith("package_manifest.json")


def test_cli_check_harness_benchmark_package_archive_json_strict(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_heldout_v1.zip"
    _write_package_archive(
        HELDOUT_SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=HELDOUT_SOURCE_PACKAGE_DIR.name,
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--package-archive",
            str(archive_path),
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert payload["report"]["suite_path"].endswith(".zip")


def test_cli_check_harness_benchmark_rejects_write_for_package_sources() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--write",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "--write is only supported" in payload["error"]


def test_cli_check_harness_benchmark_unknown_suite_returns_json_error() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--suite",
            "not_a_real_suite",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Unknown benchmark suite" in payload["error"]


def test_cli_check_harness_benchmark_unknown_bundle_returns_json_error() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark.py",
            "--bundle",
            "not_a_real_bundle",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Unknown benchmark bundle" in payload["error"]
