#!/usr/bin/env python3
"""Tests for study-specific fgsea scaffolding and activation."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from activate_fgsea_profile import ACTIVE_CONFIG_PATH, activate_fgsea_profile
from scaffold_fgsea_study import scaffold_fgsea_study


def test_scaffold_fgsea_study_creates_expected_files(tmp_path: Path) -> None:
    study_id = "unit_fgsea_study"
    studies_root = tmp_path / "pathways" / "studies"

    import scaffold_fgsea_study as scaffold_module  # type: ignore

    original_root = scaffold_module.STUDIES_ROOT
    scaffold_module.STUDIES_ROOT = studies_root
    try:
        payload = scaffold_fgsea_study(study_id)
    finally:
        scaffold_module.STUDIES_ROOT = original_root

    study_root = studies_root / study_id
    assert payload["study_id"] == study_id
    assert (study_root / "README.md").exists()
    assert (study_root / "configs" / "fgsea.yml").exists()
    assert (study_root / "configs" / "rank_prep.yml").exists()
    assert (study_root / "inputs" / f"{study_id}_ranks.csv").exists()
    assert (study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv").exists()
    assert (study_root / "inputs" / f"{study_id}_pathways.gmt").exists()
    assert (study_root / "results" / "README.md").exists()
    config = yaml.safe_load((study_root / "configs" / "fgsea.yml").read_text(encoding="utf-8"))
    assert config["raw_input_table"].endswith(f"{study_id}_differential_expression.csv")
    assert config["rank_prep_summary"].endswith("results/rank_prep/rank_prep_summary.json")


def test_activate_fgsea_profile_rewrites_active_outputs(tmp_path: Path) -> None:
    source_config = tmp_path / "fgsea.yml"
    raw_input_path = REPO_ROOT / "pathways" / "studies" / "study_x" / "inputs" / "raw" / "study_x_differential_expression.csv"
    rank_prep_summary_path = REPO_ROOT / "pathways" / "studies" / "study_x" / "results" / "rank_prep" / "rank_prep_summary.json"
    raw_input_path.parent.mkdir(parents=True, exist_ok=True)
    rank_prep_summary_path.parent.mkdir(parents=True, exist_ok=True)
    raw_input_path.write_text("gene,log2FoldChange,padj,stat\nGENE_A,1.5,0.001,5.0\n", encoding="utf-8")
    rank_prep_summary_path.write_text('{"status":"ready"}\n', encoding="utf-8")
    source_config.write_text(
        yaml.safe_dump(
            {
                "run_id": "study_x",
                "raw_input_table": "pathways/studies/study_x/inputs/raw/study_x_differential_expression.csv",
                "ranks_csv": "pathways/data/fgsea_demo_ranks.csv",
                "rank_prep_summary": "pathways/studies/study_x/results/rank_prep/rank_prep_summary.json",
                "pathways_gmt": "pathways/data/fgsea_demo_pathways.gmt",
                "output_dir": "pathways/studies/study_x/results/fgsea",
                "figure_export_csv": "pathways/studies/study_x/results/fgsea/fgsea_pathway_dot_export.csv",
                "parameters": {
                    "min_size": 5,
                    "max_size": 500,
                    "score_type": "std",
                    "eps": 0,
                    "seed": 42,
                    "top_n_per_direction": 5,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    original = ACTIVE_CONFIG_PATH.read_text(encoding="utf-8")
    try:
        payload = activate_fgsea_profile(source_config)
        active = yaml.safe_load(ACTIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    finally:
        ACTIVE_CONFIG_PATH.write_text(original, encoding="utf-8")
        if raw_input_path.exists():
            raw_input_path.unlink()
        if rank_prep_summary_path.exists():
            rank_prep_summary_path.unlink()

    assert payload["status"] == "activated"
    assert active["source_profile"].endswith("fgsea.yml")
    assert active["raw_input_table"] == "pathways/studies/study_x/inputs/raw/study_x_differential_expression.csv"
    assert active["rank_prep_summary"] == "pathways/studies/study_x/results/rank_prep/rank_prep_summary.json"
    assert active["output_dir"] == "pathways/results/active_fgsea"
    assert active["figure_export_csv"] == "pathways/results/active_fgsea/fgsea_pathway_dot_export.csv"
