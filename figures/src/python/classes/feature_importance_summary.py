#!/usr/bin/env python3
"""Class-based Python renderer for feature-importance summary figures."""

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


def _load_rank_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "feature": row["feature"],
                "feature_group": row["feature_group"],
                "display_order": int(row["display_order"]),
                "mean_abs_importance": float(row["mean_abs_importance"]),
                "label_feature": row["label_feature"],
            }
            for row in reader
        ]


def _load_effect_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "feature": row["feature"],
                "feature_group": row["feature_group"],
                "display_order": int(row["display_order"]),
                "signed_effect": float(row["signed_effect"]),
                "expected_direction": row["expected_direction"],
                "label_feature": row["label_feature"],
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any], rank_rows: list[dict[str, Any]], effect_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_rank = sorted(rank_rows, key=lambda item: item["display_order"])
    ordered_effect = sorted(effect_rows, key=lambda item: item["display_order"])
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_rank,
        ["feature", "feature_group", "display_order", "mean_abs_importance", "label_feature"],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_effect,
        [
            "feature",
            "feature_group",
            "display_order",
            "signed_effect",
            "expected_direction",
            "label_feature",
        ],
    )
    return ordered_rank, ordered_effect


def _group_colors(theme: dict[str, Any]) -> dict[str, str]:
    return {
        "Fibrotic remodeling": theme["palette"]["categorical"][0],
        "Inflammatory state": theme["palette"]["categorical"][1],
        "Proliferative state": theme["palette"]["categorical"][2],
        "Immune activation": theme["palette"]["categorical"][3],
        "Nuisance covariate": theme["palette"]["neutral"][1],
    }


def _direction_color(theme: dict[str, Any], value: float, expected_direction: str) -> str:
    if expected_direction == "neutral":
        return theme["palette"]["neutral"][1]
    return theme["palette"]["categorical"][0] if value >= 0 else theme["palette"]["categorical"][1]


def _importance_summary(rank_rows: list[dict[str, Any]]) -> str:
    total = sum(float(row["mean_abs_importance"]) for row in rank_rows)
    labeled = sum(
        float(row["mean_abs_importance"]) for row in rank_rows if row["label_feature"] == "yes"
    )
    nuisance = sum(
        float(row["mean_abs_importance"])
        for row in rank_rows
        if row["feature_group"] == "Nuisance covariate"
    )
    return (
        f"Labeled top features: {labeled / total * 100:.0f}%\n"
        f"Nuisance covariates: {nuisance / total * 100:.0f}%"
    )


def _direction_summary(effect_rows: list[dict[str, Any]]) -> str:
    aligned = sum(
        1
        for row in effect_rows
        if row["label_feature"] == "yes"
        and (
            (row["expected_direction"] == "increases_response" and row["signed_effect"] > 0)
            or (row["expected_direction"] == "decreases_response" and row["signed_effect"] < 0)
        )
    )
    labeled = sum(1 for row in effect_rows if row["label_feature"] == "yes")
    return f"Expected direction matched: {aligned}/{labeled}"


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    rank_rows = _load_rank_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    effect_rows = _load_effect_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, rank_rows, effect_rows)
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

    group_colors = _group_colors(theme)

    panel_a = axes[0]
    ordered_rank = list(reversed(panel_a_rows))
    y_positions = list(range(len(ordered_rank)))
    importance_values = [float(row["mean_abs_importance"]) for row in ordered_rank]
    panel_a.barh(
        y_positions,
        importance_values,
        color=[group_colors[str(row["feature_group"])] for row in ordered_rank],
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.4,
        alpha=0.9,
    )
    panel_a.set_yticks(y_positions)
    panel_a.set_yticklabels([str(row["feature"]) for row in ordered_rank])
    panel_a.set_xlabel("Mean absolute importance")
    panel_a.set_title("Feature importance rank", loc="left", pad=3)
    panel_a.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    panel_a.set_xlim(0.0, max(importance_values) + 0.08)
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)
    panel_a.spines["left"].set_visible(False)
    panel_a.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    for y_pos, row in zip(y_positions, ordered_rank):
        value = float(row["mean_abs_importance"])
        panel_a.text(
            value + 0.005,
            y_pos,
            f"{value * 100:.1f}%",
            ha="left",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )
    panel_a.text(
        0.98,
        0.03,
        _importance_summary(panel_a_rows),
        transform=panel_a.transAxes,
        ha="right",
        va="bottom",
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
    )

    panel_b = axes[1]
    ordered_effect = list(reversed(panel_b_rows))
    y_positions = list(range(len(ordered_effect)))
    signed_values = [float(row["signed_effect"]) for row in ordered_effect]
    panel_b.barh(
        y_positions,
        signed_values,
        color=[
            _direction_color(theme, float(row["signed_effect"]), str(row["expected_direction"]))
            for row in ordered_effect
        ],
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=0.4,
        alpha=0.9,
    )
    panel_b.axvline(0.0, color=theme["palette"]["neutral"][1], linewidth=0.9)
    panel_b.set_yticks(y_positions)
    panel_b.set_yticklabels([str(row["feature"]) for row in ordered_effect])
    panel_b.set_xlabel("Signed effect")
    panel_b.set_title("Signed effect on predicted response", loc="left", pad=3)
    panel_b.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    max_extent = max(abs(value) for value in signed_values) + 0.07
    panel_b.set_xlim(-max_extent, max_extent)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)
    panel_b.spines["left"].set_visible(False)
    panel_b.grid(axis="x", color=theme["palette"]["neutral"][2], linewidth=0.6)
    for y_pos, row in zip(y_positions, ordered_effect):
        value = float(row["signed_effect"])
        panel_b.text(
            value + (0.006 if value >= 0 else -0.006),
            y_pos,
            f"{value * 100:+.1f}%",
            ha="left" if value >= 0 else "right",
            va="center",
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
        )
    panel_b.text(
        0.98,
        0.03,
        _direction_summary(panel_b_rows),
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
            "ranked_feature_importance_panel",
            "signed_directional_effect_panel",
            "group_semantic_encoding",
            "zero_centered_effect_reference",
            "vector_first_export",
        ],
        {
            "panel_count": 2,
            "highlight_label_count": 6,
            "annotation_count": 14,
            "reference_line_count": 1,
        },
    )

    import matplotlib.pyplot as plt

    plt.close(fig)
    return outputs


if __name__ == "__main__":
    build_figure(Path("figures/specs/figure_10_feature_importance_summary.yml"))
