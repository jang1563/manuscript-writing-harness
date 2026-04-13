from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import release_bundle


def test_release_profile_registry_contains_integrated_demo() -> None:
    profiles = release_bundle.load_release_profiles(REPO_ROOT)
    assert "integrated_demo_release" in profiles
    assert profiles["integrated_demo_release"]["venue_id"] == "nature"


def test_build_release_bundle_is_ready_for_current_demo_repo() -> None:
    report = release_bundle.build_release_bundle("integrated_demo_release", REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["venue"]["venue_id"] == "nature"
    assert [item["bundle_id"] for item in report["figure_bundles"]] == [
        "bundle_bulk_omics_deg_exemplar",
        "bundle_ai_ml_evaluation_exemplar",
    ]
    assert report["review_evidence"]["readiness"] == "ready"
    assert report["reference_integrity"]["readiness"] == "ready"
    assert report["claim_coverage"]["overall_status"] == "ready"
    assert report["section_prose"]["overall_status"] == "ready"
    assert report["active_fgsea_study"]["readiness"] == "ready"
    assert all(item["status"] == "present" for item in report["required_artifacts"])


def test_write_release_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(release_bundle, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(release_bundle, "MANIFESTS_DIR", manifests_dir)

    writes = release_bundle.write_release_outputs("integrated_demo_release")
    report_json = reports_dir / "integrated_demo_release_bundle.json"
    report_md = reports_dir / "integrated_demo_release_bundle.md"
    manifest = manifests_dir / "integrated_demo_release_bundle.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "integrated_demo_release"
    assert payload["readiness"] == "ready"
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["package_id"] == "integrated_demo_release_bundle_v1"


def test_release_markdown_mentions_active_fgsea_and_required_artifacts() -> None:
    report = release_bundle.build_release_bundle("integrated_demo_release", REPO_ROOT)
    markdown = release_bundle.render_release_markdown(report)
    assert "# Integrated Demo Release Bundle" in markdown
    assert "active fgsea study" in markdown
    assert "## Required Artifacts" in markdown
    assert "`manuscript/_build/html/results/index.html`" in markdown


def test_cli_check_release_bundle_strict_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_release_bundle.py",
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
