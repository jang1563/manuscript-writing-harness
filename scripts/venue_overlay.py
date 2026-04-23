#!/usr/bin/env python3
"""Helpers for venue readiness checks and submission-package manifests."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT, load_json, load_yaml, write_text
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, load_json, load_yaml, write_text


VENUE_CONFIG_DIR = REPO_ROOT / "workflows" / "venue_configs"
CHECKLIST_DIR = REPO_ROOT / "workflows" / "checklists"
RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"
CONTENT_REGISTRY_PATH = REPO_ROOT / "manuscript" / "content_registry.json"

READY_STATUSES = {"available", "generated", "mapped"}
BLOCKING_STATUSES = {"planned"}
DEFAULT_STALE_AFTER_DAYS = 180
CURRENT_VERIFICATION_STATUS = "current"


def _strip_anchor(value: str) -> str:
    return value.split("#", 1)[0]


def _maybe_existing_path(source: str) -> str | None:
    candidate = _strip_anchor(source).strip()
    if not candidate:
        return None
    path = REPO_ROOT / candidate
    if path.exists():
        return candidate
    return None


def _relative_or_absolute(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _today() -> date:
    return date.today()


def _evaluate_verification(config: dict[str, Any]) -> dict[str, Any]:
    verification = config.get("verification", {})
    if not isinstance(verification, dict):
        verification = {}

    last_verified_raw = str(verification.get("last_verified", "")).strip()
    source_summary = str(verification.get("source_summary", "")).strip()
    stale_after_days = verification.get("stale_after_days", DEFAULT_STALE_AFTER_DAYS)
    final_confirmation_required = bool(verification.get("final_confirmation_required", False))

    issues: list[str] = []
    days_since_verification: int | None = None
    stale = False
    last_verified: str | None = None

    if not isinstance(stale_after_days, int) or stale_after_days < 0:
        issues.append("verification.stale_after_days must be a non-negative integer")
        stale_after_days = DEFAULT_STALE_AFTER_DAYS

    if last_verified_raw:
        try:
            parsed = date.fromisoformat(last_verified_raw)
            last_verified = parsed.isoformat()
            today = _today()
            if parsed > today:
                issues.append("verification.last_verified must not be in the future")
            else:
                days_since_verification = (today - parsed).days
                stale = days_since_verification > stale_after_days
        except ValueError:
            issues.append("verification.last_verified must use YYYY-MM-DD format")
    else:
        issues.append("verification.last_verified is required")

    if not source_summary:
        issues.append("verification.source_summary is required")

    if issues:
        status = "invalid"
    elif stale:
        status = "stale"
    elif final_confirmation_required:
        status = "needs_submission_confirmation"
    else:
        status = "current"

    return {
        "status": status,
        "last_verified": last_verified,
        "days_since_verification": days_since_verification,
        "stale_after_days": stale_after_days,
        "stale": stale,
        "final_confirmation_required": final_confirmation_required,
        "source_summary": source_summary,
        "issues": issues,
    }


def build_submission_gate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize whether venue verification is current enough for real submission."""

    failed_venues: list[dict[str, str]] = []
    for report in reports:
        verification_status = str(report.get("verification", {}).get("status", "unknown"))
        if verification_status != CURRENT_VERIFICATION_STATUS:
            failed_venues.append(
                {
                    "venue": str(report.get("venue")),
                    "display_name": str(report.get("display_name", report.get("venue"))),
                    "verification_status": verification_status,
                }
            )

    return {
        "status": "ready" if not failed_venues else "blocked",
        "required_verification_status": CURRENT_VERIFICATION_STATUS,
        "failed_count": len(failed_venues),
        "failed_venues": failed_venues,
    }


