#!/usr/bin/env python3
"""Shared helpers for bibliography integrity and citation-graph handling."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_ROOT = REPO_ROOT / "references"
REFERENCE_BIB_PATH = REFERENCES_ROOT / "library.bib"
REFERENCE_METADATA_DIR = REFERENCES_ROOT / "metadata"
SUGGESTED_CANDIDATES_PATH = REFERENCE_METADATA_DIR / "suggested_reference_candidates.json"
REFERENCE_REPORTS_DIR = REFERENCES_ROOT / "reports"
REFERENCE_MANIFESTS_DIR = REFERENCES_ROOT / "manifests"
CITATION_GRAPH_PATH = REPO_ROOT / "manuscript" / "plans" / "citation_graph.json"
DISPLAY_ITEM_MAP_PATH = REPO_ROOT / "manuscript" / "plans" / "display_item_map.json"

ARTICLE_LIKE_TYPES = {
    "article",
    "inproceedings",
    "conference",
    "proceedings",
    "incollection",
    "book",
    "phdthesis",
    "mastersthesis",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _find_entry_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    i = 0
    while True:
        start = text.find("@", i)
        if start == -1:
            break
        brace_open = text.find("{", start)
        if brace_open == -1:
            break
        depth = 0
        end = brace_open
        while end < len(text):
            char = text[end]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start:end + 1])
                    i = end + 1
                    break
            end += 1
        else:
            break
    return blocks


def _split_fields(body: str) -> list[str]:
    fields: list[str] = []
    current: list[str] = []
    depth = 0
    in_quotes = False
    for char in body:
        if char == '"' and (not current or current[-1] != "\\"):
            in_quotes = not in_quotes
        if not in_quotes:
            if char == "{":
                depth += 1
            elif char == "}":
                depth = max(depth - 1, 0)
        if char == "," and depth == 0 and not in_quotes:
            field = "".join(current).strip()
            if field:
                fields.append(field)
            current = []
            continue
        current.append(char)
    field = "".join(current).strip()
    if field:
        fields.append(field)
    return fields


def _clean_bib_value(value: str) -> str:
    cleaned = value.strip().rstrip(",").strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        cleaned = cleaned[1:-1]
    elif cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def load_bibliography_entries(path: Path = REFERENCE_BIB_PATH) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    entries: list[dict[str, Any]] = []
    header_re = re.compile(r"^@(?P<entry_type>[A-Za-z]+)\s*\{\s*(?P<key>[^,]+)\s*,", re.DOTALL)
    for block in _find_entry_blocks(text):
        match = header_re.match(block.strip())
        if not match:
            continue
        entry_type = match.group("entry_type").lower()
        key = match.group("key").strip()
        body = block[match.end():].rstrip("}").strip()
        fields: dict[str, str] = {}
        for field in _split_fields(body):
            if "=" not in field:
                continue
            name, value = field.split("=", 1)
            fields[name.strip().lower()] = _clean_bib_value(value)
        entries.append({"entry_type": entry_type, "key": key, "fields": fields})
    return entries


def load_citation_graph(path: Path = CITATION_GRAPH_PATH) -> dict[str, Any]:
    return load_json(path)


def load_display_item_map(path: Path = DISPLAY_ITEM_MAP_PATH) -> dict[str, Any]:
    return load_json(path)


def all_display_claim_ids() -> list[str]:
    payload = load_display_item_map()
    claim_ids: list[str] = []
    for item in payload.get("items", []):
        for claim_id in item.get("claim_ids", []):
            if claim_id not in claim_ids:
                claim_ids.append(claim_id)
    return claim_ids


def sync_citation_graph(write: bool = False) -> dict[str, Any]:
    graph = load_citation_graph()
    display_claims = all_display_claim_ids()
    existing_claim_nodes = {
        node.get("id"): node
        for node in graph.get("claim_nodes", [])
        if isinstance(node, dict) and node.get("id")
    }

    synced_claim_nodes = []
    for claim_id in display_claims:
        node = dict(existing_claim_nodes.get(claim_id, {}))
        node["id"] = claim_id
        node.setdefault("section", "results")
        synced_claim_nodes.append(node)

    synced_graph = {
        "claim_nodes": synced_claim_nodes,
        "reference_nodes": graph.get("reference_nodes", []),
        "edges": graph.get("edges", []),
    }
    if write:
        write_json(CITATION_GRAPH_PATH, synced_graph)
    return synced_graph
