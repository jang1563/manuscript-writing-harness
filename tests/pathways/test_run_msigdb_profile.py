#!/usr/bin/env python3
"""Tests for the MSigDB end-to-end profile runner."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_msigdb_profile as runner  # type: ignore


def test_run_msigdb_profile_writes_reports(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "study" / "configs" / "fgsea.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    rank_prep_path = config_path.parent / "rank_prep.yml"
    rank_prep_path.write_text(
        yaml.safe_dump(
            {
                "study_id": "study_x",
                "source_tool": "deseq2",
                "input_table": str(tmp_path / "study" / "inputs" / "raw" / "study_x_differential_expression.csv"),
                "output_ranks_csv": str(tmp_path / "study" / "inputs" / "study_x_ranks.csv"),
                "summary_json": str(tmp_path / "study" / "results" / "rank_prep_summary.json"),
                "summary_md": str(tmp_path / "study" / "results" / "rank_prep_summary.md"),
                "method": "signed_neg_log10_significance",
                "gene_column": "gene",
                "effect_column": "log2FoldChange",
                "significance_column": "padj",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "study_x",
                "raw_input_table": str(tmp_path / "study" / "inputs" / "raw" / "study_x_differential_expression.csv"),
                "ranks_csv": "pathways/data/fgsea_demo_ranks.csv",
                "rank_prep_summary": str(tmp_path / "study" / "results" / "rank_prep" / "rank_prep_summary.json"),
                "pathways_gmt": "pathways/data/fgsea_demo_pathways.gmt",
                "output_dir": str(tmp_path / "study" / "results" / "fgsea"),
                "figure_export_csv": str(tmp_path / "study" / "results" / "fgsea" / "fgsea_pathway_dot_export.csv"),
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
                    "top_n_per_direction": 3,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        runner,
        "validate_config",
        lambda _: {
            "status": "valid",
            "config": "pathways/studies/study_x/configs/fgsea.yml",
            "output_dir": "pathways/studies/study_x/results/fgsea",
            "raw_input_table": "pathways/studies/study_x/inputs/raw/study_x_differential_expression.csv",
            "rank_prep_summary": "pathways/studies/study_x/results/rank_prep/rank_prep_summary.json",
            "pathways_gmt": "pathways/studies/study_x/inputs/msigdb/study_x_H_2026.1.Hs_gene_symbol.gmt",
            "gene_set_source": {
                "provider": "msigdb",
                "species": "human",
                "collection": "H",
                "version": "2026.1.Hs",
                "identifier_type": "gene_symbol",
            },
            "errors": [],
        },
    )
    monkeypatch.setattr(
        runner,
        "activate_fgsea_profile",
        lambda _: {
            "status": "activated",
            "active_config": "pathways/configs/fgsea_active.yml",
            "source_profile": "pathways/studies/study_x/configs/fgsea.yml",
            "active_figure_export_csv": "pathways/results/active_fgsea/fgsea_pathway_dot_export.csv",
        },
    )
    monkeypatch.setattr(
        runner,
        "run_pipeline",
        lambda *args, **kwargs: (
            0,
            {
                "status": "ready",
                "run_id": "fgsea_active",
                "summary_json": "pathways/results/active_fgsea/fgsea_summary.json",
                "figure_export_csv": "pathways/results/active_fgsea/fgsea_pathway_dot_export.csv",
            },
        ),
    )
    monkeypatch.setattr(runner, "ACTIVE_CONFIG_PATH", tmp_path / "active.yml")
    monkeypatch.setattr(
        runner,
        "prepare_fgsea_ranks",
        lambda _: {
            "status": "ready",
            "output_ranks_csv": "pathways/studies/study_x/inputs/study_x_ranks.csv",
        },
    )
    monkeypatch.setattr(
        runner,
        "_report_paths",
        lambda _cfg: [
            tmp_path / "study" / "results" / "msigdb_profile_report.json",
            tmp_path / "study" / "results" / "msigdb_profile_report.md",
        ],
    )

    payload = runner.run_msigdb_profile(config_path, prepare_ranks=True)

    assert payload["status"] == "ready"
    assert payload["rank_prep"]["status"] == "ready"
    assert any(item.endswith("study_dossier.json") for item in payload["written_dossiers"])
    json_report = tmp_path / "study" / "results" / "msigdb_profile_report.json"
    markdown_report = tmp_path / "study" / "results" / "msigdb_profile_report.md"
    assert json_report.exists()
    assert markdown_report.exists()
    parsed = json.loads(json_report.read_text(encoding="utf-8"))
    assert parsed["activation"]["active_config"] == "pathways/configs/fgsea_active.yml"
    assert parsed["validation"]["rank_prep_summary"] == "pathways/studies/study_x/results/rank_prep/rank_prep_summary.json"
    assert "gene set provider: `msigdb`" in markdown_report.read_text(encoding="utf-8")


def test_run_msigdb_profile_rejects_non_msigdb(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "fgsea.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "run_id": "plain_fgsea",
                "ranks_csv": "pathways/data/fgsea_demo_ranks.csv",
                "pathways_gmt": "pathways/data/fgsea_demo_pathways.gmt",
                "output_dir": str(tmp_path / "results"),
                "figure_export_csv": str(tmp_path / "results" / "fgsea_pathway_dot_export.csv"),
                "parameters": {
                    "min_size": 5,
                    "max_size": 500,
                    "score_type": "std",
                    "eps": 0,
                    "seed": 42,
                    "top_n_per_direction": 3,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner,
        "validate_config",
        lambda _: {
            "status": "valid",
            "config": "pathways/configs/fgsea_demo.yml",
            "output_dir": "pathways/results/demo_fgsea",
            "gene_set_source": None,
            "errors": [],
        },
    )
    monkeypatch.setattr(
        runner,
        "_report_paths",
        lambda _cfg: [tmp_path / "msigdb_profile_report.json", tmp_path / "msigdb_profile_report.md"],
    )

    payload = runner.run_msigdb_profile(config_path)

    assert payload["status"] == "invalid"
    assert any("provider must be `msigdb`" in item for item in payload["validation"]["errors"])
