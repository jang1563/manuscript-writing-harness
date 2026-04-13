#!/usr/bin/env python3
"""Screening log management for the systematic review pipeline."""

from __future__ import annotations

from pathlib import Path

from review_common import (
    SCREENING_DIR,
    SCREENING_REQUIRED_COLUMNS,
    SCREENING_OPTIONAL_COLUMNS,
    load_csv,
    write_csv,
)


ALL_SCREENING_COLUMNS = SCREENING_REQUIRED_COLUMNS + SCREENING_OPTIONAL_COLUMNS


def init_screening_log(
    input_path: Path | None = None, output_path: Path | None = None
) -> Path:
    """Create a screening log from deduplicated screening input.

    All records start as stage=title_abstract, decision=pending.
    """
    inp = input_path or (SCREENING_DIR / "screening_input.csv")
    out = output_path or (SCREENING_DIR / "screening_log.csv")

    records = load_csv(inp)
    rows = []
    for rec in records:
        rows.append({
            "record_id": rec["record_id"],
            "pmid": rec.get("pmid", ""),
            "doi": rec.get("doi", ""),
            "title": rec.get("title", ""),
            "authors": rec.get("authors", ""),
            "year": rec.get("year", ""),
            "abstract": rec.get("abstract", ""),
            "source_db": rec.get("source_db", ""),
            "stage": "title_abstract",
            "decision": "pending",
            "exclusion_reason": "",
            "reviewer": "",
            "timestamp": "",
            "ai_priority_score": "",
            "notes": "",
        })

    write_csv(out, rows, ALL_SCREENING_COLUMNS)
    return out


def apply_decisions(
    log_path: Path | None = None, decisions_path: Path | None = None
) -> dict[str, int]:
    """Merge a batch of screening decisions into the log.

    The decisions CSV must have columns: record_id, stage, decision,
    exclusion_reason, reviewer, timestamp.

    Returns counts of applied decisions.
    """
    log_file = log_path or (SCREENING_DIR / "screening_log.csv")
    dec_file = decisions_path or (SCREENING_DIR / "decisions_batch.csv")

    log_rows = load_csv(log_file)
    decisions = load_csv(dec_file)

    # Index decisions by (record_id, stage)
    dec_map: dict[tuple[str, str], dict[str, str]] = {}
    for d in decisions:
        key = (d["record_id"], d.get("stage", "title_abstract"))
        dec_map[key] = d

    applied = 0
    for row in log_rows:
        key = (row["record_id"], row["stage"])
        if key in dec_map:
            d = dec_map[key]
            row["decision"] = d.get("decision", row["decision"])
            row["exclusion_reason"] = d.get("exclusion_reason", "")
            row["reviewer"] = d.get("reviewer", "")
            row["timestamp"] = d.get("timestamp", "")
            applied += 1

    write_csv(log_file, log_rows, ALL_SCREENING_COLUMNS)
    return {"applied": applied, "total_decisions": len(decisions)}


def promote_to_fulltext(log_path: Path | None = None) -> dict[str, int]:
    """Add full-text screening rows for records included at title/abstract stage.

    Returns count of promoted records.
    """
    log_file = log_path or (SCREENING_DIR / "screening_log.csv")
    log_rows = load_csv(log_file)

    # Find records already having full_text rows
    existing_ft = {
        r["record_id"] for r in log_rows if r["stage"] == "full_text"
    }

    # Find included title_abstract records not yet promoted
    to_promote = [
        r for r in log_rows
        if r["stage"] == "title_abstract"
        and r["decision"] == "include"
        and r["record_id"] not in existing_ft
    ]

    for rec in to_promote:
        log_rows.append({
            "record_id": rec["record_id"],
            "pmid": rec.get("pmid", ""),
            "doi": rec.get("doi", ""),
            "title": rec.get("title", ""),
            "authors": rec.get("authors", ""),
            "year": rec.get("year", ""),
            "abstract": rec.get("abstract", ""),
            "source_db": rec.get("source_db", ""),
            "stage": "full_text",
            "decision": "pending",
            "exclusion_reason": "",
            "reviewer": "",
            "timestamp": "",
            "ai_priority_score": "",
            "notes": "",
        })

    write_csv(log_file, log_rows, ALL_SCREENING_COLUMNS)
    return {"promoted": len(to_promote)}


def screening_summary(log_path: Path | None = None) -> dict[str, dict[str, int]]:
    """Return counts by stage and decision."""
    log_file = log_path or (SCREENING_DIR / "screening_log.csv")
    log_rows = load_csv(log_file)

    summary: dict[str, dict[str, int]] = {}
    for row in log_rows:
        stage = row.get("stage", "unknown")
        decision = row.get("decision", "unknown")
        if stage not in summary:
            summary[stage] = {}
        summary[stage][decision] = summary[stage].get(decision, 0) + 1

    return summary
