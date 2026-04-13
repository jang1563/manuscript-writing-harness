#!/usr/bin/env python3
"""Tests for Phase 4 review enhancements: NBIB/RIS parsers, fuzzy dedup,
semantic validation, and robvis export."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from review_common import load_csv, write_csv
from review_retrieve import (
    _normalize_nbib,
    _normalize_ris,
    _title_similarity,
    deduplicate,
    normalize_records,
)


# ---------------------------------------------------------------------------
# NBIB parser tests
# ---------------------------------------------------------------------------


SAMPLE_NBIB = """\
PMID- 12345678
OWN - NLM
DP  - 2021 Mar 15
TI  - A study of cancer biomarkers in solid tumours.
AB  - Background: This study investigates X. Methods: We did Y. Results:
      We found Z. Conclusion: X works.
AU  - Smith J
AU  - Lee K
AID - 10.1038/s41586-021-0001-2 [doi]
AID - PMC1234567 [pmc]
JT  - Nature

PMID- 12345679
OWN - NLM
DP  - 2022 Jul
TI  - A second study.
AU  - Park Y
AID - 10.1038/s41586-022-0002-3 [doi]
"""


class TestNbibParser:
    def test_parse_count(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = _normalize_nbib(nbib, "PubMed")
        assert len(records) == 2

    def test_parse_pmid_doi(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = _normalize_nbib(nbib, "PubMed")
        assert records[0]["pmid"] == "12345678"
        assert records[0]["doi"] == "10.1038/s41586-021-0001-2"
        assert records[0]["record_id"] == "PMID12345678"

    def test_parse_authors_joined(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = _normalize_nbib(nbib, "PubMed")
        assert "Smith J" in records[0]["authors"]
        assert "Lee K" in records[0]["authors"]

    def test_parse_year_extracted(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = _normalize_nbib(nbib, "PubMed")
        assert records[0]["year"] == "2021"
        assert records[1]["year"] == "2022"

    def test_continuation_lines_joined(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = _normalize_nbib(nbib, "PubMed")
        # Abstract has continuation lines
        assert "found Z" in records[0]["abstract"]

    def test_normalize_records_dispatches_to_nbib(self, tmp_path):
        nbib = tmp_path / "test.nbib"
        nbib.write_text(SAMPLE_NBIB)
        records = normalize_records(nbib, "PubMed")
        assert len(records) == 2
        assert records[0]["source_db"] == "PubMed"


# ---------------------------------------------------------------------------
# RIS parser tests
# ---------------------------------------------------------------------------


SAMPLE_RIS = """\
TY  - JOUR
T1  - First study on TF-X inhibition
AU  - Garcia M
AU  - Chen L
PY  - 2020
DO  - 10.1016/j.cell.2020.05.001
JO  - Cell
AB  - Background: TF-X is interesting.
ER  -

