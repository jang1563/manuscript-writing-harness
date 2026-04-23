#!/usr/bin/env python3
"""Build section-level drafting briefs from manuscript planning artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manuscript_claims import AUTHOR_CONTENT_INPUTS_PATH, CLAIM_PACKETS_PATH, WRITING_PLAN_PATH, build_claim_packets


REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
PLANS_DIR = MANUSCRIPT_ROOT / "plans"
DRAFTS_DIR = MANUSCRIPT_ROOT / "drafts"
OUTLINE_PATH = PLANS_DIR / "outline.json"
DISPLAY_ITEM_MAP_PATH = PLANS_DIR / "display_item_map.json"
REFERENCE_AUDIT_PATH = REPO_ROOT / "references" / "reports" / "reference_audit.json"
REVIEW_EVIDENCE_PATH = REPO_ROOT / "review" / "reports" / "evidence_summary.json"
SECTION_BRIEFS_JSON_PATH = DRAFTS_DIR / "section_briefs.json"
SECTION_BRIEFS_MARKDOWN_PATH = DRAFTS_DIR / "section_briefs.md"

SECTION_GUIDANCE = {
    "summary": [
        "Lead with the main scientific question, then name only the highest-signal result.",
        "Avoid introducing methods detail unless it is required to interpret scope or credibility.",
    ],
    "introduction": [
        "Use literature-backed context to frame the gap before naming the study objective.",
        "Do not present display-backed result claims as settled background knowledge.",
    ],
    "results": [
        "Write in display order and keep each subsection anchored to visible evidence.",
        "Use claim packets as the first-pass source of truth before polishing prose.",
    ],
    "discussion": [
        "Interpret the strongest claims without simply restating figure legends.",
        "Separate implication, limitation, and external comparison into distinct paragraphs.",
    ],
    "methods": [
        "Document data provenance, analytic choices, and reproducibility hooks explicitly.",
        "Point back to stable artifacts rather than describing untracked runtime state.",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return load_json(path)


def _claim_packets_payload() -> dict[str, Any]:
    if CLAIM_PACKETS_PATH.exists():
        return load_json(CLAIM_PACKETS_PATH)
    return build_claim_packets()


def build_section_briefs() -> dict[str, Any]:
    outline = load_json(OUTLINE_PATH)
    writing_plan = load_json(WRITING_PLAN_PATH)
    display_map = load_json(DISPLAY_ITEM_MAP_PATH)
    claim_packets = _claim_packets_payload()
    reference_audit = _load_optional_json(REFERENCE_AUDIT_PATH)
    review_evidence = _load_optional_json(REVIEW_EVIDENCE_PATH)

    section_order = [str(section_id) for section_id in writing_plan.get("section_order", [])]
    display_items = [item for item in display_map.get("items", []) if isinstance(item, dict)]
    display_items_by_section: dict[str, list[dict[str, Any]]] = {}
    for item in display_items:
        section_id = str(item.get("manuscript_section", "results"))
        display_items_by_section.setdefault(section_id, []).append(item)

    packets_by_section: dict[str, list[dict[str, Any]]] = {}
    for packet in claim_packets.get("claims", []):
        section_id = str(packet.get("manuscript_section", "results"))
        packets_by_section.setdefault(section_id, []).append(packet)
    author_inputs = claim_packets.get("author_inputs", {})

    outline_map = {
        str(section.get("section_id")): section
        for section in outline.get("sections", [])
        if isinstance(section, dict) and section.get("section_id")
    }

    briefs: list[dict[str, Any]] = []
    blocked_sections: list[str] = []
    provisional_sections: list[str] = []

    for section_id in section_order:
        outline_section = outline_map.get(section_id, {})
        section_display_items = display_items_by_section.get(section_id, [])
        section_packets = packets_by_section.get(section_id, [])
        claim_ids = [str(packet.get("claim_id")) for packet in section_packets]
        claim_notes = {
            str(packet.get("claim_id")): str(packet.get("author_input", {}).get("claim_note", ""))
            for packet in section_packets
            if str(packet.get("author_input", {}).get("claim_note", "")).strip()
        }
        citation_refs = sorted(
            {
                reference_id
                for packet in section_packets
                for reference_id in packet.get("citations", {}).get("reference_ids", [])
            }
        )
        status = "ready"
        warnings: list[str] = []
        blocking_issues: list[str] = []

        if section_id == "results" and section_display_items and not section_packets:
            status = "blocked"
            blocking_issues.append("results has display items but no claim packets")
        elif any(packet.get("status") == "blocked" for packet in section_packets):
            status = "blocked"
            blocking_issues.append("one or more result claims are blocked")

        needs_contextual_evidence = section_id in {"summary", "introduction", "discussion", "methods"}
        if review_evidence and review_evidence.get("readiness") != "ready" and needs_contextual_evidence:
            warnings.append(
                f"review evidence layer is `{review_evidence.get('readiness')}`"
            )
            if status != "blocked":
                status = "provisional"
        if reference_audit and reference_audit.get("readiness") != "ready":
            warnings.append(
                f"reference layer is `{reference_audit.get('readiness')}`"
            )
            if status != "blocked":
                status = "provisional"
        if any(packet.get("status") == "provisional" for packet in section_packets):
            if status != "blocked":
                status = "provisional"
        if section_id == "results" and section_packets and not citation_refs:
            warnings.append("results section currently lacks citation-linked claims")

        brief = {
            "section_id": section_id,
            "source": outline_section.get("source"),
            "purpose": outline_section.get("purpose", ""),
            "status": status,
            "display_item_ids": [str(item.get("display_item_id")) for item in section_display_items],
            "claim_ids": claim_ids,
            "claim_packet_count": len(section_packets),
            "reference_context": {
                "readiness": reference_audit.get("readiness") if reference_audit else "absent",
                "citation_edge_count": len(citation_refs),
                "linked_reference_ids": citation_refs,
            },
            "review_context": {
                "readiness": review_evidence.get("readiness") if review_evidence else "absent",
                "included_studies": review_evidence.get("screening", {})
                .get("full_text_summary", {})
                .get("included"),
                "path": str(REVIEW_EVIDENCE_PATH.relative_to(REPO_ROOT))
                if REVIEW_EVIDENCE_PATH.exists()
                else None,
            },
            "author_input": {
                "topic": str(author_inputs.get("topic", "")),
                "section_note": str(author_inputs.get("section_notes", {}).get(section_id, "")),
                "claim_notes": claim_notes,
            },
            "drafting_guidance": SECTION_GUIDANCE.get(section_id, []),
            "warnings": warnings,
            "blocking_issues": blocking_issues,
        }
        briefs.append(brief)
        if status == "blocked":
            blocked_sections.append(section_id)
        elif status == "provisional":
            provisional_sections.append(section_id)

    overall_status = "ready"
    if blocked_sections:
        overall_status = "blocked"
    elif provisional_sections:
        overall_status = "provisional"

    return {
        "generated_from": {
            "outline": str(OUTLINE_PATH.relative_to(REPO_ROOT)),
            "writing_plan": str(WRITING_PLAN_PATH.relative_to(REPO_ROOT)),
            "display_item_map": str(DISPLAY_ITEM_MAP_PATH.relative_to(REPO_ROOT)),
            "claim_packets": _relative_or_absolute(CLAIM_PACKETS_PATH),
            "author_content_inputs": _relative_or_absolute(AUTHOR_CONTENT_INPUTS_PATH),
            "reference_audit": str(REFERENCE_AUDIT_PATH.relative_to(REPO_ROOT)),
            "review_evidence": str(REVIEW_EVIDENCE_PATH.relative_to(REPO_ROOT)),
        },
        "overall_status": overall_status,
        "section_count": len(briefs),
        "ready_section_count": sum(1 for brief in briefs if brief["status"] == "ready"),
        "provisional_section_count": sum(1 for brief in briefs if brief["status"] == "provisional"),
        "blocked_section_count": sum(1 for brief in briefs if brief["status"] == "blocked"),
        "sections": briefs,
    }


def render_section_briefs_markdown(briefs: dict[str, Any]) -> str:
    lines = [
        "# Section Draft Briefs",
        "",
        f"- overall_status: `{briefs['overall_status']}`",
        f"- section_count: `{briefs['section_count']}`",
        f"- ready_section_count: `{briefs['ready_section_count']}`",
        f"- provisional_section_count: `{briefs['provisional_section_count']}`",
        f"- blocked_section_count: `{briefs['blocked_section_count']}`",
        "",
    ]
    for brief in briefs.get("sections", []):
        lines.extend(
            [
                f"## {brief['section_id']}",
                "",
                f"- status: `{brief['status']}`",
                f"- source: `{brief.get('source')}`",
                f"- purpose: {brief.get('purpose')}",
                f"- display_item_ids: `{', '.join(brief.get('display_item_ids', [])) or 'none'}`",
                f"- claim_packet_count: `{brief.get('claim_packet_count', 0)}`",
                f"- reference_readiness: `{brief.get('reference_context', {}).get('readiness')}`",
                f"- review_evidence_readiness: `{brief.get('review_context', {}).get('readiness')}`",
                f"- topic: {brief.get('author_input', {}).get('topic') or 'not set'}",
                "",
                "### Drafting Guidance",
                "",
            ]
        )
        author_input = brief.get("author_input", {})
        if author_input.get("section_note") or author_input.get("claim_notes"):
            lines.extend(["### Author Inputs", ""])
            if author_input.get("section_note"):
                lines.append(f"- section_note: {author_input['section_note']}")
            for claim_id, note in sorted(author_input.get("claim_notes", {}).items()):
                lines.append(f"- {claim_id}: {note}")
            lines.append("")
        for rule in brief.get("drafting_guidance", []):
            lines.append(f"- {rule}")
        if brief.get("warnings"):
            lines.extend(["", "### Warnings", ""])
            for warning in brief["warnings"]:
                lines.append(f"- {warning}")
        if brief.get("blocking_issues"):
            lines.extend(["", "### Blocking Issues", ""])
            for issue in brief["blocking_issues"]:
                lines.append(f"- {issue}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_section_brief_outputs() -> dict[str, str]:
    briefs = build_section_briefs()
    markdown = render_section_briefs_markdown(briefs)
    write_json(SECTION_BRIEFS_JSON_PATH, briefs)
    write_text(SECTION_BRIEFS_MARKDOWN_PATH, markdown)
    return {
        "section_briefs": str(SECTION_BRIEFS_JSON_PATH.relative_to(REPO_ROOT)),
        "section_briefs_markdown": str(SECTION_BRIEFS_MARKDOWN_PATH.relative_to(REPO_ROOT)),
    }
