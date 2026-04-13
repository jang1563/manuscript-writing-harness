#!/usr/bin/env python3
"""Build section-level prose drafts from section draft scaffolds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manuscript_section_drafts import SECTION_DRAFTS_JSON_PATH, build_section_drafts


REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "manuscript" / "drafts"
SECTIONS_DIR = DRAFTS_DIR / "sections"
SECTION_BODIES_DIR = DRAFTS_DIR / "section_bodies"
SECTION_PROSE_JSON_PATH = DRAFTS_DIR / "section_prose.json"
SECTION_PROSE_MARKDOWN_PATH = DRAFTS_DIR / "section_prose.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _section_drafts_payload() -> dict[str, Any]:
    if SECTION_DRAFTS_JSON_PATH.exists():
        return load_json(SECTION_DRAFTS_JSON_PATH)
    return build_section_drafts()


def _summary_paragraphs() -> list[str]:
    return [
        "We set out to test whether a reproducible manuscript harness can keep biological and AI/ML claims tightly bound to the figures, tables, and planning artifacts that support them.",
        "Across the current example assets, the strongest display-backed findings include treatment-associated response divergence, interferon-skewed differential expression, and pathway-level directionality recovered through a reproducible fgsea export in the biological track, together with consistently better discrimination, calibration, and training stability in the foundation-model evaluation track.",
        "Together, these outputs show how the harness can surface result-ready claims before polishing narrative prose, while keeping figure provenance, pathway-analysis artifacts, and reference readiness visible as drafting constraints rather than hidden cleanup tasks.",
    ]


def _introduction_paragraphs() -> list[str]:
    return [
        "Scientific manuscripts often lose traceability when the prose, figures, tables, pathway-analysis outputs, and literature context evolve separately. That problem becomes more acute when a project spans both bioinformatics-style evidence summaries and AI/ML model-evaluation figures, because the writing layer can drift away from the display items that actually carry the claim.",
        "The present harness is designed to reduce that drift by making planning artifacts, figure specifications, fact sheets, evidence summaries, citation graphs, and generated analysis exports explicit. Instead of asking the writer to reconstruct the evidence path from memory, it keeps display-backed claims visible at drafting time and exposes whether pathway summaries, review evidence, and citations are already ready.",
        "Within that framing, the manuscript objective is not only to present biological and model-evaluation results but also to demonstrate a reproducible writing workflow in which figure bundles, evidence packages, fgsea-derived pathway summaries, and citation coverage remain inspectable throughout drafting.",
    ]


def _discussion_paragraphs() -> list[str]:
    return [
        "The current outputs suggest that the strongest value of the harness is organizational rather than cosmetic: it keeps major claims anchored to explicit display items, and it makes figure provenance, pathway-analysis exports, and reference support inspectable while drafting.",
        "That structure is especially useful when the manuscript mixes biological interpretation with AI/ML evaluation. The figure bundles and claim packets let us compare modalities without collapsing them into one undifferentiated narrative, while the fgsea-backed pathway branch shows how an upstream analysis artifact can be carried forward into a publication-quality figure without manual copy-paste.",
        "The main limitation at this stage is no longer the bibliography layer, which is now tracked and ready, but the fact that the current figures and prose still revolve around exemplar datasets. The next submission-facing step is therefore to swap the demo inputs for study-specific data while preserving the same evidence path and review checks.",
    ]


def _methods_paragraphs() -> list[str]:
    return [
        "The manuscript harness is organized around tracked planning artifacts, script-generated figures and tables, and explicit manuscript overlays. Display items are specified in registry-backed figure classes, rendered in both Python and R where supported, and reviewed through generated QA surfaces before they are wired into the manuscript.",
        "For the bioinformatics demonstration branch, differential-expression style rankings are carried into pathway analysis through a scripted fgsea pipeline. Ranked statistics are read from a tracked CSV input, pathway definitions are loaded from a GMT file, fgsea is executed through an R wrapper, and the resulting preranked enrichment summary is exported as a normalized dot-plot table that is consumed directly by `figure_05_pathway_enrichment_dot`.",
        "Systematic-review style evidence is summarized through protocol, query, screening, extraction, bias, and PRISMA artifacts, while the reference layer maintains a bibliography, citation graph, claim-to-reference mappings, and an integrity audit that expose whether each claim has usable literature support. Drafting support is then generated in stages: claim packets summarize display-backed result statements, section briefs translate those packets into section-level writing constraints, and section prose drafts turn the resulting scaffolds into editable text artifacts without overwriting the canonical manuscript sections.",
    ]


RESULTS_SPECIAL_CASES = {
    "claim_cell_cycle_pathway_suppression": "Because these summaries come from the preranked fgsea branch rather than an ad hoc pathway annotation step, the pathway-level suppression reinforces that proliferative programs are coherently downregulated at the gene-set level and not only at isolated genes.",
    "claim_pathway_effect_sizes_align_with_directionality": "The fgsea-derived dot-plot export therefore acts as the downstream pathway summary of the ranked-expression analysis, preserving both effect magnitude and biological directionality in a format that stays aligned with the upstream gene-level figures.",
}


def _results_sections(section: dict[str, Any]) -> list[dict[str, str]]:
    subsections: list[dict[str, str]] = []
    for item in section.get("subsection_plan", []):
        claim_id = str(item.get("claim_id", item.get("subsection_id", "")))
        display_item_id = str(item.get("display_item_id", ""))
        lead = str(item.get("lead_sentence_target", "")).strip()
        second = RESULTS_SPECIAL_CASES.get(
            claim_id,
            (
                f"This pattern is shown directly in `{display_item_id}`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced."
                if display_item_id
                else "The next sentence should stay close to the visible evidence before broader implications are introduced."
            ),
        )
        subsections.append(
            {
                "subsection_id": claim_id,
                "display_item_id": display_item_id,
                "heading": claim_id.replace("claim_", "").replace("_", " ").capitalize(),
                "paragraph": f"{lead} {second}".strip(),
            }
        )
    return subsections


def _render_section_markdown(section_id: str, section_payload: dict[str, Any]) -> str:
    title = section_id.replace("_", " ").title()
    lines = [f"## {title}", ""]
    body = _render_section_body_markdown(section_id, section_payload)
    if body:
        lines.append(body.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_section_body_markdown(section_id: str, section_payload: dict[str, Any]) -> str:
    lines: list[str] = []
    if section_id == "results":
        for subsection in section_payload.get("subsections", []):
            lines.extend(
                [
                    f"### {subsection['heading']}",
                    "",
                    subsection["paragraph"],
                    "",
                ]
            )
    else:
        for paragraph in section_payload.get("paragraphs", []):
            lines.extend([paragraph, ""])
    return "\n".join(lines).rstrip() + "\n"


def build_section_prose() -> dict[str, Any]:
    drafts = _section_drafts_payload()
    sections: list[dict[str, Any]] = []

    for section in drafts.get("sections", []):
        section_id = str(section.get("section_id"))
        payload: dict[str, Any] = {
            "section_id": section_id,
            "status": str(section.get("status", "ready")),
            "source": section.get("source"),
            "recommended_opening": section.get("recommended_opening"),
            "warnings": list(section.get("warnings", [])),
            "blocking_issues": list(section.get("blocking_issues", [])),
        }
        if section_id == "summary":
            payload["paragraphs"] = _summary_paragraphs()
        elif section_id == "introduction":
            payload["paragraphs"] = _introduction_paragraphs()
        elif section_id == "discussion":
            payload["paragraphs"] = _discussion_paragraphs()
        elif section_id == "methods":
            payload["paragraphs"] = _methods_paragraphs()
        elif section_id == "results":
            payload["subsections"] = _results_sections(section)
        sections.append(payload)

    return {
        "generated_from": {
            "section_drafts": str(SECTION_DRAFTS_JSON_PATH.relative_to(REPO_ROOT)),
        },
        "overall_status": drafts.get("overall_status", "ready"),
        "section_count": len(sections),
        "sections": sections,
    }


def render_section_prose_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Section Prose Drafts",
        "",
        f"- overall_status: `{payload['overall_status']}`",
        f"- section_count: `{payload['section_count']}`",
        "",
    ]
    for section in payload.get("sections", []):
        lines.append(_render_section_markdown(str(section["section_id"]), section).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_section_prose_outputs() -> dict[str, str]:
    payload = build_section_prose()
    markdown = render_section_prose_markdown(payload)
    write_json(SECTION_PROSE_JSON_PATH, payload)
    write_text(SECTION_PROSE_MARKDOWN_PATH, markdown)
    for section in payload.get("sections", []):
        section_id = str(section["section_id"])
        write_text(SECTIONS_DIR / f"{section_id}.md", _render_section_markdown(section_id, section))
        write_text(
            SECTION_BODIES_DIR / f"{section_id}.md",
            _render_section_body_markdown(section_id, section),
        )
    return {
        "section_prose": str(SECTION_PROSE_JSON_PATH.relative_to(REPO_ROOT)),
        "section_prose_markdown": str(SECTION_PROSE_MARKDOWN_PATH.relative_to(REPO_ROOT)),
        "section_directory": str(SECTIONS_DIR.relative_to(REPO_ROOT)),
        "section_body_directory": str(SECTION_BODIES_DIR.relative_to(REPO_ROOT)),
    }
