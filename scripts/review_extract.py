#!/usr/bin/env python3
"""Extraction table management for the systematic review pipeline."""

from __future__ import annotations

from pathlib import Path

from review_common import (
    EXTRACTION_DIR,
    EXTRACTION_OPTIONAL_COLUMNS,
    EXTRACTION_REQUIRED_COLUMNS,
    SCREENING_DIR,
    load_csv,
    validate_csv_columns,
    write_csv,
)


def init_extraction_table(
    screening_log_path: Path | None = None, output_path: Path | None = None
) -> Path:
    """Create an extraction table from full-text included records.

    One row per included study with all extraction fields blank,
    ready for manual data entry.
    """
    log_file = screening_log_path or (SCREENING_DIR / "screening_log.csv")
    out_file = output_path or (EXTRACTION_DIR / "extraction_table.csv")

    log_rows = load_csv(log_file)
    included = [
        r for r in log_rows
        if r.get("stage") == "full_text" and r.get("decision") == "include"
    ]

    rows = []
    for rec in included:
        rows.append({
            "record_id": rec["record_id"],
            "study_design": "",
            "population": "",
            "intervention": "",
            "comparator": "",
            "sample_size": "",
            "outcome_name": "",
            "outcome_measure": "",
            "outcome_timing": "",
            "effect_value": "",
            "ci_lower": "",
            "ci_upper": "",
            "p_value": "",
            "extractor": "",
            "timestamp": "",
            "subgroup_notes": "",
            "heterogeneity_flags": "",
        })

    fieldnames = EXTRACTION_REQUIRED_COLUMNS + EXTRACTION_OPTIONAL_COLUMNS
    write_csv(out_file, rows, fieldnames)
    return out_file


# Allowed values for enumerated fields in extraction_table.csv.
ALLOWED_STUDY_DESIGNS = {
    "RCT",
    "cohort",
    "case-control",
    "cross-sectional",
    "single-arm trial",
    "case series",
    "case report",
    "other",
}

ALLOWED_OUTCOME_MEASURES = {
    "odds ratio",
    "risk ratio",
    "hazard ratio",
    "mean difference",
    "standardized mean difference",
    "rate ratio",
    "incidence rate",
    "proportion",
    "other",
}


def _is_positive_int(value: str) -> bool:
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def _is_p_value(value: str) -> bool:
    if not _is_float(value):
        return False
    v = float(value)
    return 0.0 <= v <= 1.0


def validate_extraction(
    table_path: Path | None = None, semantic: bool = True
) -> list[str]:
    """Validate the extraction table.

    Args:
        table_path: Path to the extraction_table.csv (defaults to repo path).
        semantic: When True, also check data types, ranges, and enumerated
                  values in addition to presence checks.

    Returns:
        List of error messages (empty if valid).
    """
    tbl_file = table_path or (EXTRACTION_DIR / "extraction_table.csv")
    rows = load_csv(tbl_file)

    errors = validate_csv_columns(rows, EXTRACTION_REQUIRED_COLUMNS, "extraction_table")
    if errors:
        return errors

    for i, row in enumerate(rows, 1):
        rid = row.get("record_id", f"row_{i}")

        # Presence check
        for col in EXTRACTION_REQUIRED_COLUMNS:
            if not row.get(col, "").strip():
                errors.append(f"Record {rid}: missing value for '{col}'")

        if not semantic:
            continue

        # Type/range/enum checks
        sample_size = row.get("sample_size", "").strip()
        if sample_size and not _is_positive_int(sample_size):
            errors.append(f"Record {rid}: sample_size must be a positive integer (got '{sample_size}')")

        for fkey in ("effect_value", "ci_lower", "ci_upper"):
            v = row.get(fkey, "").strip()
            if v and not _is_float(v):
                errors.append(f"Record {rid}: {fkey} must be a number (got '{v}')")

        p = row.get("p_value", "").strip()
        if p and not _is_p_value(p):
            errors.append(f"Record {rid}: p_value must be in [0, 1] (got '{p}')")

        # CI consistency
        try:
            lo = float(row.get("ci_lower", ""))
            hi = float(row.get("ci_upper", ""))
            if lo > hi:
                errors.append(f"Record {rid}: ci_lower ({lo}) > ci_upper ({hi})")
        except (ValueError, TypeError):
            pass  # Already flagged above if non-numeric

        # Study design enum (warn-style: only flag obvious typos)
        sd = row.get("study_design", "").strip()
        if sd and sd not in ALLOWED_STUDY_DESIGNS:
            errors.append(
                f"Record {rid}: unrecognized study_design '{sd}' "
                f"(allowed: {sorted(ALLOWED_STUDY_DESIGNS)})"
            )

        # Outcome measure enum
        om = row.get("outcome_measure", "").strip()
        if om and om not in ALLOWED_OUTCOME_MEASURES:
            errors.append(
                f"Record {rid}: unrecognized outcome_measure '{om}' "
                f"(allowed: {sorted(ALLOWED_OUTCOME_MEASURES)})"
            )

    return errors
