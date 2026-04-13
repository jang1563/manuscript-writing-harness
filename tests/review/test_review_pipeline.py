#!/usr/bin/env python3
"""Unit tests for the systematic review pipeline stages."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from review_common import (
    SCREENING_REQUIRED_COLUMNS,
    load_csv,
    load_yaml,
    validate_csv_columns,
    validate_yaml_fields,
    write_csv,
    write_yaml,
)
from review_retrieve import deduplicate, normalize_records, write_normalized, write_screening_input
from review_screen import ALL_SCREENING_COLUMNS, init_screening_log


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_records():
    """Return a list of normalized records with known duplicates."""
    return [
        {"record_id": "R001", "pmid": "1001", "doi": "10.1/a", "title": "Alpha study of X", "authors": "Smith", "year": "2020", "abstract": "...", "source_db": "PubMed"},
        {"record_id": "R002", "pmid": "1002", "doi": "10.1/b", "title": "Beta trial results", "authors": "Lee", "year": "2021", "abstract": "...", "source_db": "PubMed"},
        {"record_id": "R003", "pmid": "1003", "doi": "10.1/a", "title": "Alpha study of X", "authors": "Smith", "year": "2020", "abstract": "...", "source_db": "Europe PMC"},  # duplicate by DOI
        {"record_id": "R004", "pmid": "1004", "doi": "10.1/c", "title": "Beta trial results", "authors": "Lee", "year": "2021", "abstract": "...", "source_db": "Europe PMC"},  # duplicate by title
        {"record_id": "R005", "pmid": "1005", "doi": "10.1/d", "title": "Gamma analysis", "authors": "Park", "year": "2022", "abstract": "...", "source_db": "Europe PMC"},
    ]


@pytest.fixture
def raw_csv(tmp_path, sample_records):
    """Write sample records to a CSV and return the path."""
    path = tmp_path / "raw.csv"
    fieldnames = ["record_id", "pmid", "doi", "title", "authors", "year", "abstract", "source_db"]
    write_csv(path, sample_records, fieldnames)
    return path


# ---------------------------------------------------------------------------
# Tests: normalize_records
# ---------------------------------------------------------------------------


def test_normalize_csv(raw_csv):
    records = normalize_records(raw_csv, "TestDB")
    assert len(records) == 5
    assert all(r["source_db"] == "TestDB" for r in records)


def test_normalize_unsupported_format(tmp_path):
    # NBIB and RIS are now supported; use a truly unsupported format
    path = tmp_path / "export.xml"
    path.write_text("<dummy/>")
    with pytest.raises(NotImplementedError):
        normalize_records(path, "PubMed")


# ---------------------------------------------------------------------------
# Tests: deduplicate
# ---------------------------------------------------------------------------


def test_deduplicate_removes_known_duplicates(sample_records):
    unique, removed = deduplicate(sample_records)
    assert len(unique) == 3  # R001, R002, R005
    assert len(removed) == 2  # R003 (DOI dup), R004 (title dup)


def test_deduplicate_log_has_duplicate_of(sample_records):
    _, removed = deduplicate(sample_records)
    for entry in removed:
        assert "duplicate_of" in entry
        assert entry["duplicate_of"] in ("R001", "R002")


def test_deduplicate_empty_input():
    unique, removed = deduplicate([])
    assert unique == []
    assert removed == []


def test_deduplicate_no_duplicates():
    records = [
        {"record_id": "R1", "doi": "10.1/x", "title": "Unique A", "pmid": "", "authors": "", "year": "", "abstract": "", "source_db": ""},
        {"record_id": "R2", "doi": "10.1/y", "title": "Unique B", "pmid": "", "authors": "", "year": "", "abstract": "", "source_db": ""},
    ]
    unique, removed = deduplicate(records)
    assert len(unique) == 2
    assert len(removed) == 0


# ---------------------------------------------------------------------------
# Tests: screening log
# ---------------------------------------------------------------------------


def test_init_screening_log(tmp_path, sample_records):
    # Write screening input
    input_path = tmp_path / "screening_input.csv"
    fieldnames = ["record_id", "pmid", "doi", "title", "authors", "year", "abstract", "source_db"]
    write_csv(input_path, sample_records[:3], fieldnames)

    output_path = tmp_path / "screening_log.csv"
    init_screening_log(input_path=input_path, output_path=output_path)

    rows = load_csv(output_path)
    assert len(rows) == 3
    assert all(r["stage"] == "title_abstract" for r in rows)
    assert all(r["decision"] == "pending" for r in rows)


# ---------------------------------------------------------------------------
# Tests: validation helpers
# ---------------------------------------------------------------------------


def test_validate_yaml_fields_pass():
    data = {"a": 1, "b": "hello", "c": [1, 2]}
    errors = validate_yaml_fields(data, {"a", "b", "c"}, "test")
    assert errors == []


def test_validate_yaml_fields_missing():
    data = {"a": 1}
    errors = validate_yaml_fields(data, {"a", "b"}, "test")
    assert len(errors) == 1
    assert "missing required field 'b'" in errors[0]


def test_validate_yaml_fields_empty():
    data = {"a": 1, "b": ""}
    errors = validate_yaml_fields(data, {"a", "b"}, "test")
    assert len(errors) == 1
    assert "field 'b' is empty" in errors[0]


def test_validate_csv_columns_pass():
    rows = [{"a": "1", "b": "2"}]
    errors = validate_csv_columns(rows, ["a", "b"], "test")
    assert errors == []


def test_validate_csv_columns_missing():
    rows = [{"a": "1"}]
    errors = validate_csv_columns(rows, ["a", "b"], "test")
    assert len(errors) == 1


def test_validate_csv_columns_empty():
    errors = validate_csv_columns([], ["a"], "test")
    assert len(errors) == 1
    assert "no rows found" in errors[0]


# ---------------------------------------------------------------------------
# Tests: PRISMA count computation
# ---------------------------------------------------------------------------


def test_prisma_counts_from_artifacts(tmp_path, monkeypatch):
    """Test that compute_prisma_counts derives correct counts."""
    import review_common

    # Set up directory structure in tmp
    queries_dir = tmp_path / "queries"
    queries_dir.mkdir()
    retrieval_dir = tmp_path / "retrieval" / "dedup"
    retrieval_dir.mkdir(parents=True)
    screening_dir = tmp_path / "screening"
    screening_dir.mkdir()

    # Monkeypatch paths
    monkeypatch.setattr(review_common, "QUERIES_DIR", queries_dir)
    monkeypatch.setattr(review_common, "RETRIEVAL_DIR", tmp_path / "retrieval")
    monkeypatch.setattr(review_common, "SCREENING_DIR", screening_dir)

    # Write query files
    write_yaml(queries_dir / "query_01.yml", {
        "query_id": "q1", "database": "PubMed", "hit_count": 50,
    })
    write_yaml(queries_dir / "query_02.yml", {
        "query_id": "q2", "database": "Embase", "hit_count": 30,
    })

    # Write dedup log (10 duplicates)
    dedup_rows = [{"record_id": f"D{i}", "duplicate_of": "R001"} for i in range(10)]
    write_csv(retrieval_dir / "dedup_log.csv", dedup_rows, ["record_id", "duplicate_of"])

    # Write screening log
    screening_rows = []
    # 50 title/abstract screened: 20 include, 30 exclude
    for i in range(20):
        screening_rows.append({
            "record_id": f"R{i:03d}", "stage": "title_abstract",
            "decision": "include", "exclusion_reason": "",
        })
    for i in range(20, 50):
        screening_rows.append({
            "record_id": f"R{i:03d}", "stage": "title_abstract",
            "decision": "exclude", "exclusion_reason": "wrong population",
        })
    # 20 full-text: 15 include, 5 exclude
    for i in range(15):
        screening_rows.append({
            "record_id": f"R{i:03d}", "stage": "full_text",
            "decision": "include", "exclusion_reason": "",
        })
    for i in range(15, 20):
        screening_rows.append({
            "record_id": f"R{i:03d}", "stage": "full_text",
            "decision": "exclude", "exclusion_reason": "insufficient data",
        })

    write_csv(
        screening_dir / "screening_log.csv",
        screening_rows,
        ["record_id", "stage", "decision", "exclusion_reason"],
    )

    counts = review_common.compute_prisma_counts()

    assert counts["identification"]["total_identified"] == 80
    assert counts["identification"]["duplicates_removed"] == 10
    assert counts["identification"]["records_after_dedup"] == 70
    assert counts["screening"]["title_abstract"]["screened"] == 50
    assert counts["screening"]["title_abstract"]["excluded"] == 30
    assert counts["screening"]["title_abstract"]["included"] == 20
    assert counts["screening"]["full_text"]["assessed"] == 20
    assert counts["screening"]["full_text"]["excluded"] == 5
    assert counts["screening"]["full_text"]["included"] == 15
    assert counts["included_in_synthesis"] == 15


def test_prisma_counts_reproducible(tmp_path, monkeypatch):
    """Running compute_prisma_counts twice on the same data yields identical results."""
    import review_common

    queries_dir = tmp_path / "queries"
    queries_dir.mkdir()
    screening_dir = tmp_path / "screening"
    screening_dir.mkdir()

    monkeypatch.setattr(review_common, "QUERIES_DIR", queries_dir)
    monkeypatch.setattr(review_common, "RETRIEVAL_DIR", tmp_path / "retrieval")
    monkeypatch.setattr(review_common, "SCREENING_DIR", screening_dir)

    write_yaml(queries_dir / "query_01.yml", {"query_id": "q1", "database": "DB", "hit_count": 10})

    rows = [
        {"record_id": "R1", "stage": "title_abstract", "decision": "include", "exclusion_reason": ""},
        {"record_id": "R2", "stage": "title_abstract", "decision": "exclude", "exclusion_reason": "wrong"},
    ]
    write_csv(screening_dir / "screening_log.csv", rows, ["record_id", "stage", "decision", "exclusion_reason"])

    counts1 = review_common.compute_prisma_counts()
    counts2 = review_common.compute_prisma_counts()
    assert counts1 == counts2
