#!/usr/bin/env python3
"""Evidence-summary and package-manifest helpers for the review pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from typing import Any

from review_bias import bias_summary
from review_common import (
    BIAS_DIR,
    EXTRACTION_DIR,
    PRISMA_DIR,
    PROTOCOL_DIR,
    QUERIES_DIR,
    RETRIEVAL_DIR,
    REVIEW_ROOT,
    SCREENING_DIR,
    compute_prisma_counts,
    load_bias_assessments,
    load_extraction_table,
    load_protocol,
    load_queries,
    load_screening_log,
)
from review_extract import validate_extraction
from review_prisma import generate_all


REPORTS_DIR = REVIEW_ROOT / "reports"
MANIFESTS_DIR = REVIEW_ROOT / "manifests"


def _count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = (row.get(key, "") or "unspecified").strip() or "unspecified"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _sample_size_summary(rows: list[dict[str, str]]) -> dict[str, int | float]:
    values = [int(row["sample_size"]) for row in rows if row.get("sample_size", "").strip()]
    if not values:
        return {"count": 0, "min": 0, "median": 0, "max": 0}
    return {
        "count": len(values),
        "min": min(values),
        "median": float(median(values)),
        "max": max(values),
    }


def _query_summary(queries: list[dict[str, Any]]) -> dict[str, Any]:
    hit_count_total = sum(int(query.get("hit_count", 0) or 0) for query in queries)
    date_runs = sorted(str(query.get("date_run", "")) for query in queries if query.get("date_run"))
    package_paths = []
    databases = []
    for query in queries:
        database = str(query.get("database", "unknown"))
        databases.append(database)
        query_id = str(query.get("query_id", "query"))
        package_paths.append(str((QUERIES_DIR / f"{query_id}.yml").relative_to(REVIEW_ROOT.parent)))
        export_file = str(query.get("export_file", "")).strip()
        if export_file and (REVIEW_ROOT.parent / "review" / export_file).exists():
            package_paths.append(f"review/{export_file}")
    return {
        "count": len(queries),
        "databases": sorted(dict.fromkeys(databases)),
        "hit_count_total": hit_count_total,
        "date_run_min": date_runs[0] if date_runs else "",
        "date_run_max": date_runs[-1] if date_runs else "",
        "package_paths": sorted(dict.fromkeys(package_paths)),
    }


def build_evidence_report() -> dict[str, Any]:
    """Build a manuscript-friendly evidence summary from review artifacts."""
    generate_all()

    protocol = load_protocol()
    queries = load_queries()
    screening = load_screening_log()
    extraction = load_extraction_table()
    bias_rows = load_bias_assessments()
    prisma = compute_prisma_counts()
    bias_stats = bias_summary()

    query_summary = _query_summary(queries)
    extraction_errors = validate_extraction()

    pending_title_abstract = sum(
        1
        for row in screening
        if row.get("stage") == "title_abstract" and row.get("decision") == "pending"
    )
    pending_full_text = sum(
        1
        for row in screening
        if row.get("stage") == "full_text" and row.get("decision") == "pending"
    )
    full_text_included = int(prisma["screening"]["full_text"]["included"])

    extraction_record_ids = {row.get("record_id", "") for row in extraction}
    bias_record_ids = {row.get("record_id", "") for row in bias_rows}
    missing_bias_records = sorted(
        record_id for record_id in extraction_record_ids if record_id and record_id not in bias_record_ids
    )

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if protocol.get("status") not in {"registered", "frozen", "amended"}:
        if screening:
            blocking_issues.append("protocol is not frozen or registered while screening artifacts exist")
        else:
            warnings.append("protocol is still in draft state")
    if pending_title_abstract:
        blocking_issues.append(f"{pending_title_abstract} title/abstract decisions are still pending")
    if pending_full_text:
        blocking_issues.append(f"{pending_full_text} full-text decisions are still pending")
    if full_text_included != len(extraction):
        blocking_issues.append(
            f"full-text included count ({full_text_included}) does not match extraction rows ({len(extraction)})"
        )
    if extraction_errors:
        blocking_issues.append(f"extraction table has {len(extraction_errors)} required-field issue(s)")
    if len(bias_rows) != len(extraction):
        blocking_issues.append(
            f"bias assessment rows ({len(bias_rows)}) do not match extraction rows ({len(extraction)})"
        )
    if missing_bias_records:
        blocking_issues.append(f"{len(missing_bias_records)} extracted studies are missing bias assessments")
    if not protocol.get("registration"):
        warnings.append("protocol registration metadata is absent; keep a frozen in-repo protocol if PROSPERO is not applicable")

    readiness = "ready" if not blocking_issues else "blocked"

    package_paths = [
        str((PROTOCOL_DIR / "protocol.yml").relative_to(REVIEW_ROOT.parent)),
        str((RETRIEVAL_DIR / "normalized" / "normalized_records.csv").relative_to(REVIEW_ROOT.parent)),
        str((RETRIEVAL_DIR / "dedup" / "dedup_log.csv").relative_to(REVIEW_ROOT.parent)),
        str((SCREENING_DIR / "screening_log.csv").relative_to(REVIEW_ROOT.parent)),
        str((EXTRACTION_DIR / "extraction_table.csv").relative_to(REVIEW_ROOT.parent)),
        str((BIAS_DIR / "bias_assessments.csv").relative_to(REVIEW_ROOT.parent)),
        str((PRISMA_DIR / "prisma_counts.yml").relative_to(REVIEW_ROOT.parent)),
        str((PRISMA_DIR / "exclusion_summary.csv").relative_to(REVIEW_ROOT.parent)),
        str((PRISMA_DIR / "evidence_table.csv").relative_to(REVIEW_ROOT.parent)),
    ]
    package_paths.extend(query_summary["package_paths"])
    package_paths = sorted(dict.fromkeys(package_paths))

    return {
        "review_id": str(protocol.get("protocol_id", "review")),
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "protocol": {
            "protocol_id": str(protocol.get("protocol_id", "")),
            "title": str(protocol.get("title", "")),
            "version": str(protocol.get("version", "")),
            "status": str(protocol.get("status", "")),
            "databases": list(protocol.get("databases", [])),
            "primary_outcomes": list(protocol.get("primary_outcomes", [])),
            "secondary_outcomes": list(protocol.get("secondary_outcomes", [])),
            "registration": protocol.get("registration", {}),
        },
        "queries": query_summary,
        "screening": {
            "pending_title_abstract": pending_title_abstract,
            "pending_full_text": pending_full_text,
            "title_abstract_summary": prisma["screening"]["title_abstract"],
            "full_text_summary": prisma["screening"]["full_text"],
        },
        "prisma": prisma,
        "extraction": {
            "included_studies": len(extraction),
            "study_design_counts": _count_by(extraction, "study_design"),
            "outcome_counts": _count_by(extraction, "outcome_name"),
            "population_counts": _count_by(extraction, "population"),
            "sample_size_summary": _sample_size_summary(extraction),
            "required_field_issues": extraction_errors,
        },
        "bias": {
            "assessed_studies": len(bias_rows),
            "overall_counts": bias_stats["overall"],
            "domain_counts": bias_stats["domains"],
            "tool_counts": _count_by(bias_rows, "tool"),
            "ai_assisted_counts": _count_by(bias_rows, "ai_assisted"),
        },
        "package_paths": package_paths,
    }


def build_review_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": f"{report['review_id']}_evidence_package_v1",
        "review_id": report["review_id"],
        "readiness": report["readiness"],
        "protocol_id": report["protocol"]["protocol_id"],
        "package_paths": report["package_paths"],
        "included_studies": report["extraction"]["included_studies"],
        "databases": report["queries"]["databases"],
        "primary_outcomes": report["protocol"]["primary_outcomes"],
        "secondary_outcomes": report["protocol"]["secondary_outcomes"],
    }


def render_evidence_markdown(report: dict[str, Any]) -> str:
    registration = report["protocol"].get("registration") or {}
    if isinstance(registration, dict) and registration.get("registry"):
        registration_summary = f"{registration.get('registry')} / {registration.get('registration_id', '')}".strip(" /")
    else:
        registration_summary = "not provided"
    lines = [
        "# Review Evidence Summary",
        "",
        f"- review_id: `{report['review_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- protocol: `{report['protocol']['title']}`",
        f"- protocol status: `{report['protocol']['status']}`",
        f"- protocol registration: `{registration_summary}`",
        f"- included studies: `{report['extraction']['included_studies']}`",
        f"- databases searched: `{', '.join(report['queries']['databases'])}`",
        f"- total records identified: `{report['prisma']['identification']['total_identified']}`",
        "",
        "## Screening",
        "",
        f"- title/abstract screened: `{report['screening']['title_abstract_summary']['screened']}`",
        f"- full texts assessed: `{report['screening']['full_text_summary']['assessed']}`",
        f"- included in synthesis: `{report['prisma']['included_in_synthesis']}`",
        f"- pending title/abstract decisions: `{report['screening']['pending_title_abstract']}`",
        f"- pending full-text decisions: `{report['screening']['pending_full_text']}`",
        "",
        "## Extraction",
        "",
    ]
    for name, count in report["extraction"]["study_design_counts"].items():
        lines.append(f"- study design `{name}`: `{count}`")
    for name, count in report["extraction"]["outcome_counts"].items():
        lines.append(f"- outcome `{name}`: `{count}`")
    sample_summary = report["extraction"]["sample_size_summary"]
    lines.extend(
        [
            f"- sample size range: `{sample_summary['min']} to {sample_summary['max']}`",
            f"- sample size median: `{sample_summary['median']}`",
            "",
            "## Risk Of Bias",
            "",
        ]
    )
    for name, count in report["bias"]["overall_counts"].items():
        lines.append(f"- overall judgment `{name}`: `{count}`")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Package Paths", ""])
    for path in report["package_paths"]:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_evidence_outputs() -> dict[str, str]:
    report = build_evidence_report()
    manifest = build_review_manifest(report)

    report_json_path = REPORTS_DIR / "evidence_summary.json"
    report_md_path = REPORTS_DIR / "evidence_summary.md"
    manifest_path = MANIFESTS_DIR / "review_evidence_package.json"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(render_evidence_markdown(report), encoding="utf-8")
    report_json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return {
        "report_json": str(report_json_path.relative_to(REVIEW_ROOT.parent)),
        "report_md": str(report_md_path.relative_to(REVIEW_ROOT.parent)),
        "manifest": str(manifest_path.relative_to(REVIEW_ROOT.parent)),
    }
