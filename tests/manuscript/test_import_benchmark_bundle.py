from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_benchmark


SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_demo_v1"
HELDOUT_SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1"
GENERIC_SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "generic_author_input_source_demo_v1"


def _write_package_manifest(package_dir: Path, payload: dict) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_package_archive(source_dir: Path, archive_path: Path, *, root_prefix: str | None = None) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            relative_path = path.relative_to(source_dir)
            arcname = (Path(root_prefix) / relative_path) if root_prefix else relative_path
            archive.write(path, arcname.as_posix())


def test_import_benchmark_package_writes_bundle_to_target_dir(tmp_path) -> None:
    result = harness_benchmark.import_benchmark_package(
        SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
    )
    output_path = tmp_path / "paperwritingbench_style_demo_v1.json"
    assert result["bundle_id"] == "paperwritingbench_style_demo_v1"
    assert result["case_count"] == 2
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["adapter_type"] == "paperwritingbench_style_bundle"
    assert payload["import_source"]["manifest_path"].endswith("package_manifest.json")
    assert not payload["import_source"]["package_dir"].startswith("/")
    first_case = payload["cases"][0]
    assert first_case["source_materials"]["idea_summary"]["title"] == "Therapy response trajectories in a multimodal benchmark"
    assert first_case["mapping"]["claim_notes"]["claim_response_kinetics"].startswith("Use this")


def test_imported_bundle_can_be_scored(tmp_path, monkeypatch) -> None:
    harness_benchmark.import_benchmark_package(
        SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
    )
    monkeypatch.setattr(harness_benchmark, "BUNDLES_DIR", tmp_path)
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="paperwritingbench_style_demo_v1")
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "paperwritingbench_style_bundle"
    assert report["overall_score"] == 100.0


def test_imported_heldout_bundle_can_be_scored(tmp_path, monkeypatch) -> None:
    harness_benchmark.import_benchmark_package(
        HELDOUT_SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
    )
    monkeypatch.setattr(harness_benchmark, "BUNDLES_DIR", tmp_path)
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="paperwritingbench_style_heldout_v1")
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "paperwritingbench_style_bundle"
    assert report["overall_score"] == 100.0


def test_import_benchmark_package_archive_writes_bundle_to_target_dir(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_demo_v1.zip"
    _write_package_archive(
        SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=SOURCE_PACKAGE_DIR.name,
    )

    result = harness_benchmark.import_benchmark_package_archive(
        archive_path,
        output_dir=tmp_path / "out",
    )
    output_path = tmp_path / "out" / "paperwritingbench_style_demo_v1.json"
    assert result["bundle_id"] == "paperwritingbench_style_demo_v1"
    assert result["package_archive"].endswith(".zip")
    assert output_path.exists()

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["import_source"]["archive_path"].endswith(".zip")
    assert payload["import_source"]["manifest_path"].endswith("package_manifest.json")


def test_imported_archive_bundle_can_be_scored(tmp_path, monkeypatch) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_heldout_v1.zip"
    _write_package_archive(
        HELDOUT_SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=HELDOUT_SOURCE_PACKAGE_DIR.name,
    )
    harness_benchmark.import_benchmark_package_archive(
        archive_path,
        output_dir=tmp_path / "out",
    )
    monkeypatch.setattr(harness_benchmark, "BUNDLES_DIR", tmp_path / "out")
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="paperwritingbench_style_heldout_v1")
    assert report["definition_type"] == "bundle"
    assert report["overall_score"] == 100.0


def test_import_generic_author_input_package_can_be_scored(tmp_path, monkeypatch) -> None:
    harness_benchmark.import_benchmark_package(
        GENERIC_SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
    )
    monkeypatch.setattr(harness_benchmark, "BUNDLES_DIR", tmp_path)
    report = harness_benchmark.build_harness_benchmark_report(bundle_id="generic_author_input_demo_v1")
    assert report["definition_type"] == "bundle"
    assert report["adapter_type"] == "generic_author_input_bundle"
    assert report["overall_score"] == 100.0


