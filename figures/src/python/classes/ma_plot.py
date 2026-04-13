#!/usr/bin/env python3
"""Class-based Python renderer for MA plots."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from matplotlib.figure import Figure

from figures.src.python.common import (
    REPO_ROOT,
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


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "gene": row["gene"],
                "mean_expression": float(row["mean_expression"]),
                "log2_fc": float(row["log2_fc"]),
                "padj": float(row["padj"]),
                "highlight_label": row["highlight_label"],
            }
            for row in reader
        ]


def build_source_data(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    classified = []
    for row in rows:
        if abs(float(row["log2_fc"])) >= 1.0 and float(row["padj"]) <= 0.05:
            category = "highlighted"
        else:
            category = "background"
        classified.append({**row, "point_category": category})
    export_csv(
        REPO_ROOT / source_data_mapping(spec)["a"],
        classified,
        ["gene", "mean_expression", "log2_fc", "padj", "highlight_label", "point_category"],
    )
    return classified


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    rows = build_source_data(spec, _load_rows(REPO_ROOT / str(spec["data_inputs"][0])))
    resolved_font = resolve_font_stack(font_policy)
    configure_matplotlib(theme, font_policy, resolved_font)

    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(
        1,
        1,
        figsize=(
            mm_to_inches(float(spec["size"]["width_mm"])),
            mm_to_inches(float(spec["size"]["height_mm"])),
        ),
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)
    background = [row for row in rows if row["point_category"] == "background"]
    highlight = [row for row in rows if row["point_category"] == "highlighted"]
    axis.scatter(
        [row["mean_expression"] for row in background],
        [row["log2_fc"] for row in background],
        s=18,
        color=theme["palette"]["neutral"][2],
        alpha=0.5,
        edgecolor="none",
    )
    axis.scatter(
        [row["mean_expression"] for row in highlight],
        [row["log2_fc"] for row in highlight],
        s=28,
        color=theme["palette"]["categorical"][1],
        alpha=0.9,
        edgecolor="none",
    )
    axis.axhline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.9)
    axis.axhline(1.0, color=theme["palette"]["neutral"][1], linestyle="--", linewidth=0.9)
    axis.axhline(-1.0, color=theme["palette"]["neutral"][1], linestyle="--", linewidth=0.9)
    x_values = [row["mean_expression"] for row in rows]
    x_min = min(x_values)
    x_max = max(x_values)
    x_pad = max(0.35, (x_max - x_min) * 0.08)
    for row in [row for row in rows if row["highlight_label"] == "yes"]:
        place_right = float(row["mean_expression"]) <= (x_max - x_pad * 0.75)
        dx = x_pad * 0.55 if place_right else -x_pad * 0.3
        ha = "left" if place_right else "right"
        axis.annotate(
            str(row["gene"]),
            xy=(row["mean_expression"], row["log2_fc"]),
            xytext=(row["mean_expression"] + dx, row["log2_fc"] + 0.12),
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha=ha,
            arrowprops={"arrowstyle": "-", "color": theme["palette"]["neutral"][1], "linewidth": 0.7},
        )
    axis.text(
        float(theme["panel_labels"]["x_position_axes"]),
        float(theme["panel_labels"]["y_position_axes"]),
        "a",
        transform=axis.transAxes,
        fontsize=theme["panel_labels"]["font_size_pt"],
        fontweight=theme["panel_labels"]["font_weight"],
        va="top",
    )
    axis.set_xlim(x_min - x_pad * 0.3, x_max + x_pad)
    axis.set_title("MA plot", loc="left", pad=2)
    axis.set_xlabel("Mean expression")
    axis.set_ylabel("log2 fold change")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, _ = project_resources(spec_path)
    rows = _load_rows(REPO_ROOT / str(spec["data_inputs"][0]))
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
            "threshold_guides_for_mean_difference",
            "selective_gene_labels_for_extreme_points",
            "de_emphasized_background_points",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "highlight_label_count": sum(
                1 for row in rows if str(row["highlight_label"]) == "yes"
            ),
            "threshold_line_count": 2,
            "reference_line_count": 1,
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
