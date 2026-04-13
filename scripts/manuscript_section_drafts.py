#!/usr/bin/env python3
"""Build section-level drafting scaffolds from manuscript briefs and claim packets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manuscript_claims import CLAIM_PACKETS_PATH, build_claim_packets
from manuscript_section_briefs import SECTION_BRIEFS_JSON_PATH, build_section_briefs


REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "manuscript" / "drafts"
REFERENCE_AUDIT_PATH = REPO_ROOT / "references" / "reports" / "reference_audit.json"
REVIEW_EVIDENCE_PATH = REPO_ROOT / "review" / "reports" / "evidence_summary.json"
SECTION_DRAFTS_JSON_PATH = DRAFTS_DIR / "section_drafts.json"
SECTION_DRAFTS_MARKDOWN_PATH = DRAFTS_DIR / "section_drafts.md"

SECTION_OPENERS = {
    "summary": "Use one compact paragraph that names the question, the system, and the single strongest finding.",
    "introduction": "Use 2 to 3 paragraphs: context, gap, then objective.",
    "results": "Use one subsection per display-backed claim cluster, following manuscript display order.",
    "discussion": "Use 3 paragraphs: interpretation, comparison/limitations, then forward-looking implication.",
    "methods": "Use reproducibility-first ordering: data provenance, analysis pipeline, then runtime/export details.",
}


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


def _section_briefs_payload() -> dict[str, Any]:
    if SECTION_BRIEFS_JSON_PATH.exists():
        return load_json(SECTION_BRIEFS_JSON_PATH)
    return build_section_briefs()


def _claim_packets_payload() -> dict[str, Any]:
    if CLAIM_PACKETS_PATH.exists():
        return load_json(CLAIM_PACKETS_PATH)
    return build_claim_packets()


def _results_subsections(section_packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subsections: list[dict[str, Any]] = []
    for packet in section_packets:
        evidence_facts = packet.get("evidence_facts", [])
        lead_statement = (
            str(evidence_facts[0].get("statement"))
            if evidence_facts
            else f"State {packet.get('claim_id')} directly from the display-backed evidence."
        )
        subsections.append(
            {
                "subsection_id": str(packet.get("claim_id")),
                "display_item_id": str(packet.get("display_item", {}).get("display_item_id")),
                "claim_id": str(packet.get("claim_id")),
                "lead_sentence_target": lead_statement,
                "support_points": [
                    f"Reference `{packet.get('display_item', {}).get('display_item_id')}` before expanding interpretation.",
                    "Keep the first sentence observational and move mechanism/implication to the second sentence.",
                    "Do not add external references beyond the citation graph allowances in the packet.",
                ],
                "linked_reference_ids": list(packet.get("citations", {}).get("reference_ids", [])),
                "status": str(packet.get("status", "ready")),
            }
        )
    return subsections


def _generic_paragraph_plan(section_id: str, section_brief: dict[str, Any]) -> list[dict[str, Any]]:
    review_readiness = section_brief.get("review_context", {}).get("readiness", "absent")
    reference_readiness = section_brief.get("reference_context", {}).get("readiness", "absent")
    plans = {
        "summary": [
            "Name the scientific problem and study framing in one sentence.",
            "State only the strongest display-backed result and keep it concrete.",
            "Close with one sentence on why the finding matters.",
        ],
        "introduction": [
            "Open with the broader biological or modeling problem.",
            "Describe the gap that existing methods or studies leave unresolved.",
            "End with the exact study objective and what the manuscript contributes.",
        ],
        "discussion": [
            "Interpret the strongest results without repeating the Results text verbatim.",
            "Compare to literature only where citation coverage is explicit and available.",
            "Name limitations and next-step implications separately.",
        ],
        "methods": [
            "Describe datasets, cohorts, or inputs and where they came from.",
            "Describe the analysis/modeling pipeline in execution order.",
            "Close with reproducibility assets, figure/table generation, and software/runtime details.",
        ],
    }
    return [
        {
            "paragraph_order": index + 1,
            "goal": goal,
            "constraints": [
                f"reference_readiness={reference_readiness}",
                f"review_evidence_readiness={review_readiness}",
            ],
        }
        for index, goal in enumerate(plans.get(section_id, []))
    ]


def build_section_drafts() -> dict[str, Any]:
    section_briefs = _section_briefs_payload()
    claim_packets = _claim_packets_payload()
    reference_audit = _load_optional_json(REFERENCE_AUDIT_PATH)
    review_evidence = _load_optional_json(REVIEW_EVIDENCE_PATH)

    packets_by_section: dict[str, list[dict[str, Any]]] = {}
    for packet in claim_packets.get("claims", []):
        section_id = str(packet.get("manuscript_section", "results"))
        packets_by_section.setdefault(section_id, []).append(packet)

    sections: list[dict[str, Any]] = []
    blocked_sections: list[str] = []
    provisional_sections: list[str] = []

    for brief in section_briefs.get("sections", []):
        section_id = str(brief.get("section_id"))
        section_packets = packets_by_section.get(section_id, [])
        section_status = str(brief.get("status", "ready"))
        if section_id == "results":
            subsection_plan = _results_subsections(section_packets)
        else:
            subsection_plan = _generic_paragraph_plan(section_id, brief)
        scaffold = {
            "section_id": section_id,
            "status": section_status,
            "source": brief.get("source"),
            "purpose": brief.get("purpose"),
            "recommended_opening": SECTION_OPENERS.get(section_id, ""),
            "display_item_ids": list(brief.get("display_item_ids", [])),
            "claim_ids": list(brief.get("claim_ids", [])),
            "subsection_plan": subsection_plan,
            "drafting_constraints": [
                "Treat this as a scaffold, not polished final prose.",
                "Do not promote unsupported background assertions beyond visible evidence or citation coverage.",
                "Revise once references move from provisional to ready.",
            ],
            "reference_readiness": reference_audit.get("readiness") if reference_audit else "absent",
            "review_evidence_readiness": review_evidence.get("readiness") if review_evidence else "absent",
            "warnings": list(brief.get("warnings", [])),
            "blocking_issues": list(brief.get("blocking_issues", [])),
        }
        sections.append(scaffold)
        if section_status == "blocked":
            blocked_sections.append(section_id)
        elif section_status == "provisional":
            provisional_sections.append(section_id)

    overall_status = "ready"
    if blocked_sections:
        overall_status = "blocked"
    elif provisional_sections:
        overall_status = "provisional"

    return {
        "generated_from": {
            "section_briefs": str(SECTION_BRIEFS_JSON_PATH.relative_to(REPO_ROOT)),
            "claim_packets": str(CLAIM_PACKETS_PATH.relative_to(REPO_ROOT)),
            "reference_audit": str(REFERENCE_AUDIT_PATH.relative_to(REPO_ROOT)),
            "review_evidence": str(REVIEW_EVIDENCE_PATH.relative_to(REPO_ROOT)),
        },
        "overall_status": overall_status,
        "section_count": len(sections),
        "ready_section_count": sum(1 for section in sections if section["status"] == "ready"),
        "provisional_section_count": sum(1 for section in sections if section["status"] == "provisional"),
        "blocked_section_count": sum(1 for section in sections if section["status"] == "blocked"),
        "sections": sections,
    }


def render_section_drafts_markdown(drafts: dict[str, Any]) -> str:
    lines = [
        "# Section Draft Scaffolds",
        "",
        f"- overall_status: `{drafts['overall_status']}`",
        f"- section_count: `{drafts['section_count']}`",
        f"- ready_section_count: `{drafts['ready_section_count']}`",
        f"- provisional_section_count: `{drafts['provisional_section_count']}`",
        f"- blocked_section_count: `{drafts['blocked_section_count']}`",
        "",
    ]
    for section in drafts.get("sections", []):
        lines.extend(
            [
                f"## {section['section_id']}",
                "",
                f"- status: `{section['status']}`",
                f"- source: `{section.get('source')}`",
                f"- recommended_opening: {section.get('recommended_opening')}",
                f"- display_item_ids: `{', '.join(section.get('display_item_ids', [])) or 'none'}`",
                "",
                "### Subsection Plan",
                "",
            ]
        )
        for item in section.get("subsection_plan", []):
            if "subsection_id" in item:
                lines.append(
                    f"- `{item['subsection_id']}` via `{item.get('display_item_id')}`: {item.get('lead_sentence_target')}"
                )
            else:
                lines.append(
                    f"- paragraph {item.get('paragraph_order')}: {item.get('goal')}"
                )
        if section.get("warnings"):
            lines.extend(["", "### Warnings", ""])
            for warning in section["warnings"]:
                lines.append(f"- {warning}")
        if section.get("blocking_issues"):
            lines.extend(["", "### Blocking Issues", ""])
            for issue in section["blocking_issues"]:
                lines.append(f"- {issue}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_section_draft_outputs() -> dict[str, str]:
    drafts = build_section_drafts()
    markdown = render_section_drafts_markdown(drafts)
    write_json(SECTION_DRAFTS_JSON_PATH, drafts)
    write_text(SECTION_DRAFTS_MARKDOWN_PATH, markdown)
    return {
        "section_drafts": str(SECTION_DRAFTS_JSON_PATH.relative_to(REPO_ROOT)),
        "section_drafts_markdown": str(SECTION_DRAFTS_MARKDOWN_PATH.relative_to(REPO_ROOT)),
    }
