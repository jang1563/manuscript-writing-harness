#!/usr/bin/env python3
"""Tests for the tracked agent registry."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_agent_registry import load_agent_registry, validate_agent_registry


EXPECTED_AGENT_IDS = [
    "evaluation_agent",
    "figure_agent",
    "literature_grounding_agent",
    "planning_agent",
    "project_handoff_agent",
    "release_packaging_agent",
    "review_evidence_agent",
    "section_writing_agent",
    "submission_readiness_agent",
    "venue_compliance_agent",
]


def test_agent_registry_contains_expected_agent_set() -> None:
    payload = load_agent_registry()
    agent_ids = sorted(agent["agent_id"] for agent in payload["agents"])
    assert agent_ids == EXPECTED_AGENT_IDS


def test_agent_registry_validates_current_repo() -> None:
    report = validate_agent_registry(load_agent_registry())
    assert report["status"] == "ready"
    assert report["errors"] == []
    assert report["agent_count"] == len(EXPECTED_AGENT_IDS)


def test_check_agent_registry_cli_emits_json() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/check_agent_registry.py", "--json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ready"
    assert payload["agent_ids"] == EXPECTED_AGENT_IDS
