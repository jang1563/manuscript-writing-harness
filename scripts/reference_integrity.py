#!/usr/bin/env python3
"""Build bibliography integrity reports and citation-package manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reference_graph_common import (
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
from bibliography_common import bibliography_source_status

CLAIM_REFERENCE_MAP_PATH = REFERENCE_BIB_PATH.parent / "mappings" / "claim_reference_map.json"


def build_bibliography_scope_gate(source: dict[str, Any]) -> dict[str, Any]:
    manuscript_scope_status = str(source.get("manuscript_scope_status", "unknown"))
    return {
        "status": "ready" if manuscript_scope_status == "confirmed" else "blocked",
        "required_manuscript_scope_status": "confirmed",
        "current_manuscript_scope_status": manuscript_scope_status,
        "note": source.get("manuscript_scope_note"),
    }


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
    source = bibliography_source_status()
    suggestions = _suggested_candidates()
    claim_reference_map = _claim_reference_map()
    bibliography_scope_gate = build_bibliography_scope_gate(source)

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
    if source["status"] == "blocked":
        blocking_issues.extend(f"bibliography source: {issue}" for issue in source["issues"])
    if source["manuscript_scope_status"] == "invalid":
        blocking_issues.extend(
            f"bibliography manuscript scope: {issue}" for issue in source["manuscript_scope_issues"]
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
    if source["status"] == "provisional":
        warnings.extend(f"bibliography source: {warning}" for warning in source["warnings"])

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
        "bibliography_source": {
            "status": source["status"],
            "manifest_path": source["manifest_path"],
            "source_type": source["source_type"],
            "manifest_state": source["manifest_state"],
            "translator": source["translator"],
            "export_mode": source["export_mode"],
            "target_path": source["target_path"],
            "issues": source["issues"],
            "warnings": source["warnings"],
            "manuscript_scope_status": source["manuscript_scope_status"],
            "manuscript_scope_confirmed": source["manuscript_scope_confirmed"],
            "manuscript_scope_note": source["manuscript_scope_note"],
            "manuscript_scope_confirmed_on": source["manuscript_scope_confirmed_on"],
            "manuscript_scope_issues": source["manuscript_scope_issues"],
            "manuscript_scope_warnings": source["manuscript_scope_warnings"],
        },
        "bibliography_scope_gate": bibliography_scope_gate,
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
            source["manifest_path"],
            str(SUGGESTED_CANDIDATES_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
            str(CLAIM_REFERENCE_MAP_PATH.relative_to(REFERENCE_BIB_PATH.parent.parent)),
        ],
    }


def build_reference_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": "reference_integrity_package_v1",
        "readiness": report["readiness"],
        "entry_count": report["bibliography"]["entry_count"],
        "bibliography_source_status": report["bibliography_source"]["status"],
        "bibliography_manuscript_scope_status": report["bibliography_source"]["manuscript_scope_status"],
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
        f"- bibliography source: `{report['bibliography_source']['status']}`",
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
    lines.extend(["", "## Bibliography Source", ""])
    lines.append(f"- manifest: `{report['bibliography_source']['manifest_path']}`")
    lines.append(f"- source_type: `{report['bibliography_source']['source_type']}`")
    lines.append(f"- manifest_state: `{report['bibliography_source']['manifest_state']}`")
    lines.append(f"- export_mode: `{report['bibliography_source']['export_mode']}`")
    lines.append(f"- target_path: `{report['bibliography_source']['target_path']}`")
    lines.append(f"- manuscript_scope: `{report['bibliography_source']['manuscript_scope_status']}`")
    if report["bibliography_source"]["manuscript_scope_confirmed_on"]:
        lines.append(f"- manuscript_scope_confirmed_on: `{report['bibliography_source']['manuscript_scope_confirmed_on']}`")
    if report["bibliography_source"]["manuscript_scope_note"]:
        lines.append(f"- manuscript_scope_note: {report['bibliography_source']['manuscript_scope_note']}")
    if report["bibliography_source"]["issues"]:
        lines.append("- issues:")
        for issue in report["bibliography_source"]["issues"]:
            lines.append(f"  - {issue}")
    if report["bibliography_source"]["warnings"]:
        lines.append("- warnings:")
        for warning in report["bibliography_source"]["warnings"]:
            lines.append(f"  - {warning}")
    if report["bibliography_source"]["manuscript_scope_issues"]:
        lines.append("- manuscript_scope_issues:")
        for issue in report["bibliography_source"]["manuscript_scope_issues"]:
            lines.append(f"  - {issue}")
    if report["bibliography_source"]["manuscript_scope_warnings"]:
        lines.append("- manuscript_scope_warnings:")
        for warning in report["bibliography_source"]["manuscript_scope_warnings"]:
            lines.append(f"  - {warning}")
    lines.extend(["", "## Bibliography Scope Gate", ""])
    lines.append(f"- status: `{report['bibliography_scope_gate']['status']}`")
    lines.append(
        "- required_manuscript_scope_status: "
        f"`{report['bibliography_scope_gate']['required_manuscript_scope_status']}`"
    )
    lines.append(
        "- current_manuscript_scope_status: "
        f"`{report['bibliography_scope_gate']['current_manuscript_scope_status']}`"
    )
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
