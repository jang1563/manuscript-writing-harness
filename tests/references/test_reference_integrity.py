#!/usr/bin/env python3
"""Tests for bibliography integrity and citation-graph synchronization."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from reference_graph_common import all_display_claim_ids, load_bibliography_entries, sync_citation_graph
from reference_integrity import build_reference_report, render_reference_markdown, write_reference_outputs


def test_citation_graph_sync_covers_all_display_claims() -> None:
    graph = sync_citation_graph(write=False)
    claim_ids = [node["id"] for node in graph["claim_nodes"]]
    assert sorted(claim_ids) == sorted(all_display_claim_ids())


def test_bibliography_parser_finds_real_reference_entries() -> None:
    entries = load_bibliography_entries()
    keys = [entry["key"] for entry in entries]
    assert "loveEtAl2014DESeq2" in keys
    assert "davisGoadrich2006PRROC" in keys


def test_reference_report_is_not_blocked() -> None:
    report = build_reference_report(sync_graph=False)
    assert report["readiness"] in {"provisional", "ready"}
    assert report["blocking_issues"] == []
    assert report["bibliography"]["entry_count"] >= 1
    assert report["bibliography_source"]["status"] == "ready"
    assert report["bibliography_source"]["manuscript_scope_status"] == "unconfirmed"
    assert report["bibliography_scope_gate"]["status"] == "blocked"
    assert report["citation_graph"]["claim_count"] == len(all_display_claim_ids())
    assert report["bibliography"]["placeholder_keys"] == []


def test_reference_markdown_mentions_warnings_and_package_paths() -> None:
    markdown = render_reference_markdown(build_reference_report(sync_graph=False))
    assert "# Reference Integrity Audit" in markdown
    assert "## Bibliography Source" in markdown
    assert "## Bibliography Scope Gate" in markdown
    assert "## Warnings" not in markdown or "- " in markdown
    assert "## Package Paths" in markdown
    assert "`references/library.bib`" in markdown
    assert "`references/metadata/bibliography_source.yml`" in markdown


def test_write_reference_outputs_creates_artifacts() -> None:
    outputs = write_reference_outputs(sync_graph=False)
    assert (REPO_ROOT / outputs["report_md"]).exists()
    assert (REPO_ROOT / outputs["report_json"]).exists()
    assert (REPO_ROOT / outputs["manifest"]).exists()


def test_cli_check_reference_integrity_exits_zero_for_provisional() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_reference_integrity.py",
            "--write",
            "--sync-graph",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Reference Integrity Audit" in result.stdout
    payload = json.loads((REPO_ROOT / "references/reports/reference_audit.json").read_text(encoding="utf-8"))
    assert payload["readiness"] in {"provisional", "ready"}


def test_cli_check_reference_integrity_can_require_confirmed_manuscript_bibliography() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_reference_integrity.py",
            "--json",
            "--require-confirmed-manuscript-bibliography",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["report"]["bibliography_scope_gate"]["status"] == "blocked"
