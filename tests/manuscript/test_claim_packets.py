#!/usr/bin/env python3
"""Tests for manuscript claim packet generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from manuscript_claims import build_claim_coverage, build_claim_packets, render_results_claim_packets_markdown, write_claim_outputs


def test_claim_packets_cover_all_display_claims() -> None:
    packets = build_claim_packets()
    claim_ids = [packet["claim_id"] for packet in packets["claims"]]
    assert packets["claim_count"] == len(claim_ids)
    assert packets["claim_count"] == 20
    assert packets["blocked_claim_count"] == 0


def test_claim_packets_are_ready_when_reference_layer_is_ready() -> None:
    packets = build_claim_packets()
    coverage = build_claim_coverage(packets)
    assert packets["overall_status"] == "ready"
    assert coverage["overall_status"] == "ready"
    assert coverage["blocked_claim_count"] == 0
    assert coverage["provisional_claim_ids"] == []
    assert len(coverage["claims_with_citation_edges"]) == packets["claim_count"]


def test_claim_packet_markdown_mentions_core_artifacts() -> None:
    markdown = render_results_claim_packets_markdown(build_claim_packets())
    assert "# Results Claim Draft Packets" in markdown
    assert "## claim_response_kinetics" in markdown
    assert "`figure_01_example`" in markdown
    assert "`figures/fact_sheets/figure_01_example.json`" in markdown


def test_write_claim_outputs_creates_tracked_artifacts() -> None:
    outputs = write_claim_outputs()
    assert (REPO_ROOT / outputs["claim_packets"]).exists()
    assert (REPO_ROOT / outputs["claim_coverage"]).exists()
    assert (REPO_ROOT / outputs["draft_markdown"]).exists()


def test_claim_coverage_cli_exits_zero_for_ready_state() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_claim_coverage.py",
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
    assert payload["coverage"]["overall_status"] == "ready"
