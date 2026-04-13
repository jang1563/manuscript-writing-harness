from __future__ import annotations

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
    assert {"nature", "cell", "science", "conference"} == venues
    assert all(item["readiness"] == "ready" for item in payload["venues"])


def test_readiness_markdown_mentions_package_paths() -> None:
    report = venue_overlay.evaluate_venue("science")
    markdown = venue_overlay.render_readiness_markdown(report)
    assert "# Science Venue Readiness" in markdown
    assert "## Package Paths" in markdown
    assert "`manuscript/supplementary/science_package/README.md`" in markdown
