#!/usr/bin/env python3
"""Class-based Python renderer for pathway-enrichment dot plots."""

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
    resolve_data_input,
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
                "pathway": row["pathway"],
                "gene_ratio": float(row["gene_ratio"]),
                "neg_log10_fdr": float(row["neg_log10_fdr"]),
                "gene_count": int(row["gene_count"]),
                "direction": row["direction"],
                "highlight_order": int(row["highlight_order"]),
            }
            for row in reader
        ]


def build_source_data(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda item: item["gene_ratio"], reverse=True)
    export_csv(
        REPO_ROOT / source_data_mapping(spec)["a"],
        ordered,
        ["pathway", "gene_ratio", "neg_log10_fdr", "gene_count", "direction", "highlight_order"],
    )
    return ordered


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    rows = build_source_data(spec, _load_rows(resolve_data_input(spec, 0)))
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
    colors = {"up": theme["palette"]["categorical"][1], "down": theme["palette"]["categorical"][0]}
    y_positions = list(range(len(rows)))
    if rows:
        axis.scatter(
            [row["gene_ratio"] for row in rows],
            y_positions,
            s=[row["gene_count"] * 8 for row in rows],
            c=[colors[row["direction"]] for row in rows],
            alpha=0.85,
            edgecolors=theme["palette"]["neutral"][0],
            linewidths=0.5,
        )
    for idx, row in enumerate(rows):
        axis.text(
            row["gene_ratio"] + 0.01,
            idx,
            f"{row['neg_log10_fdr']:.1f}",
            va="center",
            ha="left",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][1],
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
    axis.set_yticks(y_positions)
    axis.set_yticklabels([row["pathway"] for row in rows])
    if rows:
        axis.invert_yaxis()
        x_min = min(float(row["gene_ratio"]) for row in rows)
        x_max = max(float(row["gene_ratio"]) for row in rows)
        axis.set_xlim(max(0.0, x_min - 0.03), x_max + 0.12)
        axis.set_ylim(len(rows) - 0.5, -0.9)
    else:
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_yticks([])
        axis.set_xticks([0.0, 0.5, 1.0])
        axis.text(
            0.5,
            0.5,
            "No enriched pathways\nfor current fgsea profile",
            transform=axis.transAxes,
            ha="center",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][1],
        )
    axis.set_title("Pathway enrichment dot plot", loc="left", pad=2)
    axis.set_xlabel("Gene ratio")
    axis.set_ylabel("")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, _ = project_resources(spec_path)
    rows = _load_rows(resolve_data_input(spec, 0))
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
            "dot_size_encodes_gene_count",
            "annotation_for_significance_strength",
            "direction_color_encoding",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "annotation_count": len(rows),
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
