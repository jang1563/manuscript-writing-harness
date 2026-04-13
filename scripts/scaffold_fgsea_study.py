#!/usr/bin/env python3
"""Scaffold a study-specific fgsea profile without touching the active profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
STUDIES_ROOT = REPO_ROOT / "pathways" / "studies"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_text(path: Path, content: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path.relative_to(REPO_ROOT)} already exists")
    path.write_text(content, encoding="utf-8")


def _study_config(study_id: str) -> dict[str, object]:
    study_root = Path("pathways") / "studies" / study_id
    return {
        "run_id": study_id,
        "raw_input_table": str(study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "ranks_csv": str(study_root / "inputs" / f"{study_id}_ranks.csv"),
        "rank_prep_summary": str(study_root / "results" / "rank_prep" / "rank_prep_summary.json"),
        "pathways_gmt": str(study_root / "inputs" / f"{study_id}_pathways.gmt"),
        "output_dir": str(study_root / "results" / "fgsea"),
        "figure_export_csv": str(study_root / "results" / "fgsea" / "fgsea_pathway_dot_export.csv"),
        "parameters": {
            "min_size": 5,
            "max_size": 500,
            "score_type": "std",
            "eps": 0,
            "seed": 42,
            "top_n_per_direction": 5,
        },
    }


def _rank_prep_config(study_id: str) -> dict[str, object]:
    study_root = Path("pathways") / "studies" / study_id
    return {
        "study_id": study_id,
        "source_tool": "deseq2",
        "input_table": str(study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "output_ranks_csv": str(study_root / "inputs" / f"{study_id}_ranks.csv"),
        "summary_json": str(study_root / "results" / "rank_prep" / "rank_prep_summary.json"),
        "summary_md": str(study_root / "results" / "rank_prep" / "rank_prep_summary.md"),
        "method": "signed_neg_log10_significance",
        "gene_column": "gene",
        "effect_column": "log2FoldChange",
        "significance_column": "padj",
        "significance_floor": 1.0e-300,
        "deduplicate_by": "max_abs_score",
        "sort_descending": True,
    }


def scaffold_fgsea_study(study_id: str, *, overwrite: bool = False) -> dict[str, object]:
    study_root = STUDIES_ROOT / study_id
    config = _study_config(study_id)

    _write_text(
        study_root / "README.md",
        "\n".join(
            [
                f"# {study_id}",
                "",
                "This study profile is scaffolded for preranked fgsea analysis.",
                "",
                "Fill in the raw differential-expression table under `inputs/raw/`, prepare ranks, validate the config, and only then activate it as the figure-backed fgsea profile.",
                "",
                "Recommended commands:",
                "",
                f"- `python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/{study_id}/configs/rank_prep.yml --json`",
                f"- `python3 scripts/fgsea_pipeline.py validate --config pathways/studies/{study_id}/configs/fgsea.yml --json`",
                f"- `python3 scripts/fgsea_pipeline.py run --config pathways/studies/{study_id}/configs/fgsea.yml --allow-missing-package --json`",
                f"- `python3 scripts/activate_fgsea_profile.py --config pathways/studies/{study_id}/configs/fgsea.yml --json`",
                "",
            ]
        ),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "configs" / "fgsea.yml",
        yaml.safe_dump(config, sort_keys=False),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "configs" / "rank_prep.yml",
        yaml.safe_dump(_rank_prep_config(study_id), sort_keys=False),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / f"{study_id}_ranks.csv",
        "gene,stat\nGENE_A,2.5\nGENE_B,-1.8\n",
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / "raw" / "README.md",
        "\n".join(
            [
                "# Raw Differential-Expression Input",
                "",
                "Place your DESeq2/edgeR/limma-style results table in this directory.",
                "",
                f"Default expected file: `{study_id}_differential_expression.csv`",
                "",
                "The default rank-prep template expects DESeq2-style columns:",
                "",
                "- `gene`",
                "- `log2FoldChange`",
                "- `padj`",
                "",
                "If your source table uses different names, edit `configs/rank_prep.yml` before running the prep step.",
                "",
            ]
        ),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv",
        "gene,log2FoldChange,padj,stat\nGENE_A,1.8,0.0005,5.2\nGENE_B,-1.4,0.0021,-4.7\n",
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / f"{study_id}_pathways.gmt",
        "Placeholder_Pathway\tna\tGENE_A\tGENE_B\n",
        overwrite=overwrite,
    )
    _write_text(
        study_root / "results" / "README.md",
        "\n".join(
            [
                "# Study fgsea Results",
                "",
                "Generated outputs for this study-local fgsea profile land here and are gitignored by default.",
                "",
                "Typical outputs:",
                "",
                "- `fgsea_summary.json`",
                "- `fgsea_results.csv`",
                "- `fgsea_pathway_dot_export.csv`",
                "",
            ]
        ),
        overwrite=overwrite,
    )
    return {
        "study_id": study_id,
        "study_root": _display_path(study_root),
        "config": _display_path(study_root / "configs" / "fgsea.yml"),
        "rank_prep_config": _display_path(study_root / "configs" / "rank_prep.yml"),
        "ranks_csv": _display_path(study_root / "inputs" / f"{study_id}_ranks.csv"),
        "raw_input_table": _display_path(study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "pathways_gmt": _display_path(study_root / "inputs" / f"{study_id}_pathways.gmt"),
        "results_readme": _display_path(study_root / "results" / "README.md"),
        "next_steps": [
            f"python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/{study_id}/configs/rank_prep.yml --json",
            f"python3 scripts/fgsea_pipeline.py validate --config pathways/studies/{study_id}/configs/fgsea.yml --json",
            f"python3 scripts/fgsea_pipeline.py run --config pathways/studies/{study_id}/configs/fgsea.yml --allow-missing-package --json",
            f"python3 scripts/activate_fgsea_profile.py --config pathways/studies/{study_id}/configs/fgsea.yml --json",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold a study-specific fgsea profile")
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = scaffold_fgsea_study(args.study_id, overwrite=args.overwrite)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Scaffolded fgsea study profile: {payload['study_root']}")
        print(f"Config: {payload['config']}")
        print("Next steps:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
