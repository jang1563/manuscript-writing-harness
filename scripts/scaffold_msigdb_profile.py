#!/usr/bin/env python3
"""Scaffold an MSigDB-backed fgsea study profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
STUDIES_ROOT = REPO_ROOT / "pathways" / "studies"
MSIGDB_CATALOG_PATH = REPO_ROOT / "pathways" / "msigdb" / "catalog.yml"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_text(path: Path, content: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists")
    path.write_text(content, encoding="utf-8")


def _load_catalog() -> dict[str, object]:
    return yaml.safe_load(MSIGDB_CATALOG_PATH.read_text(encoding="utf-8"))


def _default_version(catalog: dict[str, object], species: str) -> str:
    return str(catalog["current_versions"][species])  # type: ignore[index]


def _validate_choice(catalog: dict[str, object], species: str, collection: str, identifier_type: str) -> None:
    collections = catalog["collections"]  # type: ignore[index]
    if collection not in collections:
        raise ValueError(f"Unknown MSigDB collection: {collection}")
    allowed_species = set(collections[collection]["species"])  # type: ignore[index]
    if species not in allowed_species:
        raise ValueError(f"Collection {collection} is not available for species `{species}` in this catalog")
    identifier_types = set(catalog["download_requirements"]["identifier_types"])  # type: ignore[index]
    if identifier_type not in identifier_types:
        raise ValueError(f"identifier_type must be one of {sorted(identifier_types)}")


def scaffold_msigdb_profile(
    study_id: str,
    *,
    species: str,
    collection: str,
    version: str | None = None,
    identifier_type: str = "gene_symbol",
    overwrite: bool = False,
) -> dict[str, object]:
    species = species.lower()
    catalog = _load_catalog()
    _validate_choice(catalog, species, collection, identifier_type)
    resolved_version = version or _default_version(catalog, species)

    study_root = STUDIES_ROOT / study_id
    gmt_name = f"{study_id}_{collection}_{resolved_version}_{identifier_type}.gmt"
    gmt_relative = Path("pathways") / "studies" / study_id / "inputs" / "msigdb" / gmt_name
    ranks_relative = Path("pathways") / "studies" / study_id / "inputs" / f"{study_id}_ranks.csv"
    output_dir = Path("pathways") / "studies" / study_id / "results" / "fgsea"
    rank_prep_config = {
        "study_id": study_id,
        "source_tool": "deseq2",
        "input_table": str(Path("pathways") / "studies" / study_id / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "output_ranks_csv": str(ranks_relative),
        "summary_json": str(Path("pathways") / "studies" / study_id / "results" / "rank_prep" / "rank_prep_summary.json"),
        "summary_md": str(Path("pathways") / "studies" / study_id / "results" / "rank_prep" / "rank_prep_summary.md"),
        "method": "signed_neg_log10_significance",
        "gene_column": "gene",
        "effect_column": "log2FoldChange",
        "significance_column": "padj",
        "significance_floor": 1.0e-300,
        "deduplicate_by": "max_abs_score",
        "sort_descending": True,
    }

    config = {
        "run_id": study_id,
        "raw_input_table": str(Path("pathways") / "studies" / study_id / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "ranks_csv": str(ranks_relative),
        "rank_prep_summary": str(Path("pathways") / "studies" / study_id / "results" / "rank_prep" / "rank_prep_summary.json"),
        "pathways_gmt": str(gmt_relative),
        "output_dir": str(output_dir),
        "figure_export_csv": str(output_dir / "fgsea_pathway_dot_export.csv"),
        "gene_set_source": {
            "provider": "msigdb",
            "species": species,
            "collection": collection,
            "version": resolved_version,
            "identifier_type": identifier_type,
            "registration_required": True,
        },
        "parameters": {
            "min_size": 10,
            "max_size": 500,
            "score_type": "std",
            "eps": 0,
            "seed": 42,
            "top_n_per_direction": 5,
        },
    }

    _write_text(
        study_root / "README.md",
        "\n".join(
            [
                f"# {study_id}",
                "",
                f"This study profile is scaffolded for an MSigDB-backed fgsea run using collection `{collection}` ({species}, {resolved_version}).",
                "",
                "Steps:",
                "",
                "1. Replace the placeholder differential-expression table under `inputs/raw/` with your real study results.",
                "2. Prepare the fgsea ranks CSV from that DE table.",
                f"3. Download the MSigDB GMT for this collection and place it at `{gmt_relative.as_posix()}`.",
                "4. Validate and run the profile locally.",
                "5. Activate it only when you want the pathway figure layer to use this study profile.",
                "",
            ]
        ),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "configs" / "rank_prep.yml",
        yaml.safe_dump(rank_prep_config, sort_keys=False),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "configs" / "fgsea.yml",
        yaml.safe_dump(config, sort_keys=False),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / "raw" / "README.md",
        "\n".join(
            [
                "# Raw Differential-Expression Input",
                "",
                "Place your DESeq2/edgeR/limma-style study results in this directory before preparing fgsea ranks.",
                "",
                f"Default expected file: `{study_id}_differential_expression.csv`",
                "",
                "The default rank-prep config assumes DESeq2-style columns:",
                "",
                "- `gene`",
                "- `log2FoldChange`",
                "- `padj`",
                "",
                "Edit `configs/rank_prep.yml` if your source table uses different column names.",
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
        study_root / "inputs" / f"{study_id}_ranks.csv",
        "gene,stat\nGENE_A,2.5\nGENE_B,-1.8\n",
        overwrite=overwrite,
    )
    _write_text(
        study_root / "inputs" / "msigdb" / "README.md",
        "\n".join(
            [
                "# MSigDB GMT Drop Location",
                "",
                "Place the downloaded MSigDB GMT for this study profile in this directory.",
                "",
                f"Expected file name: `{gmt_name}`",
                f"Collection: `{collection}`",
                f"Species: `{species}`",
                f"Version: `{resolved_version}`",
                f"Identifier type: `{identifier_type}`",
                "",
                "This repo does not vendor official MSigDB files.",
                "",
            ]
        ),
        overwrite=overwrite,
    )
    _write_text(
        study_root / "results" / "README.md",
        "# Study fgsea Results\n\nGenerated outputs for this MSigDB-backed study profile land here and are gitignored by default.\n",
        overwrite=overwrite,
    )

    return {
        "study_id": study_id,
        "study_root": _display_path(study_root),
        "config": _display_path(study_root / "configs" / "fgsea.yml"),
        "rank_prep_config": _display_path(study_root / "configs" / "rank_prep.yml"),
        "ranks_csv": _display_path(study_root / "inputs" / f"{study_id}_ranks.csv"),
        "raw_input_table": _display_path(study_root / "inputs" / "raw" / f"{study_id}_differential_expression.csv"),
        "msigdb_gmt_expected": _display_path(study_root / "inputs" / "msigdb" / gmt_name),
        "results_readme": _display_path(study_root / "results" / "README.md"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scaffold an MSigDB-backed fgsea profile")
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--species", choices=["human", "mouse"], required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--version")
    parser.add_argument("--identifier-type", default="gene_symbol")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = scaffold_msigdb_profile(
        args.study_id,
        species=args.species,
        collection=args.collection,
        version=args.version,
        identifier_type=args.identifier_type,
        overwrite=args.overwrite,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Scaffolded MSigDB profile: {payload['study_root']}")
        print(f"Config: {payload['config']}")
        print(f"Expected GMT: {payload['msigdb_gmt_expected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
