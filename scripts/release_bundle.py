#!/usr/bin/env python3
"""Assemble top-level release bundles from existing manuscript subsystems."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_bundle import build_bundle_review_page, load_bundle_manifest, load_bundle_manifests
    from .figures_common import REPO_ROOT, load_json, load_yaml, write_text
    from .review_evidence import build_review_manifest, build_evidence_report
    from .reference_integrity import build_reference_report, build_reference_manifest
    from .venue_overlay import build_submission_manifest, evaluate_venue
except ImportError:  # pragma: no cover
    from figures_bundle import build_bundle_review_page, load_bundle_manifest, load_bundle_manifests
    from figures_common import REPO_ROOT, load_json, load_yaml, write_text
    from review_evidence import build_review_manifest, build_evidence_report
    from reference_integrity import build_reference_report, build_reference_manifest
    from venue_overlay import build_submission_manifest, evaluate_venue


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
PROFILE_DIR = RELEASE_ROOT / "profiles"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"
ACTIVE_FGSEA_DOSSIER_PATH = REPO_ROOT / "pathways" / "results" / "active_fgsea" / "study_dossier.json"
CLAIM_COVERAGE_PATH = REPO_ROOT / "manuscript" / "plans" / "claim_coverage.json"
SECTION_PROSE_PATH = REPO_ROOT / "manuscript" / "drafts" / "section_prose.json"

PROFILE_REQUIRED_FIELDS = {
    "profile_id",
    "title",
    "venue_id",
    "figure_bundles",
    "include_review_evidence",
    "include_reference_integrity",
    "include_active_fgsea_study",
    "include_claim_coverage",
    "include_section_prose",
    "required_artifacts",
}


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_release_profiles(repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    payload = load_yaml(repo_root / "workflows" / "release" / "profiles" / "profiles.yml")
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("workflows/release/profiles/profiles.yml must define a non-empty profiles object")
    normalized: dict[str, dict[str, Any]] = {}
    bundle_registry = load_bundle_manifests(repo_root)
    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict):
            raise ValueError(f"release profile {profile_id!r} must be an object")
        missing = sorted(PROFILE_REQUIRED_FIELDS - profile.keys())
        if missing:
            raise ValueError(f"release profile {profile_id!r} is missing {missing}")
        if profile.get("profile_id") != profile_id:
            raise ValueError(f"release profile {profile_id!r} has a mismatched profile_id")
        bundles = profile.get("figure_bundles", [])
        if not isinstance(bundles, list) or not bundles:
            raise ValueError(f"release profile {profile_id!r} must define a non-empty figure_bundles list")
        unknown = [bundle_id for bundle_id in bundles if bundle_id not in bundle_registry]
        if unknown:
            raise ValueError(f"release profile {profile_id!r} references unknown bundles {unknown}")
        required_artifacts = profile.get("required_artifacts", [])
        if not isinstance(required_artifacts, list) or not required_artifacts:
            raise ValueError(f"release profile {profile_id!r} must define a non-empty required_artifacts list")
        normalized[profile_id] = profile
    return normalized


def load_release_profile(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    profiles = load_release_profiles(repo_root)
    if profile_id not in profiles:
        raise ValueError(f"Unknown release profile {profile_id!r}")
    return profiles[profile_id]


def _bundle_component(bundle_id: str, repo_root: Path) -> dict[str, Any]:
    bundle = load_bundle_manifest(bundle_id, repo_root=repo_root)
    summary_path = repo_root / str(bundle["bundle_outputs"]["summary_json"])
    review_path = repo_root / str(bundle["bundle_outputs"]["review_page"])
    if not summary_path.exists() or not review_path.exists():
        build_bundle_review_page(bundle_id, repo_root=repo_root)
    if not summary_path.exists():
        raise ValueError(f"{bundle_id} bundle summary is missing at {summary_path}")
    summary = load_json(summary_path)
    warnings: list[str] = []
    blocking: list[str] = []
    if summary.get("manuscript_wiring_status") != "applied":
        blocking.append(f"{bundle_id} manuscript wiring is not applied")
    if not review_path.exists():
        blocking.append(f"{bundle_id} review page is missing")
    clipping_counts = summary.get("clipping_risk_counts", {})
    if isinstance(clipping_counts, dict):
        non_low = {key: value for key, value in clipping_counts.items() if key != "low"}
        if non_low:
            warnings.append(f"{bundle_id} has non-low clipping risk counts: {non_low}")
    font_counts = summary.get("font_status_counts", {})
    if isinstance(font_counts, dict):
        non_preferred = {key: value for key, value in font_counts.items() if key != "preferred"}
        if non_preferred:
            warnings.append(f"{bundle_id} has non-preferred font counts: {non_preferred}")
    return {
        "bundle_id": bundle_id,
        "recipe_id": bundle["recipe_id"],
        "acceptance_tier": bundle["acceptance_tier"],
        "member_count": summary.get("member_count", len(bundle.get("figures", []))),
        "figure_ids": list(summary.get("figure_ids", [])),
        "renderers_present": list(summary.get("renderers_present", [])),
        "manuscript_wiring_status": str(summary.get("manuscript_wiring_status", "unknown")),
        "summary_json": _relative(summary_path, repo_root),
        "review_page": _relative(review_path, repo_root),
        "warnings": warnings,
        "blocking_issues": blocking,
        "package_paths": [
            _relative(repo_root / bundle["_bundle_path"], repo_root),
            _relative(summary_path, repo_root),
            _relative(review_path, repo_root),
        ],
    }


def _active_fgsea_component(repo_root: Path) -> dict[str, Any]:
    if not ACTIVE_FGSEA_DOSSIER_PATH.exists():
        return {
            "readiness": "blocked",
            "blocking_issues": ["active fgsea study dossier is missing"],
            "warnings": [],
            "package_paths": [],
        }
    dossier = load_json(ACTIVE_FGSEA_DOSSIER_PATH)
    package_paths = [
        str(dossier.get("config", "")),
        str(dossier.get("figure_05", {}).get("python_manifest", "")),
        str(dossier.get("figure_05", {}).get("r_manifest", "")),
        str(dossier.get("figure_05", {}).get("review_page", "")),
        str(dossier.get("inputs", {}).get("raw_input_table", "")),
        str(dossier.get("inputs", {}).get("rank_prep_summary", "")),
        str(dossier.get("fgsea", {}).get("summary_json", "")),
        str(dossier.get("fgsea", {}).get("results_csv", "")),
        str(dossier.get("fgsea", {}).get("figure_export_csv", "")),
        "pathways/results/active_fgsea/study_dossier.json",
        "pathways/results/active_fgsea/study_dossier.md",
    ]
    package_paths = sorted(path for path in dict.fromkeys(package_paths) if path)
    readiness = str(dossier.get("readiness", "blocked"))
    return {
        "study_id": str(dossier.get("study_id", "active_fgsea")),
        "readiness": readiness,
        "blocking_issues": list(dossier.get("blocking_issues", [])),
        "warnings": list(dossier.get("warnings", [])),
        "study_kind": str(dossier.get("study_kind", "unknown")),
        "config": str(dossier.get("config", "")),
        "is_active_source": bool(dossier.get("active_profile", {}).get("is_active_source")),
        "figure_05_sync": str(dossier.get("active_profile", {}).get("figure_05_sync", {}).get("status", "unknown")),
        "result_count": int(dossier.get("fgsea", {}).get("result_count", 0) or 0),
        "figure_export_count": int(dossier.get("fgsea", {}).get("figure_export_count", 0) or 0),
        "package_paths": package_paths,
    }


def _claim_coverage_component(repo_root: Path) -> dict[str, Any]:
    payload = load_json(CLAIM_COVERAGE_PATH)
    readiness = str(payload.get("overall_status", "blocked"))
    blocking = [] if readiness == "ready" else [f"claim coverage overall_status is {readiness}"]
    return {
        "overall_status": readiness,
        "claim_count": int(payload.get("claim_count", 0) or 0),
        "ready_claim_count": int(payload.get("ready_claim_count", 0) or 0),
        "display_items_covered": list(payload.get("display_items_covered", [])),
        "blocking_issues": blocking,
        "warnings": [],
        "package_paths": ["manuscript/plans/claim_coverage.json", "manuscript/plans/claim_packets.json"],
    }


def _section_prose_component(repo_root: Path) -> dict[str, Any]:
    payload = load_json(SECTION_PROSE_PATH)
    readiness = str(payload.get("overall_status", "blocked"))
    blocking = [] if readiness == "ready" else [f"section prose overall_status is {readiness}"]
    section_paths = [
        str(section.get("source", ""))
        for section in payload.get("sections", [])
        if isinstance(section, dict) and section.get("source")
    ]
    return {
        "overall_status": readiness,
        "section_count": int(payload.get("section_count", 0) or 0),
        "blocking_issues": blocking,
        "warnings": [],
        "package_paths": sorted(
            dict.fromkeys(
                [
                    "manuscript/drafts/section_prose.json",
                    "manuscript/drafts/section_prose.md",
                    *section_paths,
                ]
            )
        ),
    }


def _required_artifact_status(profile: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for raw_path in profile.get("required_artifacts", []):
        path = str(raw_path)
        candidate = repo_root / path
        artifacts.append(
            {
                "path": path,
                "status": "present" if candidate.exists() else "missing",
            }
        )
    return artifacts


def build_release_bundle(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    profile = load_release_profile(profile_id, repo_root)

    venue_report = evaluate_venue(str(profile["venue_id"]), repo_root=repo_root)
    venue_manifest = build_submission_manifest(str(profile["venue_id"]), repo_root=repo_root)
    bundle_components = [_bundle_component(bundle_id, repo_root) for bundle_id in profile["figure_bundles"]]
    review_report = build_evidence_report() if profile.get("include_review_evidence") else None
    review_manifest = build_review_manifest(review_report) if review_report else None
    reference_report = build_reference_report() if profile.get("include_reference_integrity") else None
    reference_manifest = build_reference_manifest(reference_report) if reference_report else None
    fgsea_component = _active_fgsea_component(repo_root) if profile.get("include_active_fgsea_study") else None
    claim_component = _claim_coverage_component(repo_root) if profile.get("include_claim_coverage") else None
    prose_component = _section_prose_component(repo_root) if profile.get("include_section_prose") else None
    required_artifacts = _required_artifact_status(profile, repo_root)

    blocking_issues: list[str] = []
    warnings: list[str] = []
    package_paths: list[str] = []

    if venue_report["readiness"] != "ready":
        blocking_issues.append(f"venue {profile['venue_id']} is {venue_report['readiness']}")
    package_paths.extend(venue_manifest["package_paths"])
    package_paths.extend(
        [
            f"workflows/release/reports/{profile['venue_id']}_readiness.json",
            f"workflows/release/reports/{profile['venue_id']}_readiness.md",
            f"workflows/release/manifests/{profile['venue_id']}_submission_package.json",
        ]
    )

    for bundle in bundle_components:
        blocking_issues.extend(bundle["blocking_issues"])
        warnings.extend(bundle["warnings"])
        package_paths.extend(bundle["package_paths"])

    if review_report is not None:
        if review_report["readiness"] != "ready":
            blocking_issues.append(f"review evidence is {review_report['readiness']}")
        warnings.extend(str(item) for item in review_report.get("warnings", []))
        package_paths.extend(review_manifest["package_paths"])
        package_paths.extend(
            [
                "review/reports/evidence_summary.json",
                "review/reports/evidence_summary.md",
                "review/manifests/review_evidence_package.json",
            ]
        )

    if reference_report is not None:
        if reference_report["readiness"] != "ready":
            blocking_issues.append(f"reference integrity is {reference_report['readiness']}")
        warnings.extend(str(item) for item in reference_report.get("warnings", []))
        package_paths.extend(reference_manifest["package_paths"])
        package_paths.extend(
            [
                "references/reports/reference_audit.json",
                "references/reports/reference_audit.md",
                "references/manifests/reference_package.json",
            ]
        )

    if fgsea_component is not None:
        if fgsea_component["readiness"] != "ready":
            blocking_issues.append(f"active fgsea study is {fgsea_component['readiness']}")
        blocking_issues.extend(str(item) for item in fgsea_component.get("blocking_issues", []))
        warnings.extend(str(item) for item in fgsea_component.get("warnings", []))
        package_paths.extend(fgsea_component["package_paths"])

    if claim_component is not None:
        blocking_issues.extend(str(item) for item in claim_component.get("blocking_issues", []))
        package_paths.extend(claim_component["package_paths"])

    if prose_component is not None:
        blocking_issues.extend(str(item) for item in prose_component.get("blocking_issues", []))
        package_paths.extend(prose_component["package_paths"])

    missing_artifacts = [item["path"] for item in required_artifacts if item["status"] == "missing"]
    if missing_artifacts:
        blocking_issues.extend(f"required artifact is missing: {path}" for path in missing_artifacts)
    package_paths.extend(item["path"] for item in required_artifacts)

    readiness = "ready" if not blocking_issues else "blocked"
    package_paths = sorted(path for path in dict.fromkeys(package_paths) if path)
    warnings = sorted(dict.fromkeys(warnings))
    blocking_issues = sorted(dict.fromkeys(blocking_issues))

    return {
        "profile_id": profile_id,
        "title": str(profile["title"]),
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "venue": {
            "venue_id": str(profile["venue_id"]),
            "readiness": venue_report["readiness"],
            "required_section_count": len(venue_report["required_sections"]),
            "special_asset_count": len(venue_report["special_assets"]),
            "report_json": f"workflows/release/reports/{profile['venue_id']}_readiness.json",
            "report_md": f"workflows/release/reports/{profile['venue_id']}_readiness.md",
            "manifest": f"workflows/release/manifests/{profile['venue_id']}_submission_package.json",
        },
        "figure_bundles": bundle_components,
        "review_evidence": {
            "enabled": bool(review_report is not None),
            "readiness": review_report["readiness"] if review_report else None,
            "review_id": review_report["review_id"] if review_report else None,
            "manifest": "review/manifests/review_evidence_package.json" if review_report else None,
        },
        "reference_integrity": {
            "enabled": bool(reference_report is not None),
            "readiness": reference_report["readiness"] if reference_report else None,
            "entry_count": reference_report["bibliography"]["entry_count"] if reference_report else None,
            "manifest": "references/manifests/reference_package.json" if reference_report else None,
        },
        "active_fgsea_study": fgsea_component,
        "claim_coverage": claim_component,
        "section_prose": prose_component,
        "required_artifacts": required_artifacts,
        "package_paths": package_paths,
    }


def build_release_manifest(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = build_release_bundle(profile_id, repo_root=repo_root)
    return {
        "package_id": f"{profile_id}_bundle_v1",
        "profile_id": profile_id,
        "readiness": report["readiness"],
        "venue": report["venue"],
        "figure_bundle_ids": [item["bundle_id"] for item in report["figure_bundles"]],
        "review_evidence_manifest": report["review_evidence"]["manifest"],
        "reference_manifest": report["reference_integrity"]["manifest"],
        "active_fgsea_study": (
            {
                "study_id": report["active_fgsea_study"]["study_id"],
                "readiness": report["active_fgsea_study"]["readiness"],
                "config": report["active_fgsea_study"]["config"],
            }
            if report.get("active_fgsea_study")
            else None
        ),
        "claim_coverage_status": report["claim_coverage"]["overall_status"] if report.get("claim_coverage") else None,
        "section_prose_status": report["section_prose"]["overall_status"] if report.get("section_prose") else None,
        "required_artifacts": report["required_artifacts"],
        "package_paths": report["package_paths"],
    }


def render_release_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['title']}",
        "",
        f"- profile_id: `{report['profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- venue: `{report['venue']['venue_id']}`",
        "",
        "## Figure Bundles",
        "",
    ]
    for bundle in report["figure_bundles"]:
        lines.extend(
            [
                f"- `{bundle['bundle_id']}`: `{bundle['member_count']}` members, renderers `{', '.join(bundle['renderers_present'])}`, wiring `{bundle['manuscript_wiring_status']}`",
                f"  review: `{bundle['review_page']}`",
                f"  summary: `{bundle['summary_json']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Upstream Components",
            "",
            f"- review evidence: `{report['review_evidence']['readiness']}`",
            f"- reference integrity: `{report['reference_integrity']['readiness']}`",
            f"- claim coverage: `{report['claim_coverage']['overall_status']}`",
            f"- section prose: `{report['section_prose']['overall_status']}`",
        ]
    )
    if report.get("active_fgsea_study"):
        fgsea = report["active_fgsea_study"]
        lines.extend(
            [
                f"- active fgsea study: `{fgsea['study_id']}` / `{fgsea['readiness']}`",
                f"  config: `{fgsea['config']}`",
                f"  figure_05 sync: `{fgsea['figure_05_sync']}`",
                f"  fgsea result_count: `{fgsea['result_count']}`",
            ]
        )
    lines.extend(["", "## Required Artifacts", ""])
    for item in report["required_artifacts"]:
        lines.append(f"- `{item['path']}`: `{item['status']}`")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Package Paths", ""])
    for path in report["package_paths"]:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_release_outputs(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = build_release_bundle(profile_id, repo_root=repo_root)
    manifest = build_release_manifest(profile_id, repo_root=repo_root)
    stem = f"{profile_id}_bundle"
    report_json_path = REPORTS_DIR / f"{stem}.json"
    report_md_path = REPORTS_DIR / f"{stem}.md"
    manifest_path = MANIFESTS_DIR / f"{stem}.json"

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_md_path, render_release_markdown(report))
    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    return {
        "report_json": _relative(report_json_path, repo_root),
        "report_md": _relative(report_md_path, repo_root),
        "manifest": _relative(manifest_path, repo_root),
    }
