from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import archive_export


GENERATED_BUNDLE_SUMMARY = (
    REPO_ROOT / "figures/output/bundles/bundle_bulk_omics_deg_exemplar/summary.json"
)
pytestmark = pytest.mark.skipif(
    not GENERATED_BUNDLE_SUMMARY.exists(),
    reason="requires generated figure-bundle outputs from build_phase2.py",
)


def test_build_archive_export_is_ready_for_integrated_demo() -> None:
    report = archive_export.build_archive_export("integrated_demo_release", REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["file_count"] > 0
    assert report["release_bundle"]["profile_id"] == "integrated_demo_release"
    assert "figures" in report["tree_summary"]
    assert "review" in report["tree_summary"]


def test_write_archive_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    checksums_dir = tmp_path / "checksums"
    deposit_dir = tmp_path / "deposit"
    monkeypatch.setattr(archive_export, "ARCHIVE_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(archive_export, "ARCHIVE_MANIFESTS_DIR", manifests_dir)
    monkeypatch.setattr(archive_export, "CHECKSUMS_DIR", checksums_dir)
    monkeypatch.setattr(archive_export, "DEPOSIT_DIR", deposit_dir)

    writes = archive_export.write_archive_outputs("integrated_demo_release")
    report_json = reports_dir / "integrated_demo_release_archive.json"
    report_md = reports_dir / "integrated_demo_release_archive.md"
    manifest = manifests_dir / "integrated_demo_release_archive.json"
    checksum_inventory = checksums_dir / "integrated_demo_release_archive_sha256.txt"
    deposit_notes = deposit_dir / "integrated_demo_release_deposit_notes.md"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    assert Path(writes["checksum_inventory"]) == checksum_inventory
    assert Path(writes["deposit_notes"]) == deposit_notes
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()
    assert checksum_inventory.exists()
    assert deposit_notes.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["archive_id"] == "integrated_demo_release_archive_v1"
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["package_id"] == "integrated_demo_release_archive_v1"


def test_checksum_inventory_has_sha256_lines() -> None:
    report = archive_export.build_archive_export("integrated_demo_release", REPO_ROOT)
    text = archive_export.render_checksum_inventory(report)
    first_line = text.splitlines()[0]
    digest, relpath = first_line.split("  ", 1)
    assert len(digest) == 64
    assert "/" in relpath


def test_cli_check_archive_export_strict_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_archive_export.py",
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
