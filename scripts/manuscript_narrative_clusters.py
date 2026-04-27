#!/usr/bin/env python3
"""Build display-backed narrative clusters for manuscript Results drafting."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
PLANS_DIR = MANUSCRIPT_ROOT / "plans"
DISPLAY_ITEM_MAP_PATH = PLANS_DIR / "display_item_map.json"
WRITING_PLAN_PATH = PLANS_DIR / "writing_plan.json"
NARRATIVE_CLUSTERS_PATH = PLANS_DIR / "narrative_clusters.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "cluster"


def _display_item_sort_key(item: dict[str, Any], display_refs: list[str]) -> tuple[int, str]:
    display_id = str(item.get("display_item_id", ""))
    try:
        return (display_refs.index(display_id), display_id)
    except ValueError:
        return (999, display_id)


def result_display_item_ids() -> list[str]:
    display_map = load_json(DISPLAY_ITEM_MAP_PATH)
    writing_plan = load_json(WRITING_PLAN_PATH)
    display_refs = [str(item) for item in writing_plan.get("display_item_refs", [])]
    items = sorted(
        [
            item
            for item in display_map.get("items", [])
            if isinstance(item, dict)
            and str(item.get("manuscript_section", "results")) == "results"
            and item.get("claim_ids")
        ],
        key=lambda item: _display_item_sort_key(item, display_refs),
    )
    return [str(item["display_item_id"]) for item in items]


def result_display_claim_ids() -> list[str]:
    display_map = load_json(DISPLAY_ITEM_MAP_PATH)
    display_items_by_id = {
        str(item.get("display_item_id")): item
        for item in display_map.get("items", [])
        if isinstance(item, dict) and item.get("display_item_id")
    }
    claim_ids: list[str] = []
    for display_item_id in result_display_item_ids():
        item = display_items_by_id.get(display_item_id)
        if not item:
            continue
        for claim_id in item.get("claim_ids", []):
            normalized = str(claim_id)
            if normalized not in claim_ids:
                claim_ids.append(normalized)
    return claim_ids


def _load_cluster_plan(path: Path = NARRATIVE_CLUSTERS_PATH) -> dict[str, Any]:
    if not path.exists():
        return {
            "cluster_strategy": "display_item",
            "missing_display_item_mode": "default_display_item_cluster",
            "clusters": [],
        }
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("narrative cluster plan must be a JSON object")
    clusters = payload.get("clusters", [])
    if not isinstance(clusters, list):
        raise ValueError("narrative cluster plan must define a clusters list")
    return payload


def _display_id(packet: dict[str, Any]) -> str:
    return str(packet.get("display_item", {}).get("display_item_id", ""))


def _packet_claim_id(packet: dict[str, Any]) -> str:
    return str(packet.get("claim_id", ""))


def _first_evidence_statement(packet: dict[str, Any]) -> str:
    facts = packet.get("evidence_facts", [])
    if facts and isinstance(facts[0], dict):
        statement = str(facts[0].get("statement", "")).strip()
        if statement:
            return statement
    claim_id = _packet_claim_id(packet)
    return f"State {claim_id} directly from the display-backed evidence."


def _cluster_status(packets: list[dict[str, Any]], blocking_issues: list[str]) -> str:
    if blocking_issues or any(packet.get("status") == "blocked" for packet in packets):
        return "blocked"
    if any(packet.get("status") == "provisional" for packet in packets):
        return "provisional"
    return "ready"


def _aggregate_reference_ids(packets: list[dict[str, Any]]) -> list[str]:
    reference_ids: list[str] = []
    for packet in packets:
        for reference_id in packet.get("citations", {}).get("reference_ids", []):
            normalized = str(reference_id)
            if normalized not in reference_ids:
                reference_ids.append(normalized)
    return reference_ids


def _default_heading(display_item_id: str) -> str:
    label = display_item_id
    label = re.sub(r"^(figure|table)_\\d+_", "", label)
    return label.replace("_", " ").capitalize()


def _default_cluster(display_item_id: str) -> dict[str, Any]:
    return {
        "cluster_id": f"cluster_{_slug(display_item_id)}",
        "display_item_ids": [display_item_id],
        "heading": _default_heading(display_item_id),
        "narrative_role": "display-backed result cluster",
        "paragraph_goal": "Synthesize the display-backed claims without expanding beyond the visible evidence.",
    }


def _ordered_packets_for_display_ids(
    display_item_ids: list[str],
    packets_by_display: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for display_item_id in display_item_ids:
        packets.extend(packets_by_display.get(display_item_id, []))
    return packets


def _build_cluster(
    raw_cluster: dict[str, Any],
    *,
    packets_by_display: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    display_item_ids = [
        str(display_item_id)
        for display_item_id in raw_cluster.get("display_item_ids", [])
        if str(display_item_id).strip()
    ]
    packets = _ordered_packets_for_display_ids(display_item_ids, packets_by_display)
    claim_ids = [_packet_claim_id(packet) for packet in packets if _packet_claim_id(packet)]
    blocking_issues: list[str] = []
    warnings: list[str] = []

    if not display_item_ids:
        blocking_issues.append("cluster has no display_item_ids")
    missing_display_ids = [
        display_item_id
        for display_item_id in display_item_ids
        if display_item_id not in packets_by_display
    ]
    if missing_display_ids:
        blocking_issues.append(
            "cluster references display items without claim packets: "
            + ", ".join(missing_display_ids)
        )
    if not claim_ids:
        blocking_issues.append("cluster has no display-backed claims")

    requested_lead_claim_id = str(raw_cluster.get("lead_claim_id", "")).strip()
    if requested_lead_claim_id and requested_lead_claim_id in claim_ids:
        lead_claim_id = requested_lead_claim_id
    elif claim_ids:
        lead_claim_id = claim_ids[0]
        if requested_lead_claim_id:
            warnings.append(
                f"lead_claim_id `{requested_lead_claim_id}` is not present; using `{lead_claim_id}`"
            )
    else:
        lead_claim_id = ""

    packet_by_claim = {_packet_claim_id(packet): packet for packet in packets}
    lead_packet = packet_by_claim.get(lead_claim_id) or (packets[0] if packets else {})
    evidence_sentences = [
        {
            "claim_id": _packet_claim_id(packet),
            "statement": _first_evidence_statement(packet),
        }
        for packet in packets
    ]
    claim_author_notes = {
        _packet_claim_id(packet): str(packet.get("author_input", {}).get("claim_note", ""))
        for packet in packets
        if str(packet.get("author_input", {}).get("claim_note", "")).strip()
    }

    cluster_id = str(raw_cluster.get("cluster_id", "")).strip()
    if not cluster_id and display_item_ids:
        cluster_id = f"cluster_{_slug(display_item_ids[0])}"

    return {
        "cluster_id": cluster_id,
        "manuscript_section": "results",
        "display_item_ids": display_item_ids,
        "display_item_id": display_item_ids[0] if display_item_ids else "",
        "claim_ids": claim_ids,
        "lead_claim_id": lead_claim_id,
        "lead_sentence_target": _first_evidence_statement(lead_packet) if lead_packet else "",
        "heading": str(raw_cluster.get("heading") or _default_heading(display_item_ids[0] if display_item_ids else cluster_id)),
        "narrative_role": str(raw_cluster.get("narrative_role", "display-backed result cluster")),
        "paragraph_goal": str(
            raw_cluster.get(
                "paragraph_goal",
                "Synthesize the display-backed claims without expanding beyond the visible evidence.",
            )
        ),
        "evidence_sentences": evidence_sentences,
        "linked_reference_ids": _aggregate_reference_ids(packets),
        "claim_author_notes": claim_author_notes,
        "lead_author_note": str(lead_packet.get("author_input", {}).get("claim_note", "")) if lead_packet else "",
        "status": _cluster_status(packets, blocking_issues),
        "warnings": warnings,
        "blocking_issues": blocking_issues,
    }


def build_result_narrative_clusters(
    section_packets: list[dict[str, Any]],
    *,
    cluster_plan_path: Path = NARRATIVE_CLUSTERS_PATH,
) -> dict[str, Any]:
    result_packets = [
        packet
        for packet in section_packets
        if str(packet.get("manuscript_section", "results")) == "results"
    ]
    display_order: list[str] = []
    packets_by_display: dict[str, list[dict[str, Any]]] = {}
    for packet in result_packets:
        display_item_id = _display_id(packet)
        if not display_item_id:
            continue
        if display_item_id not in packets_by_display:
            packets_by_display[display_item_id] = []
            display_order.append(display_item_id)
        packets_by_display[display_item_id].append(packet)

    plan = _load_cluster_plan(cluster_plan_path)
    planned_clusters = [
        cluster
        for cluster in plan.get("clusters", [])
        if isinstance(cluster, dict)
    ]

    clusters: list[dict[str, Any]] = []
    used_display_ids: set[str] = set()
    for raw_cluster in planned_clusters:
        display_item_ids = [
            str(display_item_id)
            for display_item_id in raw_cluster.get("display_item_ids", [])
            if str(display_item_id).strip()
        ]
        if not any(display_item_id in packets_by_display for display_item_id in display_item_ids):
            continue
        cluster = _build_cluster(raw_cluster, packets_by_display=packets_by_display)
        clusters.append(cluster)
        used_display_ids.update(cluster["display_item_ids"])

    for display_item_id in display_order:
        if display_item_id in used_display_ids:
            continue
        clusters.append(
            _build_cluster(
                _default_cluster(display_item_id),
                packets_by_display=packets_by_display,
            )
        )

    blocked_clusters = [
        cluster["cluster_id"]
        for cluster in clusters
        if cluster["status"] == "blocked"
    ]
    provisional_clusters = [
        cluster["cluster_id"]
        for cluster in clusters
        if cluster["status"] == "provisional"
    ]
    overall_status = "ready"
    if blocked_clusters:
        overall_status = "blocked"
    elif provisional_clusters:
        overall_status = "provisional"

    return {
        "generated_from": {
            "display_item_map": _relative_or_absolute(DISPLAY_ITEM_MAP_PATH),
            "writing_plan": _relative_or_absolute(WRITING_PLAN_PATH),
            "narrative_clusters": _relative_or_absolute(cluster_plan_path),
        },
        "cluster_strategy": str(plan.get("cluster_strategy", "display_item")),
        "overall_status": overall_status,
        "cluster_count": len(clusters),
        "ready_cluster_count": sum(1 for cluster in clusters if cluster["status"] == "ready"),
        "provisional_cluster_count": len(provisional_clusters),
        "blocked_cluster_count": len(blocked_clusters),
        "display_item_count": len(display_order),
        "claim_count": sum(len(cluster["claim_ids"]) for cluster in clusters),
        "clusters": clusters,
    }
