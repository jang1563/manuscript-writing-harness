#!/usr/bin/env python3
"""Tests for the references and citation pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from references_common import (
    LintMessage,
    cross_reference_check,
    extract_cite_keys_from_manuscript,
    lint_entries,
    parse_bibtex,
)


# ---------------------------------------------------------------------------
# BibTeX parser tests
# ---------------------------------------------------------------------------


SAMPLE_BIB = """\
@article{smith2020cancer,
  author = {Smith, John and Lee, Jane},
  title = {A study of cancer biomarkers},
  journal = {Nature},
  year = {2020},
  volume = {580},
  pages = {100--105},
  doi = {10.1038/s41586-020-0001-1}
}

@book{jones2019methods,
  author = {Jones, Alice},
  title = {Statistical Methods in Biology},
  publisher = {Academic Press},
  year = {2019},
  isbn = {978-0-12-345678-9}
}

@misc{harnessPlaceholderReference2026,
  title = {Placeholder Reference Entry for Initial MyST Validation},
  author = {{Manuscript Harness Team}},
  year = {2026},
  note = {Replace this entry by wiring Zotero Better BibTeX export}
}
"""


class TestBibtexParser:
    def test_parse_count(self):
        entries = parse_bibtex(SAMPLE_BIB)
        assert len(entries) == 3

    def test_parse_article_fields(self):
        entries = parse_bibtex(SAMPLE_BIB)
        article = next(e for e in entries if e["cite_key"] == "smith2020cancer")
        assert article["entry_type"] == "article"
        assert article["author"] == "Smith, John and Lee, Jane"
        assert article["journal"] == "Nature"
        assert article["year"] == "2020"
        assert article["doi"] == "10.1038/s41586-020-0001-1"

    def test_parse_book_fields(self):
        entries = parse_bibtex(SAMPLE_BIB)
        book = next(e for e in entries if e["cite_key"] == "jones2019methods")
        assert book["entry_type"] == "book"
        assert book["publisher"] == "Academic Press"

    def test_parse_double_braced_author(self):
        entries = parse_bibtex(SAMPLE_BIB)
        misc = next(e for e in entries if e["cite_key"] == "harnessPlaceholderReference2026")
        assert "Manuscript Harness Team" in misc["author"]

    def test_parse_empty_string(self):
        assert parse_bibtex("") == []

    def test_parse_comments_ignored(self):
        bib = "@comment{this should be ignored}\n" + SAMPLE_BIB
        entries = parse_bibtex(bib)
        assert len(entries) == 3

    def test_parse_quoted_values(self):
        bib = '@article{test2021, author = "Doe, John", title = "A test", journal = "Science", year = "2021"}'
        entries = parse_bibtex(bib)
        assert len(entries) == 1
        assert entries[0]["author"] == "Doe, John"

    def test_parse_nested_braces(self):
        bib = '@article{test2021, author = {van {Der} Berg}, title = {The {GSK3} pathway}, journal = {Cell}, year = {2021}}'
        entries = parse_bibtex(bib)
        assert len(entries) == 1
        assert "Der" in entries[0]["author"]
        assert "GSK3" in entries[0]["title"]


# ---------------------------------------------------------------------------
# Lint tests
# ---------------------------------------------------------------------------


class TestLinting:
    def test_no_errors_on_clean_entry(self):
        entries = parse_bibtex(SAMPLE_BIB)
        messages = lint_entries(entries)
        errors = [m for m in messages if m.level == "error"]
        assert len(errors) == 0

    def test_duplicate_keys_detected(self):
        bib = SAMPLE_BIB + "\n@article{smith2020cancer, author={Dup}, title={Dup}, journal={X}, year={2020}}\n"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        dup_errors = [m for m in messages if "duplicate" in m.message]
        assert len(dup_errors) >= 1

    def test_missing_required_field(self):
        bib = "@article{noauthor2020, title={Test}, journal={X}, year={2020}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        errors = [m for m in messages if m.level == "error"]
        assert any("author" in m.message for m in errors)

    def test_missing_doi_warning_for_article(self):
        bib = "@article{nodoi2020, author={A}, title={B}, journal={C}, year={2020}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        warnings = [m for m in messages if m.level == "warning"]
        assert any("DOI" in m.message or "doi" in m.message for m in warnings)

    def test_invalid_doi_format(self):
        bib = "@article{baddoi2020, author={A}, title={B}, journal={C}, year={2020}, doi={not-a-doi}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        warnings = [m for m in messages if "DOI format" in m.message]
        assert len(warnings) == 1

    def test_valid_doi_no_warning(self):
        bib = "@article{gooddoi2020, author={A}, title={B}, journal={C}, year={2020}, doi={10.1038/nature12373}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        doi_warns = [m for m in messages if "DOI" in m.message and m.level == "warning"]
        assert len(doi_warns) == 0

    def test_bad_year(self):
        bib = "@article{badyear, author={A}, title={B}, journal={C}, year={20XX}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        year_warns = [m for m in messages if "year" in m.message.lower()]
        assert len(year_warns) >= 1

    def test_preprint_label_check(self):
        bib = "@article{preprint2023, author={A}, title={B}, journal={bioRxiv}, year={2023}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        preprint_msgs = [m for m in messages if "preprint" in m.message]
        assert len(preprint_msgs) >= 1

    def test_malformed_url(self):
        bib = "@misc{badurl, author={A}, title={B}, year={2020}, url={not a url}}"
        entries = parse_bibtex(bib)
        messages = lint_entries(entries)
        url_warns = [m for m in messages if "URL" in m.message]
        assert len(url_warns) >= 1


# ---------------------------------------------------------------------------
# Cross-reference tests
# ---------------------------------------------------------------------------


class TestCrossReference:
    def test_unresolved_key(self):
        entries = [{"cite_key": "smith2020", "entry_type": "article"}]
        manuscript_keys = {"smith2020", "missing2021"}
        messages = cross_reference_check(entries, manuscript_keys)
        unresolved = [m for m in messages if m.level == "error"]
        assert len(unresolved) == 1
        assert unresolved[0].cite_key == "missing2021"

    def test_uncited_reference(self):
        entries = [
            {"cite_key": "smith2020", "entry_type": "article"},
            {"cite_key": "unused2019", "entry_type": "book"},
        ]
        manuscript_keys = {"smith2020"}
        messages = cross_reference_check(entries, manuscript_keys)
        uncited = [m for m in messages if m.level == "info"]
        assert len(uncited) == 1
        assert uncited[0].cite_key == "unused2019"

    def test_perfect_match(self):
        entries = [{"cite_key": "a", "entry_type": "article"}]
        messages = cross_reference_check(entries, {"a"})
        assert len(messages) == 0


# ---------------------------------------------------------------------------
# Manuscript key extraction tests
# ---------------------------------------------------------------------------


class TestKeyExtraction:
    def test_myst_cite_pattern(self, tmp_path, monkeypatch):
        import references_common
        sections = tmp_path / "sections"
        sections.mkdir()
        (sections / "test.md").write_text(
            "As shown {cite}`smith2020`, and {cite:p}`jones2019,lee2021`."
        )
        monkeypatch.setattr(references_common, "MANUSCRIPT_DIR", tmp_path)
        keys = extract_cite_keys_from_manuscript()
        assert keys == {"smith2020", "jones2019", "lee2021"}

    def test_pandoc_cite_pattern(self, tmp_path, monkeypatch):
        import references_common
        sections = tmp_path / "sections"
        sections.mkdir()
        (sections / "test.md").write_text("Results confirm [@smith2020; @jones2019].")
        monkeypatch.setattr(references_common, "MANUSCRIPT_DIR", tmp_path)
        keys = extract_cite_keys_from_manuscript()
        assert keys == {"smith2020", "jones2019"}

    def test_no_sections_dir(self, tmp_path, monkeypatch):
        import references_common
        monkeypatch.setattr(references_common, "MANUSCRIPT_DIR", tmp_path)
        keys = extract_cite_keys_from_manuscript()
        assert keys == set()


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

REFERENCES_CLI = SCRIPTS_DIR / "references_cli.py"


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(REFERENCES_CLI)] + list(args)
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=check,
        env={**__import__("os").environ, "PYTHONPATH": str(SCRIPTS_DIR)},
    )


class TestCLI:
    def test_help(self):
        result = _run_cli("--help", check=False)
        assert result.returncode == 0

    def test_status(self):
        result = _run_cli("status", check=False)
        assert result.returncode == 0
        assert "Bibliography" in result.stdout

    def test_lint(self):
        result = _run_cli("lint", "--verbose", check=False)
        # May have warnings but should not crash
        assert result.returncode in (0, 1)

    def test_validate(self):
        result = _run_cli("validate", check=False)
        assert result.returncode in (0, 1)
        assert "Library" in result.stdout

    def test_list_styles(self):
        result = _run_cli("list-styles", check=False)
        assert result.returncode == 0
        assert "nature" in result.stdout.lower()

    def test_keys(self):
        result = _run_cli("keys", check=False)
        assert result.returncode == 0
        assert "loveEtAl2014DESeq2" in result.stdout
