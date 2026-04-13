#!/usr/bin/env python3
"""PRISMA output generation for the systematic review pipeline."""

from __future__ import annotations

from pathlib import Path

from review_common import (
    EXTRACTION_DIR,
    PRISMA_DIR,
    SCREENING_DIR,
    compute_prisma_counts,
    load_csv,
    write_csv,
    write_yaml,
)


def generate_prisma_counts(output_dir: Path | None = None) -> Path:
    """Generate PRISMA 2020 flow counts from versioned artifacts.

    Writes prisma_counts.yml with all numbers needed for the flow diagram.
    """
    out_dir = output_dir or PRISMA_DIR
    counts = compute_prisma_counts()
    out_path = out_dir / "prisma_counts.yml"
    write_yaml(out_path, counts)
    return out_path


def generate_exclusion_summary(
    screening_log_path: Path | None = None, output_dir: Path | None = None
) -> Path:
    """Generate aggregated exclusion reasons by stage."""
    log_file = screening_log_path or (SCREENING_DIR / "screening_log.csv")
    out_dir = output_dir or PRISMA_DIR
    out_path = out_dir / "exclusion_summary.csv"

    rows = load_csv(log_file)

    reasons: dict[tuple[str, str], int] = {}
    for r in rows:
        if r.get("decision") == "exclude":
            stage = r.get("stage", "unknown")
            reason = r.get("exclusion_reason", "not specified") or "not specified"
            key = (stage, reason)
            reasons[key] = reasons.get(key, 0) + 1

    summary_rows = [
        {"stage": stage, "exclusion_reason": reason, "count": str(count)}
        for (stage, reason), count in sorted(reasons.items())
    ]

    write_csv(out_path, summary_rows, ["stage", "exclusion_reason", "count"])
    return out_path


def generate_evidence_table(
    extraction_table_path: Path | None = None, output_dir: Path | None = None
) -> Path:
    """Generate a characteristics-of-included-studies table from extraction data."""
    ext_file = extraction_table_path or (EXTRACTION_DIR / "extraction_table.csv")
    out_dir = output_dir or PRISMA_DIR
    out_path = out_dir / "evidence_table.csv"

    rows = load_csv(ext_file)

    # Select key columns for the evidence table
    evidence_cols = [
        "record_id",
        "study_design",
        "population",
        "intervention",
        "comparator",
        "sample_size",
        "outcome_name",
        "outcome_measure",
        "effect_value",
        "ci_lower",
        "ci_upper",
        "p_value",
    ]

    evidence_rows = []
    for r in rows:
        evidence_rows.append({col: r.get(col, "") for col in evidence_cols})

    write_csv(out_path, evidence_rows, evidence_cols)
    return out_path


def generate_all(output_dir: Path | None = None) -> dict[str, str]:
    """Generate all PRISMA outputs. Returns paths of generated files."""
    out_dir = output_dir or PRISMA_DIR
    return {
        "prisma_counts": str(generate_prisma_counts(out_dir)),
        "exclusion_summary": str(generate_exclusion_summary(output_dir=out_dir)),
        "evidence_table": str(generate_evidence_table(output_dir=out_dir)),
    }
