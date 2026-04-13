#!/usr/bin/env python3
"""Integration tests for the review CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
REVIEW_CLI = SCRIPTS_DIR / "review_cli.py"


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run review_cli.py with the given arguments."""
    cmd = [sys.executable, str(REVIEW_CLI)] + list(args)
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
        env={**__import__("os").environ, "PYTHONPATH": str(SCRIPTS_DIR)},
    )


class TestCLIHelp:
    def test_help_exits_zero(self):
        result = _run_cli("--help", check=False)
        assert result.returncode == 0
        assert "review" in result.stdout.lower()

    def test_no_command_exits_zero(self):
        result = _run_cli(check=False)
        assert result.returncode == 0


class TestCLIDemo:
    """Run the demo and verify outputs. This is the primary integration test."""

    @pytest.fixture(autouse=True)
    def run_demo_once(self):
        """Run the demo once before all tests in this class."""
        result = _run_cli("demo", check=False)
        self.demo_result = result

    def test_demo_exits_zero(self):
        assert self.demo_result.returncode == 0, self.demo_result.stderr

    def test_demo_creates_protocol(self):
        assert (REPO_ROOT / "review/protocol/protocol.yml").exists()

    def test_demo_creates_queries(self):
        queries = list((REPO_ROOT / "review/queries").glob("query_0*.yml"))
        assert len(queries) >= 2

    def test_demo_creates_screening_log(self):
        assert (REPO_ROOT / "review/screening/screening_log.csv").exists()

    def test_demo_creates_extraction_table(self):
        assert (REPO_ROOT / "review/extraction/extraction_table.csv").exists()

    def test_demo_creates_bias_assessments(self):
        assert (REPO_ROOT / "review/bias/bias_assessments.csv").exists()

    def test_demo_creates_prisma_counts(self):
        assert (REPO_ROOT / "review/prisma/prisma_counts.yml").exists()

    def test_demo_creates_exclusion_summary(self):
        assert (REPO_ROOT / "review/prisma/exclusion_summary.csv").exists()

    def test_demo_creates_evidence_table(self):
        assert (REPO_ROOT / "review/prisma/evidence_table.csv").exists()


class TestCLIPostDemo:
    """Tests that depend on demo artifacts existing."""

    @pytest.fixture(autouse=True)
    def ensure_demo(self):
        """Ensure demo has been run."""
        if not (REPO_ROOT / "review/prisma/prisma_counts.yml").exists():
            _run_cli("demo")

    def test_status_exits_zero(self):
        result = _run_cli("status", check=False)
        assert result.returncode == 0
        assert "Protocol" in result.stdout

    def test_validate_exits_zero(self):
        result = _run_cli("validate", check=False)
        assert result.returncode == 0

    def test_prisma_regenerate(self):
        """PRISMA counts should be reproducible."""
        sys.path.insert(0, str(SCRIPTS_DIR))
        from review_common import load_yaml, REVIEW_ROOT
        counts_path = REVIEW_ROOT / "prisma" / "prisma_counts.yml"
        counts_before = load_yaml(counts_path)

        _run_cli("prisma")

        counts_after = load_yaml(counts_path)
        assert counts_before == counts_after
