#!/usr/bin/env python3
"""Tests for manuscript section-brief generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from manuscript_section_briefs import build_section_briefs, render_section_briefs_markdown, write_section_brief_outputs


def test_section_briefs_follow_manuscript_order() -> None:
    briefs = build_section_briefs()
    section_ids = [section["section_id"] for section in briefs["sections"]]
    assert section_ids == ["summary", "introduction", "results", "discussion", "methods"]
    assert briefs["section_count"] == 5


def test_results_section_brief_covers_display_backed_results() -> None:
    briefs = build_section_briefs()
    results = next(section for section in briefs["sections"] if section["section_id"] == "results")
    assert results["claim_packet_count"] == 20
    assert "figure_01_example" in results["display_item_ids"]
    assert "figure_11_ablation_summary" in results["display_item_ids"]
    assert "table_01_main" in results["display_item_ids"]


def test_section_briefs_are_ready_when_reference_layer_is_ready() -> None:
    briefs = build_section_briefs()
    assert briefs["overall_status"] == "ready"
    results = next(section for section in briefs["sections"] if section["section_id"] == "results")
    assert results["status"] == "ready"


def test_section_brief_markdown_mentions_results_and_methods() -> None:
    markdown = render_section_briefs_markdown(build_section_briefs())
    assert "# Section Draft Briefs" in markdown
    assert "## results" in markdown
    assert "## methods" in markdown


def test_write_section_brief_outputs_creates_artifacts() -> None:
    outputs = write_section_brief_outputs()
    assert (REPO_ROOT / outputs["section_briefs"]).exists()
    assert (REPO_ROOT / outputs["section_briefs_markdown"]).exists()


def test_section_brief_cli_exits_zero_for_ready_state() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_section_briefs.py",
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
    assert payload["briefs"]["overall_status"] == "ready"
