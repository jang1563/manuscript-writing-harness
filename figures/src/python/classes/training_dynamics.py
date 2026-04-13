#!/usr/bin/env python3
"""Class-based Python renderer for training-dynamics figures."""

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


def _load_loss_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "epoch": int(row["epoch"]),
                "split": row["split"],
                "loss": float(row["loss"]),
            }
            for row in reader
        ]


def _load_metric_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "model": row["model"],
                "display_order": int(row["display_order"]),
                "epoch": int(row["epoch"]),
                "auroc": float(row["auroc"]),
                "label_epoch": row["label_epoch"],
                "best_epoch": row["best_epoch"],
            }
            for row in reader
        ]


def build_source_data(
    spec: dict[str, Any], loss_rows: list[dict[str, Any]], metric_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered_loss = sorted(
        loss_rows,
        key=lambda item: (item["display_order"], item["split"] != "train", item["epoch"]),
    )
    ordered_metric = sorted(metric_rows, key=lambda item: (item["display_order"], item["epoch"]))
    mapping = source_data_mapping(spec)
    export_csv(
        REPO_ROOT / mapping["a"],
        ordered_loss,
        ["model", "display_order", "epoch", "split", "loss"],
    )
    export_csv(
        REPO_ROOT / mapping["b"],
        ordered_metric,
        ["model", "display_order", "epoch", "auroc", "label_epoch", "best_epoch"],
    )
    return ordered_loss, ordered_metric


def _style_map(theme: dict[str, Any], models: list[str]) -> dict[str, dict[str, Any]]:
    colors = [
        theme["palette"]["categorical"][0],
        theme["palette"]["categorical"][1],
        theme["palette"]["categorical"][2],
    ]
    markers = ["o", "s", "D"]
    return {
        model: {
            "color": colors[index % len(colors)],
            "marker": markers[index % len(markers)],
        }
        for index, model in enumerate(models)
    }


def _label_offsets() -> dict[str, tuple[float, float]]:
    return {
        "Foundation model": (0.35, 0.0),
        "Hybrid GNN": (0.35, -0.02),
        "CNN baseline": (0.35, -0.04),
    }


def _summary_text(metric_rows: list[dict[str, Any]], models: list[str]) -> str:
    lines = ["Best validation AUROC"]
    for model in models:
        best_row = max(
            (row for row in metric_rows if row["model"] == model),
            key=lambda item: (item["auroc"], -item["epoch"]),
        )
        lines.append(f"{model}: {best_row['auroc']:.2f}")
    return "\n".join(lines)


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    loss_rows = _load_loss_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metric_rows = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
    panel_a_rows, panel_b_rows = build_source_data(spec, loss_rows, metric_rows)
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

    model_names = [model for _, model in sorted({(r["display_order"], r["model"]) for r in panel_a_rows})]
    styles = _style_map(theme, model_names)

    panel_a = axes[0]
    for model in model_names:
        for split, linestyle, alpha, linewidth in (
            ("train", "--", 0.65, 1.4),
            ("validation", "-", 0.95, 1.8),
        ):
            subset = sorted(
                [row for row in panel_a_rows if row["model"] == model and row["split"] == split],
                key=lambda item: item["epoch"],
            )
            x_values = [row["epoch"] for row in subset]
            y_values = [row["loss"] for row in subset]
            panel_a.plot(
                x_values,
                y_values,
                color=styles[model]["color"],
                linestyle=linestyle,
                linewidth=linewidth,
                alpha=alpha,
            )
            if split == "validation":
                dx, dy = _label_offsets()[model]
                panel_a.text(
                    x_values[-1] + dx,
                    y_values[-1] + dy,
                    model,
                    fontsize=theme["typography"]["annotation_font_size_pt"],
                    color=theme["palette"]["neutral"][0],
                    ha="left",
                    va="center",
                )
    panel_a.text(
        1.02,
        0.95,
        "solid = validation",
        transform=panel_a.transAxes,
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
        ha="left",
        va="top",
    )
    panel_a.text(
        1.02,
        0.87,
        "dashed = train",
        transform=panel_a.transAxes,
        fontsize=theme["typography"]["annotation_font_size_pt"],
        color=theme["palette"]["neutral"][1],
        ha="left",
        va="top",
    )
    panel_a.set_title("Training and validation loss", loc="left", pad=2)
    panel_a.set_xlabel("Epoch")
    panel_a.set_ylabel("Loss")
    panel_a.set_xlim(1, max(row["epoch"] for row in panel_a_rows) + 1.1)
    panel_a.set_ylim(0.2, max(row["loss"] for row in panel_a_rows) + 0.12)
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)

    panel_b = axes[1]
    for model in model_names:
        subset = sorted(
            [row for row in panel_b_rows if row["model"] == model],
            key=lambda item: item["epoch"],
        )
        x_values = [row["epoch"] for row in subset]
        y_values = [row["auroc"] for row in subset]
        panel_b.plot(
            x_values,
            y_values,
            color=styles[model]["color"],
            linewidth=1.8,
            marker=styles[model]["marker"],
            markersize=4.6,
        )
        final_row = next(row for row in subset if row["label_epoch"] == "yes")
        dx, dy = _label_offsets()[model]
        panel_b.text(
            final_row["epoch"] + dx,
            final_row["auroc"] + dy * 0.5,
            model,
            fontsize=theme["typography"]["annotation_font_size_pt"],
            color=theme["palette"]["neutral"][0],
            ha="left",
            va="center",
        )
        best_row = next(row for row in subset if row["best_epoch"] == "yes")
        panel_b.scatter(
            best_row["epoch"],
            best_row["auroc"],
            s=70,
            color=styles[model]["color"],
            marker="*",
            edgecolor=theme["palette"]["neutral"][0],
            linewidth=0.5,
            zorder=4,
        )
    panel_b.text(
        0.98,
        0.04,
        _summary_text(panel_b_rows, model_names),
        transform=panel_b.transAxes,
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
    panel_b.set_title("Validation AUROC trajectory", loc="left", pad=2)
    panel_b.set_xlabel("Epoch")
    panel_b.set_ylabel("Validation AUROC")
    panel_b.set_xlim(1, max(row["epoch"] for row in panel_b_rows) + 1.1)
    panel_b.set_ylim(0.5, max(row["auroc"] for row in panel_b_rows) + 0.05)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)

    add_panel_labels(spec, theme, [panel_a, panel_b])
    return fig


def build_figure(spec_path: Path) -> dict[str, str]:
    spec, theme, font_policy, profile, _ = project_resources(spec_path)
    loss_rows = _load_loss_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    metric_rows = _load_metric_rows(REPO_ROOT / str(spec["data_inputs"][1]))
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
            "paired_loss_and_metric_panels",
            "split_encoding_not_color_only",
            "direct_labels_at_final_epoch",
            "best_checkpoint_markers",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "direct_label_count": 6,
            "annotation_count": 9,
            "best_checkpoint_count": 3,
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