def _normalize_requirement_items(items: list[str], registry_group: dict[str, Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item_id in items:
        entry = registry_group[item_id]
        sources = [str(value) for value in entry.get("source", [])]
        resolved_paths = [path for path in (_maybe_existing_path(source) for source in sources) if path]
        status = str(entry.get("status"))
        normalized.append(
            {
                "id": item_id,
                "status": status,
                "blocking": status in BLOCKING_STATUSES,
                "sources": sources,
                "resolved_paths": resolved_paths,
                "maps_from": list(entry.get("maps_from", [])),
            }
        )
    return normalized


def venue_checklist_path(venue_id: str) -> Path:
    return CHECKLIST_DIR / f"{venue_id}_submission.md"


def load_venue_config(venue_id: str) -> dict[str, Any]:
    config_path = VENUE_CONFIG_DIR / f"{venue_id}.yml"
    if not config_path.exists():
        raise ValueError(f"Unknown venue {venue_id!r}")
    config = load_yaml(config_path)
    if not isinstance(config, dict):
        raise ValueError(f"Invalid venue config for {venue_id!r}")
    return config


def evaluate_venue(venue_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    if repo_root != REPO_ROOT:
        raise ValueError("venue overlay evaluation currently expects the canonical repo root")

    config = load_venue_config(venue_id)
    registry = load_json(CONTENT_REGISTRY_PATH)
    sections_registry = registry.get("sections", {})
    assets_registry = registry.get("special_assets", {})
    required_sections = [str(item) for item in config.get("required_sections", [])]
    special_assets = [str(item) for item in config.get("special_assets", [])]

    missing_sections = [item for item in required_sections if item not in sections_registry]
    missing_assets = [item for item in special_assets if item not in assets_registry]
    if missing_sections or missing_assets:
        raise ValueError(
            f"Venue {venue_id!r} references unknown registry items: "
            f"sections={missing_sections}, assets={missing_assets}"
        )

    section_items = _normalize_requirement_items(required_sections, sections_registry)
    asset_items = _normalize_requirement_items(special_assets, assets_registry)
    checklist_path = venue_checklist_path(venue_id)
    config_path = VENUE_CONFIG_DIR / f"{venue_id}.yml"
    verification = _evaluate_verification(config)
    verification_blocking_issues = [
        f"invalid verification metadata: {issue}"
        for issue in verification.get("issues", [])
    ] if verification.get("status") == "invalid" else []

    blocking_items = [
        item["id"]
        for item in section_items + asset_items
        if item["blocking"]
    ]
    readiness = "ready" if not (blocking_items or verification_blocking_issues) else "blocked"

    package_paths = [
        str(config_path.relative_to(repo_root)),
        str(checklist_path.relative_to(repo_root)),
        "manuscript/content_registry.json",
    ]
    for item in section_items + asset_items:
        package_paths.extend(item["resolved_paths"])
    package_paths = sorted(dict.fromkeys(package_paths))

    return {
        "venue": venue_id,
        "display_name": str(config.get("name", venue_id)),
        "readiness": readiness,
        "blocking_items": blocking_items,
        "blocking_issues": verification_blocking_issues,
        "required_sections": section_items,
        "special_assets": asset_items,
        "notes": list(config.get("notes", [])),
        "verification": verification,
        "config_path": str(config_path.relative_to(repo_root)),
        "checklist_path": str(checklist_path.relative_to(repo_root)),
        "package_paths": package_paths,
    }


def build_submission_manifest(venue_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = evaluate_venue(venue_id, repo_root=repo_root)
    return {
        "package_id": f"{venue_id}_submission_package_v1",
        "venue": venue_id,
        "display_name": report["display_name"],
        "readiness": report["readiness"],
        "verification": report["verification"],
        "config_path": report["config_path"],
        "checklist_path": report["checklist_path"],
        "required_sections": [
            {
                "id": item["id"],
                "status": item["status"],
                "sources": item["sources"],
            }
            for item in report["required_sections"]
        ],
        "special_assets": [
            {
                "id": item["id"],
                "status": item["status"],
                "sources": item["sources"],
            }
            for item in report["special_assets"]
        ],
        "package_paths": report["package_paths"],
    }


def render_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report.get('display_name', report['venue'].capitalize())} Venue Readiness",
        "",
        f"- readiness: `{report['readiness']}`",
        f"- config: `{report['config_path']}`",
        f"- checklist: `{report['checklist_path']}`",
        f"- verification: `{report['verification']['status']}`",
        "",
        "## Verification",
        "",
        f"- status: `{report['verification']['status']}`",
        f"- last_verified: `{report['verification']['last_verified']}`",
        f"- stale_after_days: `{report['verification']['stale_after_days']}`",
        f"- final_confirmation_required: `{report['verification']['final_confirmation_required']}`",
        f"- source_summary: {report['verification']['source_summary']}",
    ]
    if report["verification"]["days_since_verification"] is not None:
        lines.append(f"- days_since_verification: `{report['verification']['days_since_verification']}`")
    if report["verification"]["issues"]:
        lines.append("- issues:")
        for issue in report["verification"]["issues"]:
            lines.append(f"  - {issue}")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    lines.extend(["", "## Required Sections", ""])
    for item in report["required_sections"]:
        lines.append(f"- `{item['id']}`: `{item['status']}`")
        for source in item["sources"]:
            lines.append(f"  source: `{source}`")
        if item["maps_from"]:
            lines.append(f"  maps_from: `{', '.join(item['maps_from'])}`")
    lines.extend(["", "## Special Assets", ""])
    for item in report["special_assets"]:
        lines.append(f"- `{item['id']}`: `{item['status']}`")
        for source in item["sources"]:
            lines.append(f"  source: `{source}`")
    lines.extend(["", "## Package Paths", ""])
    for path in report["package_paths"]:
        lines.append(f"- `{path}`")
    if report["notes"]:
        lines.extend(["", "## Notes", ""])
        for note in report["notes"]:
            lines.append(f"- {note}")
    return "\n".join(lines).rstrip() + "\n"


def write_venue_outputs(venue_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = evaluate_venue(venue_id, repo_root=repo_root)
    manifest = build_submission_manifest(venue_id, repo_root=repo_root)
    report_json_path = REPORTS_DIR / f"{venue_id}_readiness.json"
    report_md_path = REPORTS_DIR / f"{venue_id}_readiness.md"
    manifest_path = MANIFESTS_DIR / f"{venue_id}_submission_package.json"

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_text(report_md_path, render_readiness_markdown(report))
    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    return {
        "report_json": _relative_or_absolute(report_json_path, repo_root),
        "report_md": _relative_or_absolute(report_md_path, repo_root),
        "manifest": _relative_or_absolute(manifest_path, repo_root),
    }
