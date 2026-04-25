#!/usr/bin/env python3
"""Class-based Python renderer for uncertainty-abstention curves."""

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


TARGET_RISK = 0.08
TARGET_COVERAGE = 0.80


def _load_curve_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "coverage": float(row["coverage"]),
                "risk": float(row["risk"]),
                "risk_lower": float(row["risk_lower"]),
                "risk_upper": float(row["risk_upper"]),
                "operating_point": row["operating_point"],
            }
            for row in reader
        ]


def _load_summary_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "risk_at_full_coverage": float(row["risk_at_full_coverage"]),
                "risk_at_80_coverage": float(row["risk_at_80_coverage"]),
                "coverage_at_target_risk": float(row["coverage_at_target_risk"]),
                "abstained_fraction_at_target": float(row["abstained_fraction_at_target"]),
                "label_model": row["label_model"],
            }
            for row in reader
        ]
    return sorted(rows, key=lambda item: item["display_order"])


def build_source_data(
    spec: dict[str, Any],
    curve_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_curves = sorted(curve_rows, key=lambda item: (item["display_order"], item["coverage"]))
    ordered_summary = sorted(summary_rows, key=lambda item: item["display_order"])
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_curves,
        [
            "model",
            "display_order",
            "coverage",
            "risk",
            "risk_lower",
            "risk_upper",
            "operating_point",
        ],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_summary,
        [
            "model",
            "display_order",
            "risk_at_full_coverage",
            "risk_at_80_coverage",
            "coverage_at_target_risk",
            "abstained_fraction_at_target",
            "label_model",
        ],
    )
    return ordered_curves, ordered_summary


