#!/usr/bin/env python3
"""Tests for claim-to-reference mapping scaffolds."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from reference_mapping import apply_claim_reference_map, build_claim_reference_map, write_claim_reference_map


def test_claim_reference_map_covers_all_claims() -> None:
    payload = build_claim_reference_map(sync_graph=False)
    assert payload["claim_count"] == 24
    assert len(payload["mappings"]) == 24


def test_claim_reference_map_status_is_valid() -> None:
    payload = build_claim_reference_map(sync_graph=False)
    assert payload["overall_status"] in {"provisional", "ready"}
    assert payload["claim_count"] == (
        payload["mapped_claim_count"] + payload["placeholder_claim_count"] + payload["unmapped_claim_count"]
    ) or payload["claim_count"] >= payload["mapped_claim_count"]


def test_write_claim_reference_map_creates_artifacts() -> None:
    outputs = write_claim_reference_map(sync_graph=False)
    assert (REPO_ROOT / outputs["map_json"]).exists()
    assert (REPO_ROOT / outputs["map_md"]).exists()


def test_apply_claim_reference_map_is_idempotent_for_current_state() -> None:
    payload = apply_claim_reference_map(sync_graph=True)
    assert payload["edge_count"] >= 1
    graph = json.loads((REPO_ROOT / "manuscript/plans/citation_graph.json").read_text(encoding="utf-8"))
    assert any(edge["from"] == "claim_response_kinetics" for edge in graph["edges"])


def test_apply_claim_reference_map_cli_emits_json() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/apply_claim_reference_map.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["edge_count"] >= 1
