#!/usr/bin/env python3
"""Class-based Python renderer for normalized confusion-matrix figures."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean
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


def _load_matrix_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "true_label": row["true_label"],
                "predicted_label": row["predicted_label"],
                "true_order": int(row["true_order"]),
                "pred_order": int(row["pred_order"]),
                "rate": float(row["rate"]),
                "count": int(row["count"]),
                "label_cell": row["label_cell"],
                "is_diagonal": row["is_diagonal"],
            }
            for row in reader
        ]


def _load_error_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "source_class": row["source_class"],
                "target_class": row["target_class"],
                "error_rate": float(row["error_rate"]),
                "display_order": int(row["display_order"]),
                "label_text": row["label_text"],
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any], matrix_rows: list[dict[str, Any]], error_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_matrix = sorted(matrix_rows, key=lambda item: (item["true_order"], item["pred_order"]))
    ordered_errors = sorted(error_rows, key=lambda item: item["display_order"])
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_matrix,
        [
            "true_label",
            "predicted_label",
            "true_order",
            "pred_order",
            "rate",
            "count",
            "label_cell",
            "is_diagonal",
        ],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_errors,
        ["source_class", "target_class", "error_rate", "display_order", "label_text"],
    )
    return ordered_matrix, ordered_errors


def _class_styles(theme: dict[str, Any], labels: list[str]) -> dict[str, str]:
    colors = [
        theme["palette"]["categorical"][0],
        theme["palette"]["categorical"][1],
        theme["palette"]["categorical"][2],
        theme["palette"]["categorical"][3],
    ]
    return {label: colors[index % len(colors)] for index, label in enumerate(labels)}


def _matrix_lookup(matrix_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row["true_label"], row["predicted_label"]): row for row in matrix_rows
    }


def _macro_recall(matrix_rows: list[dict[str, Any]]) -> float:
    diagonal = [row["rate"] for row in matrix_rows if row["is_diagonal"] == "yes"]
    return mean(diagonal)


def _top_confusion(error_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return max(error_rows, key=lambda item: (item["error_rate"], -item["display_order"]))


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    matrix_rows = _load_matrix_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    error_rows = _load_error_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, matrix_rows, error_rows)
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
        gridspec_kw={"width_ratios": [1.15, 0.85]},
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)

    labels = [
        label
        for _, label in sorted({(row["true_order"], row["true_label"]) for row in panel_a_rows})
    ]
    colors = _class_styles(theme, labels)
    lookup = _matrix_lookup(panel_a_rows)
    matrix = [
        [lookup[(true_label, predicted_label)]["rate"] for predicted_label in labels]
        for true_label in labels
    ]

    panel_a = axes[0]
    heatmap = panel_a.imshow(matrix, cmap="Blues", vmin=0.0, vmax=1.0, aspect="equal")
    panel_a.set_title("Normalized confusion matrix", loc="left", pad=3)
    panel_a.set_xticks(range(len(labels)))
    panel_a.set_xticklabels(labels, rotation=25, ha="right")
    panel_a.set_yticks(range(len(labels)))
    panel_a.set_yticklabels(labels)
    panel_a.set_xlabel("Predicted label")
    panel_a.set_ylabel("True label")
    panel_a.set_xticks([index - 0.5 for index in range(1, len(labels))], minor=True)
    panel_a.set_yticks([index - 0.5 for index in range(1, len(labels))], minor=True)
    panel_a.grid(which="minor", color="white", linewidth=1.1)
    panel_a.tick_params(which="minor", bottom=False, left=False)

    for y_index, true_label in enumerate(labels):
        for x_index, predicted_label in enumerate(labels):
            row = lookup[(true_label, predicted_label)]
            rate = float(row["rate"])
            count = int(row["count"])
            text_color = "white" if rate >= 0.58 else theme["palette"]["neutral"][0]
            font_weight = "bold" if row["is_diagonal"] == "yes" else "normal"
            panel_a.text(
                x_index,
                y_index,
                f"{rate * 100:.0f}%\n(n={count})",
                ha="center",
                va="center",
                fontsize=theme["typography"]["annotation_font_size_pt"],
                color=text_color,
                fontweight=font_weight,
            )

    macro_recall = _macro_recall(panel_a_rows)
    panel_a.text(
        0.0,
        -0.22,
        f"Macro recall: {macro_recall * 100:.1f}%",
        transform=panel_a.transAxes,
        ha="left",
        va="top",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )
    colorbar = fig.colorbar(heatmap, ax=panel_a, fraction=0.046, pad=0.04)
    colorbar.ax.set_ylabel("Row-normalized rate", rotation=90, va="bottom")
    colorbar.ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))

    panel_b = axes[1]
    ordered_errors = list(reversed(panel_b_rows))
    y_positions = list(range(len(ordered_errors)))
    bar_values = [row["error_rate"] for row in ordered_errors]
    bar_labels = [row["label_text"] for row in ordered_errors]
    bar_colors = [colors[row["source_class"]] for row in ordered_errors]
    panel_b.barh(
        y_positions,
        bar_values,
        color=bar_colors,
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.45,
        alpha=0.88,
    )
    panel_b.set_yticks(y_positions)
    panel_b.set_yticklabels(bar_labels)
    panel_b.set_xlabel("Error rate")
    panel_b.set_title("Dominant off-diagonal confusion", loc="left", pad=3)
    panel_b.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_b.set_xlim(0.0, max(bar_values) + 0.08)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.spines["left"].set_visible(False)
    panel_b.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)

    for y_position, row in zip(y_positions, ordered_errors):
        panel_b.text(
            float(row["error_rate"]) + 0.008,
            y_position,
            f"{float(row['error_rate']) * 100:.0f}%",
            va="center",
            ha="left",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )

    top_error = _top_confusion(panel_b_rows)
    panel_b.text(
        1.0,
        -0.18,
        f"Top confusion: {top_error['label_text']} ({top_error['error_rate'] * 100:.0f}%)",
        transform=panel_b.transAxes,
        ha="right",
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

    write_manifest(
        spec,
        profile,
        resolved_font,
        "python",
        spec_path,
        outputs,
        [
            "row_normalized_confusion_heatmap",
            "annotated_cell_percentages",
            "off_diagonal_error_summary_panel",
            "class_level_error_interpretation",
            "vector_first_export",
        ],
        {
            "panel_count": 2,
            "annotation_count": 21,
            "diagonal_cell_count": 4,
            "off_diagonal_summary_count": 4,
        },
    )

    import matplotlib.pyplot as plt

    plt.close(fig)
    return outputs


if __name__ == "__main__":
    build_figure(Path("figures/specs/figure_09_confusion_matrix_normalized.yml"))
