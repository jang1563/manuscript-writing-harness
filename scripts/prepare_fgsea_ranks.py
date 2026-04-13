#!/usr/bin/env python3
"""Prepare canonical fgsea preranks from DE-style result tables."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent

GENE_ALIASES = ["gene", "symbol", "gene_symbol", "gene_id", "Gene", "SYMBOL", "GeneSymbol"]
SCORE_ALIASES = ["stat", "score", "t", "waldStat", "WaldStatistic", "signed_score"]
EFFECT_ALIASES = ["log2FoldChange", "logFC", "effect", "estimate", "coef"]
SIGNIFICANCE_ALIASES = ["padj", "FDR", "adj.P.Val", "qvalue", "pvalue", "P.Value"]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _load_config(config_path: Path) -> dict[str, Any]:
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"na", "nan", "none"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _infer_column(fieldnames: list[str], configured: str | None, aliases: list[str]) -> str | None:
    if configured:
        return configured if configured in fieldnames else None
    lowered = {name.lower(): name for name in fieldnames}
    for alias in aliases:
        match = lowered.get(alias.lower())
        if match:
            return match
    return None


def _score_from_row(row: dict[str, str], config: dict[str, Any], columns: dict[str, str]) -> float | None:
    method = str(config.get("method", "signed_neg_log10_significance"))
    if method == "direct_stat":
        score = _parse_float(row.get(columns["score"]))
        if score is None:
            return None
        if str(config.get("score_direction", "as_is")) == "invert":
            score = -score
        return score
    if method != "signed_neg_log10_significance":
        raise ValueError(f"Unsupported rank-prep method: {method}")

    effect = _parse_float(row.get(columns["effect"]))
    significance = _parse_float(row.get(columns["significance"]))
    if effect is None or significance is None:
        return None
    floor = float(config.get("significance_floor", 1e-300))
    significance = max(significance, floor)
    if effect > 0:
        direction = 1.0
    elif effect < 0:
        direction = -1.0
    else:
        direction = 0.0
    return direction * (-math.log10(significance))


def _deduplicate(rows: list[dict[str, Any]], *, policy: str) -> tuple[list[dict[str, Any]], int]:
    if policy != "max_abs_score":
        raise ValueError(f"Unsupported deduplicate_by policy: {policy}")
    kept: dict[str, dict[str, Any]] = {}
    dropped = 0
    for row in rows:
        gene = row["gene"]
        current = kept.get(gene)
        if current is None:
            kept[gene] = row
            continue
        if abs(row["stat"]) > abs(current["stat"]):
            kept[gene] = row
        dropped += 1
    return list(kept.values()), dropped


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["gene", "stat"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"gene": row["gene"], "stat": f"{row['stat']:.12g}"})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        f"# fgsea Rank Preparation: {payload['study_id']}",
        "",
        f"- status: `{payload['status']}`",
        f"- config: `{payload['config']}`",
        f"- input_table: `{payload['input_table']}`",
        f"- output_ranks_csv: `{payload['output_ranks_csv']}`",
        f"- source_tool: `{payload['source_tool']}`",
        f"- method: `{payload['method']}`",
        f"- input_rows: `{payload['input_rows']}`",
        f"- retained_rows: `{payload['retained_rows']}`",
        f"- duplicate_genes_removed: `{payload['duplicate_genes_removed']}`",
        f"- dropped_missing_or_invalid: `{payload['dropped_missing_or_invalid']}`",
        "",
        "## Top Positive",
        "",
    ]
    lines.extend(f"- `{item['gene']}`: `{item['stat']}`" for item in payload.get("top_positive", []))
    lines.extend(["", "## Top Negative", ""])
    lines.extend(f"- `{item['gene']}`: `{item['stat']}`" for item in payload.get("top_negative", []))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_fgsea_ranks(config_path: Path) -> dict[str, Any]:
    resolved_config = config_path.resolve()
    config = _load_config(resolved_config)
    input_table = _resolve_repo_path(str(config["input_table"]))
    output_ranks_csv = _resolve_repo_path(str(config["output_ranks_csv"]))
    summary_json = _resolve_repo_path(str(config["summary_json"]))
    summary_md = _resolve_repo_path(str(config["summary_md"]))

    with input_table.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        columns = {"gene": _infer_column(fieldnames, config.get("gene_column"), GENE_ALIASES)}
        method = str(config.get("method", "signed_neg_log10_significance"))
        if method == "direct_stat":
            columns["score"] = _infer_column(fieldnames, config.get("score_column"), SCORE_ALIASES)
        else:
            columns["effect"] = _infer_column(fieldnames, config.get("effect_column"), EFFECT_ALIASES)
            columns["significance"] = _infer_column(
                fieldnames, config.get("significance_column"), SIGNIFICANCE_ALIASES
            )
        missing_columns = [name for name, value in columns.items() if not value]
        if missing_columns:
            raise ValueError(f"Could not resolve required columns: {missing_columns}")

        prepared_rows: list[dict[str, Any]] = []
        input_rows = 0
        dropped_missing = 0
        for row in reader:
            input_rows += 1
            gene = str(row.get(columns["gene"] or "", "")).strip()
            if not gene:
                dropped_missing += 1
                continue
            score = _score_from_row(row, config, columns)  # type: ignore[arg-type]
            if score is None or math.isnan(score) or math.isinf(score):
                dropped_missing += 1
                continue
            prepared_rows.append({"gene": gene, "stat": score})

    deduplicated_rows, duplicate_genes_removed = _deduplicate(
        prepared_rows,
        policy=str(config.get("deduplicate_by", "max_abs_score")),
    )
    if bool(config.get("sort_descending", True)):
        deduplicated_rows.sort(key=lambda item: (-item["stat"], item["gene"]))
    else:
        deduplicated_rows.sort(key=lambda item: (item["stat"], item["gene"]))
    _write_csv(output_ranks_csv, deduplicated_rows)

    payload = {
        "study_id": str(config.get("study_id") or resolved_config.parent.parent.name),
        "status": "ready",
        "config": _display_path(resolved_config),
        "input_table": _display_path(input_table),
        "output_ranks_csv": _display_path(output_ranks_csv),
        "summary_json": _display_path(summary_json),
        "summary_md": _display_path(summary_md),
        "source_tool": str(config.get("source_tool", "custom")),
        "method": method,
        "input_rows": input_rows,
        "retained_rows": len(deduplicated_rows),
        "duplicate_genes_removed": duplicate_genes_removed,
        "dropped_missing_or_invalid": dropped_missing,
        "top_positive": [
            {"gene": row["gene"], "stat": round(float(row["stat"]), 6)}
            for row in deduplicated_rows[:5]
        ],
        "top_negative": [
            {"gene": row["gene"], "stat": round(float(row["stat"]), 6)}
            for row in sorted(deduplicated_rows, key=lambda item: (item["stat"], item["gene"]))[:5]
        ],
    }
    _write_json(summary_json, payload)
    _write_markdown(summary_md, payload)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare fgsea preranks from DE-style tables")
    parser.add_argument("--config", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = prepare_fgsea_ranks(Path(args.config))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Prepared ranks: {payload['output_ranks_csv']}")
        print(f"Summary: {payload['summary_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
