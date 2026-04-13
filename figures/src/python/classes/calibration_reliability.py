#!/usr/bin/env python3
"""Class-based Python renderer for calibration reliability figures."""

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


def _load_bin_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "bin_center": float(row["bin_center"]),
                "mean_predicted": float(row["mean_predicted"]),
                "observed_rate": float(row["observed_rate"]),
                "observed_lower": float(row["observed_lower"]),
                "observed_upper": float(row["observed_upper"]),
                "sample_fraction": float(row["sample_fraction"]),
                "sample_count": int(row["sample_count"]),
                "label_bin": row["label_bin"],
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
                "ece": float(row["ece"]),
                "max_calibration_gap": float(row["max_calibration_gap"]),
                "brier_score": float(row["brier_score"]),
            }
            for row in reader
        ]
    return sorted(rows, key=lambda item: int(item["display_order"]))


def build_source_data(
    spec: dict[str, Any], bins: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metric_map = {row["model"]: row for row in metrics}
    reliability_rows: list[dict[str, Any]] = []
    support_rows: list[dict[str, Any]] = []
    for row in sorted(bins, key=lambda item: (item["display_order"], item["mean_predicted"])):
        metric = metric_map[row["model"]]
        reliability_rows.append(
            {
                "model": row["model"],
                "display_order": row["display_order"],
                "mean_predicted": row["mean_predicted"],
                "observed_rate": row["observed_rate"],
                "observed_lower": row["observed_lower"],
                "observed_upper": row["observed_upper"],
                "sample_count": row["sample_count"],
                "sample_fraction": row["sample_fraction"],
                "label_bin": row["label_bin"],
                "ece": metric["ece"],
                "max_calibration_gap": metric["max_calibration_gap"],
                "brier_score": metric["brier_score"],
            }
        )
        support_rows.append(
            {
                "model": row["model"],
                "display_order": row["display_order"],
                "bin_center": row["bin_center"],
                "sample_fraction": row["sample_fraction"],
                "sample_count": row["sample_count"],
                "label_bin": row["label_bin"],
                "ece": metric["ece"],
                "max_calibration_gap": metric["max_calibration_gap"],
                "brier_score": metric["brier_score"],
            }
        )
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        reliability_rows,
        [
            "model",
            "display_order",
            "mean_predicted",
            "observed_rate",
            "observed_lower",
            "observed_upper",
            "sample_count",
            "sample_fraction",
            "label_bin",
            "ece",
            "max_calibration_gap",
            "brier_score",
        ],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        support_rows,
        [
            "model",
            "display_order",
            "bin_center",
            "sample_fraction",
            "sample_count",
            "label_bin",
            "ece",
            "max_calibration_gap",
            "brier_score",
        ],
    )
    return reliability_rows, support_rows


