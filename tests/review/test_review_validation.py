#!/usr/bin/env python3
"""Tests for reusable review validation helpers."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from review_common import validate_review_artifacts


def test_validate_review_artifacts_is_ready_for_demo_repo() -> None:
    validation = validate_review_artifacts()
    assert validation["overall_status"] == "ready"
    assert validation["issue_count"] == 0
    assert validation["component_status"]["protocol"] == "ready"
    assert validation["component_status"]["extraction"] == "ready"
    assert validation["component_status"]["bias"] == "ready"
