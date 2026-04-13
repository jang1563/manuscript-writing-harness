#!/usr/bin/env python3
"""Build study-level fgsea dossier artifacts for pathway-analysis handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from activate_fgsea_profile import ACTIVE_CONFIG_PATH
from fgsea_pipeline import REPO_ROOT, validate_config


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _count_csv_rows(path: Path | None) -> int:
    if path is None or not path.exists():
        return 0
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(0, len(lines) - 1)


def _count_gmt_records(path: Path | None) -> int:
    if path is None or not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _load_manifest(renderer: str) -> dict[str, Any] | None:
    return _load_json(REPO_ROOT / f"figures/output/{renderer}/figure_05_pathway_enrichment_dot.manifest.json")


def _manifest_sync_status(
    config_display_path: str,
    manifests: dict[str, dict[str, Any] | None],
    *,
    is_active_source: bool,
) -> dict[str, Any]:
    if not is_active_source:
        return {
            "status": "inactive",
            "synced_renderers": [],
            "unsynced_renderers": sorted(manifests.keys()),
        }

    synced_renderers: list[str] = []
    unsynced_renderers: list[str] = []
    for renderer, manifest in manifests.items():
        provenance = (manifest or {}).get("pathway_provenance") or {}
        if provenance.get("source_profile") == config_display_path:
            synced_renderers.append(renderer)
        else:
            unsynced_renderers.append(renderer)
    status = "synced" if not unsynced_renderers else "drift"
    return {
        "status": status,
        "synced_renderers": synced_renderers,
        "unsynced_renderers": unsynced_renderers,
    }


def _classify_readiness(
    validation: dict[str, Any],
    rank_prep_summary: dict[str, Any] | None,
    fgsea_summary: dict[str, Any] | None,
) -> tuple[str, list[str], list[str]]:
    errors = list(validation.get("errors", []))
    warnings: list[str] = []

    if fgsea_summary and str(fgsea_summary.get("status")) == "ready":
        if int(fgsea_summary.get("result_count") or 0) == 0:
            warnings.append("fgsea completed but returned zero enriched pathways for the current study profile")
        return "ready", errors, warnings

    only_missing_gmt = bool(errors) and all(
        "pathways_gmt not found" in error or "MSigDB GMT not found" in error for error in errors
    )
    if rank_prep_summary and str(rank_prep_summary.get("status")) == "ready" and only_missing_gmt:
        warnings.append("rank preparation is ready; add the licensed MSigDB GMT to move this profile to ready")
        return "provisional", errors, warnings

    if validation.get("status") == "valid":
        warnings.append("validated study config has not yet produced an fgsea summary")
        return "provisional", errors, warnings

    return "blocked", errors, warnings


def build_fgsea_study_dossier(config_path: Path) -> dict[str, Any]:
    resolved = config_path.resolve()
    config = _load_yaml(resolved)
    validation = validate_config(resolved)
    config_display_path = _display_path(resolved)
    study_id = str(config.get("run_id") or resolved.parent.parent.name)

    raw_input_path = _resolve_repo_path(str(config.get("raw_input_table", "")) or None)
    rank_prep_summary_path = _resolve_repo_path(str(config.get("rank_prep_summary", "")) or None)
    ranks_path = _resolve_repo_path(str(config.get("ranks_csv", "")) or None)
    pathways_gmt_path = _resolve_repo_path(str(config.get("pathways_gmt", "")) or None)
    output_dir = _resolve_repo_path(str(config.get("output_dir", "")) or None)
    figure_export_path = _resolve_repo_path(str(config.get("figure_export_csv", "")) or None)
    fgsea_summary_path = output_dir / "fgsea_summary.json" if output_dir is not None else None
    fgsea_results_path = output_dir / "fgsea_results.csv" if output_dir is not None else None

    rank_prep_summary = _load_json(rank_prep_summary_path)
    fgsea_summary = _load_json(fgsea_summary_path)
    active_config = _load_yaml(ACTIVE_CONFIG_PATH)
    active_config_display_path = _display_path(ACTIVE_CONFIG_PATH.resolve())
    active_source_profile = str(active_config.get("source_profile", ""))
    is_active_source = config_display_path in {
        active_config_display_path,
        active_source_profile,
    }

    manifests = {
        "python": _load_manifest("python"),
        "r": _load_manifest("r"),
    }
    manifest_sync = _manifest_sync_status(config_display_path, manifests, is_active_source=is_active_source)
    readiness, blocking_issues, warnings = _classify_readiness(validation, rank_prep_summary, fgsea_summary)

    report = {
        "study_id": study_id,
        "config": config_display_path,
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "study_kind": "msigdb"
        if ((validation.get("gene_set_source") or {}).get("provider") == "msigdb")
        else "custom",
        "active_profile": {
            "is_active_source": is_active_source,
            "active_config": active_config_display_path,
            "source_profile": active_source_profile,
            "figure_05_sync": manifest_sync,
        },
        "inputs": {
            "raw_input_table": _display_path(raw_input_path) if raw_input_path else None,
            "raw_input_rows": _count_csv_rows(raw_input_path),
            "ranks_csv": _display_path(ranks_path) if ranks_path else None,
            "ranks_rows": _count_csv_rows(ranks_path),
            "rank_prep_summary": _display_path(rank_prep_summary_path) if rank_prep_summary_path else None,
            "pathways_gmt": _display_path(pathways_gmt_path) if pathways_gmt_path else None,
            "pathway_count": _count_gmt_records(pathways_gmt_path),
        },
        "rank_prep": rank_prep_summary or {
            "status": "missing",
            "summary_json": _display_path(rank_prep_summary_path) if rank_prep_summary_path else None,
        },
        "fgsea": fgsea_summary or {
            "status": "missing",
            "summary_json": _display_path(fgsea_summary_path) if fgsea_summary_path else None,
            "results_csv": _display_path(fgsea_results_path) if fgsea_results_path else None,
            "figure_export_csv": _display_path(figure_export_path) if figure_export_path else None,
        },
        "validation": validation,
        "figure_05": {
            "review_page": "figures/output/review/index.html",
            "python_manifest": "figures/output/python/figure_05_pathway_enrichment_dot.manifest.json",
            "r_manifest": "figures/output/r/figure_05_pathway_enrichment_dot.manifest.json",
            "python_provenance": (manifests["python"] or {}).get("pathway_provenance"),
            "r_provenance": (manifests["r"] or {}).get("pathway_provenance"),
            "python_preview_png": "figures/output/python/figure_05_pathway_enrichment_dot.png",
            "r_preview_png": "figures/output/r/figure_05_pathway_enrichment_dot.png",
        },
    }
    return report


def render_fgsea_study_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# fgsea Study Dossier: {report['study_id']}",
        "",
        f"- readiness: `{report['readiness']}`",
        f"- config: `{report['config']}`",
        f"- study_kind: `{report['study_kind']}`",
        f"- active source: `{report['active_profile']['is_active_source']}`",
        f"- figure_05 sync: `{report['active_profile']['figure_05_sync']['status']}`",
        "",
        "## Inputs",
        "",
        f"- raw_input_table: `{report['inputs']['raw_input_table']}`",
        f"- raw_input_rows: `{report['inputs']['raw_input_rows']}`",
        f"- ranks_csv: `{report['inputs']['ranks_csv']}`",
        f"- ranks_rows: `{report['inputs']['ranks_rows']}`",
        f"- rank_prep_summary: `{report['inputs']['rank_prep_summary']}`",
        f"- pathways_gmt: `{report['inputs']['pathways_gmt']}`",
        f"- pathway_count: `{report['inputs']['pathway_count']}`",
        "",
        "## fgsea",
        "",
        f"- status: `{report['fgsea'].get('status', 'missing')}`",
        f"- summary_json: `{report['fgsea'].get('summary_json', 'n/a')}`",
        f"- results_csv: `{report['fgsea'].get('results_csv', 'n/a')}`",
        f"- figure_export_csv: `{report['fgsea'].get('figure_export_csv', 'n/a')}`",
        f"- result_count: `{report['fgsea'].get('result_count', 'n/a')}`",
        f"- figure_export_count: `{report['fgsea'].get('figure_export_count', 'n/a')}`",
        "",
        "## Figure 05",
        "",
        f"- review_page: `{report['figure_05']['review_page']}`",
        f"- python_manifest: `{report['figure_05']['python_manifest']}`",
        f"- r_manifest: `{report['figure_05']['r_manifest']}`",
        f"- python_preview_png: `{report['figure_05']['python_preview_png']}`",
        f"- r_preview_png: `{report['figure_05']['r_preview_png']}`",
        "",
    ]
    if report["blocking_issues"]:
        lines.extend(["## Blocking Issues", ""])
        lines.extend(f"- {item}" for item in report["blocking_issues"])
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_fgsea_study_dossier(config_path: Path, *, write_active_mirror: bool = True) -> dict[str, str]:
    report = build_fgsea_study_dossier(config_path)
    resolved = config_path.resolve()
    study_results_dir = resolved.parent.parent / "results"
    report_json_path = study_results_dir / "study_dossier.json"
    report_md_path = study_results_dir / "study_dossier.md"
    study_results_dir.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report_md_path.write_text(render_fgsea_study_markdown(report), encoding="utf-8")

    writes = {
        "report_json": _display_path(report_json_path),
        "report_md": _display_path(report_md_path),
    }

    if write_active_mirror and bool(report["active_profile"]["is_active_source"]):
        active_dir = REPO_ROOT / "pathways" / "results" / "active_fgsea"
        active_json = active_dir / "study_dossier.json"
        active_md = active_dir / "study_dossier.md"
        active_dir.mkdir(parents=True, exist_ok=True)
        active_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        active_md.write_text(render_fgsea_study_markdown(report), encoding="utf-8")
        writes["active_report_json"] = _display_path(active_json)
        writes["active_report_md"] = _display_path(active_md)

    return writes
