#!/usr/bin/env python3
"""Tests for DE-style input conversion into fgsea preranks."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prepare_fgsea_ranks import prepare_fgsea_ranks


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_prepare_fgsea_ranks_from_deseq2_style_table(tmp_path: Path) -> None:
    input_table = tmp_path / "de.csv"
    input_table.write_text(
        "\n".join(
            [
                "gene,log2FoldChange,padj,stat",
                "IFIT1,2.0,0.0001,5.8",
                "MKI67,-1.5,0.0012,-4.2",
                "IFIT1,1.7,0.0003,4.9",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "rank_prep.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "study_id": "unit",
                "source_tool": "deseq2",
                "input_table": str(input_table),
                "output_ranks_csv": str(tmp_path / "ranks.csv"),
                "summary_json": str(tmp_path / "summary.json"),
                "summary_md": str(tmp_path / "summary.md"),
                "method": "signed_neg_log10_significance",
                "gene_column": "gene",
                "effect_column": "log2FoldChange",
                "significance_column": "padj",
                "deduplicate_by": "max_abs_score",
                "sort_descending": True,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = prepare_fgsea_ranks(config_path)

    rows = _rows(tmp_path / "ranks.csv")
    assert payload["status"] == "ready"
    assert payload["retained_rows"] == 2
    assert payload["duplicate_genes_removed"] == 1
    assert rows[0]["gene"] == "IFIT1"
    assert rows[1]["gene"] == "MKI67"
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["source_tool"] == "deseq2"


def test_prepare_fgsea_ranks_from_direct_stat_table(tmp_path: Path) -> None:
    input_table = tmp_path / "limma.csv"
    input_table.write_text(
        "\n".join(
            [
                "Gene,t,adj.P.Val",
                "STAT1,6.4,0.0002",
                "CCNB1,-5.2,0.0008",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "rank_prep.yml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "study_id": "unit_limma",
                "source_tool": "limma",
                "input_table": str(input_table),
                "output_ranks_csv": str(tmp_path / "ranks.csv"),
                "summary_json": str(tmp_path / "summary.json"),
                "summary_md": str(tmp_path / "summary.md"),
                "method": "direct_stat",
                "gene_column": "Gene",
                "score_column": "t",
                "deduplicate_by": "max_abs_score",
                "sort_descending": True,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    payload = prepare_fgsea_ranks(config_path)

    rows = _rows(tmp_path / "ranks.csv")
    assert payload["status"] == "ready"
    assert rows[0]["gene"] == "STAT1"
    assert rows[1]["gene"] == "CCNB1"
