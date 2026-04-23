from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import venue_overlay


def test_all_venue_configs_evaluate_ready() -> None:
    venues = sorted(path.stem for path in venue_overlay.VENUE_CONFIG_DIR.glob("*.yml"))
    assert venues
    for venue_id in venues:
        report = venue_overlay.evaluate_venue(venue_id)
        assert report["readiness"] == "ready"
        assert report["blocking_items"] == []
        assert report["config_path"] == f"workflows/venue_configs/{venue_id}.yml"
        assert report["checklist_path"] == f"workflows/checklists/{venue_id}_submission.md"
        assert report["display_name"]
        assert report["verification"]["last_verified"]
        assert report["verification"]["status"] in {"current", "needs_submission_confirmation", "stale", "invalid"}


def test_cell_readiness_includes_overlay_assets() -> None:
    report = venue_overlay.evaluate_venue("cell")
    section_ids = {item["id"] for item in report["required_sections"]}
    asset_ids = {item["id"] for item in report["special_assets"]}
    assert "highlights" in section_ids
    assert "graphical_abstract" in section_ids
    assert "key_resources_table" in section_ids
    assert "graphical_abstract" in asset_ids
    assert "key_resources_table" in asset_ids
    assert "manuscript/frontmatter/highlights.md" in report["package_paths"]
    assert "tables/key_resources/key_resources_table.md" in report["package_paths"]


def test_write_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(venue_overlay, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(venue_overlay, "MANIFESTS_DIR", manifests_dir)

    writes = venue_overlay.write_venue_outputs("nature")
    report_json = Path(writes["report_json"])
    report_md = Path(writes["report_md"])
    manifest = Path(writes["manifest"])

    assert report_json == reports_dir / "nature_readiness.json"
    assert report_md == reports_dir / "nature_readiness.md"
    assert manifest == manifests_dir / "nature_submission_package.json"
    assert report_json.exists()
    assert report_md.exists()
    assert manifest.exists()

    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["venue"] == "nature"
    assert payload["readiness"] == "ready"


def test_cli_can_emit_all_venues_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_venue_readiness.py",
            "--all",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    venues = {item["venue"] for item in payload["venues"]}
    assert {"nature", "cell", "science", "conference", "acm_sigconf", "ieee_vis", "neurips", "icml"} == venues
    assert all(item["readiness"] == "ready" for item in payload["venues"])
    assert all("verification" in item for item in payload["venues"])
    assert payload["submission_gate"]["status"] == "blocked"


def test_conference_specializations_capture_expected_assets_and_notes() -> None:
    neurips = venue_overlay.evaluate_venue("neurips")
    icml = venue_overlay.evaluate_venue("icml")
    acm = venue_overlay.evaluate_venue("acm_sigconf")
    ieee = venue_overlay.evaluate_venue("ieee_vis")

    assert neurips["display_name"] == "NeurIPS"
    assert icml["display_name"] == "ICML"
    assert acm["display_name"] == "ACM SIGCONF"
    assert ieee["display_name"] == "IEEE VIS"

    assert {item["id"] for item in neurips["special_assets"]} == {"anonymization_check"}
    assert {item["id"] for item in icml["special_assets"]} == {"anonymization_check"}
    assert {item["id"] for item in acm["special_assets"]} == {"anonymization_check"}
    assert ieee["special_assets"] == []

    assert "workflows/release/anonymization_check.md" in neurips["package_paths"]
    assert any("double-blind" in note.lower() for note in neurips["notes"])
    assert any("double-blind" in note.lower() for note in icml["notes"])
    assert any("sigconf" in note.lower() for note in acm["notes"])
    assert any("single-blind or double-blind" in note.lower() for note in ieee["notes"])
    assert neurips["verification"]["status"] == "needs_submission_confirmation"
    assert icml["verification"]["status"] == "needs_submission_confirmation"
    assert acm["verification"]["status"] == "needs_submission_confirmation"
    assert ieee["verification"]["status"] == "needs_submission_confirmation"


def test_readiness_markdown_mentions_package_paths() -> None:
    report = venue_overlay.evaluate_venue("science")
    markdown = venue_overlay.render_readiness_markdown(report)
    assert "# Science Venue Readiness" in markdown
    assert "## Verification" in markdown
    assert "## Package Paths" in markdown
    assert "`manuscript/supplementary/science_package/README.md`" in markdown


def test_venue_verification_can_become_stale(monkeypatch) -> None:
    class FrozenDate(venue_overlay.date):
        @classmethod
        def today(cls):
            return cls(2027, 1, 1)

    monkeypatch.setattr(venue_overlay, "date", FrozenDate)
    report = venue_overlay.evaluate_venue("neurips")
    assert report["verification"]["status"] == "stale"
    assert report["verification"]["stale"] is True


def test_future_verification_date_is_invalid() -> None:
    verification = venue_overlay._evaluate_verification(
        {
            "verification": {
                "last_verified": "2099-01-01",
                "stale_after_days": 180,
                "final_confirmation_required": False,
                "source_summary": "Future-dated verification.",
            }
        }
    )
    assert verification["status"] == "invalid"
    assert verification["days_since_verification"] is None
    assert "verification.last_verified must not be in the future" in verification["issues"]


def test_invalid_verification_blocks_venue_readiness(monkeypatch) -> None:
    original = venue_overlay.load_venue_config
    invalid_config = copy.deepcopy(original("neurips"))
    invalid_config["verification"] = {
        "last_verified": "2099-01-01",
        "stale_after_days": 180,
        "final_confirmation_required": False,
        "source_summary": "Future-dated verification.",
    }

    def fake_load_venue_config(venue_id: str):
        if venue_id == "neurips":
            return invalid_config
        return original(venue_id)

    monkeypatch.setattr(venue_overlay, "load_venue_config", fake_load_venue_config)
    report = venue_overlay.evaluate_venue("neurips")
    assert report["readiness"] == "blocked"
    assert report["blocking_items"] == []
    assert report["blocking_issues"] == [
        "invalid verification metadata: verification.last_verified must not be in the future"
    ]


def test_cli_require_current_verification_fails_for_current_repo() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_venue_readiness.py",
            "--all",
            "--json",
            "--strict",
            "--require-current-verification",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["submission_gate"]["status"] == "blocked"
    assert payload["submission_gate"]["failed_count"] >= 1


def test_cli_unknown_venue_returns_json_error() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_venue_readiness.py",
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
    assert "Unknown venue" in payload["error"]
