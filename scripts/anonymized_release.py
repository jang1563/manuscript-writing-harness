#!/usr/bin/env python3
"""Build anonymized/blinded-review preview packages for project release scaffolds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

try:  # pragma: no cover
    from .figures_common import REPO_ROOT, write_text
    from .project_release import _load_project
    from .release_policy import build_release_policy
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, write_text
    from project_release import _load_project
    from release_policy import build_release_policy


MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
ANONYMIZATION_STUB = REPO_ROOT / "workflows" / "release" / "anonymization_check.md"


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _project_dir(project_id: str, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "workflows" / "release" / "projects" / project_id


def _load_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, remainder = text.split("---\n", 1)
    frontmatter, _, body = remainder.partition("\n---\n")
    payload = yaml.safe_load(frontmatter) or {}
    return payload if isinstance(payload, dict) else {}, body


def _render_frontmatter(payload: dict[str, Any]) -> str:
    return "---\n" + yaml.safe_dump(payload, sort_keys=False).strip() + "\n---\n"


def _redacted_index_text() -> str:
    frontmatter, body = _load_frontmatter(MANUSCRIPT_ROOT / "index.md")
    frontmatter["authors"] = [{"name": "Anonymous Authors"}]
    frontmatter["affiliations"] = [{"id": "anon-1", "institution": "Withheld for blind review"}]
    for key in ("corresponding", "email"):
        if isinstance(frontmatter["authors"][0], dict):
            frontmatter["authors"][0].pop(key, None)
    return _render_frontmatter(frontmatter) + body


def _copy_or_redact_section(section_name: str) -> str:
    path = MANUSCRIPT_ROOT / "sections" / section_name
    text = path.read_text(encoding="utf-8")
    if section_name == "06_acknowledgements.md":
        return "## Acknowledgements\n\nWithheld for blind review. Restore contributor, facility, and permit acknowledgements after review.\n"
    if section_name == "07_funding_and_statements.md":
        return "\n".join(
            [
                "## Funding",
                "",
                "Withheld for blind review.",
                "",
                "## Data availability",
                "",
                "Data availability wording will be restored after blind review.",
                "",
                "## Code availability",
                "",
                "Code availability wording will be restored after blind review.",
                "",
                "## Author contributions",
                "",
                "Withheld for blind review.",
                "",
                "## Competing interests",
                "",
                "Competing-interest wording will be restored after blind review.",
                "",
            ]
        )
    return text


def _redacted_release_metadata(project: dict[str, Any], policy_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": project["project_id"],
        "release_profile_id": project["release_profile_id"],
        "title": project["title"],
        "review_model": policy_report["review_model"],
        "anonymization_required": policy_report["anonymization_required"],
        "redacted_creators": ["Anonymous Authors"],
        "redacted_affiliations": ["Withheld for blind review"],
    }


def build_anonymized_release(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    project = _load_project(project_id, repo_root)
    policy_report = build_release_policy(project_id, repo_root)
    blocking_issues = list(policy_report.get("blocking_issues", []))
    warnings = list(policy_report.get("warnings", []))

    if not policy_report.get("anonymization_required"):
        warnings.append("anonymization is not required for this project policy")

    readiness = "ready"
    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"

    package_paths = [
        _relative(ANONYMIZATION_STUB, repo_root),
        _relative(repo_root / project["_project_path"], repo_root),
        f"workflows/release/policies/{project_id}.yml",
    ]

    return {
        "project_id": project_id,
        "release_profile_id": project["release_profile_id"],
        "policy_id": policy_report["policy_id"],
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "review_model": policy_report["review_model"],
        "anonymization_required": policy_report["anonymization_required"],
        "redactions": [
            "manuscript frontmatter authors and affiliations replaced with anonymous placeholders",
            "acknowledgements replaced with a blind-review placeholder block",
            "funding, author-contribution, and competing-interest wording replaced with blind-review placeholders",
            "release metadata creators replaced with anonymous placeholders",
        ],
        "package_paths": package_paths,
    }


def render_anonymized_release_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Anonymized Release Preview: {report['project_id']}",
        "",
        f"- release_profile_id: `{report['release_profile_id']}`",
        f"- policy_id: `{report['policy_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- review_model: `{report['review_model']}`",
        f"- anonymization_required: `{report['anonymization_required']}`",
        "",
        "## Redactions",
        "",
    ]
    lines.extend(f"- {item}" for item in report["redactions"])
    lines.append("")
    if report["blocking_issues"]:
        lines.extend(["## Blocking Issues", ""])
        lines.extend(f"- {item}" for item in report["blocking_issues"])
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    return "\n".join(lines)


def write_anonymized_release_outputs(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    project = _load_project(project_id, repo_root)
    project_root = _project_dir(project_id, repo_root)
    out_root = project_root / "anonymized"
    report = build_anonymized_release(project_id, repo_root)
    policy_report = build_release_policy(project_id, repo_root)

    write_text(out_root / "README.md", "# Anonymized Release Preview\n\nGenerated blinded-review preview files for this project live here.\n")
    write_text(out_root / "manuscript" / "myst.yml", (repo_root / "manuscript" / "myst.yml").read_text(encoding="utf-8"))
    write_text(out_root / "manuscript" / "index.md", _redacted_index_text())
    for section_name in (
        "01_summary.md",
        "02_introduction.md",
        "03_results.md",
        "04_discussion.md",
        "05_methods.md",
        "06_acknowledgements.md",
        "07_funding_and_statements.md",
    ):
        write_text(out_root / "manuscript" / "sections" / section_name, _copy_or_redact_section(section_name))

    write_text(
        out_root / "metadata" / "release_metadata_redacted.json",
        json.dumps(_redacted_release_metadata(project, policy_report), indent=2) + "\n",
    )
    write_text(out_root / "notes" / "blind_review_notes.md", ANONYMIZATION_STUB.read_text(encoding="utf-8"))

    report_json = project_root / "anonymized_release.json"
    report_md = project_root / "anonymized_release.md"
    write_text(report_json, json.dumps(report, indent=2) + "\n")
    write_text(report_md, render_anonymized_release_markdown(report))

    return {
        "report_json": _relative(report_json, repo_root),
        "report_md": _relative(report_md, repo_root),
        "anonymized_root": _relative(out_root, repo_root),
        "anonymized_index": _relative(out_root / "manuscript" / "index.md", repo_root),
        "redacted_metadata": _relative(out_root / "metadata" / "release_metadata_redacted.json", repo_root),
    }
