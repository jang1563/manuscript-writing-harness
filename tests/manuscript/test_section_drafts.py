#!/usr/bin/env python3
"""Tests for manuscript section draft scaffold generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from manuscript_section_drafts import build_section_drafts, render_section_drafts_markdown, write_section_draft_outputs


def test_section_drafts_follow_manuscript_order() -> None:
    drafts = build_section_drafts()
    section_ids = [section["section_id"] for section in drafts["sections"]]
    assert section_ids == ["summary", "introduction", "results", "discussion", "methods"]
    assert drafts["section_count"] == 5


def test_results_section_draft_contains_display_backed_subsections() -> None:
    drafts = build_section_drafts()
    results = next(section for section in drafts["sections"] if section["section_id"] == "results")
    assert len(results["subsection_plan"]) == 20
    assert results["subsection_plan"][0]["display_item_id"] == "figure_01_example"
    assert results["subsection_plan"][-1]["display_item_id"] == "table_01_main"


def test_section_drafts_are_ready_when_inputs_are_ready() -> None:
    drafts = build_section_drafts()
    assert drafts["overall_status"] == "ready"
    results = next(section for section in drafts["sections"] if section["section_id"] == "results")
    assert results["status"] == "ready"


def test_section_draft_markdown_mentions_results_and_discussion() -> None:
    markdown = render_section_drafts_markdown(build_section_drafts())
    assert "# Section Draft Scaffolds" in markdown
    assert "## results" in markdown
    assert "## discussion" in markdown


def test_write_section_draft_outputs_creates_artifacts() -> None:
    outputs = write_section_draft_outputs()
    assert (REPO_ROOT / outputs["section_drafts"]).exists()
    assert (REPO_ROOT / outputs["section_drafts_markdown"]).exists()


def test_section_draft_cli_exits_zero_for_ready_state() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_section_drafts.py",
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
    assert payload["drafts"]["overall_status"] == "ready"
