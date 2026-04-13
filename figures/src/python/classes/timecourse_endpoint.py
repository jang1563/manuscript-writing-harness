#!/usr/bin/env python3
"""Class-based Python renderer for time-course plus endpoint figures."""

from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean, stdev
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


def _load_rows(data_path: Path) -> list[dict[str, Any]]:
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "timepoint_hours": int(row["timepoint_hours"]),
                "condition": row["condition"],
                "replicate": int(row["replicate"]),
                "response": float(row["response"]),
            }
            for row in reader
        ]


def _summarize_by_timepoint(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        key = (str(row["condition"]), int(row["timepoint_hours"]))
        grouped.setdefault(key, []).append(float(row["response"]))

    summary: list[dict[str, Any]] = []
    for condition, timepoint in sorted(grouped):
        values = grouped[(condition, timepoint)]
        summary.append(
            {
                "condition": condition,
                "timepoint_hours": timepoint,
                "mean_response": mean(values),
                "std_response": stdev(values) if len(values) > 1 else 0.0,
                "n": len(values),
            }
        )
    return summary


def _summarize_endpoint(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_timepoint = max(int(row["timepoint_hours"]) for row in rows)
    endpoint_rows = [row for row in rows if int(row["timepoint_hours"]) == max_timepoint]
    grouped: dict[str, list[float]] = {}
    for row in endpoint_rows:
        grouped.setdefault(str(row["condition"]), []).append(float(row["response"]))

    summary: list[dict[str, Any]] = []
    for condition in sorted(grouped):
        values = grouped[condition]
        summary.append(
            {
                "condition": condition,
                "timepoint_hours": max_timepoint,
                "mean_response": mean(values),
                "std_response": stdev(values) if len(values) > 1 else 0.0,
                "n": len(values),
                "replicate_values": values,
            }
        )
    return summary


def build_source_data(spec: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    panel_summary = _summarize_by_timepoint(rows)
    endpoint_summary = _summarize_endpoint(rows)
    source_outputs = source_data_mapping(spec)
    panel_a_path = REPO_ROOT / source_outputs["a"]
    panel_b_path = REPO_ROOT / source_outputs["b"]

    export_csv(
        panel_a_path,
        panel_summary,
        ["condition", "timepoint_hours", "mean_response", "std_response", "n"],
    )

    panel_b_rows: list[dict[str, Any]] = []
    for item in endpoint_summary:
        for replicate_index, value in enumerate(item["replicate_values"], start=1):
            panel_b_rows.append(
                {
                    "condition": item["condition"],
                    "endpoint_hours": item["timepoint_hours"],
                    "replicate": replicate_index,
                    "response": value,
                    "mean_response": item["mean_response"],
                    "std_response": item["std_response"],
                }
            )
    export_csv(
        panel_b_path,
        panel_b_rows,
        [
            "condition",
            "endpoint_hours",
            "replicate",
            "response",
            "mean_response",
            "std_response",
        ],
    )
    return panel_summary, endpoint_summary


def create_figure(spec_path: Path) -> Figure:
    spec, theme, font_policy, profile, class_entry = project_resources(spec_path)
    validate_common_contract(spec, theme, font_policy, profile, class_entry)
    rows = _load_rows(REPO_ROOT / str(spec["data_inputs"][0]))
    panel_summary, endpoint_summary = build_source_data(spec, rows)
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
        "Control": theme["palette"]["categorical"][0],
        "Treated": theme["palette"]["categorical"][1],
    }

    panel_a = axes[0]
    line_endpoints: dict[str, tuple[float, float]] = {}
    for condition in ("Control", "Treated"):
        subset = [row for row in panel_summary if row["condition"] == condition]
        x = [row["timepoint_hours"] for row in subset]
        y = [row["mean_response"] for row in subset]
        yerr = [row["std_response"] for row in subset]
        panel_a.plot(x, y, marker="o", color=colors[condition], label=condition)
        panel_a.fill_between(
            x,
            [a - b for a, b in zip(y, yerr)],
            [a + b for a, b in zip(y, yerr)],
            color=colors[condition],
            alpha=0.12,
        )
        line_endpoints[condition] = (x[-1], y[-1])
    max_timepoint = max(point[0] for point in line_endpoints.values())
    panel_a.set_xlim(0, max_timepoint + 1.1)
    for condition, (x_end, y_end) in line_endpoints.items():
        panel_a.text(
            x_end + 0.28,
            y_end,
            condition,
            color=colors[condition],
            fontsize=theme["typography"]["annotation_font_size_pt"],
            va="center",
            ha="left",
        )
    panel_a.set_title("Time-course response", loc="left", pad=2)
    panel_a.set_xlabel("Time (hours)")
    panel_a.set_ylabel("Normalized signal")
    panel_a.spines["top"].set_visible(False)
    panel_a.spines["right"].set_visible(False)

    panel_b = axes[1]
    conditions = [item["condition"] for item in endpoint_summary]
    x_positions = list(range(len(conditions)))
    panel_b.bar(
        x_positions,
        [item["mean_response"] for item in endpoint_summary],
        yerr=[item["std_response"] for item in endpoint_summary],
        color=[colors[condition] for condition in conditions],
        alpha=0.88,
        capsize=3,
        width=0.62,
        edgecolor=theme["palette"]["neutral"][0],
        linewidth=theme["strokes"]["errorbar_line_width_pt"],
    )
    for index, item in enumerate(endpoint_summary):
        for offset, value in zip((-0.08, 0.0, 0.08), item["replicate_values"]):
            panel_b.scatter(
                index + offset,
                value,
                color=theme["export_defaults"]["background"],
                edgecolor=theme["palette"]["neutral"][0],
                linewidth=theme["strokes"]["marker_edge_width_pt"],
                s=22,
                zorder=3,
            )
    panel_b.set_title("Endpoint summary", loc="left", pad=2)
    panel_b.set_xlabel("Condition")
    panel_b.set_ylabel("Normalized signal at 6 h")
    panel_b.set_xticks(x_positions)
    panel_b.set_xticklabels(conditions)
    panel_b.spines["top"].set_visible(False)
    panel_b.spines["right"].set_visible(False)

    add_panel_labels(spec, theme, [panel_a, panel_b])
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
            "direct_labels_for_small_number_of_series",
            "replicate_level_points_in_endpoint_panel",
            "vector_first_export",
        ],
        {
            "panel_count": len(spec.get("panels", [])),
            "direct_label_count": 2,
            "endpoint_replicate_count": sum(
                1 for row in rows if int(row["timepoint_hours"]) == max(item["timepoint_hours"] for item in rows)
            ),
        },
    )
    return outputs


if __name__ == "__main__":
    raise SystemExit("Use figures/src/python/run_class_renderer.py")
