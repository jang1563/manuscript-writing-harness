from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import deposit_metadata


GENERATED_BUNDLE_SUMMARY = (
    REPO_ROOT / "figures/output/bundles/bundle_bulk_omics_deg_exemplar/summary.json"
)
pytestmark = pytest.mark.skipif(
    not GENERATED_BUNDLE_SUMMARY.exists(),
    reason="requires generated figure-bundle outputs from build_phase2.py",
)


def test_build_deposit_metadata_is_ready_for_integrated_demo() -> None:
    report = deposit_metadata.build_deposit_metadata("integrated_demo_release", REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["creators_count"] >= 1
    assert report["export_bundle"]["export_id"] == "integrated_demo_release_export_v1"
    assert set(report["targets"]) == {"citation_cff", "codemeta", "zenodo", "osf"}
    assert report["release_title"] == "Integrated Demo Release Bundle"
    assert "creator metadata contains a placeholder affiliation" not in report["warnings"]


def test_write_deposit_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    deposit_dir = tmp_path / "deposit"
    monkeypatch.setattr(deposit_metadata, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(deposit_metadata, "MANIFESTS_DIR", manifests_dir)
    monkeypatch.setattr(deposit_metadata, "DEPOSIT_DIR", deposit_dir)

    writes = deposit_metadata.write_deposit_outputs("integrated_demo_release")
    report_json = reports_dir / "integrated_demo_release_deposit_metadata.json"
    report_md = reports_dir / "integrated_demo_release_deposit_metadata.md"
    manifest = manifests_dir / "integrated_demo_release_deposit_metadata.json"
    citation_cff = deposit_dir / "integrated_demo_release_CITATION.cff"
    codemeta = deposit_dir / "integrated_demo_release_codemeta.json"
    zenodo = deposit_dir / "integrated_demo_release_zenodo_metadata.json"
    osf = deposit_dir / "integrated_demo_release_osf_metadata.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    assert Path(writes["citation_cff"]) == citation_cff
    assert Path(writes["codemeta"]) == codemeta
    assert Path(writes["zenodo"]) == zenodo
    assert Path(writes["osf"]) == osf
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()
    assert citation_cff.exists()
    assert codemeta.exists()
    assert zenodo.exists()
    assert osf.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["deposit_metadata_id"] == "integrated_demo_release_deposit_metadata_v1"
    cff_payload = yaml.safe_load(citation_cff.read_text(encoding="utf-8"))
    assert cff_payload["cff-version"] == "1.2.0"
    assert cff_payload["title"]
    assert "multi-agent manuscript system" in cff_payload["abstract"].lower()


def test_cli_check_deposit_metadata_strict_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_deposit_metadata.py",
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
