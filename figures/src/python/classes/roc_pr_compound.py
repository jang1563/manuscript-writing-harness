#!/usr/bin/env python3
"""Class-based Python renderer for ROC and precision-recall compound figures."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from matplotlib.figure import Figure

from figures.src.python.common import (
    REPO_ROOT,
    add_panel_labels,
    apply_publication_layout,
    configure_matplotlib,
    export_csv,
    mm_to_inches,
    project_resources,
    resolve_font_stack,
    source_data_mapping,
    validate_common_contract,
    write_manifest,
)


def _load_curve_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "model": row["model"],
                "panel": row["panel"],
                "x": float(row["x"]),
                "y": float(row["y"]),
                "y_lower": float(row["y_lower"]),
                "y_upper": float(row["y_upper"]),
                "operating_point": row["operating_point"],
            }
            for row in reader
        ]


def _load_metric_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "auroc": float(row["auroc"]),
                "auprc": float(row["auprc"]),
                "ece": float(row["ece"]),
                "brier_score": float(row["brier_score"]),
                "prevalence": float(row["prevalence"]),
            }
            for row in reader
        ]
    return sorted(rows, key=lambda item: int(item["display_order"]))


def _source_rows(
    curves: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metric_map = {row["model"]: row for row in metrics}
    roc_rows: list[dict[str, Any]] = []
    pr_rows: list[dict[str, Any]] = []
    for row in curves:
        metric = metric_map[row["model"]]
        base = {
            "model": row["model"],
            "operating_point": row["operating_point"],
            "display_order": metric["display_order"],
            "ece": metric["ece"],
            "brier_score": metric["brier_score"],
        }
        if row["panel"] == "roc":
            roc_rows.append(
                {
                    **base,
                    "false_positive_rate": row["x"],
                    "true_positive_rate": row["y"],
                    "true_positive_rate_lower": row["y_lower"],
                    "true_positive_rate_upper": row["y_upper"],
                    "auroc": metric["auroc"],
                }
            )
        elif row["panel"] == "pr":
            pr_rows.append(
                {
                    **base,
                    "recall": row["x"],
                    "precision": row["y"],
                    "precision_lower": row["y_lower"],
                    "precision_upper": row["y_upper"],
                    "auprc": metric["auprc"],
                    "prevalence": metric["prevalence"],
                }
            )
    return roc_rows, pr_rows


def build_source_data(
    spec: dict[str, Any], curves: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    roc_rows, pr_rows = _source_rows(curves, metrics)
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        roc_rows,
        [
            "model",
            "display_order",
            "false_positive_rate",
            "true_positive_rate",
            "true_positive_rate_lower",
            "true_positive_rate_upper",
            "operating_point",
            "auroc",
            "ece",
            "brier_score",
        ],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        pr_rows,
        [
            "model",
            "display_order",
            "recall",
            "precision",
            "precision_lower",
            "precision_upper",
            "operating_point",
            "auprc",
            "prevalence",
            "ece",
            "brier_score",
        ],
    )
    return roc_rows, pr_rows


def _style_maps(theme: dict[str, Any], metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    line_styles = ["solid", "--", "-."]
    markers = ["o", "s", "D"]
    colors = [
        theme["palette"]["categorical"][0],
        theme["palette"]["categorical"][1],
        theme["palette"]["categorical"][2],
    ]
    style_map: dict[str, dict[str, Any]] = {}
    for index, metric in enumerate(metrics):
        style_map[str(metric["model"])] = {
            "color": colors[index % len(colors)],
            "linestyle": line_styles[index % len(line_styles)],
            "marker": markers[index % len(markers)],
        }
    return style_map


def _label_offsets() -> dict[str, dict[str, tuple[float, float]]]:
    return {
        "roc": {
            "Foundation model": (0.03, 0.055),
            "Hybrid GNN": (0.03, -0.03),
            "CNN baseline": (0.03, -0.055),
        },
        "pr": {
            "Foundation model": (0.035, 0.045),
            "Hybrid GNN": (0.035, -0.015),
            "CNN baseline": (0.035, -0.05),
        },
    }


def _summary_text(metrics: list[dict[str, Any]], metric_key: str, title: str) -> str:
    lines = [title]
    for row in metrics:
        lines.append(f"{row['model']}: {row[metric_key]:.3f}")
    return "\n".join(lines)


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    curves = _load_curve_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metrics = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    roc_rows, pr_rows = build_source_data(spec, curves, metrics)
    resolved_font = resolve_font_stack(font_policy)
    configure_matplotlib(theme, font_policy, resolved_font)

    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(
            mm_to_inches(float(spec["size"]["width_mm"])),
            mm_to_inches(float(spec["size"]["height_mm"])),
        ),
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)
    style_map = _style_maps(theme, metrics)
    offsets = _label_offsets()

    panel_a = axes[0]
    for metric in metrics:
        model = str(metric["model"])
        model_rows = sorted(
            [row for row in roc_rows if str(row["model"]) == model],
            key=lambda item: float(item["false_positive_rate"]),
        )
        x_values = [float(row["false_positive_rate"]) for row in model_rows]
        y_values = [float(row["true_positive_rate"]) for row in model_rows]
        lower = [float(row["true_positive_rate_lower"]) for row in model_rows]
        upper = [float(row["true_positive_rate_upper"]) for row in model_rows]
        panel_a.fill_between(
            x_values,
            lower,
            upper,
            color=style_map[model]["color"],
            alpha=0.12,
            linewidth=0.0,
        )
        panel_a.plot(
            x_values,
            y_values,
            color=style_map[model]["color"],
            linestyle=style_map[model]["linestyle"],
            linewidth=1.8,
        )
        op_row = next(row for row in model_rows if str(row["operating_point"]) == "yes")
        panel_a.scatter(
            float(op_row["false_positive_rate"]),
            float(op_row["true_positive_rate"]),
            s=28,
            color=style_map[model]["color"],
            marker=style_map[model]["marker"],
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.5,
            zorder=4,
        )
        dx, dy = offsets["roc"][model]
        panel_a.text(
            float(op_row["false_positive_rate"]) + dx,
            float(op_row["true_positive_rate"]) + dy,
            model,
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left",
            va="center",
        )
    panel_a.plot(
        [0.0, 1.0],
        [0.0, 1.0],
        color=theme["palette"]["neutral"][1],
        linestyle=":",
        linewidth=1.0,
    )
    panel_a.set_title("ROC discrimination", loc="left", pad=2)
    panel_a.set_xlabel("False positive rate")
    panel_a.set_ylabel("True positive rate")
    panel_a.set_xlim(0.0, 1.0)
    panel_a.set_ylim(0.0, 1.02)
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)
    panel_a.text(
        0.98,
        0.05,
        _summary_text(metrics, "auroc", "AUROC summary"),
        transform=panel_a.transAxes,
        ha="right",
        va="bottom",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][0],
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": theme["palette"]["neutral"][2],
            "linewidth": 0.6,
        },
    )

    panel_b = axes[1]
    prevalence = float(metrics[0]["prevalence"])
    for metric in metrics:
        model = str(metric["model"])
        model_rows = sorted(
            [row for row in pr_rows if str(row["model"]) == model],
            key=lambda item: float(item["recall"]),
        )
        x_values = [float(row["recall"]) for row in model_rows]
        y_values = [float(row["precision"]) for row in model_rows]
        lower = [float(row["precision_lower"]) for row in model_rows]
        upper = [float(row["precision_upper"]) for row in model_rows]
        panel_b.fill_between(
            x_values,
            lower,
            upper,
            color=style_map[model]["color"],
            alpha=0.12,
            linewidth=0.0,
        )
        panel_b.plot(
            x_values,
            y_values,
            color=style_map[model]["color"],
            linestyle=style_map[model]["linestyle"],
            linewidth=1.8,
        )
        op_row = next(row for row in model_rows if str(row["operating_point"]) == "yes")
        panel_b.scatter(
            float(op_row["recall"]),
            float(op_row["precision"]),
            s=28,
            color=style_map[model]["color"],
            marker=style_map[model]["marker"],
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.5,
            zorder=4,
        )
        dx, dy = offsets["pr"][model]
        panel_b.text(
            float(op_row["recall"]) + dx,
            float(op_row["precision"]) + dy,
            model,
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left",
            va="center",
        )
    panel_b.axhline(
        prevalence,
        color=theme["palette"]["neutral"][1],
        linestyle=":",
        linewidth=1.0,
    )
    panel_b.text(
        0.02,
        prevalence + 0.025,
        "Prevalence baseline",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
        ha="left",
        va="bottom",
    )
    panel_b.set_title("Precision-recall under imbalance", loc="left", pad=2)
    panel_b.set_xlabel("Recall")
    panel_b.set_ylabel("Precision")
    panel_b.set_xlim(0.0, 1.0)
    panel_b.set_ylim(0.0, 1.02)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.text(
        0.98,
        0.05,
        _summary_text(metrics, "auprc", "AUPRC summary"),
        transform=panel_b.transAxes,
        ha="right",
        va="bottom",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][0],
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": theme["palette"]["neutral"][2],
            "linewidth": 0.6,
        },
    )

    add_panel_labels(spec, theme, [panel_a, panel_b])
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, _, font_policy, profile, _ = project_resources(spec_path)
    curves = _load_curve_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metrics = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    build_source_data(spec, curves, metrics)
    resolved_font = resolve_font_stack(font_policy)
    fig = create_figure(spec_path)
    output_dir = REPO_ROOT / str(spec["renderers"]["python"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = str(spec["figure_id"])
    svg_path = output_dir / f"{stem}.svg"
    pdf_path = output_dir / f"{stem}.pdf"
    png_path = output_dir / f"{stem}.png"
    fig.savefig(svg_path, format="svg")
    fig.savefig(pdf_path, format="pdf")
    fig.savefig(png_path, format="png", dpi=int(profile["preview_dpi"]))
    outputs = {
        "svg": str(svg_path.relative_to(REPO_ROOT)),
        "pdf": str(pdf_path.relative_to(REPO_ROOT)),
        "png": str(png_path.relative_to(REPO_ROOT)),
    }
    write_manifest(
        spec,
        profile,
        resolved_font,
        "python",
        spec_path,
        outputs,
        [
            "paired_roc_and_pr_panels",
            "uncertainty_ribbons_for_curve_stability",
            "operating_point_markers_and_direct_labels",
            "prevalence_baseline_in_pr_panel",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "reference_line_count": 2,
            "annotation_count": 8,
            "operating_point_count": 6,
            "uncertainty_band_count": 6,
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