def test_cli_import_benchmark_bundle_dry_run_json(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["bundle_id"] == "paperwritingbench_style_demo_v1"
    assert payload["dry_run"] is True
    assert not (tmp_path / "paperwritingbench_style_demo_v1.json").exists()


def test_cli_import_generic_author_input_bundle_dry_run_json(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(GENERIC_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["bundle_id"] == "generic_author_input_demo_v1"
    assert payload["dry_run"] is True
    assert not (tmp_path / "generic_author_input_demo_v1.json").exists()


def test_cli_import_heldout_bundle_dry_run_json(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["bundle_id"] == "paperwritingbench_style_heldout_v1"
    assert payload["dry_run"] is True
    assert not (tmp_path / "paperwritingbench_style_heldout_v1.json").exists()


def test_cli_import_archive_bundle_dry_run_json(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_demo_v1.zip"
    _write_package_archive(
        SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=SOURCE_PACKAGE_DIR.name,
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-archive",
            str(archive_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["bundle_id"] == "paperwritingbench_style_demo_v1"
    assert payload["package_archive"].endswith(".zip")
    assert not (tmp_path / "out" / "paperwritingbench_style_demo_v1.json").exists()


def test_import_benchmark_package_rejects_path_escape(tmp_path) -> None:
    package_dir = tmp_path / "malicious_package"
    outside_file = tmp_path / "outside.md"
    outside_file.write_text("secret", encoding="utf-8")
    _write_package_manifest(
        package_dir,
        {
            "bundle_id": "malicious_bundle",
            "adapter_type": "paperwritingbench_style_bundle",
            "benchmark_family": "paperwritingbench_style_bundle",
            "reference_benchmark": "PaperWritingBench",
            "description": "malicious package",
            "notes": [],
            "cases": [
                {
                    "case_id": "escape_case",
                    "kind": "paperwritingbench_style_error",
                    "dimension": "guardrails",
                    "source_material_files": {
                        "experimental_log": "../outside.md",
                    },
                    "source_materials": {
                        "idea_summary": {"title": "Example topic"},
                    },
                    "mapping": {
                        "claim_notes": {
                            "claim_not_in_repo": "bad",
                        }
                    },
                    "expect_error_contains": "unknown claim_ids",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="must stay within package root"):
        harness_benchmark.import_benchmark_package(package_dir, output_dir=tmp_path / "out")


def test_import_benchmark_package_archive_rejects_path_escape(tmp_path) -> None:
    archive_path = tmp_path / "malicious_package.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "package_manifest.json",
            json.dumps(
                {
                    "bundle_id": "archive_bundle",
                    "adapter_type": "paperwritingbench_style_bundle",
                    "benchmark_family": "paperwritingbench_style_bundle",
                    "reference_benchmark": "PaperWritingBench",
                    "description": "archive bundle",
                    "notes": [],
                    "cases": [],
                }
            ),
        )
        archive.writestr("../escape.txt", "secret")

    with pytest.raises(ValueError, match="unsafe member path"):
        harness_benchmark.import_benchmark_package_archive(archive_path, output_dir=tmp_path / "out")


def test_import_benchmark_package_archive_requires_manifest(tmp_path) -> None:
    archive_path = tmp_path / "missing_manifest.zip"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("notes.txt", "missing manifest")

    with pytest.raises(ValueError, match="does not contain package_manifest.json"):
        harness_benchmark.import_benchmark_package_archive(archive_path, output_dir=tmp_path / "out")


def test_import_benchmark_package_validates_adapter_type_before_write(tmp_path) -> None:
    package_dir = tmp_path / "invalid_adapter"
    _write_package_manifest(
        package_dir,
        {
            "bundle_id": "invalid_adapter_bundle",
            "adapter_type": "not_supported",
            "benchmark_family": "paperwritingbench_style_bundle",
            "reference_benchmark": "PaperWritingBench",
            "description": "invalid adapter",
            "notes": [],
            "cases": [],
        },
    )

    with pytest.raises(ValueError, match="Unsupported benchmark bundle adapter_type"):
        harness_benchmark.import_benchmark_package(package_dir, output_dir=tmp_path / "out")
    assert not (tmp_path / "out" / "invalid_adapter_bundle.json").exists()


def test_import_benchmark_package_validates_case_kind_before_write(tmp_path) -> None:
    package_dir = tmp_path / "invalid_case_kind"
    _write_package_manifest(
        package_dir,
        {
            "bundle_id": "invalid_case_kind_bundle",
            "adapter_type": "paperwritingbench_style_bundle",
            "benchmark_family": "paperwritingbench_style_bundle",
            "reference_benchmark": "PaperWritingBench",
            "description": "invalid case kind",
            "notes": [],
            "cases": [
                {
                    "case_id": "bad_case",
                    "kind": "not_supported",
                    "dimension": "guardrails",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="unsupported case kind"):
        harness_benchmark.import_benchmark_package(package_dir, output_dir=tmp_path / "out")
    assert not (tmp_path / "out" / "invalid_case_kind_bundle.json").exists()


def test_import_benchmark_package_refuses_to_overwrite_without_force(tmp_path) -> None:
    harness_benchmark.import_benchmark_package(
        SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
    )

    dry_run_result = harness_benchmark.import_benchmark_package(
        SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
        dry_run=True,
    )
    assert dry_run_result["dry_run"] is True

    with pytest.raises(ValueError, match="Refusing to overwrite existing benchmark bundle"):
        harness_benchmark.import_benchmark_package(
            SOURCE_PACKAGE_DIR,
            output_dir=tmp_path,
        )

    result = harness_benchmark.import_benchmark_package(
        SOURCE_PACKAGE_DIR,
        output_dir=tmp_path,
        force=True,
    )
    assert result["bundle_id"] == "paperwritingbench_style_demo_v1"


def test_cli_import_benchmark_bundle_missing_manifest_returns_json_error(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
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
    assert "Benchmark package manifest not found" in payload["error"]


def test_cli_import_benchmark_bundle_requires_exactly_one_source_flag(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--output-dir",
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
    assert "exactly one" in payload["error"]


def test_cli_import_benchmark_bundle_refuses_overwrite_without_force(tmp_path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--output-dir",
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
    assert "Refusing to overwrite existing benchmark bundle" in payload["error"]

    forced = subprocess.run(
        [
            sys.executable,
            "scripts/import_benchmark_bundle.py",
            "--package-dir",
            str(SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--force",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    forced_payload = json.loads(forced.stdout)
    assert forced_payload["bundle_id"] == "paperwritingbench_style_demo_v1"
