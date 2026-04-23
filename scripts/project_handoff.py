#!/usr/bin/env python3
"""Assemble a top-level handoff report for real-project onboarding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover
    from .anonymized_release import build_anonymized_release
    from .figures_common import REPO_ROOT, write_text
    from .project_release import _load_project, build_project_release
    from .release_policy import build_release_policy
except ImportError:  # pragma: no cover
    from anonymized_release import build_anonymized_release
    from figures_common import REPO_ROOT, write_text
    from project_release import _load_project, build_project_release
    from release_policy import build_release_policy


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def build_project_handoff(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    project = _load_project(project_id, repo_root)
    project_report = build_project_release(project_id, repo_root)
    policy_report = build_release_policy(project_id, repo_root)
    anonymized_report = build_anonymized_release(project_id, repo_root)

    blocking_issues: list[str] = []
    warnings: list[str] = []
    next_steps: list[str] = []

    for subreport in (project_report, policy_report, anonymized_report):
        if subreport.get("readiness") == "blocked":
            blocking_issues.extend(subreport.get("blocking_issues", []))
    warnings.extend(project_report["warnings"])
    warnings.extend(policy_report["warnings"])
    warnings.extend(anonymized_report["warnings"])

    next_steps.extend(project_report.get("next_steps", []))
    if policy_report["readiness"] != "ready":
        next_steps.append(f"python3 scripts/check_release_policy.py --project {project_id} --write --json")
    if anonymized_report["readiness"] != "ready":
        next_steps.append(f"python3 scripts/check_anonymized_release.py --project {project_id} --write --json")

    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"
    else:
        readiness = "ready"

    package_paths = sorted(
        path
        for path in dict.fromkeys(
            [
                project["_project_path"],
                *project_report.get("package_paths", []),
                *policy_report.get("package_paths", []),
                *anonymized_report.get("package_paths", []),
            ]
        )
        if path
    )

    return {
        "project_id": project_id,
        "title": project["title"],
        "release_profile_id": project["release_profile_id"],
        "readiness": readiness,
        "blocking_issues": sorted(dict.fromkeys(blocking_issues)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "project_readiness": {
            "status": project_report["readiness"],
            "report": f"workflows/release/projects/{project_id}/project_readiness.json",
        },
        "policy_readiness": {
            "status": policy_report["readiness"],
            "report": f"workflows/release/projects/{project_id}/policy_readiness.json",
        },
        "anonymized_preview": {
            "status": anonymized_report["readiness"],
            "report": f"workflows/release/projects/{project_id}/anonymized_release.json",
            "anonymized_index": f"workflows/release/projects/{project_id}/anonymized/manuscript/index.md",
        },
        "package_paths": package_paths,
        "next_steps": list(dict.fromkeys(next_steps)),
    }


def render_project_handoff_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Project Handoff: {report['project_id']}",
        "",
        f"- title: `{report['title']}`",
        f"- release_profile_id: `{report['release_profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- project_readiness: `{report['project_readiness']['status']}`",
        f"- policy_readiness: `{report['policy_readiness']['status']}`",
        f"- anonymized_preview: `{report['anonymized_preview']['status']}`",
        "",
    ]
    if report["blocking_issues"]:
        lines.extend(["## Blocking Issues", ""])
        lines.extend(f"- {item}" for item in report["blocking_issues"])
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {item}" for item in report["warnings"])
        lines.append("")
    lines.extend(["## Next Steps", ""])
    lines.extend(f"- `{item}`" for item in report["next_steps"])
    lines.append("")
    return "\n".join(lines)


def write_project_handoff_outputs(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = build_project_handoff(project_id, repo_root)
    project_root = repo_root / "workflows" / "release" / "projects" / project_id
    report_json = project_root / "handoff.json"
    report_md = project_root / "handoff.md"
    write_text(report_json, json.dumps(report, indent=2) + "\n")
    write_text(report_md, render_project_handoff_markdown(report))
    return {
        "report_json": _relative(report_json, repo_root),
        "report_md": _relative(report_md, repo_root),
    }
