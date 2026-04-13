#!/usr/bin/env python3
"""Shared helpers for Python class-based figure renderers."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
CACHE_ROOT = REPO_ROOT / ".cache"
MPL_CACHE = CACHE_ROOT / "matplotlib"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
import matplotlib.pyplot as plt

from scripts.figures_common import (
    load_class_registry,
    load_yaml,
    normalize_spec,
    source_data_mapping,
)


THEME_PATH = REPO_ROOT / "figures/config/project_theme.yml"
FONT_POLICY_PATH = REPO_ROOT / "figures/config/font_policy.yml"
VENUE_PROFILES_PATH = REPO_ROOT / "figures/config/venue_profiles.yml"


def project_resources(spec_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    spec = normalize_spec(load_yaml(spec_path), spec_path)
    theme = load_yaml(THEME_PATH)
    font_policy = load_yaml(FONT_POLICY_PATH)
    profiles = load_yaml(VENUE_PROFILES_PATH)
    registry = load_class_registry()
    profile = profiles["profiles"][spec["target_profile"]]
    class_entry = registry[spec["class_id"]]
    return spec, theme, font_policy, profile, class_entry


def resolve_data_input(spec: dict[str, Any], index: int = 0) -> Path:
    generated_inputs = spec.get("generated_data_inputs", [])
    if isinstance(generated_inputs, list) and index < len(generated_inputs):
        generated_path = REPO_ROOT / str(generated_inputs[index])
        if generated_path.exists():
            return generated_path
    return REPO_ROOT / str(spec["data_inputs"][index])


def resolved_data_inputs(spec: dict[str, Any]) -> list[Path]:
    return [resolve_data_input(spec, index) for index, _ in enumerate(spec["data_inputs"])]


def _display_repo_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_fgsea_summary_for_export(export_path: Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    summary_path = export_path.parent / "fgsea_summary.json"
    if not summary_path.exists():
        return None
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    pathways_gmt = payload.get("pathways_gmt")
    config = payload.get("config")
    source_profile = payload.get("source_profile")
    summary_json = payload.get("summary_json") or _display_repo_path(summary_path, repo_root)
    figure_export_csv = payload.get("figure_export_csv") or _display_repo_path(export_path, repo_root)
    return {
        "run_id": payload.get("run_id"),
        "status": payload.get("status"),
        "config": config,
        "source_profile": source_profile,
        "raw_input_table": payload.get("raw_input_table"),
        "rank_prep_summary": payload.get("rank_prep_summary"),
        "summary_json": summary_json,
        "figure_export_csv": figure_export_csv,
        "pathways_gmt": pathways_gmt,
        "result_count": payload.get("result_count"),
        "figure_export_count": payload.get("figure_export_count"),
        "gene_set_source": payload.get("gene_set_source"),
        "top_pathways": payload.get("top_pathways", []),
    }


def infer_pathway_provenance(spec: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    for resolved_input in resolved_data_inputs(spec):
        if resolved_input.name != "fgsea_pathway_dot_export.csv":
            continue
        provenance = load_fgsea_summary_for_export(resolved_input, repo_root=repo_root)
        if provenance is None:
            return {
                "figure_export_csv": _display_repo_path(resolved_input, repo_root),
                "summary_json": _display_repo_path(resolved_input.parent / "fgsea_summary.json", repo_root),
                "status": "missing_summary",
            }
        return provenance
    return None


def mm_to_inches(value: float) -> float:
    return value / 25.4


def md5_for_path(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_csv_hash(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = sorted(reader.fieldnames or [])
        header = "\x1f".join(fieldnames)
        rows = []
        for row in reader:
            normalized = [_normalize_csv_semantic_value(row.get(field)) for field in fieldnames]
            rows.append("\x1f".join(normalized))
    payload = "\x1e".join([header, *sorted(rows)])
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def _normalize_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _normalize_csv_semantic_value(value: Any) -> str:
    normalized = _normalize_csv_value(value)
    stripped = normalized.strip()
    if not stripped:
        return ""
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered
    try:
        decimal_value = Decimal(stripped)
    except InvalidOperation:
        return stripped
    integral_value = decimal_value.to_integral_value()
    if decimal_value == integral_value:
        return str(int(integral_value))
    decimal_text = format(decimal_value.normalize(), "f")
    return decimal_text.rstrip("0").rstrip(".")


def export_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        normalized_rows = []
        for row in rows:
            normalized_rows.append(
                {field: _normalize_csv_value(row.get(field)) for field in fieldnames}
            )
        writer.writerows(normalized_rows)


def resolve_font_stack(font_policy: dict[str, Any]) -> dict[str, Any]:
    families = font_policy["families"]
    candidates = list(families["sans_preferred"]) + list(families["sans_fallbacks"])
    for family in candidates:
        try:
            font_path = font_manager.findfont(
                font_manager.FontProperties(family=family),
                fallback_to_default=False,
            )
        except ValueError:
            continue
        return {"family": family, "path": font_path, "candidates": candidates}
    raise RuntimeError("Could not resolve any font from the configured sans-serif stack")


def validate_common_contract(
    spec: dict[str, Any],
    theme: dict[str, Any],
    font_policy: dict[str, Any],
    profile: dict[str, Any],
    class_entry: dict[str, Any],
) -> None:
    required_spec_keys = {
        "figure_id",
        "class_id",
        "class_version",
        "title",
        "font_policy_id",
        "target_profile",
        "claim_ids",
        "fact_sheet",
        "visualization_plan",
        "legend_path",
        "qa_profile",
        "review_preset",
        "parity_status",
        "size",
        "renderers",
        "data_inputs",
    }
    missing_spec = sorted(required_spec_keys - spec.keys())
    if missing_spec:
        raise ValueError(f"figure spec is missing keys: {missing_spec}")
    source_data_mapping(spec)

    requirements = font_policy["requirements"]
    base_size = float(theme["typography"]["base_font_size_pt"])
    if not (requirements["min_text_size_pt"] <= base_size <= requirements["max_text_size_pt"]):
        raise ValueError("base font size is outside the configured publication range")

    panel_label_size = float(theme["panel_labels"]["font_size_pt"])
    if panel_label_size != float(requirements["panel_label_font_size_pt"]):
        raise ValueError("panel label font size does not match the font policy")
    if theme["panel_labels"]["case"] != requirements["panel_label_case"]:
        raise ValueError("panel label case does not match the font policy")

    if float(spec["size"]["height_mm"]) > float(profile["max_height_mm"]):
        raise ValueError("figure height exceeds the selected venue profile")
    if float(spec["size"]["width_mm"]) > float(profile["width_mm"]):
        raise ValueError("figure width exceeds the selected venue profile")

    if spec["class_version"] != class_entry["class_version"]:
        raise ValueError("spec class_version does not match the class registry")
    if spec["qa_profile"] != class_entry["qa_profile"]:
        raise ValueError("spec qa_profile does not match the class registry")
    if spec["review_preset"] != class_entry["review_preset"]:
        raise ValueError("spec review_preset does not match the class registry")
    if spec["parity_status"] not in {"dual", "authority_only"}:
        raise ValueError("spec parity_status must be dual or authority_only")
    if spec["parity_status"] == "authority_only" and not spec.get("authority_renderer"):
        raise ValueError("authority_only specs must define authority_renderer")


def configure_matplotlib(
    theme: dict[str, Any], font_policy: dict[str, Any], resolved_font: dict[str, Any]
) -> None:
    families = font_policy["families"]
    sans_candidates = list(families["sans_preferred"]) + list(families["sans_fallbacks"])
    plt.rcParams.update(
        {
            "font.family": font_policy["python"]["family"],
            "font.sans-serif": sans_candidates,
            "font.size": theme["typography"]["base_font_size_pt"],
            "axes.titlesize": theme["typography"]["title_font_size_pt"],
            "axes.labelsize": theme["typography"]["axis_label_font_size_pt"],
            "xtick.labelsize": theme["typography"]["tick_label_font_size_pt"],
            "ytick.labelsize": theme["typography"]["tick_label_font_size_pt"],
            "axes.linewidth": theme["strokes"]["axis_line_width_pt"],
            "lines.linewidth": theme["strokes"]["data_line_width_pt"],
            "pdf.fonttype": font_policy["python"]["pdf_fonttype"],
            "ps.fonttype": font_policy["python"]["ps_fonttype"],
            "svg.fonttype": font_policy["python"]["svg_fonttype"],
            "savefig.facecolor": theme["export_defaults"]["background"],
            "figure.facecolor": theme["export_defaults"]["background"],
        }
    )
    if not resolved_font.get("path"):
        raise RuntimeError("font resolution did not produce a concrete font path")


def apply_publication_layout(fig: Any, theme: dict[str, Any]) -> None:
    layout = theme.get("layout", {})
    if not bool(layout.get("constrained", False)):
        return
    layout_kwargs = {
        "w_pad": float(layout.get("constrained_w_pad_in", 0.08)),
        "h_pad": float(layout.get("constrained_h_pad_in", 0.08)),
        "wspace": float(layout.get("constrained_wspace", layout.get("panel_gap_wspace", 0.12))),
        "hspace": float(layout.get("constrained_hspace", layout.get("panel_gap_hspace", 0.12))),
    }
    layout_engine_getter = getattr(fig, "get_layout_engine", None)
    if callable(layout_engine_getter):
        layout_engine = layout_engine_getter()
        if layout_engine is not None and hasattr(layout_engine, "set"):
            layout_engine.set(**layout_kwargs)
            return
    fig.set_constrained_layout_pads(**layout_kwargs)


def add_panel_labels(spec: dict[str, Any], theme: dict[str, Any], axes: list[Any]) -> None:
    panels = spec.get("panels", [])
    labels = [str(panel["id"]) for panel in panels]
    for axis, label in zip(axes, labels):
        axis.text(
            float(theme["panel_labels"]["x_position_axes"]),
            float(theme["panel_labels"]["y_position_axes"]),
            label.lower(),
            transform=axis.transAxes,
            fontsize=theme["panel_labels"]["font_size_pt"],
            fontweight=theme["panel_labels"]["font_weight"],
            va="top",
        )


def write_manifest(
    spec: dict[str, Any],
    profile: dict[str, Any],
    resolved_font: dict[str, Any],
    renderer: str,
    spec_path: Path,
    outputs: dict[str, str],
    design_features: list[str],
    qa_metrics: dict[str, Any] | None = None,
) -> None:
    output_dir = REPO_ROOT / str(spec["renderers"][renderer]["output_dir"])
    source_data = source_data_mapping(spec)
    resolved_inputs = resolved_data_inputs(spec)
    checksum_paths = {
        "data_inputs": [REPO_ROOT / path for path in spec["data_inputs"]],
        "resolved_data_inputs": resolved_inputs,
        "source_data": [REPO_ROOT / path for path in source_data.values()],
        "outputs": [REPO_ROOT / path for path in outputs.values()],
    }
    checksums: dict[str, dict[str, str]] = {}
    for group, paths in checksum_paths.items():
        checksums[group] = {
            str(path.relative_to(REPO_ROOT)): md5_for_path(path) for path in paths
        }
    semantic_checksums = {
        "source_data": {
            str(path.relative_to(REPO_ROOT)): semantic_csv_hash(path)
            for path in checksum_paths["source_data"]
        }
    }

    manifest = {
        "figure_id": spec["figure_id"],
        "class_id": spec["class_id"],
        "class_version": spec["class_version"],
        "renderer": renderer,
        "title": spec["title"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "theme_id": spec["theme_id"],
        "font_policy_id": spec["font_policy_id"],
        "style_profile": spec["style_profile"],
        "target_profile": spec["target_profile"],
        "figure_size_mm": spec["size"],
        "profile_constraints": {
            "width_mm": profile["width_mm"],
            "max_height_mm": profile["max_height_mm"],
            "authoritative_formats": profile["authoritative_formats"],
        },
        "qa_profile": spec["qa_profile"],
        "review_preset": spec["review_preset"],
        "parity_status": spec["parity_status"],
        "authority_renderer": spec.get("authority_renderer"),
        "font_resolution": resolved_font,
        "spec_path": str(spec_path.relative_to(REPO_ROOT)),
        "data_inputs": list(spec["data_inputs"]),
        "generated_data_inputs": list(spec.get("generated_data_inputs", [])),
        "resolved_data_inputs": [str(path.relative_to(REPO_ROOT)) for path in resolved_inputs],
        "source_data": source_data,
        "pathway_provenance": infer_pathway_provenance(spec),
        "claim_ids": list(spec["claim_ids"]),
        "fact_sheet": str(spec["fact_sheet"]),
        "visualization_plan": str(spec["visualization_plan"]),
        "legend_path": str(spec["legend_path"]),
        "outputs": outputs,
        "checksums_md5": checksums,
        "checksums_semantic": semantic_checksums,
        "caption_stub": spec["caption_stub"],
        "design_features": design_features,
        "qa_metrics": qa_metrics or {},
    }
    manifest_path = output_dir / f"{spec['figure_id']}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
