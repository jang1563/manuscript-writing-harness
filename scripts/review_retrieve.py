#!/usr/bin/env python3
"""Retrieval and deduplication stage for the systematic review pipeline.

Supports CSV, NBIB (PubMed), and RIS (Reference Manager) export formats.
Provides exact and fuzzy deduplication strategies.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from review_common import (
    RETRIEVAL_DIR,
    SCREENING_DIR,
    SCREENING_REQUIRED_COLUMNS,
    load_csv,
    write_csv,
)


def normalize_records(raw_path: Path, source_db: str) -> list[dict[str, str]]:
    """Normalize a raw export file into a common record format.

    Supports CSV, NBIB (PubMed), and RIS (Reference Manager) formats.
    Format is detected from the file extension.
    """
    suffix = raw_path.suffix.lower()
    if suffix == ".csv":
        return _normalize_csv(raw_path, source_db)
    if suffix == ".nbib":
        return _normalize_nbib(raw_path, source_db)
    if suffix == ".ris":
        return _normalize_ris(raw_path, source_db)
    raise NotImplementedError(
        f"Format '{suffix}' not yet supported. "
        "Supported formats: .csv, .nbib, .ris"
    )


def _normalize_csv(raw_path: Path, source_db: str) -> list[dict[str, str]]:
    """Parse a CSV export into normalized records."""
    raw_rows = load_csv(raw_path)
    records = []
    for row in raw_rows:
        records.append({
            "record_id": row.get("record_id", ""),
            "pmid": row.get("pmid", ""),
            "doi": row.get("doi", ""),
            "title": row.get("title", ""),
            "authors": row.get("authors", ""),
            "year": row.get("year", ""),
            "abstract": row.get("abstract", ""),
            "source_db": source_db,
        })
    return records


def _normalize_nbib(raw_path: Path, source_db: str) -> list[dict[str, str]]:
    """Parse a PubMed NBIB export into normalized records.

    NBIB format uses 4-character tags followed by ``- `` and the value.
    Records are separated by blank lines. Continuation lines start with
    spaces.
    """
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    records: list[dict[str, str]] = []

    for raw_block in re.split(r"\n\s*\n", text):
        if not raw_block.strip():
            continue
        fields = _parse_nbib_block(raw_block)
        if not fields:
            continue

        pmid = fields.get("PMID", "")
        records.append({
            "record_id": f"PMID{pmid}" if pmid else "",
            "pmid": pmid,
            "doi": _extract_doi_from_aid(fields.get("AID_LIST", [])),
            "title": fields.get("TI", ""),
            "authors": "; ".join(fields.get("AU_LIST", [])),
            "year": _extract_year(fields.get("DP", "")),
            "abstract": fields.get("AB", ""),
            "source_db": source_db,
        })

    return records


def _parse_nbib_block(block: str) -> dict:
    """Parse a single NBIB record block into a dict of fields.

    Multi-value fields (AU, AID) are returned as lists with the ``_LIST``
    suffix.
    """
    fields: dict = {}
    current_tag = None
    current_value: list[str] = []

    for line in block.splitlines():
        if not line.strip():
            continue
        # Tagged line: 4-char tag, then "- "
        m = re.match(r"^([A-Z][A-Z0-9 ]{1,3})\s*-\s?(.*)$", line)
        if m:
            # Flush previous tag
            if current_tag is not None:
                _store_nbib_field(fields, current_tag, " ".join(current_value).strip())
            current_tag = m.group(1).strip()
            current_value = [m.group(2)]
        else:
            # Continuation line
            if current_tag is not None:
                current_value.append(line.strip())

    # Flush last
    if current_tag is not None:
        _store_nbib_field(fields, current_tag, " ".join(current_value).strip())

    return fields


def _store_nbib_field(fields: dict, tag: str, value: str) -> None:
    """Store an NBIB field, accumulating multi-value tags as lists."""
    multi_value_tags = {"AU", "AID", "MH", "PT"}
    if tag in multi_value_tags:
        key = f"{tag}_LIST"
        fields.setdefault(key, []).append(value)
    else:
        fields[tag] = value


def _extract_doi_from_aid(aid_list: list[str]) -> str:
    """Extract DOI from PubMed AID entries (format: 'value [type]')."""
    for aid in aid_list:
        m = re.match(r"^(\S+)\s*\[doi\]", aid, re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def _extract_year(date_str: str) -> str:
    """Extract a 4-digit year from a date string."""
    m = re.search(r"\b(19|20)\d{2}\b", date_str)
    return m.group(0) if m else ""


def _normalize_ris(raw_path: Path, source_db: str) -> list[dict[str, str]]:
    """Parse a RIS (Reference Manager) export into normalized records.

    RIS format uses 2-character tags followed by ``  - `` and the value.
    Records start with ``TY  - `` and end with ``ER  - ``.
    """
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    records: list[dict[str, str]] = []
    current: dict = {}
    authors: list[str] = []

    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])\s+-\s?(.*)$", line)
        if not m:
            continue
        tag = m.group(1)
        value = m.group(2).strip()

        if tag == "TY":
            current = {"_type": value}
            authors = []
        elif tag == "ER":
            if current:
                records.append(_finalize_ris_record(current, authors, source_db))
            current = {}
            authors = []
        elif tag in ("AU", "A1", "A2", "A3"):
            authors.append(value)
        else:
            current[tag] = value

    return records


def _finalize_ris_record(
    fields: dict, authors: list[str], source_db: str
) -> dict[str, str]:
    """Convert RIS fields to the common record format."""
    pmid = ""
    if fields.get("AN"):
        # Sometimes PMID is in AN, prefixed
        m = re.search(r"\b(\d{6,9})\b", fields["AN"])
        pmid = m.group(1) if m else ""

    doi = fields.get("DO", "") or fields.get("M3", "")
    # Year from PY or Y1
    year = _extract_year(fields.get("PY", "") or fields.get("Y1", ""))

    title = fields.get("TI", "") or fields.get("T1", "") or fields.get("ST", "")
    abstract = fields.get("AB", "") or fields.get("N2", "")

    record_id = ""
    if pmid:
        record_id = f"PMID{pmid}"
    elif doi:
        record_id = f"DOI{doi}"

    return {
        "record_id": record_id,
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "authors": "; ".join(authors),
        "year": year,
        "abstract": abstract,
        "source_db": source_db,
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _normalize_title(title: str) -> str:
    """Normalize title for fuzzy comparison: lowercase, alphanumeric only."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _title_similarity(a: str, b: str) -> float:
    """Return similarity ratio in [0, 1] between two normalized titles."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def deduplicate(
    records: list[dict[str, str]],
    strategy: str = "exact",
    similarity_threshold: float = 0.92,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Remove duplicate records.

    Args:
        records: List of normalized record dicts.
        strategy: 'exact' matches on DOI then exact lowercase title.
                  'fuzzy' adds a similarity check for near-duplicates
                  (different formatting, punctuation, abstract whitespace).
        similarity_threshold: Title similarity threshold for fuzzy mode
                              (0.0 to 1.0). Only used when strategy='fuzzy'.

    Returns:
        (unique_records, dedup_log) where dedup_log contains removed
        duplicates with a 'duplicate_of' field referencing the retained
        record.
    """
    if strategy not in ("exact", "fuzzy"):
        raise ValueError(f"Unknown strategy: {strategy!r} (use 'exact' or 'fuzzy')")

    seen_dois: dict[str, str] = {}
    seen_titles: dict[str, str] = {}  # exact lowercase title -> record_id
    seen_pmids: dict[str, str] = {}
    unique: list[dict[str, str]] = []
    removed: list[dict[str, str]] = []

    for rec in records:
        doi = rec.get("doi", "").strip().lower()
        pmid = rec.get("pmid", "").strip()
        title_key = rec.get("title", "").strip().lower()
        record_id = rec.get("record_id", "")

        duplicate_of = None

        # Tier 1: exact DOI match
        if doi and doi in seen_dois:
            duplicate_of = seen_dois[doi]
        # Tier 2: exact PMID match
        elif pmid and pmid in seen_pmids:
            duplicate_of = seen_pmids[pmid]
        # Tier 3: exact title match
        elif title_key and title_key in seen_titles:
            duplicate_of = seen_titles[title_key]
        # Tier 4: fuzzy title match (only if strategy is fuzzy)
        elif strategy == "fuzzy" and title_key:
            for existing_title, existing_id in seen_titles.items():
                sim = _title_similarity(title_key, existing_title)
                if sim >= similarity_threshold:
                    duplicate_of = existing_id
                    break

        if duplicate_of:
            entry = dict(rec)
            entry["duplicate_of"] = duplicate_of
            removed.append(entry)
        else:
            unique.append(rec)
            if doi:
                seen_dois[doi] = record_id
            if pmid:
                seen_pmids[pmid] = record_id
            if title_key:
                seen_titles[title_key] = record_id

    return unique, removed


