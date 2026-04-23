#!/usr/bin/env python3
"""Aggregate submission-readiness checks into one go/no-go audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT, write_text
    from .manuscript_scope_common import build_manuscript_scope_gate, build_manuscript_scope_status
    from .manuscript_claims import build_claim_coverage, build_claim_packets
    from .reference_integrity import build_reference_report
    from .review_common import validate_review_artifacts
    from .review_evidence import build_evidence_report
    from .venue_overlay import VENUE_CONFIG_DIR, build_submission_gate, evaluate_venue
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, write_text
    from manuscript_scope_common import build_manuscript_scope_gate, build_manuscript_scope_status
    from manuscript_claims import build_claim_coverage, build_claim_packets
    from reference_integrity import build_reference_report
    from review_common import validate_review_artifacts
    from review_evidence import build_evidence_report
    from venue_overlay import VENUE_CONFIG_DIR, build_submission_gate, evaluate_venue


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"


def _available_venues() -> list[str]:
    return sorted(path.stem for path in VENUE_CONFIG_DIR.glob("*.yml"))


def _resolve_venues(selected_venues: list[str] | None = None) -> list[str]:
    available = _available_venues()
    if not selected_venues:
        return available
    unknown = sorted(set(selected_venues) - set(available))
    if unknown:
        raise ValueError(f"Unknown venue ids for pre-submission audit: {', '.join(unknown)}")
    return [venue for venue in available if venue in selected_venues]


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def build_bibliography_scope_gate(reference_report: dict[str, Any]) -> dict[str, Any]:
    source = reference_report.get("bibliography_source", {})
    current_status = str(source.get("manuscript_scope_status", "unknown"))
    return {
        "status": "ready" if current_status == "confirmed" else "blocked",
        "required_manuscript_scope_status": "confirmed",
        "current_manuscript_scope_status": current_status,
        "note": source.get("manuscript_scope_note"),
    }


def build_pre_submission_audit(
    repo_root: Path = REPO_ROOT,
    selected_venues: list[str] | None = None,
) -> dict[str, Any]:
    venue_ids = _resolve_venues(selected_venues)
    venues = [evaluate_venue(venue_id, repo_root=repo_root) for venue_id in venue_ids]
    submission_gate = build_submission_gate(venues)
    manuscript_scope = build_manuscript_scope_status(repo_root)
    manuscript_scope_gate = build_manuscript_scope_gate(manuscript_scope)
    reference_report = build_reference_report()
    bibliography_scope_gate = build_bibliography_scope_gate(reference_report)
    review_evidence = build_evidence_report()
    review_validation = validate_review_artifacts()
    claim_coverage = build_claim_coverage(build_claim_packets())

    blocking_issues: list[str] = []
    warnings: list[str] = []
    package_paths: list[str] = []

    venue_blocked = [report["venue"] for report in venues if report["readiness"] != "ready"]
    venue_verification_pending = [
        report["venue"]
        for report in venues
        if report.get("verification", {}).get("status") == "needs_submission_confirmation"
    ]
    venue_verification_stale = [
        report["venue"]
        for report in venues
        if report.get("verification", {}).get("status") == "stale"
    ]
    venue_verification_invalid = [
        report["venue"]
        for report in venues
        if report.get("verification", {}).get("status") == "invalid"
    ]
    if venue_blocked:
        blocking_issues.append(f"venue readiness is not ready for: {', '.join(venue_blocked)}")
    for report in venues:
        for issue in report.get("blocking_issues", []):
            blocking_issues.append(f"{report['venue']}: {issue}")
    package_paths.extend(path for report in venues for path in report.get("package_paths", []))
    package_paths.append(str(manuscript_scope["manifest_path"]))
    if manuscript_scope["status"] == "invalid":
        blocking_issues.extend(
            f"manuscript scope: {issue}" for issue in manuscript_scope.get("issues", [])
        )

    if reference_report["readiness"] == "blocked":
        blocking_issues.extend(reference_report.get("blocking_issues", []))
    elif reference_report["readiness"] != "ready":
        warnings.extend(reference_report.get("warnings", []))
    package_paths.extend(reference_report.get("package_paths", []))

    if review_evidence["readiness"] != "ready":
        blocking_issues.extend(review_evidence.get("blocking_issues", []))
    warnings.extend(review_evidence.get("warnings", []))
    package_paths.extend(review_evidence.get("package_paths", []))

    if review_validation["overall_status"] != "ready":
        blocking_issues.extend(review_validation.get("issues", []))

    if claim_coverage["overall_status"] == "blocked":
        blocking_issues.append("claim coverage is blocked")
    elif claim_coverage["overall_status"] != "ready":
        warnings.append(
            "claim coverage is provisional for: "
            + ", ".join(claim_coverage.get("provisional_claim_ids", []))
        )
    package_paths.extend(
        [
            "manuscript/plans/claim_packets.json",
            "manuscript/plans/claim_coverage.json",
        ]
    )

    readiness = "ready"
    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"

    audit_id = "pre_submission_audit_v1"
    if selected_venues and len(venue_ids) == 1:
        audit_id = f"pre_submission_audit_{venue_ids[0]}_v1"

    return {
        "audit_id": audit_id,
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "venue_scope": {
            "mode": "selected" if selected_venues else "all",
            "venue_ids": venue_ids,
        },
        "venues": {
            "checked": len(venues),
            "ready": sum(1 for report in venues if report["readiness"] == "ready"),
            "verification_pending": len(venue_verification_pending),
            "verification_stale": len(venue_verification_stale),
            "verification_invalid": len(venue_verification_invalid),
            "reports": venues,
        },
        "submission_gate": submission_gate,
        "manuscript_scope": manuscript_scope,
        "manuscript_scope_gate": manuscript_scope_gate,
        "bibliography_scope_gate": bibliography_scope_gate,
        "reference_integrity": reference_report,
        "review_evidence": review_evidence,
        "review_validation": review_validation,
        "claim_coverage": claim_coverage,
        "package_paths": sorted(dict.fromkeys(package_paths)),
    }


def build_pre_submission_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "package_id": report["audit_id"],
        "readiness": report["readiness"],
        "blocking_issue_count": len(report["blocking_issues"]),
        "warning_count": len(report["warnings"]),
        "venues_checked": report["venues"]["checked"],
        "venue_verification_pending": report["venues"]["verification_pending"],
        "venue_verification_stale": report["venues"]["verification_stale"],
        "venue_verification_invalid": report["venues"]["verification_invalid"],
        "submission_gate_status": report["submission_gate"]["status"],
        "submission_gate_failed_count": report["submission_gate"]["failed_count"],
        "manuscript_scope_gate_status": report["manuscript_scope_gate"]["status"],
        "bibliography_scope_gate_status": report["bibliography_scope_gate"]["status"],
        "package_paths": report["package_paths"],
    }


def render_pre_submission_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pre-Submission Audit",
        "",
        f"- audit_id: `{report['audit_id']}`",
        f"- venue_scope: `{', '.join(report['venue_scope']['venue_ids'])}`",
        f"- readiness: `{report['readiness']}`",
        f"- venues_checked: `{report['venues']['checked']}`",
        f"- ready_venues: `{report['venues']['ready']}`",
        f"- venue_verification_pending: `{report['venues']['verification_pending']}`",
        f"- venue_verification_stale: `{report['venues']['verification_stale']}`",
        f"- venue_verification_invalid: `{report['venues']['verification_invalid']}`",
        f"- submission_gate: `{report['submission_gate']['status']}`",
        f"- manuscript_scope_gate: `{report['manuscript_scope_gate']['status']}`",
        f"- bibliography_scope_gate: `{report['bibliography_scope_gate']['status']}`",
        f"- reference_integrity: `{report['reference_integrity']['readiness']}`",
        f"- review_evidence: `{report['review_evidence']['readiness']}`",
        f"- review_validation: `{report['review_validation']['overall_status']}`",
        f"- claim_coverage: `{report['claim_coverage']['overall_status']}`",
        "",
        "## Venue Readiness",
        "",
    ]
    for venue in report["venues"]["reports"]:
        label = str(venue.get("display_name", venue["venue"]))
        verification = venue.get("verification", {}).get("status", "unknown")
        lines.append(f"- `{label}` (`{venue['venue']}`): readiness `{venue['readiness']}`, verification `{verification}`")
    lines.extend(["", "## Submission Gate", ""])
    lines.append(f"- status: `{report['submission_gate']['status']}`")
    lines.append(
        f"- required_verification_status: `{report['submission_gate']['required_verification_status']}`"
    )
    if report["submission_gate"]["failed_venues"]:
        for item in report["submission_gate"]["failed_venues"]:
            lines.append(
                "- "
                f"`{item['display_name']}` (`{item['venue']}`): "
                f"`{item['verification_status']}`"
            )
    lines.extend(["", "## Manuscript Scope Gate", ""])
    lines.append(f"- status: `{report['manuscript_scope_gate']['status']}`")
    lines.append(
        f"- required_scope_status: `{report['manuscript_scope_gate']['required_scope_status']}`"
    )
    lines.append(
        f"- current_scope_status: `{report['manuscript_scope_gate']['current_scope_status']}`"
    )
    if report["manuscript_scope_gate"]["confirmed_on"]:
        lines.append(f"- confirmed_on: `{report['manuscript_scope_gate']['confirmed_on']}`")
    if report["manuscript_scope_gate"]["note"]:
        lines.append(f"- note: {report['manuscript_scope_gate']['note']}")
    for issue in report["manuscript_scope_gate"]["issues"]:
        lines.append(f"- issue: {issue}")
    for warning in report["manuscript_scope_gate"]["warnings"]:
        lines.append(f"- warning: {warning}")
    lines.extend(["", "## Bibliography Scope Gate", ""])
    lines.append(f"- status: `{report['bibliography_scope_gate']['status']}`")
    lines.append(
        "- required_manuscript_scope_status: "
        f"`{report['bibliography_scope_gate']['required_manuscript_scope_status']}`"
    )
    lines.append(
        "- current_manuscript_scope_status: "
        f"`{report['bibliography_scope_gate']['current_manuscript_scope_status']}`"
    )
    if report["bibliography_scope_gate"]["note"]:
        lines.append(f"- note: {report['bibliography_scope_gate']['note']}")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Review Validation",
            "",
            f"- issue_count: `{report['review_validation']['issue_count']}`",
        ]
    )
    for component, status in report["review_validation"]["component_status"].items():
        lines.append(f"- `{component}`: `{status}`")
    lines.extend(["", "## Package Paths", ""])
    for path in report["package_paths"]:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def _audit_stem(selected_venues: list[str] | None = None) -> str:
    venue_ids = _resolve_venues(selected_venues)
    if selected_venues and len(venue_ids) == 1:
        return f"pre_submission_audit_{venue_ids[0]}"
    return "pre_submission_audit"


def write_pre_submission_outputs(
    repo_root: Path = REPO_ROOT,
    selected_venues: list[str] | None = None,
) -> dict[str, str]:
    report = build_pre_submission_audit(repo_root=repo_root, selected_venues=selected_venues)
    manifest = build_pre_submission_manifest(report)
    stem = _audit_stem(selected_venues)

    report_json_path = REPORTS_DIR / f"{stem}.json"
    report_md_path = REPORTS_DIR / f"{stem}.md"
    manifest_path = MANIFESTS_DIR / f"{stem}.json"

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(report_md_path, render_pre_submission_markdown(report))
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")

    return {
        "report_json": _relative(report_json_path, repo_root),
        "report_md": _relative(report_md_path, repo_root),
        "manifest": _relative(manifest_path, repo_root),
    }
