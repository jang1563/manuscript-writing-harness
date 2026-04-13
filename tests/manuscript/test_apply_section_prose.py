#!/usr/bin/env python3
"""Tests for applying generated section prose into manuscript sections."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from apply_section_prose import END_MARKER, START_MARKER, apply_section_prose


def test_apply_section_prose_updates_expected_sections() -> None:
    payload = apply_section_prose()
    assert payload["updated_sections"] == [
        "manuscript/sections/01_summary.md",
        "manuscript/sections/02_introduction.md",
        "manuscript/sections/04_discussion.md",
        "manuscript/sections/05_methods.md",
    ]


def test_canonical_sections_contain_managed_include_blocks() -> None:
    apply_section_prose()
    for relative in (
        "manuscript/sections/01_summary.md",
        "manuscript/sections/02_introduction.md",
        "manuscript/sections/04_discussion.md",
        "manuscript/sections/05_methods.md",
    ):
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert START_MARKER in text
        assert END_MARKER in text
    intro = (REPO_ROOT / "manuscript/sections/02_introduction.md").read_text(encoding="utf-8")
    assert "../drafts/section_bodies/introduction.md" in intro


def test_apply_section_prose_cli_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/apply_section_prose.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "updated_sections" in payload
