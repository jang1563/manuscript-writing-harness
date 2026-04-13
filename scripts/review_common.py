#!/usr/bin/env python3
"""Shared helpers for the systematic review pipeline."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent

# Directory layout
REVIEW_ROOT = REPO_ROOT / "review"
REVIEW_SCHEMAS_DIR = REVIEW_ROOT / "schemas"
PROTOCOL_DIR = REVIEW_ROOT / "protocol"
QUERIES_DIR = REVIEW_ROOT / "queries"
RETRIEVAL_DIR = REVIEW_ROOT / "retrieval"
SCREENING_DIR = REVIEW_ROOT / "screening"
EXTRACTION_DIR = REVIEW_ROOT / "extraction"
BIAS_DIR = REVIEW_ROOT / "bias"
PRISMA_DIR = REVIEW_ROOT / "prisma"
DEMO_DIR = REVIEW_ROOT / "demo"

# Schema required-field names (top-level name values from each schema)
PROTOCOL_REQUIRED_FIELDS = {
    "protocol_id",
    "title",
    "version",
    "status",
    "question",
    "inclusion_criteria",
    "exclusion_criteria",
    "databases",
    "primary_outcomes",
    "secondary_outcomes",
}

QUERY_REQUIRED_FIELDS = {
    "query_id",
    "protocol_id",
    "database",
    "query_text",
    "filters",
    "date_run",
    "export_format",
    "hit_count",
    "export_file",
}

SCREENING_REQUIRED_COLUMNS = [
    "record_id",
    "pmid",
    "doi",
    "title",
    "authors",
    "year",
    "abstract",
    "source_db",
    "stage",
    "decision",
    "exclusion_reason",
    "reviewer",
    "timestamp",
]

SCREENING_OPTIONAL_COLUMNS = [
    "ai_priority_score",
    "notes",
]

EXTRACTION_REQUIRED_COLUMNS = [
    "record_id",
    "study_design",
    "population",
    "intervention",
    "comparator",
    "sample_size",
    "outcome_name",
    "outcome_measure",
    "outcome_timing",
    "effect_value",
    "ci_lower",
    "ci_upper",
    "p_value",
    "extractor",
    "timestamp",
]

EXTRACTION_OPTIONAL_COLUMNS = [
    "subgroup_notes",
    "heterogeneity_flags",
]

BIAS_REQUIRED_COLUMNS = [
    "record_id",
    "tool",
    "overall_judgment",
    "assessor",
    "ai_assisted",
    "timestamp",
]

ROB2_DOMAINS = [
    "D1_randomisation",
    "D2_deviations",
    "D3_missing_data",
    "D4_measurement",
    "D5_selection_reporting",
]

ROBINS_I_DOMAINS = [
    "D1_confounding",
    "D2_selection",
    "D3_classification",
    "D4_deviations",
    "D5_missing_data",
    "D6_measurement",
    "D7_selection_reporting",
]

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write data to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=False, allow_unicode=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    """Load a CSV file and return rows as a list of dicts."""
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    """Write rows to a CSV file with the given column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_yaml_fields(data: dict[str, Any], required: set[str], label: str) -> list[str]:
    """Check that all required top-level keys are present and non-empty.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    for field in sorted(required):
        if field not in data:
            errors.append(f"{label}: missing required field '{field}'")
        elif data[field] is None or data[field] == "":
            errors.append(f"{label}: field '{field}' is empty")
    return errors


def validate_csv_columns(
    rows: list[dict[str, str]], required: list[str], label: str
) -> list[str]:
    """Check that all required columns exist in the CSV rows.

    Returns a list of error messages (empty if valid).
    """
    if not rows:
        return [f"{label}: no rows found"]
    present = set(rows[0].keys())
    missing = [c for c in required if c not in present]
    if missing:
        return [f"{label}: missing columns {missing}"]
    return []


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_protocol() -> dict[str, Any]:
    """Load and return the protocol YAML."""
    path = PROTOCOL_DIR / "protocol.yml"
    if not path.exists():
        raise FileNotFoundError(f"Protocol not found: {path}")
    return load_yaml(path)


def load_queries() -> list[dict[str, Any]]:
    """Load all query YAML files (excluding templates)."""
    queries = []
    for p in sorted(QUERIES_DIR.glob("*.yml")):
        if "template" in p.name:
            continue
        queries.append(load_yaml(p))
    return queries


def load_screening_log() -> list[dict[str, str]]:
    """Load the screening log CSV."""
    path = SCREENING_DIR / "screening_log.csv"
    if not path.exists():
        raise FileNotFoundError(f"Screening log not found: {path}")
    return load_csv(path)


def load_extraction_table() -> list[dict[str, str]]:
    """Load the extraction table CSV."""
    path = EXTRACTION_DIR / "extraction_table.csv"
    if not path.exists():
        raise FileNotFoundError(f"Extraction table not found: {path}")
    return load_csv(path)


def load_bias_assessments() -> list[dict[str, str]]:
    """Load the bias assessments CSV."""
    path = BIAS_DIR / "bias_assessments.csv"
    if not path.exists():
        raise FileNotFoundError(f"Bias assessments not found: {path}")
    return load_csv(path)


def load_dedup_log() -> list[dict[str, str]]:
    """Load the deduplication log CSV."""
    path = RETRIEVAL_DIR / "dedup" / "dedup_log.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dedup log not found: {path}")
    return load_csv(path)


# ---------------------------------------------------------------------------
# PRISMA count computation
# ---------------------------------------------------------------------------


def compute_prisma_counts() -> dict[str, Any]:
    """Derive all PRISMA 2020 flow counts from versioned artifacts.

    Reads: query files, dedup log, screening log.
    Returns a dict with all counts needed for the PRISMA flow diagram.
    """
    # Identification
    queries = load_queries()
    db_counts: dict[str, int] = {}
    for q in queries:
        db = q.get("database", "unknown")
        db_counts[db] = db_counts.get(db, 0) + int(q.get("hit_count", 0))
    total_identified = sum(db_counts.values())

    # Deduplication
    try:
        dedup_log = load_dedup_log()
        duplicates_removed = len(dedup_log)
    except FileNotFoundError:
        duplicates_removed = 0

    records_after_dedup = total_identified - duplicates_removed

    # Screening
    screening_log = load_screening_log()

    # Title/abstract stage
    ta_rows = [r for r in screening_log if r.get("stage") == "title_abstract"]
    ta_screened = len(ta_rows)
    ta_excluded = len([r for r in ta_rows if r.get("decision") == "exclude"])
    ta_included = len([r for r in ta_rows if r.get("decision") == "include"])

    # Exclusion reasons at title/abstract
    ta_exclusion_reasons: dict[str, int] = {}
    for r in ta_rows:
        if r.get("decision") == "exclude":
            reason = r.get("exclusion_reason", "not specified")
            ta_exclusion_reasons[reason] = ta_exclusion_reasons.get(reason, 0) + 1

    # Full-text stage
    ft_rows = [r for r in screening_log if r.get("stage") == "full_text"]
    ft_assessed = len(ft_rows)
    ft_excluded = len([r for r in ft_rows if r.get("decision") == "exclude"])
    ft_included = len([r for r in ft_rows if r.get("decision") == "include"])

    # Exclusion reasons at full-text
    ft_exclusion_reasons: dict[str, int] = {}
    for r in ft_rows:
        if r.get("decision") == "exclude":
            reason = r.get("exclusion_reason", "not specified")
            ft_exclusion_reasons[reason] = ft_exclusion_reasons.get(reason, 0) + 1

    return {
        "identification": {
            "databases_searched": db_counts,
            "total_identified": total_identified,
            "duplicates_removed": duplicates_removed,
            "records_after_dedup": records_after_dedup,
        },
        "screening": {
            "title_abstract": {
                "screened": ta_screened,
                "excluded": ta_excluded,
                "included": ta_included,
                "exclusion_reasons": ta_exclusion_reasons,
            },
            "full_text": {
                "assessed": ft_assessed,
                "excluded": ft_excluded,
                "included": ft_included,
                "exclusion_reasons": ft_exclusion_reasons,
            },
        },
        "included_in_synthesis": ft_included,
    }
