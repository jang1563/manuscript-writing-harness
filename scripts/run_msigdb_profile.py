#!/usr/bin/env python3
"""Validate, activate, and optionally build an MSigDB-backed fgsea profile."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

from activate_fgsea_profile import ACTIVE_CONFIG_PATH, activate_fgsea_profile
from fgsea_pipeline import REPO_ROOT, run_pipeline, validate_config
from fgsea_study_dossier import write_fgsea_study_dossier
from prepare_fgsea_ranks import prepare_fgsea_ranks


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _tail(text: str, *, limit: int = 30) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def _run_python_step(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "status": "ok" if result.returncode == 0 else "failed",
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _run_myst_step() -> dict[str, Any]:
    command = [str(REPO_ROOT / ".venv" / "bin" / "myst"), "build", "--html"]
    env = os.environ.copy()
    env["PATH"] = f"{REPO_ROOT / '.nodeenv' / 'bin'}:{env.get('PATH', '')}"
    result = subprocess.run(
        command,
        cwd=REPO_ROOT / "manuscript",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return {
        "command": ["cd", "manuscript", "&&", *command],
        "returncode": result.returncode,
        "status": "ok" if result.returncode == 0 else "failed",
        "stdout_tail": _tail(result.stdout),
        "stderr_tail": _tail(result.stderr),
    }


def _write_markdown_report(payload: dict[str, Any], report_path: Path) -> None:
    validation = payload["validation"]
    activation = payload.get("activation", {})
    fgsea_run = payload.get("fgsea_run", {})
    rank_prep = payload.get("rank_prep", {})
    gene_set_source = validation.get("gene_set_source") or {}
    lines = [
        f"# MSigDB Profile Report: {payload['study_id']}",
        "",
        f"- status: `{payload['status']}`",
        f"- config: `{payload['config']}`",
        f"- source profile: `{activation.get('source_profile', validation.get('config'))}`",
        f"- active config: `{activation.get('active_config', _display_path(ACTIVE_CONFIG_PATH))}`",
        f"- gene set provider: `{gene_set_source.get('provider', 'n/a')}`",
        f"- collection: `{gene_set_source.get('collection', 'n/a')}`",
        f"- species: `{gene_set_source.get('species', 'n/a')}`",
        f"- version: `{gene_set_source.get('version', 'n/a')}`",
        f"- identifier_type: `{gene_set_source.get('identifier_type', 'n/a')}`",
        f"- pathways_gmt: `{validation.get('pathways_gmt', 'n/a')}`",
        f"- raw_input_table: `{validation.get('raw_input_table', 'n/a')}`",
        f"- rank_prep_summary: `{validation.get('rank_prep_summary', rank_prep.get('summary_json', 'n/a'))}`",
        f"- fgsea status: `{fgsea_run.get('status', validation.get('status'))}`",
        f"- figure export: `{fgsea_run.get('figure_export_csv', activation.get('active_figure_export_csv', 'n/a'))}`",
        "",
    ]
    if rank_prep:
        lines.extend(
            [
                "## Rank Preparation",
                "",
                f"- status: `{rank_prep.get('status', 'unknown')}`",
                f"- output_ranks_csv: `{rank_prep.get('output_ranks_csv', 'n/a')}`",
                "",
            ]
        )
    if validation.get("errors"):
        lines.extend(["## Validation Errors", ""])
        lines.extend(f"- {item}" for item in validation["errors"])
        lines.append("")
    if payload.get("build_phase2"):
        lines.extend(
            [
                "## Build Phase 2",
                "",
                f"- status: `{payload['build_phase2']['status']}`",
                f"- returncode: `{payload['build_phase2']['returncode']}`",
                "",
            ]
        )
    if payload.get("myst"):
        lines.extend(
            [
                "## MyST Build",
                "",
                f"- status: `{payload['myst']['status']}`",
                f"- returncode: `{payload['myst']['returncode']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Morning Paths",
            "",
            f"- review page: `{payload['review_page']}`",
            f"- figure_05 python manifest: `{payload['figure_05_python_manifest']}`",
            f"- figure_05 r manifest: `{payload['figure_05_r_manifest']}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _report_paths(config_payload: dict[str, Any]) -> list[Path]:
    config_output_dir = REPO_ROOT / str(config_payload["output_dir"])
    study_results_dir = config_output_dir.parent
    active_results_dir = REPO_ROOT / "pathways" / "results" / "active_fgsea"
    return [
        study_results_dir / "msigdb_profile_report.json",
        study_results_dir / "msigdb_profile_report.md",
        active_results_dir / "msigdb_profile_report.json",
        active_results_dir / "msigdb_profile_report.md",
    ]


def run_msigdb_profile(
    config_path: Path,
    *,
    prepare_ranks: bool = False,
    build_phase2: bool = False,
    build_myst: bool = False,
    allow_missing_package: bool = False,
) -> dict[str, Any]:
    resolved = config_path.resolve()
    rank_prep_config = resolved.parent / "rank_prep.yml"
    rank_prep_payload: dict[str, Any] | None = None
    if prepare_ranks and rank_prep_config.exists():
        rank_prep_payload = prepare_fgsea_ranks(rank_prep_config)
    validation = validate_config(resolved)
    gene_set_source = validation.get("gene_set_source") or {}
    study_id = resolved.parent.parent.name
    payload: dict[str, Any] = {
        "study_id": study_id,
        "config": _display_path(resolved),
        "status": "invalid",
        "validation": validation,
        "review_page": "figures/output/review/index.html",
        "figure_05_python_manifest": "figures/output/python/figure_05_pathway_enrichment_dot.manifest.json",
        "figure_05_r_manifest": "figures/output/r/figure_05_pathway_enrichment_dot.manifest.json",
    }
    if rank_prep_payload is not None:
        payload["rank_prep"] = rank_prep_payload

    if gene_set_source.get("provider") != "msigdb":
        payload["validation"]["errors"] = list(payload["validation"].get("errors", [])) + [
            "Config is not MSigDB-backed; gene_set_source.provider must be `msigdb`"
        ]
        payload["status"] = "invalid"
    elif validation["status"] != "valid":
        payload["status"] = "invalid"
    else:
        activation = activate_fgsea_profile(resolved)
        payload["activation"] = activation
        _, fgsea_run = run_pipeline(
            ACTIVE_CONFIG_PATH,
            allow_missing_package=allow_missing_package,
        )
        payload["fgsea_run"] = fgsea_run
        payload["status"] = "ready" if fgsea_run.get("status") == "ready" else str(fgsea_run.get("status"))

        if build_phase2:
            build_payload = _run_python_step([sys.executable, "scripts/build_phase2.py"])
            payload["build_phase2"] = build_payload
            if build_payload["status"] != "ok":
                payload["status"] = "build_failed"

        if build_myst:
            myst_payload = _run_myst_step()
            payload["myst"] = myst_payload
            if myst_payload["status"] != "ok" and payload["status"] == "ready":
                payload["status"] = "myst_failed"

    report_paths = _report_paths(
        yaml.safe_load(resolved.read_text(encoding="utf-8"))
    )
    json_payload = json.dumps(payload, indent=2)
    for report_path in report_paths:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if report_path.suffix == ".json":
            report_path.write_text(json_payload + "\n", encoding="utf-8")
        else:
            _write_markdown_report(payload, report_path)
    payload["written_reports"] = [_display_path(path) for path in report_paths]
    payload["written_dossiers"] = list(write_fgsea_study_dossier(resolved).values())
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the MSigDB fgsea handoff workflow")
    parser.add_argument("--config", required=True)
    parser.add_argument("--prepare-ranks", action="store_true")
    parser.add_argument("--build-phase2", action="store_true")
    parser.add_argument("--myst", action="store_true")
    parser.add_argument("--allow-missing-package", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = run_msigdb_profile(
        Path(args.config),
        prepare_ranks=args.prepare_ranks,
        build_phase2=args.build_phase2,
        build_myst=args.myst,
        allow_missing_package=args.allow_missing_package,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"status: {payload['status']}")
        print(f"config: {payload['config']}")
        for report in payload.get("written_reports", []):
            print(f"report: {report}")
    return 0 if payload["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
