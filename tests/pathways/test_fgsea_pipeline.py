#!/usr/bin/env python3
"""Tests for the optional fgsea pathway pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from fgsea_pipeline import build_run_command, validate_config


def test_validate_fgsea_demo_config() -> None:
    payload = validate_config(REPO_ROOT / "pathways/configs/fgsea_demo.yml")
    assert payload["status"] == "valid"
    assert payload["pathway_count"] == 6
    assert payload["figure_export_csv"].endswith("pathways/results/demo_fgsea/fgsea_pathway_dot_export.csv")


def test_validate_fgsea_active_config() -> None:
    payload = validate_config(REPO_ROOT / "pathways/configs/fgsea_active.yml")
    assert payload["status"] == "valid"
    assert payload["pathway_count"] >= 1
    assert payload["figure_export_csv"].endswith("pathways/results/active_fgsea/fgsea_pathway_dot_export.csv")


def test_validate_config_allows_generated_rank_summary_to_be_absent(tmp_path: Path) -> None:
    ranks = tmp_path / "ranks.csv"
    ranks.write_text("gene,stat\nA,1.0\nB,-1.0\n", encoding="utf-8")
    gmt = tmp_path / "pathways.gmt"
    gmt.write_text("demo\ttest\tA\tB\n", encoding="utf-8")
    config = tmp_path / "fgsea.yml"
    config.write_text(
        "\n".join(
            [
                "run_id: clean_checkout",
                f"ranks_csv: {ranks}",
                f"rank_prep_summary: {tmp_path / 'rank_prep_summary.json'}",
                f"pathways_gmt: {gmt}",
                f"output_dir: {tmp_path / 'results'}",
                f"figure_export_csv: {tmp_path / 'results' / 'fgsea_pathway_dot_export.csv'}",
                "parameters:",
                "  min_size: 1",
                "  max_size: 500",
                "  score_type: std",
                "  eps: 0",
                "  seed: 42",
                "  top_n_per_direction: 3",
                "",
            ]
        ),
        encoding="utf-8",
    )

    payload = validate_config(config)

    assert payload["status"] == "valid"


def test_build_run_command_includes_expected_runner() -> None:
    command = build_run_command(
        REPO_ROOT / "pathways/configs/fgsea_demo.yml",
        validate_only=True,
        allow_missing_package=True,
        output_dir_override="pathways/results/test_fgsea",
    )
    assert command[0] == "Rscript"
    assert command[1].endswith("scripts/run_fgsea_pipeline.R")
    assert "--validate-only" in command
    assert "--allow-missing-package" in command
    assert "pathways/results/test_fgsea" in command


def test_fgsea_validate_cli_emits_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/fgsea_pipeline.py",
            "validate",
            "--config",
            "pathways/configs/fgsea_demo.yml",
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "valid"


def test_fgsea_run_cli_allows_missing_package_with_tmp_output(tmp_path: Path) -> None:
    output_dir = tmp_path / "fgsea_demo"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/fgsea_pipeline.py",
            "run",
            "--config",
            "pathways/configs/fgsea_demo.yml",
            "--allow-missing-package",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] in {"ready", "skipped_missing_package"}
    assert (output_dir / "fgsea_summary.json").exists()
