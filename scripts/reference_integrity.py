#!/usr/bin/env python3
"""Build bibliography integrity reports and citation-package manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reference_common import (
    ARTICLE_LIKE_TYPES,
    CITATION_GRAPH_PATH,
    DISPLAY_ITEM_MAP_PATH,
    REFERENCE_BIB_PATH,
    REFERENCE_MANIFESTS_DIR,
    REFERENCE_REPORTS_DIR,
    SUGGESTED_CANDIDATES_PATH,
    load_bibliography_entries,
    load_json,
    sync_citation_graph,
    write_json,
    write_text,
)

CLAIM_REFERENCE_MAP_PATH = REFERENCE_BIB_PATH.parent / "mappings" / "claim_reference_map.json"


def _suggested_candidates() -> dict[str, Any]:
    if not SUGGESTED_CANDIDATES_PATH.exists():
        return {"status": "absent", "generated_by": None, "candidates": []}
    payload = load_json(SUGGESTED_CANDIDATES_PATH)
    if "candidates" not in payload:
        payload["candidates"] = []
    return payload


def _claim_reference_map() -> dict[str, Any]:
    if not CLAIM_REFERENCE_MAP_PATH.exists():
        return {
            "overall_status": "absent",
            "claim_count": 0,
            "mapped_claim_count": 0,
            "placeholder_claim_count": 0,
            "unmapped_claim_count": 0,
        }
    payload = load_json(CLAIM_REFERENCE_MAP_PATH)
    return {
        "overall_status": payload.get("overall_status", "absent"),
        "claim_count": payload.get("claim_count", 0),
        "mapped_claim_count": payload.get("mapped_claim_count", 0),
        "placeholder_claim_count": payload.get("placeholder_claim_count", 0),
        "unmapped_claim_count": payload.get("unmapped_claim_count", 0),
    }


def build_reference_report(sync_graph: bool = False) -> dict[str, Any]:
    graph = sync_citation_graph(write=sync_graph)
    entries = load_bibliography_entries()
    suggestions = _suggested_candidates()
    claim_reference_map = _claim_reference_map()

    key_to_entry = {entry["key"]: entry for entry in entries}
    key_counts: dict[str, int] = {}
    doi_counts: dict[str, int] = {}
    title_counts: dict[str, int] = {}
    placeholder_keys: list[str] = []
    missing_identifier_keys: list[str] = []

    for entry in entries:
        key = str(entry["key"])
        key_counts[key] = key_counts.get(key, 0) + 1
        fields = entry["fields"]
        doi = fields.get("doi", "").strip().lower()
        pmid = fields.get("pmid", "").strip()
        title = fields.get("title", "").strip().lower()
        note = fields.get("note", "").lower()
        if doi:
            doi_counts[doi] = doi_counts.get(doi, 0) + 1
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1
        if "placeholder" in key.lower() or "placeholder" in note:
            placeholder_keys.append(key)
        if entry["entry_type"] in ARTICLE_LIKE_TYPES and not doi and not pmid:
            missing_identifier_keys.append(key)

    duplicate_keys = sorted(key for key, count in key_counts.items() if count > 1)
    duplicate_dois = sorted(doi for doi, count in doi_counts.items() if count > 1)
    duplicate_titles = sorted(title for title, count in title_counts.items() if count > 1)

    claim_nodes = graph.get("claim_nodes", [])
    reference_nodes = graph.get("reference_nodes", [])
    edges = graph.get("edges", [])

    claim_ids = [str(node.get("id")) for node in claim_nodes if node.get("id")]
    reference_ids = [str(node.get("id")) for node in reference_nodes if node.get("id")]
    edge_targets = [str(edge.get("to")) for edge in edges if edge.get("to")]
    edge_sources = [str(edge.get("from")) for edge in edges if edge.get("from")]

    unresolved_reference_nodes = sorted(reference_id for reference_id in reference_ids if reference_id not in key_to_entry)
    uncited_bibliography_keys = sorted(key for key in key_to_entry if key not in edge_targets)
    unlinked_claim_ids = sorted(claim_id for claim_id in claim_ids if claim_id not in edge_sources)

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if duplicate_keys:
        blocking_issues.append(f"duplicate citation keys detected: {', '.join(duplicate_keys)}")
    if duplicate_dois:
        blocking_issues.append(f"duplicate DOI-backed entries detected: {', '.join(duplicate_dois)}")
    if unresolved_reference_nodes:
        blocking_issues.append(
            f"citation graph references missing bibliography keys: {', '.join(unresolved_reference_nodes)}"
        )

    if duplicate_titles:
        warnings.append(f"duplicate titles detected: {', '.join(duplicate_titles)}")
    if placeholder_keys:
        warnings.append(f"placeholder bibliography entries remain: {', '.join(placeholder_keys)}")
    if missing_identifier_keys:
        warnings.append(
            f"article-like entries without DOI or PMID: {', '.join(sorted(missing_identifier_keys))}"
        )
    if uncited_bibliography_keys:
        warnings.append(f"bibliography entries not linked from citation graph: {', '.join(uncited_bibliography_keys)}")
    if unlinked_claim_ids:
        warnings.append(f"claim nodes without citation edges: {', '.join(unlinked_claim_ids)}")

    readiness = "ready"
    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"

    return {
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "bibliography": {
            "entry_count": len(entries),
            "keys": sorted(key_to_entry.keys()),
            "placeholder_keys": sorted(placeholder_keys),
            "missing_identifier_keys": sorted(missing_identifier_keys),
            "uncited_keys": uncited_bibliography_keys,
        },
        "citation_graph": {
            "claim_count": len(claim_ids),
            "reference_node_count": len(reference_ids),
            "edge_count": len(edges),
            "unlinked_claim_ids": unlinked_claim_ids,
            "unresolved_reference_nodes": unresolved_reference_nodes,
        },
        "literature_intelligence": {
            "candidate_status": suggestions.get("status", "absent"),
            "generated_by": suggestions.get("generated_by"),
            "candidate_count": len(suggestions.get("candidates", [])),
            "separate_suggestion_store": str(SUGGESTED_CANDIDATES_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        },
        "claim_reference_mapping": {
            "status": claim_reference_map["overall_status"],
            "claim_count": claim_reference_map["claim_count"],
            "mapped_claim_count": claim_reference_map["mapped_claim_count"],
            "placeholder_claim_count": claim_reference_map["placeholder_claim_count"],
            "unmapped_claim_count": claim_reference_map["unmapped_claim_count"],
            "mapping_store": str(CLAIM_REFERENCE_MAP_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        },
        "package_paths": [
            str(REFERENCE_BIB_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
            str(CITATION_GRAPH_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
            str(DISPLAY_ITEM_MAP_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
            str(SUGGESTED_CANDIDATES_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
            str(CLAIM_REFERENCE_MAP_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        ],
    }


def build_reference_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": "reference_integrity_package_v1",
        "readiness": report["readiness"],
        "entry_count": report["bibliography"]["entry_count"],
        "claim_count": report["citation_graph"]["claim_count"],
        "reference_node_count": report["citation_graph"]["reference_node_count"],
        "edge_count": report["citation_graph"]["edge_count"],
        "package_paths": report["package_paths"],
    }


def render_reference_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Reference Integrity Audit",
        "",
        f"- readiness: `{report['readiness']}`",
        f"- bibliography entries: `{report['bibliography']['entry_count']}`",
        f"- citation-graph claims: `{report['citation_graph']['claim_count']}`",
        f"- citation-graph edges: `{report['citation_graph']['edge_count']}`",
        f"- literature-intelligence candidates: `{report['literature_intelligence']['candidate_count']}`",
        f"- claim-reference mappings: `{report['claim_reference_mapping']['mapped_claim_count']}` mapped / `{report['claim_reference_mapping']['unmapped_claim_count']}` unmapped",
        "",
        "## Bibliography",
        "",
    ]
    for key in report["bibliography"]["keys"]:
        lines.append(f"- `{key}`")
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


def write_reference_outputs(sync_graph: bool = False) -> dict[str, str]:
    report = build_reference_report(sync_graph=sync_graph)
    manifest = build_reference_manifest(report)

    report_json_path = REFERENCE_REPORTS_DIR / "reference_audit.json"
    report_md_path = REFERENCE_REPORTS_DIR / "reference_audit.md"
    manifest_path = REFERENCE_MANIFESTS_DIR / "reference_package.json"

    write_json(report_json_path, report)
    write_text(report_md_path, render_reference_markdown(report))
    write_json(manifest_path, manifest)

    return {
        "report_json": str(report_json_path.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        "report_md": str(report_md_path.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        "manifest": str(manifest_path.relative_to(REFERENCE_BIB_PATH.parent.parent)),
    }
