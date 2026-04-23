from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import manuscript_scope_common


def _write_scope(repo_root: Path, payload: dict[str, object]) -> Path:
    path = repo_root / "manuscript" / "plans" / "manuscript_scope.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_build_manuscript_scope_status_is_provisional_for_current_repo() -> None:
    report = manuscript_scope_common.build_manuscript_scope_status(REPO_ROOT)
    gate = manuscript_scope_common.build_manuscript_scope_gate(report)
    assert report["status"] == "provisional"
    assert report["scope_status"] == "exemplar"
    assert gate["status"] == "blocked"
    assert gate["current_scope_status"] == "exemplar"


def test_build_manuscript_scope_status_rejects_invalid_scope_status(tmp_path: Path) -> None:
    _write_scope(
        tmp_path,
        {
            "scope_status": "drafty",
            "confirmed_on": None,
            "note": "Testing invalid status.",
        },
    )
    report = manuscript_scope_common.build_manuscript_scope_status(tmp_path)
    assert report["status"] == "invalid"
    assert "`scope_status` must be one of exemplar, mixed, or real" in report["issues"]


def test_build_manuscript_scope_status_requires_note(tmp_path: Path) -> None:
    _write_scope(
        tmp_path,
        {
            "scope_status": "mixed",
            "confirmed_on": None,
            "note": "",
        },
    )
    report = manuscript_scope_common.build_manuscript_scope_status(tmp_path)
    assert report["status"] == "invalid"
    assert "`note` is required" in report["issues"]


def test_build_manuscript_scope_status_rejects_future_confirmation_date(tmp_path: Path) -> None:
    _write_scope(
        tmp_path,
        {
            "scope_status": "real",
            "confirmed_on": (date.today() + timedelta(days=1)).isoformat(),
            "note": "Future dates are not allowed.",
        },
    )
    report = manuscript_scope_common.build_manuscript_scope_status(tmp_path)
    assert report["status"] == "invalid"
    assert "`confirmed_on` must not be in the future" in report["issues"]


def test_build_manuscript_scope_status_requires_confirmation_date_for_real(tmp_path: Path) -> None:
    _write_scope(
        tmp_path,
        {
            "scope_status": "real",
            "confirmed_on": None,
            "note": "Real manuscript scope requires a confirmation date.",
        },
    )
    report = manuscript_scope_common.build_manuscript_scope_status(tmp_path)
    gate = manuscript_scope_common.build_manuscript_scope_gate(report)
    assert report["status"] == "invalid"
    assert "`confirmed_on` is required when `scope_status` is `real`" in report["issues"]
    assert gate["status"] == "blocked"
