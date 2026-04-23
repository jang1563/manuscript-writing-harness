#!/usr/bin/env python3
"""Build and apply claim-to-reference mapping scaffolds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reference_graph_common import (
    CITATION_GRAPH_PATH,
    REFERENCE_BIB_PATH,
    REFERENCE_METADATA_DIR,
    SUGGESTED_CANDIDATES_PATH,
    load_bibliography_entries,
    load_json,
    sync_citation_graph,
    write_json,
    write_text,
)


REPO_ROOT = Path(__file__).resolve().parent.parent
CLAIM_PACKETS_PATH = REPO_ROOT / "manuscript" / "plans" / "claim_packets.json"
REFERENCE_MAPPINGS_DIR = REFERENCE_METADATA_DIR.parent / "mappings"
CLAIM_REFERENCE_MAP_JSON_PATH = REFERENCE_MAPPINGS_DIR / "claim_reference_map.json"
CLAIM_REFERENCE_MAP_MD_PATH = REFERENCE_MAPPINGS_DIR / "claim_reference_map.md"


def _optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def _edge_lookup(graph: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    mapping: dict[str, list[dict[str, str]]] = {}
    for edge in graph.get("edges", []):
        claim_id = str(edge.get("from", ""))
        ref_id = str(edge.get("to", ""))
        relation = str(edge.get("relation", "background_context"))
        if not claim_id or not ref_id:
            continue
        mapping.setdefault(claim_id, []).append({"reference_id": ref_id, "relation": relation})
    return mapping


def _suggestion_lookup() -> dict[str, list[dict[str, Any]]]:
    payload = _optional_json(SUGGESTED_CANDIDATES_PATH) or {"candidates": []}
    lookup: dict[str, list[dict[str, Any]]] = {}
    for candidate in payload.get("candidates", []):
        claim_id = str(candidate.get("claim_id", ""))
        if not claim_id:
            continue
        lookup.setdefault(claim_id, []).append(candidate)
    return lookup


def _existing_mapping_lookup() -> dict[str, dict[str, Any]]:
    payload = _optional_json(CLAIM_REFERENCE_MAP_JSON_PATH) or {"mappings": []}
    lookup: dict[str, dict[str, Any]] = {}
    for item in payload.get("mappings", []):
        claim_id = str(item.get("claim_id", ""))
        if claim_id:
            lookup[claim_id] = item
    return lookup


def build_claim_reference_map(sync_graph: bool = False) -> dict[str, Any]:
    graph = sync_citation_graph(write=sync_graph)
    claim_packets = load_json(CLAIM_PACKETS_PATH)
    bib_entries = load_bibliography_entries()
    entry_keys = {entry["key"] for entry in bib_entries}
    edge_lookup = _edge_lookup(graph)
    suggestion_lookup = _suggestion_lookup()
    existing_mapping_lookup = _existing_mapping_lookup()

    mappings: list[dict[str, Any]] = []
    placeholder_claims: list[str] = []
    unmapped_claims: list[str] = []

    for packet in claim_packets.get("claims", []):
        claim_id = str(packet.get("claim_id"))
        display_item_id = str(packet.get("display_item", {}).get("display_item_id", ""))
        current_edges = edge_lookup.get(claim_id, [])
        current_reference_ids = [edge["reference_id"] for edge in current_edges]
        existing = existing_mapping_lookup.get(claim_id, {})
        accepted_reference_ids = [
            reference_id
            for reference_id in existing.get("accepted_reference_ids", current_reference_ids)
            if reference_id in entry_keys
        ]
        accepted_relation = str(existing.get("accepted_relation", current_edges[0]["relation"] if current_edges else "background_context"))
        placeholder_refs = [ref_id for ref_id in current_reference_ids if "placeholder" in ref_id.lower()]
        if placeholder_refs:
            status = "placeholder"
            placeholder_claims.append(claim_id)
        elif current_reference_ids:
            status = "mapped"
        elif accepted_reference_ids:
            status = "curated"
        else:
            status = "unmapped"
            unmapped_claims.append(claim_id)

        mappings.append(
            {
                "claim_id": claim_id,
                "status": status,
                "manuscript_section": str(packet.get("manuscript_section", "results")),
                "display_item_id": display_item_id,
                "fact_sheet": packet.get("display_item", {}).get("fact_sheet"),
                "legend_path": packet.get("display_item", {}).get("legend_path"),
                "current_reference_ids": current_reference_ids,
                "current_relations": [edge["relation"] for edge in current_edges],
                "accepted_reference_ids": accepted_reference_ids,
                "accepted_relation": accepted_relation,
                "reference_candidates": existing.get("reference_candidates", suggestion_lookup.get(claim_id, [])),
                "allowed_bibliography_keys": sorted(entry_keys),
                "notes": str(existing.get("notes", "")),
            }
        )

    overall_status = "ready"
    if placeholder_claims:
        overall_status = "provisional"
    if unmapped_claims:
        overall_status = "provisional"

    return {
        "generated_from": {
            "claim_packets": str(CLAIM_PACKETS_PATH.relative_to(REPO_ROOT)),
            "citation_graph": str(CITATION_GRAPH_PATH.relative_to(REPO_ROOT)),
            "bibliography": str(REFERENCE_BIB_PATH.relative_to(REPO_ROOT)),
            "suggested_candidates": str(SUGGESTED_CANDIDATES_PATH.relative_to(REPO_ROOT)),
        },
        "overall_status": overall_status,
        "claim_count": len(mappings),
        "mapped_claim_count": sum(1 for item in mappings if item["status"] == "mapped"),
        "placeholder_claim_count": len(placeholder_claims),
        "unmapped_claim_count": len(unmapped_claims),
        "mappings": mappings,
    }


def render_claim_reference_map_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Claim Reference Map",
        "",
        f"- overall_status: `{payload['overall_status']}`",
        f"- claim_count: `{payload['claim_count']}`",
        f"- mapped_claim_count: `{payload['mapped_claim_count']}`",
        f"- placeholder_claim_count: `{payload['placeholder_claim_count']}`",
        f"- unmapped_claim_count: `{payload['unmapped_claim_count']}`",
        "",
    ]
    for item in payload.get("mappings", []):
        lines.extend(
            [
                f"## {item['claim_id']}",
                "",
                f"- status: `{item['status']}`",
                f"- display_item_id: `{item['display_item_id']}`",
                f"- current_reference_ids: `{', '.join(item['current_reference_ids']) or 'none'}`",
                f"- accepted_relation: `{item['accepted_relation']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_claim_reference_map(sync_graph: bool = False) -> dict[str, str]:
    payload = build_claim_reference_map(sync_graph=sync_graph)
    write_json(CLAIM_REFERENCE_MAP_JSON_PATH, payload)
    write_text(CLAIM_REFERENCE_MAP_MD_PATH, render_claim_reference_map_markdown(payload))
    return {
        "map_json": str(CLAIM_REFERENCE_MAP_JSON_PATH.relative_to(REPO_ROOT)),
        "map_md": str(CLAIM_REFERENCE_MAP_MD_PATH.relative_to(REPO_ROOT)),
    }


def apply_claim_reference_map(sync_graph: bool = False) -> dict[str, Any]:
    graph = sync_citation_graph(write=sync_graph)
    mapping = _optional_json(CLAIM_REFERENCE_MAP_JSON_PATH)
    if mapping is None:
        mapping = build_claim_reference_map(sync_graph=sync_graph)
        write_json(CLAIM_REFERENCE_MAP_JSON_PATH, mapping)

    bib_entries = load_bibliography_entries()
    entry_keys = {entry["key"] for entry in bib_entries}
    existing_reference_nodes = {
        str(node.get("id")): node
        for node in graph.get("reference_nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    other_edges = [
        edge
        for edge in graph.get("edges", [])
        if str(edge.get("from")) not in {item["claim_id"] for item in mapping.get("mappings", [])}
    ]
    next_edges = list(other_edges)

    for item in mapping.get("mappings", []):
        claim_id = str(item.get("claim_id"))
        relation = str(item.get("accepted_relation", "background_context"))
        for reference_id in item.get("accepted_reference_ids", []):
            if reference_id not in entry_keys:
                continue
            node = dict(existing_reference_nodes.get(reference_id, {}))
            node["id"] = reference_id
            note = reference_id.lower()
            node["source"] = "references/library.bib"
            node["status"] = "placeholder" if "placeholder" in note else "accepted"
            existing_reference_nodes[reference_id] = node
            next_edges.append(
                {
                    "from": claim_id,
                    "to": reference_id,
                    "relation": relation,
                }
            )

    used_reference_ids = {str(edge.get("to")) for edge in next_edges if edge.get("to")}
    next_graph = {
        "claim_nodes": graph.get("claim_nodes", []),
        "reference_nodes": sorted(
            [node for ref_id, node in existing_reference_nodes.items() if ref_id in used_reference_ids],
            key=lambda node: str(node["id"]),
        ),
        "edges": sorted(
            next_edges,
            key=lambda edge: (str(edge.get("from", "")), str(edge.get("to", "")), str(edge.get("relation", ""))),
        ),
    }
    write_json(CITATION_GRAPH_PATH, next_graph)
    return {
        "citation_graph": str(CITATION_GRAPH_PATH.relative_to(REPO_ROOT)),
        "reference_node_count": len(next_graph["reference_nodes"]),
        "edge_count": len(next_graph["edges"]),
    }
