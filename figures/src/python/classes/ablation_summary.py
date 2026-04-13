#!/usr/bin/env python3
"""Class-based Python renderer for ablation-summary figures."""

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


def _load_primary_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "variant": row["variant"],
                "module_group": row["module_group"],
                "display_order": int(row["display_order"]),
                "auroc": float(row["auroc"]),
                "delta_auroc": float(row["delta_auroc"]),
                "label_variant": row["label_variant"],
            }
            for row in reader
        ]


def _load_secondary_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "variant": row["variant"],
                "module_group": row["module_group"],
                "display_order": int(row["display_order"]),
                "metric": row["metric"],
                "delta_value": float(row["delta_value"]),
                "label_variant": row["label_variant"],
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any], primary_rows: list[dict[str, Any]], secondary_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_primary = sorted(primary_rows, key=lambda item: item["display_order"])
    ordered_secondary = sorted(
        secondary_rows, key=lambda item: (item["display_order"], item["metric"])
    )
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_primary,
        ["variant", "module_group", "display_order", "auroc", "delta_auroc", "label_variant"],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_secondary,
        ["variant", "module_group", "display_order", "metric", "delta_value", "label_variant"],
    )
    return ordered_primary, ordered_secondary


def _group_colors(theme: dict[str, Any]) -> dict[str, str]:
    return {
        "Full system": theme["palette"]["neutral"][0],
        "Architectural module": theme["palette"]["categorical"][0],
        "Training recipe": theme["palette"]["categorical"][2],
        "Objective design": theme["palette"]["categorical"][1],
        "Auxiliary input": theme["palette"]["categorical"][3],
    }


def _metric_styles() -> dict[str, dict[str, Any]]:
    return {
        "AUPRC": {"marker": "o", "offset": -0.15},
        "ECE": {"marker": "s", "offset": 0.15},
    }


def _summary_text(primary_rows: list[dict[str, Any]], secondary_rows: list[dict[str, Any]]) -> str:
    largest_drop = min(
        (row for row in primary_rows if row["display_order"] != 1),
        key=lambda item: item["delta_auroc"],
    )
    worst_ece = max(
        (row for row in secondary_rows if row["metric"] == "ECE" and row["display_order"] != 1),
        key=lambda item: item["delta_value"],
    )
    return (
        f"Largest AUROC loss:\n{largest_drop['variant']}\n"
        f"Worst ECE increase:\n{worst_ece['variant']}"
    )


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    primary_rows = _load_primary_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    secondary_rows = _load_secondary_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, primary_rows, secondary_rows)
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
        gridspec_kw={"width_ratios": [1.0, 1.0]},
        constrained_layout=bool(theme["layout"]["constrained"]),
    )
    apply_publication_layout(fig, theme)

    colors = _group_colors(theme)
    metric_styles = _metric_styles()

    panel_a = axes[0]
    ordered_primary = list(reversed(panel_a_rows))
    y_positions = list(range(len(ordered_primary)))
    values = [float(row["delta_auroc"]) for row in ordered_primary]
    panel_a.barh(
        y_positions,
        values,
        color=[colors[str(row["module_group"])] for row in ordered_primary],
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.4,
        alpha=0.9,
    )
    panel_a.axvline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.9)
    panel_a.set_yticks(y_positions)
    panel_a.set_yticklabels([str(row["variant"]) for row in ordered_primary])
    panel_a.set_xlabel("AUROC drop vs full model")
    panel_a.set_title("AUROC drop vs full model", loc="left", pad=3)
    panel_a.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_a.set_xlim(min(values) - 0.018, 0.02)
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)
    panel_a.spines["left"].set_visible(False)
    panel_a.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    for y_pos, row in zip(y_positions, ordered_primary):
        value = float(row["delta_auroc"])
        panel_a.text(
            value - 0.003 if value < 0 else value + 0.003,
            y_pos,
            f"{float(row['auroc']):.3f}",
            ha="right" if value < 0 else "left",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )

    panel_b = axes[1]
    variants = list(reversed(panel_a_rows))
    base_y = {str(row["variant"]): index for index, row in enumerate(variants)}
    panel_b.axvline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.9)
    for row in panel_b_rows:
        metric = str(row["metric"])
        style = metric_styles[metric]
        y_value = base_y[str(row["variant"])] + float(style["offset"])
        x_value = float(row["delta_value"])
        panel_b.plot(
            [0.0, x_value],
            [y_value, y_value],
            color=colors[str(row["module_group"])],
            linewidth=1.1,
            alpha=0.75,
        )
        panel_b.scatter(
            [x_value],
            [y_value],
            color=colors[str(row["module_group"])],
            marker=style["marker"],
            s=34,
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.35,
            zorder=3,
        )
    panel_b.set_yticks(list(base_y.values()))
    panel_b.set_yticklabels(list(base_y.keys()))
    panel_b.set_xlabel("Secondary metric shift")
    panel_b.set_title("Secondary metric shifts", loc="left", pad=3)
    panel_b.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    extent = max(abs(float(row["delta_value"])) for row in panel_b_rows) + 0.02
    panel_b.set_xlim(-extent, extent)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.spines["left"].set_visible(False)
    panel_b.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    panel_b.text(
        1.02,
        0.96,
        "circle = AUPRC",
        transform=panel_b.transAxes,
        ha="left",
        va="top",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )
    panel_b.text(
        1.02,
        0.88,
        "square = ECE",
        transform=panel_b.transAxes,
        ha="left",
        va="top",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )
    panel_b.text(
        0.98,
        0.03,
        _summary_text(panel_a_rows, panel_b_rows),
        transform=panel_b.transAxes,
        ha="right",
        va="bottom",
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
            "ranked_primary_metric_drop_panel",
            "secondary_metric_shift_panel",
            "group_semantic_encoding",
            "metric_shape_encoding_not_color_only",
            "zero_centered_effect_reference",
            "vector_first_export",
        ],
        {
            "panel_count": 2,
            "highlight_label_count": 5,
            "annotation_count": 10,
            "reference_line_count": 2,
        },
    )

    import matplotlib.pyplot as plt

    plt.close(fig)
    return outputs


if __name__ == "__main__":
    build_figure(Path("figures/specs/figure_11_ablation_summary.yml"))
