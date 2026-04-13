#!/usr/bin/env python3
"""Tests for MSigDB-specific fgsea scaffolding and validation."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fgsea_pipeline import validate_config
from scaffold_msigdb_profile import scaffold_msigdb_profile


def test_validate_msigdb_source_metadata_when_present(tmp_path: Path) -> None:
    gmt_path = tmp_path / "msigdb.gmt"
    gmt_path.write_text("Hallmark_IFN\tna\tIFI27\tIFIT1\tCXCL10\n", encoding="utf-8")
    config_path = tmp_path / "fgsea.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "msigdb_valid",
                "ranks_csv": "pathways/data/fgsea_demo_ranks.csv",
                "pathways_gmt": str(gmt_path),
                "output_dir": str(tmp_path / "results"),
                "figure_export_csv": str(tmp_path / "results" / "fgsea_pathway_dot_export.csv"),
                "gene_set_source": {
                    "provider": "msigdb",
                    "species": "human",
                    "collection": "H",
                    "version": "2026.1.Hs",
                    "identifier_type": "gene_symbol",
                    "registration_required": True,
                },
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
    payload = validate_config(config_path)
    assert payload["status"] == "valid"
    assert payload["gene_set_source"]["provider"] == "msigdb"
    assert payload["gene_set_source"]["collection"] == "H"


def test_scaffold_msigdb_profile_creates_expected_layout(tmp_path: Path) -> None:
    import scaffold_msigdb_profile as scaffold_module  # type: ignore

    original_root = scaffold_module.STUDIES_ROOT
    scaffold_module.STUDIES_ROOT = tmp_path / "pathways" / "studies"
    try:
        payload = scaffold_msigdb_profile(
            "msigdb_unit",
            species="human",
            collection="H",
            version="2026.1.Hs",
            identifier_type="gene_symbol",
        )
    finally:
        scaffold_module.STUDIES_ROOT = original_root

    study_root = tmp_path / "pathways" / "studies" / "msigdb_unit"
    config_path = study_root / "configs" / "fgsea.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert payload["study_id"] == "msigdb_unit"
    assert config["raw_input_table"].endswith("msigdb_unit_differential_expression.csv")
    assert config["rank_prep_summary"].endswith("results/rank_prep/rank_prep_summary.json")
    assert config["gene_set_source"]["provider"] == "msigdb"
    assert config["gene_set_source"]["collection"] == "H"
    assert config["gene_set_source"]["species"] == "human"
    assert (study_root / "configs" / "rank_prep.yml").exists()
    assert (study_root / "inputs" / "raw" / "msigdb_unit_differential_expression.csv").exists()
    assert (study_root / "inputs" / "msigdb" / "README.md").exists()


def test_validate_config_reports_missing_msigdb_gmt(tmp_path: Path) -> None:
    config_path = tmp_path / "fgsea.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "msigdb_missing",
                "ranks_csv": "pathways/data/fgsea_demo_ranks.csv",
                "pathways_gmt": str(tmp_path / "missing.gmt"),
                "output_dir": str(tmp_path / "results"),
                "figure_export_csv": str(tmp_path / "results" / "fgsea_pathway_dot_export.csv"),
                "gene_set_source": {
                    "provider": "msigdb",
                    "species": "human",
                    "collection": "H",
                    "version": "2026.1.Hs",
                    "identifier_type": "gene_symbol",
                    "registration_required": True,
                },
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

    payload = validate_config(config_path)
    assert payload["status"] == "invalid"
    assert any("MSigDB GMT not found" in item for item in payload["errors"])
