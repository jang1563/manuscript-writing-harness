#!/usr/bin/env python3
"""Class-based Python renderer for embedding projection figures."""

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


def _load_coordinate_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "sample_id": row["sample_id"],
                "biological_state": row["biological_state"],
                "domain": row["domain"],
                "embedding_1": float(row["embedding_1"]),
                "embedding_2": float(row["embedding_2"]),
                "local_density": float(row["local_density"]),
                "highlight_label": row["highlight_label"],
            }
            for row in reader
        ]


def _load_summary_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "biological_state": row["biological_state"],
                "centroid_x": float(row["centroid_x"]),
                "centroid_y": float(row["centroid_y"]),
                "display_order": int(row["display_order"]),
                "sample_count": int(row["sample_count"]),
                "cross_domain_fraction": float(row["cross_domain_fraction"]),
                "label_cluster": row["label_cluster"],
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any],
    coordinate_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_coordinates = sorted(
        coordinate_rows,
        key=lambda item: (item["biological_state"], item["domain"], item["sample_id"]),
    )
    ordered_summary = sorted(summary_rows, key=lambda item: item["display_order"])
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_coordinates,
        [
            "sample_id",
            "biological_state",
            "domain",
            "embedding_1",
            "embedding_2",
            "local_density",
            "highlight_label",
        ],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_summary,
        [
            "biological_state",
            "centroid_x",
            "centroid_y",
            "display_order",
            "sample_count",
            "cross_domain_fraction",
            "label_cluster",
        ],
    )
    return ordered_coordinates, ordered_summary


def _state_colors(theme: dict[str, Any]) -> dict[str, str]:
    return {
        "Quiescent": theme["palette"]["categorical"][0],
        "Inflammatory": theme["palette"]["categorical"][1],
        "Proliferative": theme["palette"]["categorical"][2],
        "Fibrotic": theme["palette"]["categorical"][3],
    }


def _domain_markers() -> dict[str, str]:
    return {
        "Cohort A": "o",
        "Cohort B": "s",
        "Cohort C": "^",
    }


def _support_label(row: dict[str, Any]) -> str:
    return f"{row['cross_domain_fraction'] * 100:.0f}% / n={row['sample_count']}"


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    coordinate_rows = _load_coordinate_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    summary_rows = _load_summary_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, coordinate_rows, summary_rows)
    resolved_font = resolve_font_stack(font_policy)
    configure_matplotlib(theme, font_policy, resolved_font)

    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import PercentFormatter

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(
            mm_to_inches(float(spec["size"]["width_mm"])),
            mm_to_inches(float(spec["size"]["height_mm"])),
        ),
        gridspec_kw={"width_ratios": [1.25, 0.95]},
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)

    colors = _state_colors(theme)
    markers = _domain_markers()
    panel_a = axes[0]
    for domain, marker in markers.items():
        domain_rows = [row for row in panel_a_rows if row["domain"] == domain]
        panel_a.scatter(
            [row["embedding_1"] for row in domain_rows],
            [row["embedding_2"] for row in domain_rows],
            s=[30 + 36 * row["local_density"] for row in domain_rows],
            marker=marker,
            color=[colors[row["biological_state"]] for row in domain_rows],
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.45,
            alpha=0.88,
            label=domain,
        )

    for row in panel_b_rows:
        if row["label_cluster"] != "yes":
            continue
        panel_a.text(
            row["centroid_x"],
            row["centroid_y"] + 0.28,
            f"{row['biological_state']}\nn={row['sample_count']}",
            ha="center",
            va="bottom",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            bbox={
                "boxstyle": "round,pad=0.22",
                "facecolor": theme["export_defaults"]["background"],
                "edgecolor": theme["palette"]["neutral"][2],
                "linewidth": 0.5,
                "alpha": 0.86,
            },
        )

    panel_a.axhline(0.0, color=theme["palette"]["neutral"][2], linewidth=0.6)
    panel_a.axvline(0.0, color=theme["palette"]["neutral"][2], linewidth=0.6)
    panel_a.set_title("Embedding projection", loc="left", pad=3)
    panel_a.set_xlabel("UMAP 1")
    panel_a.set_ylabel("UMAP 2")
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)
    panel_a.grid(color=theme["palette"]["neutral"][2], linewidth=0.45, alpha=0.45)
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=marker,
            color="none",
            markerfacecolor=theme["palette"]["neutral"][2],
            markeredgecolor=theme["palette"]["neutral"][0],
            markersize=5,
            label=domain,
        )
        for domain, marker in markers.items()
    ]
    panel_a.legend(
        handles=legend_handles,
        frameon=False,
        loc="lower left",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        title="Domain",
        title_fontsize=theme["typography"]["annotation_font_size_pt"],
    )

    panel_b = axes[1]
    ordered_summary = list(reversed(panel_b_rows))
    y_positions = list(range(len(ordered_summary)))
    support_values = [row["cross_domain_fraction"] for row in ordered_summary]
    panel_b.barh(
        y_positions,
        support_values,
        color=[colors[row["biological_state"]] for row in ordered_summary],
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.45,
        alpha=0.9,
    )
    panel_b.axvline(0.5, color=theme["palette"]["neutral"][1], linewidth=0.8, linestyle="--")
    panel_b.set_yticks(y_positions)
    panel_b.set_yticklabels([row["biological_state"] for row in ordered_summary])
    panel_b.set_xlabel("Cross-domain support")
    panel_b.set_title("Cross-domain support", loc="left", pad=3)
    panel_b.set_xlim(0.0, 0.82)
    panel_b.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.spines["left"].set_visible(False)
    panel_b.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    for y_pos, row in zip(y_positions, ordered_summary):
        panel_b.text(
            row["cross_domain_fraction"] + 0.015,
            y_pos,
            _support_label(row),
            ha="left",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )
    panel_b.text(
        0.5,
        -0.62,
        "50% mixed-domain reference",
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

    coordinate_rows = _load_coordinate_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    summary_rows = _load_summary_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    write_manifest(
        spec,
        profile,
        resolved_font,
        "python",
        spec_path,
        outputs,
        [
            "density_aware_cluster_labels",
            "domain_shape_encoding",
            "state_color_encoding_not_geometry_only",
            "cross_domain_support_panel",
            "vector_first_export",
        ],
        {
            "panel_count": 2,
            "highlight_label_count": sum(1 for row in summary_rows if row["label_cluster"] == "yes"),
            "annotation_count": sum(1 for row in summary_rows if row["label_cluster"] == "yes")
            + len(summary_rows)
            + 1,
            "reference_line_count": 3,
            "domain_count": len({row["domain"] for row in coordinate_rows}),
        },
    )

    import matplotlib.pyplot as plt

    plt.close(fig)
    return outputs


if __name__ == "__main__":
    build_figure(Path("figures/specs/figure_12_embedding_projection.yml"))
