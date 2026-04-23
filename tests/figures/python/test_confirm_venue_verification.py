from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from contextlib import redirect_stdout

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import confirm_venue_verification


SAMPLE_CONFIG = """\
name: Test Venue
verification:
  last_verified: 2026-04-16
  stale_after_days: 180
  final_confirmation_required: true
  source_summary: Baseline guidance check.
required_sections:
  - abstract
special_assets: []
notes:
  - Example note.
"""


def test_confirm_venue_verification_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    config_dir = tmp_path / "venue_configs"
    config_dir.mkdir()
    config_path = config_dir / "testvenue.yml"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

    payload = confirm_venue_verification.confirm_venue_verification(
        "testvenue",
        source_summary="Confirmed against the target 2026 CFP.",
        verified_on="2026-04-17",
        dry_run=True,
        config_dir=config_dir,
        repo_root=tmp_path,
    )

    assert payload["dry_run"] is True
    assert payload["updated"] is False
    assert payload["verification_after"]["final_confirmation_required"] is False
    assert payload["verification_after"]["last_verified"] == "2026-04-17"
    assert config_path.read_text(encoding="utf-8") == SAMPLE_CONFIG


def test_confirm_venue_verification_writes_updated_yaml(tmp_path: Path) -> None:
    config_dir = tmp_path / "venue_configs"
    config_dir.mkdir()
    config_path = config_dir / "testvenue.yml"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

    payload = confirm_venue_verification.confirm_venue_verification(
        "testvenue",
        source_summary="Confirmed against the target 2026 CFP.",
        verified_on="2026-04-17",
        stale_after_days=90,
        config_dir=config_dir,
        repo_root=tmp_path,
    )

    assert payload["updated"] is True
    updated = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert updated["verification"]["last_verified"] == "2026-04-17"
    assert updated["verification"]["stale_after_days"] == 90
    assert updated["verification"]["final_confirmation_required"] is False
    assert updated["verification"]["source_summary"] == "Confirmed against the target 2026 CFP."


def test_confirm_venue_verification_rejects_blank_summary(tmp_path: Path) -> None:
    config_dir = tmp_path / "venue_configs"
    config_dir.mkdir()
    config_path = config_dir / "testvenue.yml"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

    try:
        confirm_venue_verification.confirm_venue_verification(
            "testvenue",
            source_summary="   ",
            config_dir=config_dir,
            repo_root=tmp_path,
        )
    except ValueError as exc:
        assert "source_summary" in str(exc)
    else:
        raise AssertionError("Expected blank source_summary to raise ValueError")


def test_confirm_venue_verification_rejects_future_date(tmp_path: Path) -> None:
    config_dir = tmp_path / "venue_configs"
    config_dir.mkdir()
    config_path = config_dir / "testvenue.yml"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

    try:
        confirm_venue_verification.confirm_venue_verification(
            "testvenue",
            source_summary="Confirmed against the target 2026 CFP.",
            verified_on="2099-01-01",
            config_dir=config_dir,
            repo_root=tmp_path,
        )
    except ValueError as exc:
        assert "must not be in the future" in str(exc)
    else:
        raise AssertionError("Expected future verified_on to raise ValueError")


def test_cli_confirm_venue_verification_json(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / "venue_configs"
    config_dir.mkdir()
    config_path = config_dir / "testvenue.yml"
    config_path.write_text(SAMPLE_CONFIG, encoding="utf-8")

    monkeypatch.setattr(confirm_venue_verification, "VENUE_CONFIG_DIR", config_dir)
    monkeypatch.setattr(confirm_venue_verification, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "confirm_venue_verification.py",
            "--venue",
            "testvenue",
            "--source-summary",
            "Confirmed against the target 2026 CFP.",
            "--date",
            "2026-04-17",
            "--dry-run",
            "--json",
        ],
    )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert confirm_venue_verification.main() == 0
    payload = json.loads(stdout.getvalue())
    assert payload["venue"] == "testvenue"
    assert payload["dry_run"] is True
    assert payload["verification_after"]["final_confirmation_required"] is False
