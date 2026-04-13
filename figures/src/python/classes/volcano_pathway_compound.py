#!/usr/bin/env python3
"""Class-based Python renderer for volcano plus pathway compound figures."""

from __future__ import annotations

import csv
import math
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


def _read_gene_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, Any]] = []
        for row in reader:
            padj = float(row["padj"])
            rows.append(
                {
                    "gene": row["gene"],
                    "log2_fc": float(row["log2_fc"]),
                    "padj": padj,
                    "neg_log10_padj": -math.log10(max(padj, 1e-300)),
                    "highlight_label": row["highlight_label"],
                }
            )
        return rows


def _read_pathway_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "pathway": row["pathway"],
                "nes": float(row["nes"]),
                "fdr": float(row["fdr"]),
                "direction": row["direction"],
                "highlight_order": int(row["highlight_order"]),
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any],
    gene_rows: list[dict[str, Any]],
    pathway_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    classified: list[dict[str, Any]] = []
    for row in gene_rows:
        if float(row["log2_fc"]) >= 1.0 and float(row["padj"]) <= 0.05:
            category = "up_significant"
        elif float(row["log2_fc"]) <= -1.0 and float(row["padj"]) <= 0.05:
            category = "down_significant"
        else:
            category = "background"
        classified.append({**row, "significance_category": category})

    ordered_pathways = [
        {**row, "fdr_label": f"FDR {row['fdr']:.1e}"}
        for row in sorted(pathway_rows, key=lambda item: item["nes"], reverse=True)
    ]
    source_outputs = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / source_outputs["a"],
        classified,
        [
            "gene",
            "log2_fc",
            "padj",
            "neg_log10_padj",
            "highlight_label",
            "significance_category",
        ],
    )
    export_csv(
        REPO_ROOT / source_outputs["b"],
        ordered_pathways,
        [
            "pathway",
            "nes",
            "fdr",
            "direction",
            "highlight_order",
            "fdr_label",
        ],
    )
    return classified, ordered_pathways


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    gene_rows = _read_gene_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    pathway_rows = _read_pathway_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, gene_rows, pathway_rows)
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

    colors = {
        "background": theme["palette"]["neutral"][2],
        "up_significant": theme["palette"]["categorical"][1],
        "down_significant": theme["palette"]["categorical"][0],
        "up": theme["palette"]["categorical"][1],
        "down": theme["palette"]["categorical"][0],
    }

    panel_a = axes[0]
    for category in ("background", "down_significant", "up_significant"):
        subset = [row for row in panel_a_rows if row["significance_category"] == category]
        if subset:
            panel_a.scatter(
                [float(row["log2_fc"]) for row in subset],
                [float(row["neg_log10_padj"]) for row in subset],
                s=18 if category == "background" else 28,
                color=colors[category],
                alpha=0.55 if category == "background" else 0.92,
                edgecolor="none",
            )
    threshold_y = -math.log10(0.05)
    panel_a.axvline(-1.0, color=theme["palette"]["neutral"][1], linestyle="--", linewidth=0.9)
    panel_a.axvline(1.0, color=theme["palette"]["neutral"][1], linestyle="--", linewidth=0.9)
    panel_a.axhline(threshold_y, color=theme["palette"]["neutral"][1], linestyle="--", linewidth=0.9)
    label_offsets = {
        "CXCL10": (0.18, 0.36),
        "IFIT1": (0.16, 0.12),
        "MX1": (0.16, -0.12),
        "MKI67": (-0.18, 0.34),
        "TOP2A": (-0.18, 0.10),
        "CDK1": (-0.18, -0.14),
    }
    for row in [row for row in panel_a_rows if row["highlight_label"] == "yes"]:
        dx, dy = label_offsets.get(str(row["gene"]), (0.14, 0.14))
        x = float(row["log2_fc"])
        y = float(row["neg_log10_padj"])
        panel_a.annotate(
            str(row["gene"]),
            xy=(x, y),
            xytext=(x + dx, y + dy),
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left" if dx >= 0 else "right",
            va="center",
            arrowprops={
                "arrowstyle": "-",
                "color": theme["palette"]["neutral"][1],
                "linewidth": 0.7,
            },
        )
    max_abs_fc = max(abs(float(row["log2_fc"])) for row in panel_a_rows)
    max_y = max(float(row["neg_log10_padj"]) for row in panel_a_rows)
    panel_a.set_xlim(-(max_abs_fc + 0.8), max_abs_fc + 0.8)
    panel_a.set_ylim(0, max_y + 1.45)
    panel_a.set_title("Differential expression volcano", loc="left", pad=2)
    panel_a.set_xlabel("log2 fold change")
    panel_a.set_ylabel("-log10 adjusted P")
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)

    panel_b = axes[1]
    y_positions = list(range(len(panel_b_rows)))
    panel_b.barh(
        y_positions,
        [float(row["nes"]) for row in panel_b_rows],
        color=[colors[str(row["direction"])] for row in panel_b_rows],
        alpha=0.9,
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=theme["strokes"]["errorbar_line_width_pt"],
    )
    panel_b.axvline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.9)
    panel_b.set_yticks(y_positions)
    panel_b.set_yticklabels([str(row["pathway"]) for row in panel_b_rows])
    panel_b.invert_yaxis()
    x_extent = max(abs(float(row["nes"])) for row in panel_b_rows) + 0.65
    panel_b.set_xlim(-x_extent, x_extent)
    for index, row in enumerate(panel_b_rows):
        nes = float(row["nes"])
        panel_b.text(
            nes + (0.12 if nes >= 0 else -0.12),
            index,
            str(row["fdr_label"]),
            ha="left" if nes >= 0 else "right",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][1],
        )
    panel_b.set_title("Pathway enrichment summary", loc="left", pad=2)
    panel_b.set_xlabel("Normalized enrichment score")
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)

    add_panel_labels(spec, theme, [panel_a, panel_b])
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, _ = project_resources(spec_path)
    gene_rows = _read_gene_rows(REPO_ROOT / str(spec["data_inputs"][0]))
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
            "threshold_guides_for_significance",
            "selective_gene_labels_for_extreme_points",
            "de_emphasized_nonsignificant_points",
            "signed_enrichment_panel",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "highlight_label_count": sum(
                1 for row in gene_rows if str(row["highlight_label"]) == "yes"
            ),
            "threshold_line_count": 3,
            "reference_line_count": 1,
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