def write_normalized(records: list[dict[str, str]], output_dir: Path | None = None) -> Path:
    """Write normalized records to CSV."""
    out_dir = output_dir or (RETRIEVAL_DIR / "normalized")
    out_path = out_dir / "normalized_records.csv"
    fieldnames = ["record_id", "pmid", "doi", "title", "authors", "year", "abstract", "source_db"]
    write_csv(out_path, records, fieldnames)
    return out_path


def write_dedup_log(dedup_log: list[dict[str, str]], output_dir: Path | None = None) -> Path:
    """Write deduplication log to CSV."""
    out_dir = output_dir or (RETRIEVAL_DIR / "dedup")
    out_path = out_dir / "dedup_log.csv"
    fieldnames = [
        "record_id", "pmid", "doi", "title", "authors", "year",
        "abstract", "source_db", "duplicate_of",
    ]
    write_csv(out_path, dedup_log, fieldnames)
    return out_path


def write_screening_input(
    records: list[dict[str, str]], output_dir: Path | None = None
) -> Path:
    """Write deduplicated records as a screening-ready CSV."""
    out_dir = output_dir or SCREENING_DIR
    out_path = out_dir / "screening_input.csv"
    fieldnames = ["record_id", "pmid", "doi", "title", "authors", "year", "abstract", "source_db"]
    write_csv(out_path, records, fieldnames)
    return out_path


def run_retrieval(
    raw_exports: list[tuple[Path, str]],
    strategy: str = "exact",
    similarity_threshold: float = 0.92,
) -> dict[str, int]:
    """Run the full retrieval + dedup pipeline.

    Args:
        raw_exports: List of (path, database_name) tuples.
        strategy: Deduplication strategy ('exact' or 'fuzzy').
        similarity_threshold: Title similarity threshold for fuzzy mode.

    Returns:
        Summary counts.
    """
    all_records: list[dict[str, str]] = []
    for raw_path, db_name in raw_exports:
        records = normalize_records(raw_path, db_name)
        all_records.extend(records)

    write_normalized(all_records)
    unique, removed = deduplicate(
        all_records,
        strategy=strategy,
        similarity_threshold=similarity_threshold,
    )
    write_dedup_log(removed)
    write_screening_input(unique)

    return {
        "total_raw": len(all_records),
        "duplicates_removed": len(removed),
        "unique_records": len(unique),
    }