TY  - JOUR
T1  - Second paper about something
AU  - Kim S
PY  - 2021
DO  - 10.1038/nature.2021.001
JO  - Nature
ER  -
"""


class TestRisParser:
    def test_parse_count(self, tmp_path):
        ris = tmp_path / "test.ris"
        ris.write_text(SAMPLE_RIS)
        records = _normalize_ris(ris, "Scopus")
        assert len(records) == 2

    def test_parse_doi_year(self, tmp_path):
        ris = tmp_path / "test.ris"
        ris.write_text(SAMPLE_RIS)
        records = _normalize_ris(ris, "Scopus")
        assert records[0]["doi"] == "10.1016/j.cell.2020.05.001"
        assert records[0]["year"] == "2020"

    def test_authors_collected(self, tmp_path):
        ris = tmp_path / "test.ris"
        ris.write_text(SAMPLE_RIS)
        records = _normalize_ris(ris, "Scopus")
        assert "Garcia M" in records[0]["authors"]
        assert "Chen L" in records[0]["authors"]

    def test_record_id_uses_doi_when_no_pmid(self, tmp_path):
        ris = tmp_path / "test.ris"
        ris.write_text(SAMPLE_RIS)
        records = _normalize_ris(ris, "Scopus")
        assert records[0]["record_id"] == "DOI10.1016/j.cell.2020.05.001"

    def test_normalize_records_dispatches_to_ris(self, tmp_path):
        ris = tmp_path / "test.ris"
        ris.write_text(SAMPLE_RIS)
        records = normalize_records(ris, "Scopus")
        assert len(records) == 2


def test_unsupported_format_message(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("nothing")
    with pytest.raises(NotImplementedError) as exc:
        normalize_records(bad, "X")
    assert ".csv" in str(exc.value) and ".nbib" in str(exc.value) and ".ris" in str(exc.value)


# ---------------------------------------------------------------------------
# Fuzzy deduplication tests
# ---------------------------------------------------------------------------


class TestFuzzyDedup:
    def test_title_similarity_identical(self):
        assert _title_similarity("Hello world", "Hello world") == 1.0

    def test_title_similarity_normalization(self):
        # Punctuation differences should not matter much
        sim = _title_similarity(
            "A study of cancer: a review.",
            "A study of cancer  a review",
        )
        assert sim > 0.95

    def test_title_similarity_different(self):
        assert _title_similarity("apple pie recipe", "rocket science") < 0.5

    def test_fuzzy_catches_punctuation_diff(self):
        records = [
            {"record_id": "R1", "doi": "", "pmid": "", "title": "A study of cancer biomarkers."},
            {"record_id": "R2", "doi": "", "pmid": "", "title": "A study of cancer biomarkers"},
        ]
        unique, removed = deduplicate(records, strategy="fuzzy")
        assert len(unique) == 1
        assert len(removed) == 1
        assert removed[0]["duplicate_of"] == "R1"

    def test_exact_strategy_misses_fuzzy_dup(self):
        # Different punctuation = different exact title
        records = [
            {"record_id": "R1", "doi": "", "pmid": "", "title": "A study of cancer biomarkers."},
            {"record_id": "R2", "doi": "", "pmid": "", "title": "A study of cancer biomarkers,"},
        ]
        unique, _ = deduplicate(records, strategy="exact")
        assert len(unique) == 2  # exact would NOT catch this

    def test_fuzzy_does_not_overmatch(self):
        records = [
            {"record_id": "R1", "doi": "", "pmid": "", "title": "TF-X inhibition in NSCLC"},
            {"record_id": "R2", "doi": "", "pmid": "", "title": "TF-Y inhibition in melanoma"},
        ]
        unique, _ = deduplicate(records, strategy="fuzzy")
        assert len(unique) == 2

    def test_threshold_controls_strictness(self):
        records = [
            {"record_id": "R1", "doi": "", "pmid": "", "title": "First paper on A"},
            {"record_id": "R2", "doi": "", "pmid": "", "title": "First paper on B"},
        ]
        # High threshold: not duplicates
        unique_strict, _ = deduplicate(records, strategy="fuzzy", similarity_threshold=0.99)
        assert len(unique_strict) == 2
        # Lenient threshold: catches them
        unique_loose, _ = deduplicate(records, strategy="fuzzy", similarity_threshold=0.7)
        assert len(unique_loose) == 1

    def test_pmid_match_in_dedup(self):
        records = [
            {"record_id": "R1", "doi": "", "pmid": "12345", "title": "Title A"},
            {"record_id": "R2", "doi": "", "pmid": "12345", "title": "Title B"},
        ]
        unique, removed = deduplicate(records, strategy="exact")
        assert len(unique) == 1
        assert removed[0]["duplicate_of"] == "R1"

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError):
            deduplicate([], strategy="magic")


# ---------------------------------------------------------------------------
# Semantic validation: extraction
# ---------------------------------------------------------------------------


def _make_extraction_row(**overrides):
    base = {
        "record_id": "R001",
        "study_design": "RCT",
        "population": "Adults",
        "intervention": "TF-X",
        "comparator": "placebo",
        "sample_size": "100",
        "outcome_name": "ORR",
        "outcome_measure": "odds ratio",
        "outcome_timing": "12 months",
        "effect_value": "1.5",
        "ci_lower": "1.0",
        "ci_upper": "2.0",
        "p_value": "0.03",
        "extractor": "A",
        "timestamp": "2026-04-12T00:00:00",
        "subgroup_notes": "",
        "heterogeneity_flags": "",
    }
    base.update(overrides)
    return base


def _write_extraction_csv(tmp_path, rows):
    from review_common import EXTRACTION_OPTIONAL_COLUMNS, EXTRACTION_REQUIRED_COLUMNS
    path = tmp_path / "extraction.csv"
    write_csv(path, rows, EXTRACTION_REQUIRED_COLUMNS + EXTRACTION_OPTIONAL_COLUMNS)
    return path


class TestExtractionSemantic:
    def test_valid_row_no_errors(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row()])
        errors = validate_extraction(table_path=path, semantic=True)
        assert errors == []

    def test_negative_sample_size(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row(sample_size="-5")])
        errors = validate_extraction(table_path=path, semantic=True)
        assert any("sample_size" in e for e in errors)

    def test_p_value_out_of_range(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row(p_value="1.5")])
        errors = validate_extraction(table_path=path, semantic=True)
        assert any("p_value" in e for e in errors)

    def test_ci_inverted(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(
            tmp_path, [_make_extraction_row(ci_lower="2.0", ci_upper="1.0")]
        )
        errors = validate_extraction(table_path=path, semantic=True)
        assert any("ci_lower" in e and "ci_upper" in e for e in errors)

    def test_unknown_study_design(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row(study_design="moonshot")])
        errors = validate_extraction(table_path=path, semantic=True)
        assert any("study_design" in e for e in errors)

    def test_unknown_outcome_measure(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row(outcome_measure="vibes")])
        errors = validate_extraction(table_path=path, semantic=True)
        assert any("outcome_measure" in e for e in errors)

    def test_semantic_off_skips_type_checks(self, tmp_path):
        from review_extract import validate_extraction
        path = _write_extraction_csv(tmp_path, [_make_extraction_row(p_value="999")])
        errors = validate_extraction(table_path=path, semantic=False)
        # No semantic check, so no error from out-of-range p-value
        assert not any("must be in [0, 1]" in e for e in errors)


# ---------------------------------------------------------------------------
# Semantic validation: bias
# ---------------------------------------------------------------------------


def _make_bias_row(**overrides):
    base = {
        "record_id": "R001",
        "tool": "rob2",
        "overall_judgment": "low",
        "assessor": "A",
        "ai_assisted": "false",
        "timestamp": "2026-04-12",
        "D1_randomisation": "low",
        "D2_deviations": "low",
        "D3_missing_data": "low",
        "D4_measurement": "low",
        "D5_selection_reporting": "low",
    }
    base.update(overrides)
    return base


def _write_bias_csv(tmp_path, rows):
    from review_common import BIAS_REQUIRED_COLUMNS, ROB2_DOMAINS
    path = tmp_path / "bias.csv"
    write_csv(path, rows, BIAS_REQUIRED_COLUMNS + list(ROB2_DOMAINS))
    return path


class TestBiasSemantic:
    def test_valid_row_no_errors(self, tmp_path):
        from review_bias import validate_bias
        path = _write_bias_csv(tmp_path, [_make_bias_row()])
        errors = validate_bias(table_path=path, semantic=True)
        assert errors == []

    def test_unknown_tool(self, tmp_path):
        from review_bias import validate_bias
        path = _write_bias_csv(tmp_path, [_make_bias_row(tool="vibe_check")])
        errors = validate_bias(table_path=path, semantic=True)
        assert any("tool" in e for e in errors)

    def test_unknown_overall_judgment(self, tmp_path):
        from review_bias import validate_bias
        path = _write_bias_csv(tmp_path, [_make_bias_row(overall_judgment="meh")])
        errors = validate_bias(table_path=path, semantic=True)
        assert any("overall_judgment" in e for e in errors)

    def test_invalid_domain_judgment(self, tmp_path):
        from review_bias import validate_bias
        path = _write_bias_csv(tmp_path, [_make_bias_row(D1_randomisation="probably_fine")])
        errors = validate_bias(table_path=path, semantic=True)
        assert any("D1_randomisation" in e for e in errors)

    def test_invalid_ai_assisted(self, tmp_path):
        from review_bias import validate_bias
        path = _write_bias_csv(tmp_path, [_make_bias_row(ai_assisted="yes")])
        errors = validate_bias(table_path=path, semantic=True)
        assert any("ai_assisted" in e for e in errors)


# ---------------------------------------------------------------------------
# robvis export tests
# ---------------------------------------------------------------------------


class TestRobvisExport:
    def test_export_creates_robvis_csv(self, tmp_path):
        from review_bias import export_robvis_data
        in_path = _write_bias_csv(tmp_path, [_make_bias_row(), _make_bias_row(record_id="R002")])
        out_path = tmp_path / "robvis.csv"
        export_robvis_data(table_path=in_path, output_path=out_path)
        assert out_path.exists()

    def test_export_columns(self, tmp_path):
        from review_bias import export_robvis_data
        in_path = _write_bias_csv(tmp_path, [_make_bias_row()])
        out_path = tmp_path / "robvis.csv"
        export_robvis_data(table_path=in_path, output_path=out_path)
        rows = load_csv(out_path)
        assert "Study" in rows[0]
        assert "D1" in rows[0]
        assert "D5" in rows[0]
        assert "Overall" in rows[0]
        assert "Weight" in rows[0]

    def test_export_translates_judgments(self, tmp_path):
        from review_bias import export_robvis_data
        rows_in = [
            _make_bias_row(D1_randomisation="some_concerns", overall_judgment="high"),
        ]
        in_path = _write_bias_csv(tmp_path, rows_in)
        out_path = tmp_path / "robvis.csv"
        export_robvis_data(table_path=in_path, output_path=out_path)
        rows_out = load_csv(out_path)
        assert rows_out[0]["D1"] == "Some concerns"
        assert rows_out[0]["Overall"] == "High"

    def test_export_handles_empty_input(self, tmp_path):
        from review_bias import export_robvis_data
        in_path = tmp_path / "empty_bias.csv"
        from review_common import BIAS_REQUIRED_COLUMNS, ROB2_DOMAINS
        write_csv(in_path, [], BIAS_REQUIRED_COLUMNS + list(ROB2_DOMAINS))
        out_path = tmp_path / "robvis.csv"
        result = export_robvis_data(table_path=in_path, output_path=out_path)
        assert result.exists()
