#!/usr/bin/env python3
"""Build claim-driven drafting packets from manuscript planning artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
PLANS_DIR = MANUSCRIPT_ROOT / "plans"
DRAFTS_DIR = MANUSCRIPT_ROOT / "drafts"
DISPLAY_ITEM_MAP_PATH = PLANS_DIR / "display_item_map.json"
WRITING_PLAN_PATH = PLANS_DIR / "writing_plan.json"
REVISION_CHECKS_PATH = PLANS_DIR / "revision_checks.json"
OUTLINE_PATH = PLANS_DIR / "outline.json"
CITATION_GRAPH_PATH = PLANS_DIR / "citation_graph.json"
REFERENCE_AUDIT_PATH = REPO_ROOT / "references" / "reports" / "reference_audit.json"
REVIEW_EVIDENCE_PATH = REPO_ROOT / "review" / "reports" / "evidence_summary.json"
CLAIM_PACKETS_PATH = PLANS_DIR / "claim_packets.json"
CLAIM_COVERAGE_PATH = PLANS_DIR / "claim_coverage.json"
RESULTS_CLAIM_DRAFTS_PATH = DRAFTS_DIR / "results_claim_packets.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def _load_fact_sheet(relative_path: str) -> dict[str, Any]:
    return load_json(REPO_ROOT / relative_path)


def _load_legend(relative_path: str) -> str:
    if not relative_path:
        return ""
    path = REPO_ROOT / relative_path
    if not path.exists() or path.is_dir():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _section_order_map() -> dict[str, int]:
    writing_plan = load_json(WRITING_PLAN_PATH)
    return {
        str(section_id): index
        for index, section_id in enumerate(writing_plan.get("section_order", []))
    }


def _display_item_sort_key(item: dict[str, Any], order_map: dict[str, int]) -> tuple[int, int, str]:
    section = str(item.get("manuscript_section", "results"))
    section_rank = order_map.get(section, 999)
    display_refs = load_json(WRITING_PLAN_PATH).get("display_item_refs", [])
    try:
        display_rank = display_refs.index(item.get("display_item_id"))
    except ValueError:
        display_rank = 999
    return (section_rank, display_rank, str(item.get("display_item_id", "")))


def _citation_lookup(graph: dict[str, Any]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for edge in graph.get("edges", []):
        claim_id = str(edge.get("from", ""))
        ref_id = str(edge.get("to", ""))
        if not claim_id or not ref_id:
            continue
        mapping.setdefault(claim_id, [])
        if ref_id not in mapping[claim_id]:
            mapping[claim_id].append(ref_id)
    return mapping


def build_claim_packets() -> dict[str, Any]:
    display_map = load_json(DISPLAY_ITEM_MAP_PATH)
    writing_plan = load_json(WRITING_PLAN_PATH)
    revision_checks = load_json(REVISION_CHECKS_PATH)
    outline = load_json(OUTLINE_PATH)
    citation_graph = load_json(CITATION_GRAPH_PATH)
    reference_audit = _load_optional_json(REFERENCE_AUDIT_PATH)
    review_evidence = _load_optional_json(REVIEW_EVIDENCE_PATH)

    citation_lookup = _citation_lookup(citation_graph)
    order_map = _section_order_map()
    display_items = sorted(
        [item for item in display_map.get("items", []) if isinstance(item, dict)],
        key=lambda item: _display_item_sort_key(item, order_map),
    )
    section_purpose = {
        str(section.get("section_id")): str(section.get("purpose", ""))
        for section in outline.get("sections", [])
        if isinstance(section, dict)
    }

    packets: list[dict[str, Any]] = []
    blocked_claims: list[str] = []
    provisional_claims: list[str] = []

    for item in display_items:
        claim_ids = [str(claim_id) for claim_id in item.get("claim_ids", [])]
        if not claim_ids:
            continue
        fact_sheet = _load_fact_sheet(str(item.get("fact_sheet")))
        facts = fact_sheet.get("facts", [])
        legend = _load_legend(str(item.get("legend_path", "")))

        for claim_id in claim_ids:
            matched_facts = [fact for fact in facts if str(fact.get("fact_id")) == claim_id]
            citations = citation_lookup.get(claim_id, [])
            claim_status = "ready"
            claim_warnings: list[str] = []
            claim_blockers: list[str] = []

            if not matched_facts:
                claim_status = "blocked"
                claim_blockers.append("no fact-sheet statement was found for this claim")
            if citations and reference_audit and reference_audit.get("readiness") != "ready":
                claim_warnings.append(
                    f"citations are linked, but reference layer is `{reference_audit.get('readiness')}`"
                )
                if claim_status != "blocked":
                    claim_status = "provisional"
            elif not citations:
                claim_warnings.append("no citation edge is currently linked to this claim")

            packet = {
                "claim_id": claim_id,
                "manuscript_section": str(item.get("manuscript_section", "results")),
                "section_purpose": section_purpose.get(str(item.get("manuscript_section", "")), ""),
                "display_item": {
                    "display_item_id": str(item.get("display_item_id")),
                    "type": str(item.get("type", "figure")),
                    "preview_asset": item.get("preview_asset"),
                    "spec_path": item.get("spec_path"),
                    "schema_path": item.get("schema_path"),
                    "fact_sheet": item.get("fact_sheet"),
                    "legend_path": item.get("legend_path"),
                    "source_data": list(item.get("source_data", [])),
                    "manifest_path": item.get("manifest_path"),
                },
                "evidence_facts": matched_facts,
                "legend_summary": legend,
                "citations": {
                    "reference_ids": citations,
                    "reference_layer_readiness": reference_audit.get("readiness") if reference_audit else "absent",
                },
                "drafting_guidance": [
                    "State the claim in one sentence before interpreting mechanism or implication.",
                    "Anchor the prose to the fact-sheet statement instead of rephrasing the legend from memory.",
                    "Use only citation keys already linked in the citation graph if you add background context.",
                    "Keep the first results sentence display-backed; move broader context to the Discussion.",
                ],
                "revision_checks": revision_checks.get("checks", []),
                "supporting_context": {
                    "review_evidence_readiness": review_evidence.get("readiness") if review_evidence else "absent",
                    "review_evidence_path": str(REVIEW_EVIDENCE_PATH.relative_to(REPO_ROOT))
                    if REVIEW_EVIDENCE_PATH.exists()
                    else None,
                    "reference_audit_path": str(REFERENCE_AUDIT_PATH.relative_to(REPO_ROOT))
                    if REFERENCE_AUDIT_PATH.exists()
                    else None,
                },
                "status": claim_status,
                "blocking_issues": claim_blockers,
                "warnings": claim_warnings,
            }
            packets.append(packet)
            if claim_status == "blocked":
                blocked_claims.append(claim_id)
            elif claim_status == "provisional":
                provisional_claims.append(claim_id)

    overall_status = "ready"
    if blocked_claims:
        overall_status = "blocked"
    elif provisional_claims or (reference_audit and reference_audit.get("readiness") != "ready"):
        overall_status = "provisional"

    return {
        "generated_from": {
            "display_item_map": str(DISPLAY_ITEM_MAP_PATH.relative_to(REPO_ROOT)),
            "writing_plan": str(WRITING_PLAN_PATH.relative_to(REPO_ROOT)),
            "revision_checks": str(REVISION_CHECKS_PATH.relative_to(REPO_ROOT)),
            "outline": str(OUTLINE_PATH.relative_to(REPO_ROOT)),
            "citation_graph": str(CITATION_GRAPH_PATH.relative_to(REPO_ROOT)),
            "reference_audit": str(REFERENCE_AUDIT_PATH.relative_to(REPO_ROOT)),
            "review_evidence": str(REVIEW_EVIDENCE_PATH.relative_to(REPO_ROOT)),
        },
        "overall_status": overall_status,
        "claim_count": len(packets),
        "ready_claim_count": sum(1 for packet in packets if packet["status"] == "ready"),
        "provisional_claim_count": sum(1 for packet in packets if packet["status"] == "provisional"),
        "blocked_claim_count": sum(1 for packet in packets if packet["status"] == "blocked"),
        "claims": packets,
    }


def build_claim_coverage(packets: dict[str, Any]) -> dict[str, Any]:
    claims = packets.get("claims", [])
    blocked_claims = [claim["claim_id"] for claim in claims if claim["status"] == "blocked"]
    provisional_claims = [claim["claim_id"] for claim in claims if claim["status"] == "provisional"]
    display_items = sorted(
        {claim["display_item"]["display_item_id"] for claim in claims if claim.get("display_item")}
    )
    citation_linked = sorted(
        {
            claim["claim_id"]
            for claim in claims
            if claim.get("citations", {}).get("reference_ids")
        }
    )
    return {
        "overall_status": packets["overall_status"],
        "claim_count": packets["claim_count"],
        "ready_claim_count": packets["ready_claim_count"],
        "provisional_claim_count": packets["provisional_claim_count"],
        "blocked_claim_count": packets["blocked_claim_count"],
        "blocked_claim_ids": blocked_claims,
        "provisional_claim_ids": provisional_claims,
        "display_items_covered": display_items,
        "claims_with_citation_edges": citation_linked,
    }


def render_results_claim_packets_markdown(packets: dict[str, Any]) -> str:
    lines = [
        "# Results Claim Draft Packets",
        "",
        f"- overall_status: `{packets['overall_status']}`",
        f"- claim_count: `{packets['claim_count']}`",
        f"- ready_claim_count: `{packets['ready_claim_count']}`",
        f"- provisional_claim_count: `{packets['provisional_claim_count']}`",
        f"- blocked_claim_count: `{packets['blocked_claim_count']}`",
        "",
    ]
    for packet in packets.get("claims", []):
        display_item = packet["display_item"]
        lines.extend(
            [
                f"## {packet['claim_id']}",
                "",
                f"- status: `{packet['status']}`",
                f"- manuscript_section: `{packet['manuscript_section']}`",
                f"- display_item: `{display_item['display_item_id']}`",
                f"- preview_asset: `{display_item.get('preview_asset')}`",
                f"- fact_sheet: `{display_item.get('fact_sheet')}`",
                "",
                "### Evidence Facts",
                "",
            ]
        )
        for fact in packet.get("evidence_facts", []):
            lines.append(f"- `{fact.get('fact_id')}`: {fact.get('statement')}")
        if packet.get("legend_summary"):
            lines.extend(["", "### Legend Summary", "", packet["legend_summary"], ""])
        if packet.get("citations", {}).get("reference_ids"):
            lines.extend(["### Citation Links", ""])
            for reference_id in packet["citations"]["reference_ids"]:
                lines.append(f"- `{reference_id}`")
            lines.append("")
        if packet.get("warnings"):
            lines.extend(["### Warnings", ""])
            for warning in packet["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")
        if packet.get("blocking_issues"):
            lines.extend(["### Blocking Issues", ""])
            for issue in packet["blocking_issues"]:
                lines.append(f"- {issue}")
            lines.append("")
        lines.extend(["### Drafting Guidance", ""])
        for rule in packet.get("drafting_guidance", []):
            lines.append(f"- {rule}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_claim_outputs() -> dict[str, str]:
    packets = build_claim_packets()
    coverage = build_claim_coverage(packets)
    markdown = render_results_claim_packets_markdown(packets)

    write_json(CLAIM_PACKETS_PATH, packets)
    write_json(CLAIM_COVERAGE_PATH, coverage)
    write_text(RESULTS_CLAIM_DRAFTS_PATH, markdown)

    return {
        "claim_packets": str(CLAIM_PACKETS_PATH.relative_to(REPO_ROOT)),
        "claim_coverage": str(CLAIM_COVERAGE_PATH.relative_to(REPO_ROOT)),
        "draft_markdown": str(RESULTS_CLAIM_DRAFTS_PATH.relative_to(REPO_ROOT)),
    }
