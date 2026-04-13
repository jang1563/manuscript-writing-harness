#!/usr/bin/env python3
"""Tests for fgsea study dossier generation."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fgsea_study_dossier import build_fgsea_study_dossier  # type: ignore


def test_build_fgsea_study_dossier_for_active_template() -> None:
    report = build_fgsea_study_dossier(
        REPO_ROOT / "pathways/studies/rnaseq_case_control_template/configs/fgsea.yml"
    )
    assert report["readiness"] == "ready"
    assert report["active_profile"]["is_active_source"] is True
    assert report["active_profile"]["figure_05_sync"]["status"] == "synced"
    assert report["inputs"]["raw_input_rows"] >= 1
    assert report["rank_prep"]["status"] == "ready"
    assert report["fgsea"]["status"] == "ready"


def test_build_fgsea_study_dossier_for_msigdb_scaffold_without_gmt() -> None:
    report = build_fgsea_study_dossier(
        REPO_ROOT / "pathways/studies/msigdb_hallmark_demo/configs/fgsea.yml"
    )
    assert report["study_kind"] == "msigdb"
    assert report["readiness"] == "provisional"
    assert report["active_profile"]["is_active_source"] is False
    assert report["rank_prep"]["status"] == "ready"
    assert any("MSigDB GMT" in issue for issue in report["blocking_issues"])
