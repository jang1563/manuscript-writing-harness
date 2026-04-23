from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pre_submission_audit


def test_build_pre_submission_audit_is_ready_for_current_repo() -> None:
    report = pre_submission_audit.build_pre_submission_audit(REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["submission_gate"]["status"] == "blocked"
    assert report["manuscript_scope_gate"]["status"] == "blocked"
    assert report["bibliography_scope_gate"]["status"] == "blocked"
    assert report["review_validation"]["overall_status"] == "ready"
    assert report["review_evidence"]["readiness"] == "ready"
    assert report["reference_integrity"]["readiness"] == "ready"
    assert report["claim_coverage"]["overall_status"] == "ready"
    assert report["venues"]["checked"] >= 4
    assert report["venues"]["verification_pending"] >= 1
    assert report["venues"]["verification_invalid"] == 0
    assert "manuscript/plans/manuscript_scope.json" in report["package_paths"]


def test_build_pre_submission_audit_can_scope_to_one_venue() -> None:
    report = pre_submission_audit.build_pre_submission_audit(REPO_ROOT, selected_venues=["neurips"])
    assert report["audit_id"] == "pre_submission_audit_neurips_v1"
    assert report["venue_scope"]["mode"] == "selected"
    assert report["venue_scope"]["venue_ids"] == ["neurips"]
    assert report["venues"]["checked"] == 1
    assert report["submission_gate"]["failed_count"] == 1
    assert report["bibliography_scope_gate"]["status"] == "blocked"
    assert report["submission_gate"]["failed_venues"][0]["venue"] == "neurips"


def test_build_pre_submission_audit_blocks_invalid_verification(monkeypatch) -> None:
    monkeypatch.setattr(pre_submission_audit, "_available_venues", lambda: ["fake"])

    def fake_evaluate_venue(_venue_id: str, repo_root=pre_submission_audit.REPO_ROOT):
        return {
            "venue": "fake",
            "display_name": "Fake Venue",
            "readiness": "blocked",
            "blocking_items": [],
            "blocking_issues": ["invalid verification metadata: bad metadata"],
            "required_sections": [],
            "special_assets": [],
            "notes": [],
            "verification": {
                "status": "invalid",
                "last_verified": None,
                "days_since_verification": None,
                "stale_after_days": 180,
                "stale": False,
                "final_confirmation_required": False,
                "source_summary": "",
                "issues": ["bad metadata"],
            },
            "config_path": "workflows/venue_configs/fake.yml",
            "checklist_path": "workflows/checklists/fake_submission.md",
            "package_paths": [],
        }

    monkeypatch.setattr(pre_submission_audit, "evaluate_venue", fake_evaluate_venue)
    report = pre_submission_audit.build_pre_submission_audit(REPO_ROOT, selected_venues=["fake"])
    assert report["readiness"] == "blocked"
    assert report["venues"]["verification_invalid"] == 1
    assert "venue readiness is not ready for: fake" in report["blocking_issues"]
    assert "fake: invalid verification metadata: bad metadata" in report["blocking_issues"]


def test_build_pre_submission_audit_blocks_invalid_manuscript_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        pre_submission_audit,
        "build_manuscript_scope_status",
        lambda repo_root=pre_submission_audit.REPO_ROOT: {
            "status": "invalid",
            "scope_status": "real",
            "confirmed_on": None,
            "note": "",
            "issues": ["`note` is required"],
            "warnings": [],
            "manifest_path": "manuscript/plans/manuscript_scope.json",
        },
    )
    report = pre_submission_audit.build_pre_submission_audit(REPO_ROOT, selected_venues=["neurips"])
    assert report["readiness"] == "blocked"
    assert report["manuscript_scope_gate"]["status"] == "blocked"
    assert "manuscript scope: `note` is required" in report["blocking_issues"]


def test_write_pre_submission_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(pre_submission_audit, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(pre_submission_audit, "MANIFESTS_DIR", manifests_dir)

    writes = pre_submission_audit.write_pre_submission_outputs()
    report_json = reports_dir / "pre_submission_audit.json"
    report_md = reports_dir / "pre_submission_audit.md"
    manifest = manifests_dir / "pre_submission_audit.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["audit_id"] == "pre_submission_audit_v1"
    assert payload["readiness"] == "ready"
    assert payload["submission_gate"]["status"] == "blocked"
    assert payload["venues"]["verification_pending"] >= 1


def test_write_pre_submission_outputs_can_scope_to_one_venue(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(pre_submission_audit, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(pre_submission_audit, "MANIFESTS_DIR", manifests_dir)

    writes = pre_submission_audit.write_pre_submission_outputs(selected_venues=["neurips"])
    report_json = reports_dir / "pre_submission_audit_neurips.json"
    report_md = reports_dir / "pre_submission_audit_neurips.md"
    manifest = manifests_dir / "pre_submission_audit_neurips.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["audit_id"] == "pre_submission_audit_neurips_v1"
    assert payload["venues"]["checked"] == 1
    assert payload["venue_scope"]["venue_ids"] == ["neurips"]


def test_cli_check_pre_submission_audit_strict_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
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
    assert payload["report"]["submission_gate"]["status"] == "blocked"
    assert payload["report"]["bibliography_scope_gate"]["status"] == "blocked"
    assert payload["report"]["venues"]["verification_pending"] >= 1


def test_cli_check_pre_submission_audit_can_scope_to_one_venue() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--venue",
            "neurips",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["venues"]["checked"] == 1
    assert payload["report"]["venue_scope"]["venue_ids"] == ["neurips"]
    assert payload["report"]["submission_gate"]["failed_count"] == 1
    assert payload["report"]["bibliography_scope_gate"]["status"] == "blocked"


def test_cli_check_pre_submission_audit_requires_current_venue_verification() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--json",
            "--strict",
            "--require-current-venue-verification",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["submission_gate"]["status"] == "blocked"
    assert payload["report"]["submission_gate"]["failed_count"] >= 1


def test_cli_check_pre_submission_audit_requires_confirmed_manuscript_bibliography() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--json",
            "--strict",
            "--require-confirmed-manuscript-bibliography",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["bibliography_scope_gate"]["status"] == "blocked"


def test_cli_check_pre_submission_audit_requires_current_venue_verification_for_one_venue() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--venue",
            "neurips",
            "--json",
            "--strict",
            "--require-current-venue-verification",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report"]["venues"]["checked"] == 1
    assert payload["report"]["submission_gate"]["failed_count"] == 1
    assert payload["report"]["submission_gate"]["failed_venues"][0]["venue"] == "neurips"


def test_cli_check_pre_submission_audit_requires_confirmed_manuscript_bibliography_for_one_venue() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--venue",
            "neurips",
            "--json",
            "--strict",
            "--require-confirmed-manuscript-bibliography",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report"]["venues"]["checked"] == 1
    assert payload["report"]["bibliography_scope_gate"]["status"] == "blocked"


def test_cli_check_pre_submission_audit_unknown_venue_returns_json_error() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_pre_submission_audit.py",
            "--venue",
            "not_a_real_venue",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Unknown venue ids for pre-submission audit" in payload["error"]
