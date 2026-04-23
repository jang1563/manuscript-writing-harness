from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import confirm_manuscript_scope
import manuscript_scope_common


SAMPLE_SCOPE = {
    "scope_status": "exemplar",
    "confirmed_on": None,
    "note": "The tracked manuscript still uses exemplar/demo scientific content.",
}


def _write_scope(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(SAMPLE_SCOPE, indent=2) + "\n", encoding="utf-8")


def test_confirm_manuscript_scope_dry_run_leaves_file_unchanged(tmp_path: Path) -> None:
    manifest = tmp_path / "manuscript" / "plans" / "manuscript_scope.json"
    _write_scope(manifest)
    original = manifest.read_text(encoding="utf-8")

    payload = confirm_manuscript_scope.confirm_manuscript_scope(
        note="Confirmed against the finalized manuscript package for submission.",
        confirmed_on="2026-04-21",
        dry_run=True,
        manifest_path=manifest,
    )

    assert payload["dry_run"] is True
    assert payload["updated"] is False
    assert payload["manuscript_scope_after"]["scope_status"] == "real"
    assert payload["manuscript_scope_after"]["confirmed_on"] == "2026-04-21"
    assert manifest.read_text(encoding="utf-8") == original


def test_confirm_manuscript_scope_writes_manifest_and_makes_scope_ready(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest = repo_root / "manuscript" / "plans" / "manuscript_scope.json"
    _write_scope(manifest)

    payload = confirm_manuscript_scope.confirm_manuscript_scope(
        note="Confirmed against the finalized manuscript package for submission.",
        confirmed_on="2026-04-21",
        manifest_path=manifest,
    )

    assert payload["updated"] is True
    report = manuscript_scope_common.build_manuscript_scope_status(repo_root)
    gate = manuscript_scope_common.build_manuscript_scope_gate(report)
    assert report["status"] == "ready"
    assert report["scope_status"] == "real"
    assert report["confirmed_on"] == "2026-04-21"
    assert gate["status"] == "ready"


def test_confirm_manuscript_scope_rejects_future_date(tmp_path: Path) -> None:
    manifest = tmp_path / "manuscript" / "plans" / "manuscript_scope.json"
    _write_scope(manifest)

    try:
        confirm_manuscript_scope.confirm_manuscript_scope(
            note="Confirmed against the finalized manuscript package for submission.",
            confirmed_on="2099-01-01",
            manifest_path=manifest,
        )
    except ValueError as exc:
        assert "must not be in the future" in str(exc)
    else:
        raise AssertionError("Expected future confirmed_on to raise ValueError")


def test_confirm_manuscript_scope_requires_nonblank_note(tmp_path: Path) -> None:
    manifest = tmp_path / "manuscript" / "plans" / "manuscript_scope.json"
    _write_scope(manifest)

    try:
        confirm_manuscript_scope.confirm_manuscript_scope(
            note="   ",
            confirmed_on="2026-04-21",
            manifest_path=manifest,
        )
    except ValueError as exc:
        assert "note must not be blank" in str(exc)
    else:
        raise AssertionError("Expected blank note to raise ValueError")


def test_cli_confirm_manuscript_scope_json(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "manuscript" / "plans" / "manuscript_scope.json"
    _write_scope(manifest)

    monkeypatch.setattr(confirm_manuscript_scope, "MANUSCRIPT_SCOPE_PATH", manifest)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "confirm_manuscript_scope.py",
            "--note",
            "Confirmed against the finalized manuscript package for submission.",
            "--date",
            "2026-04-21",
            "--dry-run",
            "--json",
        ],
    )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert confirm_manuscript_scope.main() == 0
    payload = json.loads(stdout.getvalue())
    assert payload["dry_run"] is True
    assert payload["manuscript_scope_after"]["scope_status"] == "real"
