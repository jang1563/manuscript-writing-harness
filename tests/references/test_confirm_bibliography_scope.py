from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import confirm_bibliography_scope


SAMPLE_MANIFEST = """\
source_type: zotero_better_bibtex_auto_export
status: configured
translator: Better BibTeX
export_mode: keep_updated
output:
  path: references/library.bib
  relative_to: repo_root
  format: bibtex
  encoding: utf-8
policy:
  allow_manual_edits: false
manuscript_scope:
  confirmed: false
  note: Starter bibliography still in place.
"""


def test_confirm_bibliography_scope_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    manifest = tmp_path / "bibliography_source.yml"
    manifest.write_text(SAMPLE_MANIFEST, encoding="utf-8")

    payload = confirm_bibliography_scope.confirm_bibliography_scope(
        note="Confirmed against the accepted manuscript Zotero export.",
        confirmed_on="2026-04-18",
        dry_run=True,
        manifest_path=manifest,
    )

    assert payload["dry_run"] is True
    assert payload["updated"] is False
    assert payload["manuscript_scope_after"]["confirmed"] is True
    assert payload["manuscript_scope_after"]["confirmed_on"] == "2026-04-18"
    assert manifest.read_text(encoding="utf-8") == SAMPLE_MANIFEST


def test_confirm_bibliography_scope_writes_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "bibliography_source.yml"
    manifest.write_text(SAMPLE_MANIFEST, encoding="utf-8")

    payload = confirm_bibliography_scope.confirm_bibliography_scope(
        note="Confirmed against the accepted manuscript Zotero export.",
        confirmed_on="2026-04-18",
        manifest_path=manifest,
    )

    assert payload["updated"] is True
    updated = manifest.read_text(encoding="utf-8")
    assert "confirmed: true" in updated
    assert "confirmed_on: '2026-04-18'" in updated or "confirmed_on: 2026-04-18" in updated


def test_confirm_bibliography_scope_rejects_future_date(tmp_path: Path) -> None:
    manifest = tmp_path / "bibliography_source.yml"
    manifest.write_text(SAMPLE_MANIFEST, encoding="utf-8")

    try:
        confirm_bibliography_scope.confirm_bibliography_scope(
            note="Confirmed against the accepted manuscript Zotero export.",
            confirmed_on="2099-01-01",
            manifest_path=manifest,
        )
    except ValueError as exc:
        assert "must not be in the future" in str(exc)
    else:
        raise AssertionError("Expected future confirmed_on to raise ValueError")


def test_cli_confirm_bibliography_scope_json(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "bibliography_source.yml"
    manifest.write_text(SAMPLE_MANIFEST, encoding="utf-8")

    monkeypatch.setattr(confirm_bibliography_scope, "BIBLIOGRAPHY_SOURCE_MANIFEST", manifest)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "confirm_bibliography_scope.py",
            "--note",
            "Confirmed against the accepted manuscript Zotero export.",
            "--date",
            "2026-04-18",
            "--dry-run",
            "--json",
        ],
    )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert confirm_bibliography_scope.main() == 0
    payload = json.loads(stdout.getvalue())
    assert payload["dry_run"] is True
    assert payload["manuscript_scope_after"]["confirmed"] is True
