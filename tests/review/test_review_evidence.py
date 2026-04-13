#!/usr/bin/env python3
"""Tests for review evidence summary generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from review_evidence import build_evidence_report, render_evidence_markdown, write_evidence_outputs


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "review_cli.py"), *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SCRIPTS_DIR)},
    )


def test_evidence_report_is_ready_for_demo_dataset() -> None:
    report = build_evidence_report()
    assert report["review_id"] == "sr_demo_001"
    assert report["readiness"] == "ready"
    assert report["blocking_issues"] == []
    assert report["extraction"]["included_studies"] == report["prisma"]["included_in_synthesis"]
    assert "PubMed" in report["queries"]["databases"]
    assert "Europe PMC" in report["queries"]["databases"]
    assert report["bias"]["assessed_studies"] == report["extraction"]["included_studies"]


def test_evidence_markdown_mentions_core_sections() -> None:
    markdown = render_evidence_markdown(build_evidence_report())
    assert "# Review Evidence Summary" in markdown
    assert "## Screening" in markdown
    assert "## Extraction" in markdown
    assert "## Risk Of Bias" in markdown
    assert "`review/protocol/protocol.yml`" in markdown


def test_write_evidence_outputs_creates_report_and_manifest() -> None:
    outputs = write_evidence_outputs()
    report_md = REPO_ROOT / outputs["report_md"]
    report_json = REPO_ROOT / outputs["report_json"]
    manifest = REPO_ROOT / outputs["manifest"]
    assert report_md.exists()
    assert report_json.exists()
    assert manifest.exists()
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["readiness"] == "ready"


def test_cli_evidence_generates_outputs() -> None:
    result = _run_cli("evidence")
    assert "Evidence outputs generated:" in result.stdout
    assert (REPO_ROOT / "review/reports/evidence_summary.md").exists()
    assert (REPO_ROOT / "review/manifests/review_evidence_package.json").exists()
