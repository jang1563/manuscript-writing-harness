#!/usr/bin/env python3
"""Class-based Python renderer for sample-level PCA plots."""

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
                "sample_id": row["sample_id"],
                "condition": row["condition"],
                "batch": row["batch"],
                "pc1": float(row["pc1"]),
                "pc2": float(row["pc2"]),
                "highlight_label": row["highlight_label"],
            }
            for row in reader
        ]


def build_source_data(spec: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    export_csv(
        REPO_ROOT / source_data_mapping(spec)["a"],
        rows,
        ["sample_id", "condition", "batch", "pc1", "pc2", "highlight_label"],
    )
    return rows


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
    colors = {
        "Control": theme["palette"]["categorical"][0],
        "Treatment": theme["palette"]["categorical"][1],
    }
    markers = {"Batch1": "o", "Batch2": "s"}
    for row in rows:
        axis.scatter(
            row["pc1"],
            row["pc2"],
            s=42,
            color=colors[row["condition"]],
            marker=markers[row["batch"]],
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.6,
        )
        if row["highlight_label"] == "yes":
            axis.text(
                row["pc1"] + 0.12,
                row["pc2"] + 0.12,
                row["sample_id"],
                fontsize=theme["typography"]["annotation_font_size_pt"],
                color=theme["palette"]["neutral"][0],
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
    axis.axhline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.8)
    axis.axvline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.8)
    axis.set_title("Sample PCA", loc="left", pad=2)
    axis.set_xlabel("PC1 (48%)")
    axis.set_ylabel("PC2 (23%)")
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
            "group_coloring_for_sample_separation",
            "batch_shape_encoding",
            "selective_sample_labels",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "highlight_label_count": sum(
                1 for row in rows if str(row["highlight_label"]) == "yes"
            ),
            "reference_line_count": 2,
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
