#!/usr/bin/env python3
"""Integration checks for fgsea-driven pathway figure inputs."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PYTHON_FIGURES_DIR = REPO_ROOT / "figures" / "src" / "python"
for path in (str(SCRIPTS_DIR), str(PYTHON_FIGURES_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from common import resolve_data_input  # type: ignore
from common import load_fgsea_summary_for_export  # type: ignore


ACTIVE_EXPORT = REPO_ROOT / "pathways/results/active_fgsea/fgsea_pathway_dot_export.csv"
ACTIVE_SUMMARY = REPO_ROOT / "pathways/results/active_fgsea/fgsea_summary.json"


def require_active_fgsea_outputs() -> None:
    if not ACTIVE_EXPORT.exists() or not ACTIVE_SUMMARY.exists():
        pytest.skip("requires generated active fgsea outputs from build_phase2.py")


def test_pathway_figure_prefers_fgsea_export_when_present() -> None:
    require_active_fgsea_outputs()
    spec = yaml.safe_load((REPO_ROOT / "figures/specs/figure_05_pathway_enrichment_dot.yml").read_text(encoding="utf-8"))
    resolved = resolve_data_input(spec, 0)
    assert resolved == ACTIVE_EXPORT
    assert resolved.exists()


def test_load_fgsea_summary_for_active_export() -> None:
    require_active_fgsea_outputs()
    payload = load_fgsea_summary_for_export(ACTIVE_EXPORT)
    assert payload is not None
    assert payload["run_id"] == "fgsea_active"
    assert payload["summary_json"] == "pathways/results/active_fgsea/fgsea_summary.json"
    assert "raw_input_table" in payload
    assert "rank_prep_summary" in payload


def test_pathway_figure_handles_empty_fgsea_export() -> None:
    require_active_fgsea_outputs()
    module_path = REPO_ROOT / "figures/src/python/classes/pathway_enrichment_dot.py"
    module_spec = importlib.util.spec_from_file_location("test_pathway_enrichment_dot_empty", module_path)
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    spec_path = REPO_ROOT / "figures/specs/figure_05_pathway_enrichment_dot.yml"
    original_export = ACTIVE_EXPORT.read_text(encoding="utf-8")
    original_summary = ACTIVE_SUMMARY.read_text(encoding="utf-8")
    try:
        ACTIVE_EXPORT.write_text(
            "pathway,gene_ratio,neg_log10_fdr,gene_count,direction,highlight_order\n",
            encoding="utf-8",
        )
        summary = json.loads(original_summary)
        summary["result_count"] = 0
        summary["figure_export_count"] = 0
        summary["top_pathways"] = []
        ACTIVE_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        figure = module.create_figure(spec_path)
    finally:
        ACTIVE_EXPORT.write_text(original_export, encoding="utf-8")
        ACTIVE_SUMMARY.write_text(original_summary, encoding="utf-8")

    assert figure is not None
