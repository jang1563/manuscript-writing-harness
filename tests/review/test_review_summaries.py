#!/usr/bin/env python3
"""Tests for review summary helpers used by the status and evidence surfaces."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from review_bias import bias_summary
from review_common import BIAS_REQUIRED_COLUMNS, ROB2_DOMAINS, ROBINS_I_DOMAINS, write_csv
from review_screen import ALL_SCREENING_COLUMNS, screening_summary


def _make_screening_row(**overrides: str) -> dict[str, str]:
    row = {column: "" for column in ALL_SCREENING_COLUMNS}
    row.update(
        {
            "record_id": "R001",
            "pmid": "12345",
            "doi": "10.1/example",
            "title": "Example study",
            "authors": "Smith",
            "year": "2025",
            "abstract": "Example abstract",
            "source_db": "PubMed",
            "stage": "title_abstract",
            "decision": "pending",
            "reviewer": "reviewer_1",
            "timestamp": "2026-04-16T12:00:00",
        }
    )
    row.update(overrides)
    return row


def _make_bias_row(tool: str = "rob2", **overrides: str) -> dict[str, str]:
    row = {column: "" for column in BIAS_REQUIRED_COLUMNS + ROB2_DOMAINS + ROBINS_I_DOMAINS}
    row.update(
        {
            "record_id": "R001",
            "tool": tool,
            "overall_judgment": "",
            "assessor": "reviewer_1",
            "ai_assisted": "false",
            "timestamp": "2026-04-16T12:00:00",
        }
    )
    row.update(overrides)
    return row


def test_screening_summary_counts_stage_and_decision(tmp_path: Path) -> None:
    log_path = tmp_path / "screening_log.csv"
    rows = [
        _make_screening_row(record_id="R001", stage="title_abstract", decision="include"),
        _make_screening_row(record_id="R002", stage="title_abstract", decision="exclude"),
        _make_screening_row(record_id="R003", stage="full_text", decision="include"),
        _make_screening_row(record_id="R004", stage="full_text", decision="pending"),
    ]
    write_csv(log_path, rows, ALL_SCREENING_COLUMNS)

    assert screening_summary(log_path) == {
        "title_abstract": {"include": 1, "exclude": 1},
        "full_text": {"include": 1, "pending": 1},
    }


def test_screening_summary_coerces_blank_values_to_unknown(tmp_path: Path) -> None:
    log_path = tmp_path / "screening_log.csv"
    rows = [
        _make_screening_row(record_id="R001", stage="", decision=""),
        _make_screening_row(record_id="R002", stage="  ", decision="exclude"),
        _make_screening_row(record_id="R003", stage="title_abstract", decision=" "),
    ]
    write_csv(log_path, rows, ALL_SCREENING_COLUMNS)

    assert screening_summary(log_path) == {
        "unknown": {"unknown": 1, "exclude": 1},
        "title_abstract": {"unknown": 1},
    }


def test_bias_summary_counts_overall_and_domain_judgments(tmp_path: Path) -> None:
    table_path = tmp_path / "bias_assessments.csv"
    rows = [
        _make_bias_row(
            record_id="R001",
            tool="rob2",
            overall_judgment="low",
            **{domain: "low" for domain in ROB2_DOMAINS},
        ),
        _make_bias_row(
            record_id="R002",
            tool="rob2",
            overall_judgment="high",
            **{domain: "high" for domain in ROB2_DOMAINS},
        ),
        _make_bias_row(
            record_id="R003",
            tool="robins_i",
            overall_judgment=" ",
            **(
                {domain: " " for domain in ROBINS_I_DOMAINS}
                | {"D1_confounding": "moderate"}
            ),
        ),
    ]
    write_csv(table_path, rows, BIAS_REQUIRED_COLUMNS + ROB2_DOMAINS + ROBINS_I_DOMAINS)

    summary = bias_summary(table_path)

    assert summary["overall"] == {"low": 1, "high": 1, "unassessed": 1}
    assert summary["domains"]["D1_randomisation"] == {"low": 1, "high": 1}
    assert summary["domains"]["D1_confounding"] == {"moderate": 1}
    assert summary["domains"]["D2_selection"] == {"unassessed": 1}
