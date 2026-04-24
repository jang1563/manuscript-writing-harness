#!/usr/bin/env python3
"""Validate and orchestrate the optional fgsea pathway pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = REPO_ROOT / "scripts" / "run_fgsea_pipeline.R"
LOCAL_R_LIBS = REPO_ROOT / ".r_libs"
MSIGDB_CATALOG_PATH = REPO_ROOT / "pathways" / "msigdb" / "catalog.yml"


def _display_repo_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_config(config_path: Path) -> dict[str, Any]:
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def load_msigdb_catalog() -> dict[str, Any]:
    return yaml.safe_load(MSIGDB_CATALOG_PATH.read_text(encoding="utf-8"))


def _read_ranks_header(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    return [item.strip() for item in lines[0].split(",")]


def _count_gmt_records(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            count += 1
    return count


def _validate_gene_set_source(
    payload: dict[str, Any],
    *,
    gmt_exists: bool,
) -> tuple[list[str], dict[str, Any] | None]:
    source = payload.get("gene_set_source")
    if not isinstance(source, dict):
        return [], None

    provider = str(source.get("provider", "")).strip().lower()
    summary: dict[str, Any] = {"provider": provider}
    errors: list[str] = []
    if provider != "msigdb":
        summary.update(source)
        return errors, summary

    catalog = load_msigdb_catalog()
    collection = str(source.get("collection", "")).strip()
    species = str(source.get("species", "")).strip().lower()
    version = str(source.get("version", "")).strip()
    identifier_type = str(source.get("identifier_type", "")).strip()
    registration_required = bool(source.get("registration_required", False))

    summary.update(
        {
            "collection": collection,
            "species": species,
            "version": version,
            "identifier_type": identifier_type,
            "registration_required": registration_required,
        }
    )

    for field in ("collection", "species", "version", "identifier_type"):
        if not source.get(field):
            errors.append(f"gene_set_source.provider=msigdb requires `{field}`")

    allowed_identifier_types = set(catalog["download_requirements"]["identifier_types"])
    if identifier_type and identifier_type not in allowed_identifier_types:
        errors.append(
            f"gene_set_source.identifier_type must be one of {sorted(allowed_identifier_types)}"
        )

    collections = catalog["collections"]
    if collection:
        if collection not in collections:
            errors.append(f"unknown MSigDB collection: {collection}")
        else:
            allowed_species = set(collections[collection]["species"])
            if species and species not in allowed_species:
                errors.append(
                    f"MSigDB collection {collection} is not configured for species `{species}`"
                )
            summary["collection_label"] = collections[collection]["label"]
            summary["best_for"] = collections[collection]["best_for"]

    if not registration_required:
        errors.append("gene_set_source.registration_required should be true for MSigDB profiles")

    if not gmt_exists:
        errors.append(
            "MSigDB GMT not found at pathways_gmt; download the licensed GMT and place it at the configured path"
        )

    return errors, summary


def detect_fgsea_available() -> bool | None:
    env = os.environ.copy()
    if LOCAL_R_LIBS.exists():
        env["R_LIBS_USER"] = str(LOCAL_R_LIBS)
    try:
        result = subprocess.run(
            ["Rscript", "-e", 'cat(requireNamespace("fgsea", quietly=TRUE))'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    stdout = result.stdout.strip().lower()
    if stdout.endswith("true"):
        return True
    if stdout.endswith("false"):
        return False
    return None


def validate_config(config_path: Path) -> dict[str, Any]:
    payload = load_config(config_path)
    errors: list[str] = []

    required = ["run_id", "ranks_csv", "pathways_gmt", "output_dir", "figure_export_csv", "parameters"]
    for field in required:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    params = payload.get("parameters", {})
    for field in ["min_size", "max_size", "score_type", "eps", "seed", "top_n_per_direction"]:
        if field not in params:
            errors.append(f"missing parameters.{field}")

    ranks_path = _resolve_repo_path(str(payload.get("ranks_csv", "")))
    raw_input_path = _resolve_repo_path(str(payload.get("raw_input_table", ""))) if payload.get("raw_input_table") else None
    rank_prep_summary_path = (
        _resolve_repo_path(str(payload.get("rank_prep_summary", ""))) if payload.get("rank_prep_summary") else None
    )
    gmt_path = _resolve_repo_path(str(payload.get("pathways_gmt", "")))
    output_dir = _resolve_repo_path(str(payload.get("output_dir", "")))
    export_path = _resolve_repo_path(str(payload.get("figure_export_csv", "")))

    if not ranks_path.exists():
        errors.append(f"ranks_csv not found: {payload.get('ranks_csv', '')}")
    else:
        header = _read_ranks_header(ranks_path)
        for required_col in ["gene", "stat"]:
            if required_col not in header:
                errors.append(f"ranks_csv missing required column: {required_col}")

    if not gmt_path.exists():
        errors.append(f"pathways_gmt not found: {payload.get('pathways_gmt', '')}")
    elif _count_gmt_records(gmt_path) == 0:
        errors.append("pathways_gmt contains no pathways")

    if raw_input_path is not None and not raw_input_path.exists():
        errors.append(f"raw_input_table not found: {payload.get('raw_input_table', '')}")

    if rank_prep_summary_path is not None and not rank_prep_summary_path.exists():
        errors.append(f"rank_prep_summary not found: {payload.get('rank_prep_summary', '')}")

    source_errors, source_summary = _validate_gene_set_source(payload, gmt_exists=gmt_path.exists())
    errors.extend(source_errors)

    if export_path.parent != output_dir:
        errors.append("figure_export_csv must live under output_dir")

    fgsea_available = detect_fgsea_available()

    return {
        "config": _display_repo_path(config_path),
        "run_id": payload.get("run_id"),
        "fgsea_available": fgsea_available,
        "raw_input_table": (
            _display_repo_path(raw_input_path) if raw_input_path is not None and raw_input_path.exists() else payload.get("raw_input_table")
        ),
        "rank_prep_summary": (
            _display_repo_path(rank_prep_summary_path)
            if rank_prep_summary_path is not None and rank_prep_summary_path.exists()
            else payload.get("rank_prep_summary")
        ),
        "ranks_csv": _display_repo_path(ranks_path) if ranks_path.exists() else str(payload.get("ranks_csv", "")),
        "pathways_gmt": _display_repo_path(gmt_path) if gmt_path.exists() else str(payload.get("pathways_gmt", "")),
        "output_dir": _display_repo_path(output_dir),
        "figure_export_csv": _display_repo_path(export_path),
        "pathway_count": _count_gmt_records(gmt_path) if gmt_path.exists() else 0,
        "gene_set_source": source_summary,
        "errors": errors,
        "status": "valid" if not errors else "invalid",
    }


def build_run_command(
    config_path: Path,
    *,
    validate_only: bool = False,
    allow_missing_package: bool = False,
    output_dir_override: str | None = None,
) -> list[str]:
    command = [
        "Rscript",
        str(RUNNER_PATH),
        "--config",
        str(config_path),
    ]
    if validate_only:
        command.append("--validate-only")
    if allow_missing_package:
        command.append("--allow-missing-package")
    if output_dir_override:
        command.extend(["--output-dir", output_dir_override])
    return command


def run_pipeline(
    config_path: Path,
    *,
    validate_only: bool = False,
    allow_missing_package: bool = False,
    output_dir_override: str | None = None,
) -> tuple[int, dict[str, Any]]:
    command = build_run_command(
        config_path,
        validate_only=validate_only,
        allow_missing_package=allow_missing_package,
        output_dir_override=output_dir_override,
    )
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            **({"R_LIBS_USER": str(LOCAL_R_LIBS)} if LOCAL_R_LIBS.exists() else {}),
        },
    )
    payload: dict[str, Any]
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {
            "status": "runner_error",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    payload["returncode"] = result.returncode
    return result.returncode, payload


def cmd_validate(args: argparse.Namespace) -> int:
    payload = validate_config(Path(args.config).resolve())
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"fgsea config: {payload['config']}")
        print(f"status: {payload['status']}")
        print(f"fgsea_available: {payload['fgsea_available']}")
        if payload["errors"]:
            for error in payload["errors"]:
                print(f"- {error}")
    return 0 if payload["status"] == "valid" else 1


def cmd_run(args: argparse.Namespace) -> int:
    code, payload = run_pipeline(
        Path(args.config).resolve(),
        validate_only=args.validate_only,
        allow_missing_package=args.allow_missing_package,
        output_dir_override=args.output_dir,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"status: {payload.get('status')}")
        if "summary_json" in payload:
            print(f"summary_json: {payload['summary_json']}")
        if "results_csv" in payload:
            print(f"results_csv: {payload['results_csv']}")
        if "figure_export_csv" in payload:
            print(f"figure_export_csv: {payload['figure_export_csv']}")
        if payload.get("stderr"):
            print(payload["stderr"], file=sys.stderr)
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="fgsea pipeline interface for the manuscript system")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate fgsea config")
    validate_parser.add_argument("--config", required=True)
    validate_parser.add_argument("--json", action="store_true")
    validate_parser.set_defaults(func=cmd_validate)

    run_parser = subparsers.add_parser("run", help="run fgsea pipeline")
    run_parser.add_argument("--config", required=True)
    run_parser.add_argument("--validate-only", action="store_true")
    run_parser.add_argument("--allow-missing-package", action="store_true")
    run_parser.add_argument("--output-dir")
    run_parser.add_argument("--json", action="store_true")
    run_parser.set_defaults(func=cmd_run)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
