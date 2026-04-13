#!/usr/bin/env python3
"""Tests for manuscript section prose generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from manuscript_section_prose import build_section_prose, render_section_prose_markdown, write_section_prose_outputs


def test_section_prose_covers_all_sections() -> None:
    prose = build_section_prose()
    section_ids = [section["section_id"] for section in prose["sections"]]
    assert section_ids == ["summary", "introduction", "results", "discussion", "methods"]


def test_results_section_contains_many_subsections() -> None:
    prose = build_section_prose()
    results = next(section for section in prose["sections"] if section["section_id"] == "results")
    assert len(results["subsections"]) == 20
    assert results["subsections"][0]["display_item_id"] == "figure_01_example"
    assert results["subsections"][-1]["display_item_id"] == "table_01_main"


def test_prose_markdown_mentions_introduction_and_results() -> None:
    markdown = render_section_prose_markdown(build_section_prose())
    assert "# Section Prose Drafts" in markdown
    assert "## Introduction" in markdown
    assert "## Results" in markdown


def test_write_section_prose_outputs_creates_artifacts() -> None:
    outputs = write_section_prose_outputs()
    assert (REPO_ROOT / outputs["section_prose"]).exists()
    assert (REPO_ROOT / outputs["section_prose_markdown"]).exists()
    assert (REPO_ROOT / outputs["section_directory"] / "results.md").exists()


def test_section_prose_cli_exits_zero_for_ready_state() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_section_prose.py",
            "--write",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["prose"]["overall_status"] == "ready"
