#!/usr/bin/env python3
"""Assemble real-manuscript promotion preflight checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT, write_text
    from .manuscript_scope_common import build_manuscript_scope_status
    from .pre_submission_audit import build_bibliography_scope_gate
    from .project_handoff import build_project_handoff
    from .project_release import build_project_release
    from .reference_integrity import build_reference_report
    from .venue_overlay import build_submission_gate, evaluate_venue
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, write_text
    from manuscript_scope_common import build_manuscript_scope_status
    from pre_submission_audit import build_bibliography_scope_gate
    from project_handoff import build_project_handoff
    from project_release import build_project_release
    from reference_integrity import build_reference_report
    from venue_overlay import build_submission_gate, evaluate_venue


PREFLIGHT_CONFIG_PATH = REPO_ROOT / "manuscript" / "plans" / "real_manuscript_preflight.json"
RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_preflight_config(path: Path = PREFLIGHT_CONFIG_PATH) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Missing real-manuscript preflight config: {_relative(path)}")
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("real-manuscript preflight config must be a JSON object")
    for field in ("preflight_id", "project_id", "release_profile_id", "venue_id"):
        if not str(payload.get(field, "")).strip():
            raise ValueError(f"real-manuscript preflight config is missing `{field}`")
    return payload


def _status_check(
    *,
    check_id: str,
    observed: str,
    required: str,
    summary: str,
    evidence: dict[str, Any] | None = None,
    remediation: str = "",
    ready: bool | None = None,
) -> dict[str, Any]:
    passed = observed == required if ready is None else ready
    return {
        "check_id": check_id,
        "status": "ready" if passed else "blocked",
        "observed": observed,
        "required": required,
        "summary": summary,
        "evidence": evidence or {},
        "remediation": remediation,
    }


def _contains_placeholder_release_warning(warnings: list[str]) -> bool:
    return any("release_metadata." in warning and "placeholder" in warning for warning in warnings)


def _active_project_study_ready(project_report: dict[str, Any]) -> bool:
    return bool(
        project_report.get("study_report", {})
        .get("active_profile", {})
        .get("is_active_source")
    )


def build_real_manuscript_preflight(
    repo_root: Path = REPO_ROOT,
    *,
    config_path: Path = PREFLIGHT_CONFIG_PATH,
) -> dict[str, Any]:
    if repo_root != REPO_ROOT:
        raise ValueError("real manuscript preflight currently expects the canonical repo root")

    config = load_preflight_config(config_path)
    project_id = str(config["project_id"])
    release_profile_id = str(config["release_profile_id"])
    venue_id = str(config["venue_id"])
    requirements = config.get("requirements", {})
    if not isinstance(requirements, dict):
        requirements = {}

    manuscript_scope = build_manuscript_scope_status(repo_root)
    reference_report = build_reference_report(sync_graph=False)
    bibliography_gate = build_bibliography_scope_gate(reference_report)
    venue_report = evaluate_venue(venue_id, repo_root=repo_root)
    submission_gate = build_submission_gate([venue_report])
    project_release = build_project_release(project_id, repo_root=repo_root)
    project_handoff = build_project_handoff(project_id, repo_root=repo_root)

    release_metadata_warnings = [
        str(warning)
        for warning in project_release.get("warnings", [])
        if "release_metadata." in str(warning)
    ]
    placeholder_warnings_present = _contains_placeholder_release_warning(release_metadata_warnings)
    active_study_ready = _active_project_study_ready(project_release)
    scope_metadata_valid = manuscript_scope.get("status") != "invalid"
    active_study_required = bool(requirements.get("active_project_study_source", True))

    checks = [
        _status_check(
            check_id="manuscript_scope_metadata_valid",
            observed="valid" if scope_metadata_valid else "invalid",
            required=str(requirements.get("manuscript_scope_metadata", "valid")),
            ready=scope_metadata_valid,
            summary="manuscript scope metadata is valid enough to be promoted after external gates pass",
            evidence={
                "scope_readiness": manuscript_scope.get("status"),
                "scope_status": manuscript_scope.get("scope_status"),
                "confirmed_on": manuscript_scope.get("confirmed_on"),
                "issues": manuscript_scope.get("issues", []),
                "warnings": manuscript_scope.get("warnings", []),
            },
            remediation="Fix manuscript/plans/manuscript_scope.json validation issues before promotion.",
        ),
        _status_check(
            check_id="bibliography_scope_confirmed",
            observed=str(bibliography_gate.get("current_manuscript_scope_status", "unknown")),
            required=str(requirements.get("bibliography_scope_status", "confirmed")),
            summary="bibliography export has been confirmed for the accepted manuscript scope",
            evidence=bibliography_gate,
            remediation="Run confirm_bibliography_scope.py after replacing the starter export with the accepted manuscript bibliography.",
        ),
        _status_check(
            check_id="venue_verification_current",
            observed=str(venue_report.get("verification", {}).get("status", "unknown")),
            required=str(requirements.get("venue_verification_status", "current")),
            summary=f"target venue `{venue_id}` verification is current for submission use",
            evidence={
                "venue": venue_id,
                "submission_gate": submission_gate,
                "verification": venue_report.get("verification", {}),
            },
            remediation="Run confirm_venue_verification.py after checking the exact target venue-year author guidance.",
        ),
        _status_check(
            check_id="release_profile_matches_project",
            observed=str(project_release.get("release_profile_id", "")),
            required=release_profile_id,
            summary="preflight config targets the same release profile as the project scaffold",
            evidence={
                "project_id": project_id,
                "project_release_profile_id": project_release.get("release_profile_id"),
            },
            remediation="Update manuscript/plans/real_manuscript_preflight.json or the project manifest so the release profile ids match.",
        ),
        _status_check(
            check_id="project_release_ready",
            observed=str(project_release.get("readiness", "unknown")),
            required=str(requirements.get("project_release_readiness", "ready")),
            summary=f"project release scaffold `{project_id}` is ready",
            evidence={
                "warnings": project_release.get("warnings", []),
                "blocking_issues": project_release.get("blocking_issues", []),
                "next_steps": project_release.get("next_steps", []),
            },
            remediation="Complete the project release next steps, including real inputs, licensed pathway files, and release metadata.",
        ),
        _status_check(
            check_id="project_handoff_ready",
            observed=str(project_handoff.get("readiness", "unknown")),
            required=str(requirements.get("project_handoff_readiness", "ready")),
            summary=f"project handoff `{project_id}` is ready",
            evidence={
                "warnings": project_handoff.get("warnings", []),
                "blocking_issues": project_handoff.get("blocking_issues", []),
                "next_steps": project_handoff.get("next_steps", []),
            },
            remediation="Clear project handoff warnings for policy, anonymized preview, and release readiness.",
        ),
        _status_check(
            check_id="active_project_study_source",
            observed=str(active_study_ready).lower(),
            required=str(active_study_required).lower(),
            ready=active_study_ready == active_study_required,
            summary="project study profile is the active fgsea source that feeds the manuscript figure",
            evidence={
                "study_id": project_release.get("study_id"),
                "active_profile": project_release.get("study_report", {}).get("active_profile", {}),
            },
            remediation="Run the project MSigDB profile and activate it before final manuscript promotion.",
        ),
        _status_check(
            check_id="release_metadata_placeholders_absent",
            observed="present" if placeholder_warnings_present else "absent",
            required=str(requirements.get("release_metadata_placeholders", "absent")),
            summary="release metadata no longer contains scaffold placeholders",
            evidence={"warnings": release_metadata_warnings},
            remediation="Replace release metadata placeholder author names, affiliations, and summaries.",
        ),
    ]

    blocking_issues = [
        check["summary"]
        for check in checks
        if check["status"] != "ready"
    ]
    readiness = "ready" if not blocking_issues else "blocked"

    package_paths = sorted(
        dict.fromkeys(
            [
                _relative(config_path, repo_root),
                manuscript_scope["manifest_path"],
                "references/metadata/bibliography_source.yml",
                str(venue_report.get("config_path", "")),
                *project_release.get("package_paths", []),
                *project_handoff.get("package_paths", []),
            ]
        )
    )

    return {
        "preflight_id": str(config["preflight_id"]),
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "project_id": project_id,
        "release_profile_id": release_profile_id,
        "venue_id": venue_id,
        "target_scope_status": str(config.get("target_scope_status", "real")),
        "checks": checks,
        "evidence": {
            "manuscript_scope": manuscript_scope,
            "bibliography_scope_gate": bibliography_gate,
            "venue_verification": venue_report.get("verification", {}),
            "submission_gate": submission_gate,
            "project_release_readiness": project_release.get("readiness"),
            "project_handoff_readiness": project_handoff.get("readiness"),
        },
        "notes": list(config.get("notes", [])),
        "package_paths": package_paths,
        "repo_root": _relative(repo_root, repo_root),
    }


def build_real_manuscript_preflight_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": f"{report['preflight_id']}_package",
        "readiness": report["readiness"],
        "blocking_issue_count": len(report["blocking_issues"]),
        "project_id": report["project_id"],
        "release_profile_id": report["release_profile_id"],
        "venue_id": report["venue_id"],
        "ready_check_count": sum(1 for check in report["checks"] if check["status"] == "ready"),
        "blocked_check_count": sum(1 for check in report["checks"] if check["status"] != "ready"),
        "package_paths": report["package_paths"],
    }


def render_real_manuscript_preflight_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Real Manuscript Preflight",
        "",
        f"- preflight_id: `{report['preflight_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- project_id: `{report['project_id']}`",
        f"- release_profile_id: `{report['release_profile_id']}`",
        f"- venue_id: `{report['venue_id']}`",
        f"- target_scope_status: `{report['target_scope_status']}`",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"]:
        lines.append(
            f"- `{check['check_id']}`: `{check['status']}` "
            f"(observed `{check['observed']}`, required `{check['required']}`)"
        )
        lines.append(f"  - {check['summary']}")
        if check.get("remediation") and check["status"] != "ready":
            lines.append(f"  - remediation: {check['remediation']}")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        lines.extend(f"- {issue}" for issue in report["blocking_issues"])
    if report.get("notes"):
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in report["notes"])
    lines.extend(["", "## Package Paths", ""])
    lines.extend(f"- `{path}`" for path in report["package_paths"])
    return "\n".join(lines).rstrip() + "\n"


def write_real_manuscript_preflight_outputs(
    repo_root: Path = REPO_ROOT,
    *,
    config_path: Path = PREFLIGHT_CONFIG_PATH,
) -> dict[str, str]:
    report = build_real_manuscript_preflight(repo_root=repo_root, config_path=config_path)
    manifest = build_real_manuscript_preflight_manifest(report)
    report_json = REPORTS_DIR / "real_manuscript_preflight.json"
    report_md = REPORTS_DIR / "real_manuscript_preflight.md"
    manifest_path = MANIFESTS_DIR / "real_manuscript_preflight.json"
    write_text(report_json, json.dumps(report, indent=2) + "\n")
    write_text(report_md, render_real_manuscript_preflight_markdown(report))
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    return {
        "report_json": _relative(report_json, repo_root),
        "report_md": _relative(report_md, repo_root),
        "manifest": _relative(manifest_path, repo_root),
    }