def _style_map(theme: dict[str, Any], metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    colors = [
        theme["palette"]["categorical"][0],
        theme["palette"]["categorical"][1],
        theme["palette"]["categorical"][2],
    ]
    linestyles = ["solid", "--", "-."]
    markers = ["o", "s", "D"]
    hatches = ["", "//", ".."]
    styles: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(metrics):
        styles[str(row["model"])] = {
            "color": colors[index % len(colors)],
            "linestyle": linestyles[index % len(linestyles)],
            "marker": markers[index % len(markers)],
            "hatch": hatches[index % len(hatches)],
        }
    return styles


def _label_offsets() -> dict[str, tuple[float, float]]:
    return {
        "Foundation model": (0.025, 0.0),
        "Hybrid GNN": (0.025, -0.03),
        "CNN baseline": (0.025, -0.065),
    }


def _summary_text(metrics: list[dict[str, Any]]) -> str:
    lines = ["ECE summary"]
    for row in metrics:
        lines.append(f"{row['model']}: {row['ece']:.3f}")
    return "\n".join(lines)


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    bins = _load_bin_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metrics = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    reliability_rows, support_rows = build_source_data(spec, bins, metrics)
    resolved_font = resolve_font_stack(font_policy)
    configure_matplotlib(theme, font_policy, resolved_font)

    import matplotlib.pyplot as plt
    from matplotlib.ticker import PercentFormatter

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
    styles = _style_map(theme, metrics)

    panel_a = axes[0]
    panel_a.plot(
        [0.0, 1.0],
        [0.0, 1.0],
        color=theme["palette"]["neutral"][1],
        linestyle=":",
        linewidth=1.0,
    )
    for metric in metrics:
        model = str(metric["model"])
        model_rows = [row for row in reliability_rows if str(row["model"]) == model]
        x_values = [float(row["mean_predicted"]) for row in model_rows]
        y_values = [float(row["observed_rate"]) for row in model_rows]
        lower = [float(row["observed_lower"]) for row in model_rows]
        upper = [float(row["observed_upper"]) for row in model_rows]
        panel_a.fill_between(
            x_values,
            lower,
            upper,
            color=styles[model]["color"],
            alpha=0.09,
            linewidth=0.0,
        )
        panel_a.plot(
            x_values,
            y_values,
            color=styles[model]["color"],
            linestyle=styles[model]["linestyle"],
            marker=styles[model]["marker"],
            markersize=4.8,
            linewidth=1.8,
        )
        yerr = [
            [max(0.0, y - lo) for y, lo in zip(y_values, lower)],
            [max(0.0, hi - y) for y, hi in zip(y_values, upper)],
        ]
        panel_a.errorbar(
            x_values,
            y_values,
            yerr=yerr,
            fmt="none",
            ecolor=styles[model]["color"],
            elinewidth=0.8,
            alpha=0.7,
            capsize=2.2,
        )
        label_row = next(row for row in model_rows if str(row["label_bin"]) == "yes")
        dx, dy = _label_offsets()[model]
        panel_a.text(
            float(label_row["mean_predicted"]) + dx,
            float(label_row["observed_rate"]) + dy,
            model,
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left",
            va="center",
        )
    panel_a.text(
        0.98,
        0.04,
        _summary_text(metrics),
        transform=panel_a.transAxes,
        ha="right",
        va="bottom",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][0],
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": theme["palette"]["neutral"][1],
            "linewidth": 0.6,
        },
    )
    panel_a.set_title("Reliability diagram", loc="left", pad=2)
    panel_a.set_xlabel("Mean predicted probability")
    panel_a.set_ylabel("Observed event rate")
    panel_a.set_xlim(0.0, 1.0)
    panel_a.set_ylim(0.0, 1.02)
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)

    panel_b = axes[1]
    centers = sorted({float(row["bin_center"]) for row in support_rows})
    width = 0.045
    offsets = {
        metric["model"]: (-width, 0.0, width)[index]
        for index, metric in enumerate(metrics)
    }
    for metric in metrics:
        model = str(metric["model"])
        rows = sorted(
            [row for row in support_rows if str(row["model"]) == model],
            key=lambda item: float(item["bin_center"]),
        )
        panel_b.bar(
            [float(row["bin_center"]) + offsets[model] for row in rows],
            [float(row["sample_fraction"]) for row in rows],
            width=width * 0.92,
            color=styles[model]["color"],
            alpha=0.72,
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.5,
            hatch=styles[model]["hatch"],
        )
    panel_b.set_title("Confidence support by bin", loc="left", pad=2)
    panel_b.set_xlabel("Predicted probability bin")
    panel_b.set_ylabel("Sample fraction")
    panel_b.set_xlim(min(centers) - 0.08, max(centers) + 0.12)
    panel_b.set_ylim(0.0, max(float(row["sample_fraction"]) for row in support_rows) + 0.06)
    panel_b.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)

    add_panel_labels(spec, theme, [panel_a, panel_b])
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, _ = project_resources(spec_path)
    bins = _load_bin_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metrics = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
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
            "reliability_diagram_with_identity_reference",
            "bin_level_uncertainty_intervals",
            "direct_labels_for_model_identity",
            "confidence_support_panel_for_coverage_context",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "direct_label_count": len(metrics),
            "annotation_count": len(metrics) + 1,
            "support_bin_count": len(bins),
            "reference_line_count": 1,
            "uncertainty_band_count": len(metrics),
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
