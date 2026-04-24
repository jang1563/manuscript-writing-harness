from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import export_bundle


GENERATED_BUNDLE_SUMMARY = (
    REPO_ROOT / "figures/output/bundles/bundle_bulk_omics_deg_exemplar/summary.json"
)
pytestmark = pytest.mark.skipif(
    not GENERATED_BUNDLE_SUMMARY.exists(),
    reason="requires generated figure-bundle outputs from build_phase2.py",
)


def test_build_export_bundle_is_ready_for_integrated_demo() -> None:
    report = export_bundle.build_export_bundle("integrated_demo_release", REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["included_file_count"] > 0
    assert report["archive_prefix"] == "integrated_demo_release_export"


def test_write_export_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    exports_dir = tmp_path / "exports"
    monkeypatch.setattr(export_bundle, "EXPORTS_DIR", exports_dir)

    writes = export_bundle.write_export_outputs("integrated_demo_release")
    report_json = exports_dir / "integrated_demo_release_export.json"
    report_md = exports_dir / "integrated_demo_release_export.md"
    checksums = exports_dir / "integrated_demo_release_export_checksums.txt"
    tar_gz = exports_dir / "integrated_demo_release_export.tar.gz"
    zip_path = exports_dir / "integrated_demo_release_export.zip"
    manifest = exports_dir / "integrated_demo_release_export_manifest.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["checksums"]) == checksums
    assert Path(writes["tar_gz"]) == tar_gz
    assert Path(writes["zip"]) == zip_path
    assert Path(writes["manifest"]) == manifest
    assert tar_gz.exists()
    assert zip_path.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["export_id"] == "integrated_demo_release_export_v1"


def test_written_archives_include_release_prefix(tmp_path, monkeypatch) -> None:
    exports_dir = tmp_path / "exports"
    monkeypatch.setattr(export_bundle, "EXPORTS_DIR", exports_dir)
    writes = export_bundle.write_export_outputs("integrated_demo_release")
    tar_path = Path(writes["tar_gz"])
    zip_path = Path(writes["zip"])

    with tarfile.open(tar_path, "r:gz") as handle:
        names = handle.getnames()
    assert any(name.startswith("integrated_demo_release_export/") for name in names)
    assert "integrated_demo_release_export/workflows/release/reports/integrated_demo_release_archive.md" in names

    with zipfile.ZipFile(zip_path) as handle:
        names = handle.namelist()
    assert "integrated_demo_release_export/workflows/release/reports/integrated_demo_release_archive.md" in names


def test_cli_check_export_bundle_strict_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_export_bundle.py",
            "--profile",
            "integrated_demo_release",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "ready"
