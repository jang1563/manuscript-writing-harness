#!/usr/bin/env python3
"""Tests for author-supplied manuscript content inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import manuscript_claims
import manuscript_section_briefs
import manuscript_section_drafts


def test_author_content_inputs_propagate_through_results_pipeline(tmp_path, monkeypatch) -> None:
    author_inputs_path = tmp_path / "author_content_inputs.json"
    author_inputs_path.write_text(
        json.dumps(
            {
                "topic": "Therapy response trajectories in a multimodal benchmark",
                "section_notes": {
                    "results": "Start the Results with the strongest treatment-response separation.",
                },
                "claim_notes": {
                    "claim_response_kinetics": "Use this as the opening sentence for the first results subsection."
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(manuscript_claims, "AUTHOR_CONTENT_INPUTS_PATH", author_inputs_path)
    monkeypatch.setattr(manuscript_section_briefs, "CLAIM_PACKETS_PATH", tmp_path / "claim_packets.json")
    monkeypatch.setattr(manuscript_section_drafts, "CLAIM_PACKETS_PATH", tmp_path / "claim_packets.json")
    monkeypatch.setattr(manuscript_section_drafts, "SECTION_BRIEFS_JSON_PATH", tmp_path / "section_briefs.json")

    packets = manuscript_claims.build_claim_packets()
    response_packet = next(packet for packet in packets["claims"] if packet["claim_id"] == "claim_response_kinetics")
    assert packets["author_inputs"]["topic"] == "Therapy response trajectories in a multimodal benchmark"
    assert response_packet["author_input"]["claim_note"].startswith("Use this as the opening sentence")

    briefs = manuscript_section_briefs.build_section_briefs()
    results_brief = next(section for section in briefs["sections"] if section["section_id"] == "results")
    assert results_brief["author_input"]["section_note"].startswith("Start the Results")
    assert results_brief["author_input"]["claim_notes"]["claim_response_kinetics"].startswith("Use this")

    drafts = manuscript_section_drafts.build_section_drafts()
    results_draft = next(section for section in drafts["sections"] if section["section_id"] == "results")
    first_subsection = next(
        item for item in results_draft["subsection_plan"] if item["claim_id"] == "claim_response_kinetics"
    )
    assert results_draft["manuscript_topic"] == "Therapy response trajectories in a multimodal benchmark"
    assert first_subsection["author_note"].startswith("Use this as the opening sentence")


def test_unknown_author_claim_ids_raise_clear_error(tmp_path, monkeypatch) -> None:
    author_inputs_path = tmp_path / "author_content_inputs.json"
    author_inputs_path.write_text(
        json.dumps(
            {
                "topic": "Example topic",
                "section_notes": {},
                "claim_notes": {
                    "claim_not_in_repo": "This should stop generation until the claim source is clarified."
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(manuscript_claims, "AUTHOR_CONTENT_INPUTS_PATH", author_inputs_path)

    with pytest.raises(ValueError, match="unknown claim_ids"):
        manuscript_claims.build_claim_packets()
