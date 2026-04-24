#!/usr/bin/env python3
"""Validate generated figure and table artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

from build_figure_review import analyze_png
from figures_common import (
    REPO_ROOT,
    enabled_renderers,
    figure_output_paths,
    load_json,
    manuscript_figure_items,
    resolve_specs,
    source_data_mapping,
)


BASE_REQUIRED_FILES = [
    "figures/config/project_theme.yml",
    "figures/config/font_policy.yml",
    "figures/config/venue_profiles.yml",
    "figures/registry/classes.yml",
    "figures/plans/visualization_plan.json",
    "manuscript/plans/display_item_map.json",
    "figures/output/review/index.html",
]

TABLE_REQUIRED_FILES = [
    "tables/fact_sheets/table_01_main.json",
    "tables/output/table_01_main.md",
    "tables/output/table_01_main.csv",
    "tables/output/table_01_main.json",
    "tables/output/table_01_main.manifest.json",
]


def _resolved_data_inputs(spec: dict[str, Any]) -> list[str]:
    resolved = []
    generated_inputs = spec.get("generated_data_inputs", [])
    for index, declared_path in enumerate(spec["data_inputs"]):
        if isinstance(generated_inputs, list) and index < len(generated_inputs):
            generated_path = REPO_ROOT / str(generated_inputs[index])
            if generated_path.exists():
                resolved.append(str(Path(generated_inputs[index])))
                continue
        resolved.append(str(Path(declared_path)))
    return resolved


def _expected_pathway_provenance(spec: dict[str, Any]) -> dict[str, Any] | None:
    for resolved in _resolved_data_inputs(spec):
        resolved_path = REPO_ROOT / resolved
        if resolved_path.name != "fgsea_pathway_dot_export.csv":
            continue
        summary_path = resolved_path.parent / "fgsea_summary.json"
        if not summary_path.exists():
            return {
                "figure_export_csv": resolved,
                "summary_json": str(summary_path.relative_to(REPO_ROOT)),
                "status": "missing_summary",
            }
        summary = load_json(summary_path)
        return {
            "run_id": summary.get("run_id"),
            "status": summary.get("status"),
            "config": summary.get("config"),
            "source_profile": summary.get("source_profile"),
            "raw_input_table": summary.get("raw_input_table"),
            "rank_prep_summary": summary.get("rank_prep_summary"),
            "summary_json": summary.get("summary_json"),
            "figure_export_csv": summary.get("figure_export_csv"),
            "pathways_gmt": summary.get("pathways_gmt"),
            "result_count": summary.get("result_count"),
            "figure_export_count": summary.get("figure_export_count"),
            "gene_set_source": summary.get("gene_set_source"),
            "top_pathways": summary.get("top_pathways", []),
        }
    return None


def _normalize_pathway_provenance(value: Any) -> Any:
    if value in (None, {}, []):
        return None
    if isinstance(value, dict):
        normalized = {key: _normalize_pathway_provenance(item) for key, item in value.items()}
        return {
            key: item
            for key, item in normalized.items()
            if item not in (None, {}, [])
        }
    if isinstance(value, list):
        normalized_list = [_normalize_pathway_provenance(item) for item in value]
        return [item for item in normalized_list if item not in (None, {}, [])]
    return value


def _allows_empty_pathway_export(spec: dict[str, Any]) -> bool:
    provenance = _expected_pathway_provenance(spec)
    if not provenance:
        return False
    return str(provenance.get("status")) == "ready" and int(provenance.get("figure_export_count") or 0) == 0


def _source_data_tokens(spec: dict[str, Any], column: str, *, limit: int = 2) -> list[str]:
    tokens: list[str] = []
    for panel_path in source_data_mapping(spec).values():
        path = REPO_ROOT / panel_path
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                token = str(row.get(column, "")).strip()
                if token and token not in tokens:
                    tokens.append(token)
                if len(tokens) >= limit:
                    return tokens
    return tokens


def _svg_token_rules_for_spec(
    spec: dict[str, Any],
    *,
    allow_empty_pathway_export: bool,
) -> list[str]:
    figure_id = spec["figure_id"]
    if figure_id == "figure_05_pathway_enrichment_dot" and not allow_empty_pathway_export:
        tokens = _source_data_tokens(spec, "pathway")
        if tokens:
            return tokens
    return SVG_TOKEN_RULES.get(figure_id, [])


SVG_TOKEN_RULES = {
    "figure_01_example": ["Control", "Treated"],
    "figure_02_volcano_pathway": [
        "CXCL10",
        "MKI67",
        "Interferon alpha response",
        "Cell cycle checkpoint",
    ],
    "figure_03_ma_plot": ["CXCL10", "CDK1"],
    "figure_04_sample_pca": ["C1", "T2", "PC1 (48%)"],
    "figure_05_pathway_enrichment_dot": [
        "Interferon alpha response",
        "Cell cycle checkpoint",
    ],
    "figure_06_roc_pr_compound": [
        "Foundation model",
        "AUROC summary",
        "AUPRC summary",
        "Prevalence baseline",
    ],
    "figure_07_calibration_reliability": [
        "Foundation model",
        "ECE summary",
        "Reliability diagram",
        "Confidence support by bin",
    ],
    "figure_08_training_dynamics": [
        "Foundation model",
        "Training and validation loss",
        "Validation AUROC trajectory",
        "Best validation AUROC",
    ],
    "figure_09_confusion_matrix_normalized": [
        "Healthy",
        "Inflammatory",
        "Proliferative",
        "Fibrotic",
        "Normalized confusion matrix",
        "Dominant off-diagonal confusion",
    ],
    "figure_10_feature_importance_summary": [
        "Fibrosis score",
        "IL6 program",
        "Feature importance rank",
        "Signed effect on predicted response",
    ],
    "figure_11_ablation_summary": [
        "No context encoder",
        "No calibration loss",
        "AUROC drop vs full model",
        "Secondary metric shifts",
    ],
}

CLASS_DESIGN_FEATURES = {
    "timecourse_endpoint": [
        "direct_labels_for_small_number_of_series",
        "replicate_level_points_in_endpoint_panel",
        "vector_first_export",
    ],
    "volcano_pathway_compound": [
        "threshold_guides_for_significance",
        "selective_gene_labels_for_extreme_points",
        "de_emphasized_nonsignificant_points",
        "signed_enrichment_panel",
        "vector_first_export",
    ],
    "ma_plot": [
        "threshold_guides_for_mean_difference",
        "selective_gene_labels_for_extreme_points",
        "de_emphasized_background_points",
        "vector_first_export",
    ],
    "sample_pca": [
        "group_coloring_for_sample_separation",
        "batch_shape_encoding",
        "selective_sample_labels",
        "vector_first_export",
    ],
    "pathway_enrichment_dot": [
        "dot_size_encodes_gene_count",
        "annotation_for_significance_strength",
        "direction_color_encoding",
        "vector_first_export",
    ],
    "roc_pr_compound": [
        "paired_roc_and_pr_panels",
        "uncertainty_ribbons_for_curve_stability",
        "operating_point_markers_and_direct_labels",
        "prevalence_baseline_in_pr_panel",
        "vector_first_export",
    ],
    "calibration_reliability": [
        "reliability_diagram_with_identity_reference",
        "bin_level_uncertainty_intervals",
        "direct_labels_for_model_identity",
        "confidence_support_panel_for_coverage_context",
        "vector_first_export",
    ],
    "training_dynamics": [
        "paired_loss_and_metric_panels",
        "split_encoding_not_color_only",
        "direct_labels_at_final_epoch",
        "best_checkpoint_markers",
        "vector_first_export",
    ],
    "confusion_matrix_normalized": [
        "row_normalized_confusion_heatmap",
        "annotated_cell_percentages",
        "off_diagonal_error_summary_panel",
        "class_level_error_interpretation",
        "vector_first_export",
    ],
    "feature_importance_summary": [
        "ranked_feature_importance_panel",
        "signed_directional_effect_panel",
        "group_semantic_encoding",
        "zero_centered_effect_reference",
        "vector_first_export",
    ],
    "ablation_summary": [
        "ranked_primary_metric_drop_panel",
        "secondary_metric_shift_panel",
        "group_semantic_encoding",
        "metric_shape_encoding_not_color_only",
        "zero_centered_effect_reference",
        "vector_first_export",
    ],
}

CLASS_QA_RULES = {
    "volcano_pathway_compound": {
        "max_highlight_labels": 8,
        "required_threshold_line_count": 3,
        "required_reference_line_count": 1,
    },
    "ma_plot": {
        "max_highlight_labels": 8,
        "required_threshold_line_count": 2,
        "required_reference_line_count": 1,
    },
    "sample_pca": {
        "max_highlight_labels": 4,
        "required_reference_line_count": 2,
    },
    "pathway_enrichment_dot": {
        "min_annotation_count": 4,
    },
    "roc_pr_compound": {
        "required_reference_line_count": 2,
        "min_annotation_count": 8,
        "min_operating_point_count": 6,
        "min_uncertainty_band_count": 6,
    },
    "calibration_reliability": {
        "required_reference_line_count": 1,
        "min_annotation_count": 3,
        "min_uncertainty_band_count": 3,
    },
    "training_dynamics": {
        "min_annotation_count": 8,
        "min_best_checkpoint_count": 3,
    },
    "confusion_matrix_normalized": {
        "min_annotation_count": 8,
        "min_diagonal_cell_count": 4,
        "min_off_diagonal_summary_count": 4,
    },
    "feature_importance_summary": {
        "max_highlight_labels": 6,
        "required_reference_line_count": 1,
        "min_annotation_count": 10,
    },
    "ablation_summary": {
        "max_highlight_labels": 5,
        "required_reference_line_count": 2,
        "min_annotation_count": 10,
    },
}


def _ensure_nonempty(path: Path) -> None:
    if path.stat().st_size == 0:
        raise ValueError(f"{path.relative_to(REPO_ROOT)} is empty")


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return sum(1 for _ in reader)


def required_files(specs: list[dict[str, Any]], include_table: bool) -> list[str]:
    files = list(BASE_REQUIRED_FILES)
    manuscript_items = manuscript_figure_items()
    for spec in specs:
        figure_id = spec["figure_id"]
        files.extend(
            [
                str(spec["_spec_path"]),
                str(spec["fact_sheet"]),
                str(spec["legend_path"]),
                *spec["data_inputs"],
                *source_data_mapping(spec).values(),
            ]
        )
        for renderer in enabled_renderers(spec):
            for output in figure_output_paths(spec, renderer).values():
                files.append(output)
        item = manuscript_items.get(figure_id)
        if item is not None:
            files.append(str(item["preview_asset"]))
            files.append(f"manuscript/sections/assets/generated/{figure_id}.png")
    if include_table:
        files.extend(TABLE_REQUIRED_FILES)
    return files


def _validate_manifest(manifest: dict[str, Any], spec: dict[str, Any], renderer: str) -> None:
    if manifest.get("figure_id") != spec["figure_id"]:
        raise ValueError(f"{renderer} manifest has unexpected figure_id for {spec['figure_id']}")
    if manifest.get("class_id") != spec["class_id"]:
        raise ValueError(f"{renderer} manifest has unexpected class_id for {spec['figure_id']}")
    if manifest.get("renderer") != renderer:
        raise ValueError(f"{renderer} manifest has wrong renderer field for {spec['figure_id']}")
    if manifest.get("class_version") != spec["class_version"]:
        raise ValueError(f"{renderer} manifest has wrong class_version for {spec['figure_id']}")
    if manifest.get("qa_profile") != spec["qa_profile"]:
        raise ValueError(f"{renderer} manifest has wrong qa_profile for {spec['figure_id']}")
    if manifest.get("review_preset") != spec["review_preset"]:
        raise ValueError(f"{renderer} manifest has wrong review_preset for {spec['figure_id']}")
    if manifest.get("style_profile") != spec["style_profile"]:
        raise ValueError(f"{renderer} manifest has wrong style_profile for {spec['figure_id']}")
    if manifest.get("parity_status") != spec["parity_status"]:
        raise ValueError(f"{renderer} manifest has wrong parity_status for {spec['figure_id']}")
    if manifest.get("claim_ids") != spec["claim_ids"]:
        raise ValueError(f"{renderer} manifest claim_ids do not match spec for {spec['figure_id']}")
    if manifest.get("fact_sheet") != spec["fact_sheet"]:
        raise ValueError(f"{renderer} manifest fact_sheet does not match spec for {spec['figure_id']}")
    if manifest.get("visualization_plan") != spec["visualization_plan"]:
        raise ValueError(
            f"{renderer} manifest visualization_plan does not match spec for {spec['figure_id']}"
        )
    if manifest.get("legend_path") != spec["legend_path"]:
        raise ValueError(f"{renderer} manifest legend_path does not match spec for {spec['figure_id']}")
    if manifest.get("data_inputs") != spec["data_inputs"]:
        raise ValueError(f"{renderer} manifest data_inputs do not match spec for {spec['figure_id']}")
    if manifest.get("generated_data_inputs", []) != spec.get("generated_data_inputs", []):
        raise ValueError(f"{renderer} manifest generated_data_inputs do not match spec for {spec['figure_id']}")
    if manifest.get("resolved_data_inputs") != _resolved_data_inputs(spec):
        raise ValueError(f"{renderer} manifest resolved_data_inputs do not match resolved inputs for {spec['figure_id']}")
    expected_pathway_provenance = _normalize_pathway_provenance(_expected_pathway_provenance(spec))
    manifest_pathway_provenance = _normalize_pathway_provenance(manifest.get("pathway_provenance"))
    if manifest_pathway_provenance != expected_pathway_provenance:
        raise ValueError(
            f"{renderer} manifest pathway_provenance does not match fgsea summary for {spec['figure_id']}"
        )
    if manifest.get("source_data") != source_data_mapping(spec):
        raise ValueError(f"{renderer} manifest source_data do not match spec for {spec['figure_id']}")
    semantic_checksums = manifest.get("checksums_semantic", {})
    if sorted(semantic_checksums.keys()) != ["source_data"]:
        raise ValueError(
            f"{renderer} manifest semantic checksums are incomplete for {spec['figure_id']}"
        )
    if sorted(semantic_checksums["source_data"].keys()) != sorted(source_data_mapping(spec).values()):
        raise ValueError(
            f"{renderer} manifest semantic source-data checksums do not match spec for {spec['figure_id']}"
        )
    outputs = manifest.get("outputs", {})
    if sorted(outputs.keys()) != ["pdf", "png", "svg"]:
        raise ValueError(f"{renderer} manifest outputs are incomplete for {spec['figure_id']}")
    design_features = manifest.get("design_features", [])
    for feature in CLASS_DESIGN_FEATURES[spec["class_id"]]:
        if feature not in design_features:
            raise ValueError(
                f"{renderer} manifest missing design feature {feature} for {spec['figure_id']}"
            )


def _validate_fact_sheet(spec: dict[str, Any]) -> None:
    fact_sheet = load_json(REPO_ROOT / str(spec["fact_sheet"]))
    if fact_sheet.get("figure_id") != spec["figure_id"]:
        raise ValueError(f"fact sheet does not match figure_id for {spec['figure_id']}")
    if fact_sheet.get("claim_ids") != spec["claim_ids"]:
        raise ValueError(f"fact sheet claim_ids do not match spec for {spec['figure_id']}")


def _validate_visualization_plan(spec: dict[str, Any], visualization_plan: dict[str, Any]) -> None:
    plan_items = visualization_plan.get("figures", [])
    matched = next(
        (item for item in plan_items if item.get("figure_id") == spec["figure_id"]),
        None,
    )
    if matched is None:
        raise ValueError(f"visualization_plan.json is missing {spec['figure_id']}")
    if matched.get("spec_path") != spec["_spec_path"]:
        raise ValueError(f"visualization plan spec_path drift detected for {spec['figure_id']}")
    if matched.get("fact_sheet") != spec["fact_sheet"]:
        raise ValueError(f"visualization plan fact_sheet drift detected for {spec['figure_id']}")
    if matched.get("claim_ids") != spec["claim_ids"]:
        raise ValueError(f"visualization plan claim_ids drift detected for {spec['figure_id']}")


def _validate_class_specific_rules(
    spec: dict[str, Any], manifest_by_renderer: dict[str, dict[str, Any]]
) -> None:
    rules = CLASS_QA_RULES.get(spec["class_id"], {})
    if not rules:
        return
    qa_metrics = {
        renderer: manifest.get("qa_metrics", {})
        for renderer, manifest in manifest_by_renderer.items()
    }
    reference = next(iter(qa_metrics.values()))
    allow_empty_pathway_export = _allows_empty_pathway_export(spec)
    for renderer, metrics in qa_metrics.items():
        if metrics != reference:
            raise ValueError(
                f"{spec['figure_id']} renderer parity drift detected between manifests"
            )
        highlight_count = int(metrics.get("highlight_label_count", 0))
        if "max_highlight_labels" in rules and highlight_count > int(rules["max_highlight_labels"]):
            raise ValueError(
                f"{spec['figure_id']} exceeds the highlighted-label limit for {spec['class_id']}"
            )
        threshold_count = int(metrics.get("threshold_line_count", 0))
        if threshold_count < int(rules.get("required_threshold_line_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required threshold lines for {spec['figure_id']}"
            )
        reference_count = int(metrics.get("reference_line_count", 0))
        if reference_count < int(rules.get("required_reference_line_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required reference lines for {spec['figure_id']}"
            )
        annotation_count = int(metrics.get("annotation_count", 0))
        if not allow_empty_pathway_export and annotation_count < int(rules.get("min_annotation_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required annotations for {spec['figure_id']}"
            )
        operating_point_count = int(metrics.get("operating_point_count", 0))
        if operating_point_count < int(rules.get("min_operating_point_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required operating points for {spec['figure_id']}"
            )
        uncertainty_band_count = int(metrics.get("uncertainty_band_count", 0))
        if uncertainty_band_count < int(rules.get("min_uncertainty_band_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required uncertainty bands for {spec['figure_id']}"
            )
        best_checkpoint_count = int(metrics.get("best_checkpoint_count", 0))
        if best_checkpoint_count < int(rules.get("min_best_checkpoint_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required best-checkpoint markers for {spec['figure_id']}"
            )
        diagonal_cell_count = int(metrics.get("diagonal_cell_count", 0))
        if diagonal_cell_count < int(rules.get("min_diagonal_cell_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required diagonal cell coverage for {spec['figure_id']}"
            )
        off_diagonal_summary_count = int(metrics.get("off_diagonal_summary_count", 0))
        if off_diagonal_summary_count < int(rules.get("min_off_diagonal_summary_count", 0)):
            raise ValueError(
                f"{renderer} manifest is missing required off-diagonal summaries for {spec['figure_id']}"
            )


def _validate_dual_renderer_semantics(
    spec: dict[str, Any], manifest_by_renderer: dict[str, dict[str, Any]]
) -> None:
    if spec["parity_status"] != "dual" or len(manifest_by_renderer) < 2:
        return
    reference_renderer, reference_manifest = next(iter(manifest_by_renderer.items()))
    for renderer, manifest in manifest_by_renderer.items():
        if renderer == reference_renderer:
            continue
        if manifest.get("claim_ids") != reference_manifest.get("claim_ids"):
            raise ValueError(f"{spec['figure_id']} claim_ids drift between {reference_renderer} and {renderer}")
        if manifest.get("data_inputs") != reference_manifest.get("data_inputs"):
            raise ValueError(
                f"{spec['figure_id']} data_inputs drift between {reference_renderer} and {renderer}"
            )
        if manifest.get("source_data") != reference_manifest.get("source_data"):
            raise ValueError(
                f"{spec['figure_id']} source_data mapping drift between {reference_renderer} and {renderer}"
            )
        if sorted(manifest.get("design_features", [])) != sorted(reference_manifest.get("design_features", [])):
            raise ValueError(
                f"{spec['figure_id']} design feature drift detected between {reference_renderer} and {renderer}"
            )
        if manifest.get("qa_metrics", {}) != reference_manifest.get("qa_metrics", {}):
            raise ValueError(
                f"{spec['figure_id']} qa_metrics drift detected between {reference_renderer} and {renderer}"
            )
        # Source-data CSVs are shared artifact paths. Renderer manifests keep their
        # own build-time hashes, while the final files are validated separately.


def _validate_figure_outputs(
    spec: dict[str, Any],
    review_html: str,
    visualization_plan: dict[str, Any],
    manuscript_items: dict[str, dict[str, Any]],
) -> None:
    figure_id = spec["figure_id"]
    allow_empty_pathway_export = _allows_empty_pathway_export(spec)
    if figure_id not in review_html:
        raise ValueError(f"review HTML is missing {figure_id}")
    _validate_fact_sheet(spec)
    _validate_visualization_plan(spec, visualization_plan)

    manifest_by_renderer: dict[str, dict[str, Any]] = {}
    for panel_path in source_data_mapping(spec).values():
        minimum_rows = 1 if allow_empty_pathway_export else 2
        if _count_csv_rows(REPO_ROOT / panel_path) < minimum_rows:
            raise ValueError(f"source-data export {panel_path} is too small for {figure_id}")
    for renderer in enabled_renderers(spec):
        output_paths = figure_output_paths(spec, renderer)
        svg_text = (REPO_ROOT / output_paths["svg"]).read_text(encoding="utf-8")
        if "<svg" not in svg_text or "<text" not in svg_text:
            raise ValueError(f"{renderer} SVG for {figure_id} is missing vector text")
        token_rules = (
            []
            if allow_empty_pathway_export and figure_id == "figure_05_pathway_enrichment_dot"
            else _svg_token_rules_for_spec(
                spec,
                allow_empty_pathway_export=allow_empty_pathway_export,
            )
        )
        for token in token_rules:
            if token not in svg_text:
                raise ValueError(f"{renderer} SVG for {figure_id} is missing expected token {token!r}")
        png_analysis = analyze_png(REPO_ROOT / output_paths["png"])
        if png_analysis["clipping_risk"] == "high":
            raise ValueError(
                f"{renderer} PNG for {figure_id} has high clipping risk at "
                f"{png_analysis['hotspot_edge']} ({png_analysis['clipping_reason']})"
            )
        manifest = load_json(REPO_ROOT / output_paths["manifest"])
        _validate_manifest(manifest, spec, renderer)
        manifest_by_renderer[renderer] = manifest

    _validate_dual_renderer_semantics(spec, manifest_by_renderer)
    _validate_class_specific_rules(spec, manifest_by_renderer)
    mapped_item = manuscript_items.get(figure_id)
    if mapped_item is not None:
        if str(mapped_item.get("spec_path")) != spec["_spec_path"]:
            raise ValueError(f"display_item_map spec_path drift detected for {figure_id}")
        if str(mapped_item.get("fact_sheet")) != spec["fact_sheet"]:
            raise ValueError(f"display_item_map fact_sheet drift detected for {figure_id}")
        if str(mapped_item.get("legend_path")) != spec["legend_path"]:
            raise ValueError(f"display_item_map legend drift detected for {figure_id}")
        if mapped_item.get("claim_ids") != spec["claim_ids"]:
            raise ValueError(f"display_item_map claim_ids drift detected for {figure_id}")
        preview_path = REPO_ROOT / str(mapped_item["preview_asset"])
        if not preview_path.exists():
            raise ValueError(f"preview asset is missing for manuscript figure {figure_id}")
        section_preview = REPO_ROOT / f"manuscript/sections/assets/generated/{figure_id}.png"
        if not section_preview.exists():
            raise ValueError(f"section preview asset is missing for manuscript figure {figure_id}")


def _validate_table_outputs() -> None:
    table_md = (REPO_ROOT / "tables/output/table_01_main.md").read_text(encoding="utf-8")
    if "| Model | Cohort | N | AUROC | AUPRC | Calibration Error |" not in table_md:
        raise ValueError("table markdown header is missing or malformed")
    table_json = load_json(REPO_ROOT / "tables/output/table_01_main.json")
    if table_json.get("table_id") != "table_01_main":
        raise ValueError("table JSON has an unexpected table_id")
    if len(table_json.get("rows", [])) < 2:
        raise ValueError("table JSON does not contain enough rows")
    table_manifest = load_json(REPO_ROOT / "tables/output/table_01_main.manifest.json")
    if table_manifest.get("claim_ids") != ["claim_model_ranking"]:
        raise ValueError("table manifest claim_ids are missing or malformed")


def validate_generated_artifacts(
    figure_ids: list[str] | None = None, include_table: bool = False
) -> None:
    specs = resolve_specs(figure_ids)
    expected_files = required_files(specs, include_table=include_table)
    missing = [path for path in expected_files if not (REPO_ROOT / path).exists()]
    if missing:
        raise ValueError(f"Missing files: {missing}")
    for relative in expected_files:
        _ensure_nonempty(REPO_ROOT / relative)

    review_html = (REPO_ROOT / "figures/output/review/index.html").read_text(encoding="utf-8")
    if "Generated Figure Review" not in review_html:
        raise ValueError("review HTML is missing its expected title")
    for required_fragment in (
        "Renderer Comparison",
        "Thumbnail diff",
        "Small-size readability",
        "Font audit",
        "Clipping risk",
    ):
        if required_fragment not in review_html:
            raise ValueError(f"review HTML is missing QA section {required_fragment!r}")

    visualization_plan = load_json(REPO_ROOT / "figures/plans/visualization_plan.json")
    all_plan_ids = {
        item.get("figure_id") for item in visualization_plan.get("figures", [])
    }
    missing_from_plan = [spec["figure_id"] for spec in specs if spec["figure_id"] not in all_plan_ids]
    if missing_from_plan:
        raise ValueError(f"visualization_plan.json is missing figure ids {missing_from_plan}")

    manuscript_items = manuscript_figure_items()
    for spec in specs:
        _validate_figure_outputs(spec, review_html, visualization_plan, manuscript_items)

    if include_table:
        _validate_table_outputs()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--figure",
        action="append",
        dest="figure_ids",
        help="Validate only the specified figure id. Repeatable.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Validate all figures and table outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_generated_artifacts(
            figure_ids=args.figure_ids,
            include_table=bool(args.all or not args.figure_ids),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Generated artifact check failed: {exc}")
        return 1

    validated_specs = resolve_specs(args.figure_ids)
    print("Generated artifact check passed.")
    print(
        f"Validated {len(required_files(validated_specs, include_table=bool(args.all or not args.figure_ids)))} required figure/table contract files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