def _style_maps(theme: dict[str, Any], summary_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    colors = [
        theme["palette"]["categorical"][0],
        theme["palette"]["categorical"][1],
        theme["palette"]["categorical"][2],
    ]
    line_styles = ["solid", "--", "-."]
    markers = ["o", "s", "D"]
    style_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(summary_rows):
        style_map[str(row["model"])] = {
            "color": colors[index % len(colors)],
            "linestyle": line_styles[index % len(line_styles)],
            "marker": markers[index % len(markers)],
        }
    return style_map


def _label_offsets() -> dict[str, tuple[float, float]]:
    return {
        "Foundation model": (0.018, -0.010),
        "Hybrid GNN": (0.018, 0.006),
        "CNN baseline": (0.018, 0.012),
    }


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    curve_rows = _load_curve_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    summary_rows = _load_summary_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, curve_rows, summary_rows)
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
        gridspec_kw={"width_ratios": [1.15, 0.95]},
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)
    style_map = _style_maps(theme, panel_b_rows)
    offsets = _label_offsets()

    panel_a = axes[0]
    for summary in panel_b_rows:
        model = str(summary["model"])
        model_rows = sorted(
            [row for row in panel_a_rows if str(row["model"]) == model],
            key=lambda item: float(item["coverage"]),
        )
        x_values = [float(row["coverage"]) for row in model_rows]
        y_values = [float(row["risk"]) for row in model_rows]
        lower = [float(row["risk_lower"]) for row in model_rows]
        upper = [float(row["risk_upper"]) for row in model_rows]
        panel_a.fill_between(
            x_values,
            lower,
            upper,
            color=style_map[model]["color"],
            alpha=0.13,
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
            float(op_row["coverage"]),
            float(op_row["risk"]),
            s=30,
            color=style_map[model]["color"],
            marker=style_map[model]["marker"],
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.5,
            zorder=4,
        )
        dx, dy = offsets[model]
        panel_a.text(
            float(op_row["coverage"]) + dx,
            float(op_row["risk"]) + dy,
            model,
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left",
            va="center",
        )

    panel_a.axhline(
        TARGET_RISK,
        color=theme["palette"]["neutral"][1],
        linestyle=":",
        linewidth=1.0,
    )
    panel_a.axvline(
        TARGET_COVERAGE,
        color=theme["palette"]["neutral"][2],
        linestyle="--",
        linewidth=0.8,
    )
    panel_a.text(
        0.50,
        TARGET_RISK + 0.006,
        "8% target risk",
        ha="left",
        va="bottom",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )
    panel_a.text(
        TARGET_COVERAGE + 0.012,
        0.185,
        "80% coverage\noperating points",
        ha="left",
        va="top",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )
    panel_a.set_title("Coverage-risk curve", loc="left", pad=3)
    panel_a.set_xlabel("Coverage retained")
    panel_a.set_ylabel("Observed risk")
    panel_a.set_xlim(0.48, 1.02)
    panel_a.set_ylim(0.0, 0.21)
    panel_a.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_a.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)
    panel_a.grid(color=theme["palette"]["neutral"][2], linewidth=0.45, alpha=0.45)

    panel_b = axes[1]
    ordered_summary = list(reversed(panel_b_rows))
    y_positions = list(range(len(ordered_summary)))
    coverage_values = [float(row["coverage_at_target_risk"]) for row in ordered_summary]
    panel_b.barh(
        y_positions,
        coverage_values,
        color=[style_map[str(row["model"])]["color"] for row in ordered_summary],
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.45,
        alpha=0.9,
    )
    panel_b.axvline(
        TARGET_COVERAGE,
        color=theme["palette"]["neutral"][1],
        linestyle="--",
        linewidth=0.8,
    )
    panel_b.set_yticks(y_positions)
    panel_b.set_yticklabels([str(row["model"]) for row in ordered_summary])
    panel_b.set_xlabel("Coverage at risk <= 8%")
    panel_b.set_title("Target-risk coverage", loc="left", pad=3)
    panel_b.set_xlim(0.0, 1.0)
    panel_b.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.spines["left"].set_visible(False)
    panel_b.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    for y_pos, row in zip(y_positions, ordered_summary):
        panel_b.text(
            float(row["coverage_at_target_risk"]) + 0.015,
            y_pos,
            f"{row['coverage_at_target_risk'] * 100:.0f}% retained\nrisk@80% {row['risk_at_80_coverage'] * 100:.1f}%",
            ha="left",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )
    panel_b.text(
        TARGET_COVERAGE,
        -0.58,
        "80% target coverage",
        ha="center",
        va="top",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )

    add_panel_labels(spec, theme, [panel_a, panel_b])
    fig.text(
        0.01,
        0.965,
        spec["title"],
        ha="left",
        va="top",
        fontsize=theme["typography"]["title_font_size_pt"],
        fontweight="bold",
        color=theme["palette"]["neutral"][0],
    )
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    resolved_font = resolve_font_stack(font_policy)
    configure_matplotlib(theme, font_policy, resolved_font)
    fig = create_figure(spec_path)

    output_dir = REPO_ROOT / str(spec["renderers"]["python"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = spec["figure_id"]
    outputs = {
        "svg": str((output_dir / f"{stem}.svg").relative_to(REPO_ROOT)),
        "pdf": str((output_dir / f"{stem}.pdf").relative_to(REPO_ROOT)),
        "png": str((output_dir / f"{stem}.png").relative_to(REPO_ROOT)),
    }
    fig.savefig(REPO_ROOT / outputs["svg"], format="svg", transparent=False)
    fig.savefig(REPO_ROOT / outputs["pdf"], format="pdf", transparent=False)
    fig.savefig(
        REPO_ROOT / outputs["png"],
        format="png",
        dpi=int(profile["preview_dpi"]),
        transparent=False,
    )

    curve_rows = _load_curve_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    summary_rows = _load_summary_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    write_manifest(
        spec,
        profile,
        resolved_font,
        "python",
        spec_path,
        outputs,
        [
            "coverage_risk_curve_panel",
            "uncertainty_band_for_risk",
            "operating_point_markers_and_direct_labels",
            "target_risk_reference",
            "selective_prediction_summary_panel",
            "vector_first_export",
        ],
        {
            "panel_count": 2,
            "reference_line_count": 3,
            "annotation_count": 2 + len(summary_rows) + sum(1 for row in curve_rows if row["operating_point"] == "yes"),
            "operating_point_count": sum(1 for row in curve_rows if row["operating_point"] == "yes"),
            "uncertainty_band_count": len(summary_rows),
        },
    )

    import matplotlib.pyplot as plt

    plt.close(fig)
    return outputs


if __name__ == "__main__":
    build_figure(Path("figures/specs/figure_13_uncertainty_abstention_curve.yml"))
