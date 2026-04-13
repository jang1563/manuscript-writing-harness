#!/usr/bin/env python3
"""Shared helpers for the references and citation pipeline.

Includes a lightweight BibTeX parser (no external dependencies) and
citation linting logic aligned with the quality bar in
research/04_references_and_identifiers.md.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Paths
REFERENCES_DIR = REPO_ROOT / "references"
LIBRARY_BIB = REFERENCES_DIR / "library.bib"
CSL_DIR = REFERENCES_DIR / "csl"
METADATA_DIR = REFERENCES_DIR / "metadata"
MANUSCRIPT_DIR = REPO_ROOT / "manuscript"

# BibTeX entry types that should normally have a DOI
DOI_EXPECTED_TYPES = {"article", "inproceedings", "incollection", "book", "inbook"}

# Fields that are required for a high-quality entry (by entry type)
REQUIRED_FIELDS: dict[str, set[str]] = {
    "article": {"author", "title", "journal", "year"},
    "book": {"author", "title", "year", "publisher"},
    "incollection": {"author", "title", "booktitle", "year"},
    "inproceedings": {"author", "title", "booktitle", "year"},
    "phdthesis": {"author", "title", "school", "year"},
    "mastersthesis": {"author", "title", "school", "year"},
    "misc": {"author", "title", "year"},
    "techreport": {"author", "title", "institution", "year"},
    "unpublished": {"author", "title", "year"},
}

# Recommended fields (warnings, not errors)
RECOMMENDED_FIELDS: dict[str, set[str]] = {
    "article": {"volume", "pages", "doi"},
    "inproceedings": {"doi"},
    "book": {"isbn"},
}

# Regex for DOI validation
DOI_REGEX = re.compile(r"^10\.\d{4,}/\S+$")

# Regex for URL validation
URL_REGEX = re.compile(r"^https?://\S+$")


# ---------------------------------------------------------------------------
# Lightweight BibTeX parser
# ---------------------------------------------------------------------------

# Matches the start of a BibTeX entry: @type{key,
_ENTRY_START = re.compile(r"@(\w+)\s*\{([^,\s]+)\s*,", re.IGNORECASE)


def parse_bibtex(text: str) -> list[dict[str, Any]]:
    """Parse BibTeX text into a list of entry dicts.

    Each entry has keys: 'entry_type', 'cite_key', and field names
    (lowercased). Values have outer braces/quotes stripped.

    This is intentionally simple -- it handles well-formed BibTeX from
    Zotero/Better BibTeX exports. It does not handle string macros,
    @preamble, or @comment blocks.
    """
    entries: list[dict[str, Any]] = []

    # Find all entry starts
    for match in _ENTRY_START.finditer(text):
        entry_type = match.group(1).lower()
        cite_key = match.group(2)

        if entry_type in ("comment", "preamble", "string"):
            continue

        # Extract the body between { and the matching }
        start = match.end()
        body = _extract_braced_body(text, start)
        if body is None:
            continue

        fields = _parse_fields(body)
        fields["entry_type"] = entry_type
        fields["cite_key"] = cite_key
        entries.append(fields)

    return entries


def _extract_braced_body(text: str, start: int) -> str | None:
    """Extract text up to the matching closing brace, handling nesting."""
    depth = 1
    i = start
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[start : i - 1]


def _parse_fields(body: str) -> dict[str, str]:
    """Parse BibTeX field assignments from the body text."""
    fields: dict[str, str] = {}
    # Match field = {value} or field = "value" or field = number
    # This handles nested braces in values
    pos = 0
    while pos < len(body):
        # Find next field name
        field_match = re.search(r"(\w+)\s*=\s*", body[pos:])
        if not field_match:
            break

        field_name = field_match.group(1).lower()
        value_start = pos + field_match.end()

        # Determine value delimiter
        if value_start >= len(body):
            break

        ch = body[value_start]
        if ch == "{":
            value = _extract_braced_body(body, value_start + 1)
            if value is None:
                break
            pos = value_start + len(value) + 2  # skip past closing }
        elif ch == '"':
            end_quote = body.index('"', value_start + 1)
            value = body[value_start + 1 : end_quote]
            pos = end_quote + 1
        else:
            # Bare value (number or macro)
            end = re.search(r"[,}\s]", body[value_start:])
            if end:
                value = body[value_start : value_start + end.start()]
                pos = value_start + end.start()
            else:
                value = body[value_start:]
                pos = len(body)

        fields[field_name] = value.strip()
        # Skip comma
        comma = body.find(",", pos)
        if comma != -1:
            pos = comma + 1
        else:
            break

    return fields


# ---------------------------------------------------------------------------
# Citation linting
# ---------------------------------------------------------------------------


class LintMessage:
    """A single lint finding."""

    def __init__(self, level: str, cite_key: str, message: str):
        self.level = level  # "error", "warning", "info"
        self.cite_key = cite_key
        self.message = message

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.cite_key}: {self.message}"

    def __repr__(self) -> str:
        return f"LintMessage({self.level!r}, {self.cite_key!r}, {self.message!r})"


def lint_entries(entries: list[dict[str, Any]]) -> list[LintMessage]:
    """Run all lint checks on a list of parsed BibTeX entries.

    Returns a list of LintMessage objects sorted by severity then key.
    """
    messages: list[LintMessage] = []
    messages.extend(_check_duplicate_keys(entries))
    for entry in entries:
        messages.extend(_check_required_fields(entry))
        messages.extend(_check_recommended_fields(entry))
        messages.extend(_check_doi(entry))
        messages.extend(_check_url(entry))
        messages.extend(_check_year(entry))
        messages.extend(_check_preprint_label(entry))

    # Sort: errors first, then warnings, then info
    order = {"error": 0, "warning": 1, "info": 2}
    messages.sort(key=lambda m: (order.get(m.level, 9), m.cite_key))
    return messages


def _check_duplicate_keys(entries: list[dict[str, Any]]) -> list[LintMessage]:
    """Check for duplicate citation keys."""
    seen: dict[str, int] = {}
    msgs: list[LintMessage] = []
    for entry in entries:
        key = entry.get("cite_key", "")
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            msgs.append(LintMessage("error", key, f"duplicate citation key (appears {count} times)"))
    return msgs


def _check_required_fields(entry: dict[str, Any]) -> list[LintMessage]:
    """Check that required fields are present and non-empty."""
    msgs: list[LintMessage] = []
    etype = entry.get("entry_type", "")
    key = entry.get("cite_key", "?")
    required = REQUIRED_FIELDS.get(etype, set())
    for field in sorted(required):
        if not entry.get(field, "").strip():
            msgs.append(LintMessage("error", key, f"missing required field '{field}'"))
    return msgs


def _check_recommended_fields(entry: dict[str, Any]) -> list[LintMessage]:
    """Check recommended fields (warnings only)."""
    msgs: list[LintMessage] = []
    etype = entry.get("entry_type", "")
    key = entry.get("cite_key", "?")
    recommended = RECOMMENDED_FIELDS.get(etype, set())
    for field in sorted(recommended):
        if not entry.get(field, "").strip():
            msgs.append(LintMessage("warning", key, f"missing recommended field '{field}'"))
    return msgs


def _check_doi(entry: dict[str, Any]) -> list[LintMessage]:
    """Check DOI presence and format."""
    msgs: list[LintMessage] = []
    key = entry.get("cite_key", "?")
    etype = entry.get("entry_type", "")
    doi = entry.get("doi", "").strip()

    if etype in DOI_EXPECTED_TYPES and not doi:
        msgs.append(LintMessage("warning", key, "no DOI for entry type that typically has one"))
    elif doi and not DOI_REGEX.match(doi):
        msgs.append(LintMessage("warning", key, f"DOI format looks invalid: '{doi}'"))

    return msgs


def _check_url(entry: dict[str, Any]) -> list[LintMessage]:
    """Check URL format if present."""
    msgs: list[LintMessage] = []
    key = entry.get("cite_key", "?")
    url = entry.get("url", "").strip()
    if url and not URL_REGEX.match(url):
        msgs.append(LintMessage("warning", key, f"malformed URL: '{url}'"))
    return msgs


def _check_year(entry: dict[str, Any]) -> list[LintMessage]:
    """Check that year is a valid 4-digit number."""
    msgs: list[LintMessage] = []
    key = entry.get("cite_key", "?")
    year = entry.get("year", "").strip()
    if year:
        if not re.match(r"^\d{4}$", year):
            msgs.append(LintMessage("warning", key, f"year is not a 4-digit number: '{year}'"))
        else:
            y = int(year)
            if y < 1800 or y > 2030:
                msgs.append(LintMessage("warning", key, f"year looks suspicious: {y}"))
    return msgs


def _check_preprint_label(entry: dict[str, Any]) -> list[LintMessage]:
    """Check that preprints are clearly labeled."""
    msgs: list[LintMessage] = []
    key = entry.get("cite_key", "?")
    journal = entry.get("journal", "").lower()
    note = entry.get("note", "").lower()
    keywords = entry.get("keywords", "").lower()

    is_preprint = any(
        server in journal
        for server in ["biorxiv", "medrxiv", "arxiv", "preprint", "ssrn", "chemrxiv"]
    )

    if is_preprint:
        has_label = any(
            "preprint" in field
            for field in [note, keywords, entry.get("howpublished", "").lower()]
        )
        if not has_label:
            msgs.append(
                LintMessage("info", key, "appears to be a preprint but lacks explicit preprint label")
            )

    return msgs


# ---------------------------------------------------------------------------
# Manuscript citation key extraction
# ---------------------------------------------------------------------------


def extract_cite_keys_from_manuscript() -> set[str]:
    """Scan manuscript .md files for MyST citation keys.

    Looks for patterns like {cite}`key`, {cite:p}`key`, {cite:t}`key`,
    and [@key] pandoc-style citations.
    """
    keys: set[str] = set()
    myst_pattern = re.compile(r"\{cite(?::(?:p|t|ps|ts))?\}`([^`]+)`")
    pandoc_pattern = re.compile(r"\[@([^\]]+)\]")

    sections_dir = MANUSCRIPT_DIR / "sections"
    if not sections_dir.exists():
        return keys

    for md_file in sections_dir.glob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for m in myst_pattern.finditer(text):
            # May be comma-separated keys
            for k in m.group(1).split(","):
                keys.add(k.strip())
        for m in pandoc_pattern.finditer(text):
            for k in m.group(1).split(";"):
                k = k.strip().lstrip("@")
                if k:
                    keys.add(k)

    return keys


def cross_reference_check(
    entries: list[dict[str, Any]], manuscript_keys: set[str]
) -> list[LintMessage]:
    """Check for uncited references and unresolved citation keys."""
    msgs: list[LintMessage] = []
    bib_keys = {e["cite_key"] for e in entries}

    # Unresolved keys (in manuscript but not in bib)
    for key in sorted(manuscript_keys - bib_keys):
        msgs.append(LintMessage("error", key, "cited in manuscript but not found in bibliography"))

    # Uncited references (in bib but not in manuscript)
    for key in sorted(bib_keys - manuscript_keys):
        msgs.append(LintMessage("info", key, "in bibliography but not cited in manuscript"))

    return msgs


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_library() -> list[dict[str, Any]]:
    """Load and parse the main bibliography file."""
    if not LIBRARY_BIB.exists():
        raise FileNotFoundError(f"Bibliography not found: {LIBRARY_BIB}")
    text = LIBRARY_BIB.read_text(encoding="utf-8")
    return parse_bibtex(text)


def available_csl_styles() -> list[str]:
    """Return names of available CSL style files."""
    if not CSL_DIR.exists():
        return []
    return sorted(p.stem for p in CSL_DIR.glob("*.csl"))
