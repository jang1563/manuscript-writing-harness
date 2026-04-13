#!/usr/bin/env python3
"""Freeze release-bundle exports into archive-ready manifests and checksums."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT, write_text
    from .release_bundle import (
        MANIFESTS_DIR as RELEASE_MANIFESTS_DIR,
        REPORTS_DIR as RELEASE_REPORTS_DIR,
        build_release_bundle,
        build_release_manifest,
    )
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, write_text
    from release_bundle import (
        MANIFESTS_DIR as RELEASE_MANIFESTS_DIR,
        REPORTS_DIR as RELEASE_REPORTS_DIR,
        build_release_bundle,
        build_release_manifest,
    )


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
CHECKSUMS_DIR = RELEASE_ROOT / "checksums"
DEPOSIT_DIR = RELEASE_ROOT / "deposit"
ARCHIVE_REPORTS_DIR = RELEASE_REPORTS_DIR
ARCHIVE_MANIFESTS_DIR = RELEASE_MANIFESTS_DIR


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _release_output_paths(profile_id: str) -> dict[str, str]:
    stem = f"{profile_id}_bundle"
    return {
        "report_json": f"workflows/release/reports/{stem}.json",
        "report_md": f"workflows/release/reports/{stem}.md",
        "manifest": f"workflows/release/manifests/{stem}.json",
    }


def _expand_package_paths(package_paths: list[str], repo_root: Path = REPO_ROOT) -> tuple[list[str], list[str]]:
    files: list[str] = []
    missing: list[str] = []
    for raw_path in package_paths:
        rel = str(raw_path)
        path = repo_root / rel
        if path.is_file():
            files.append(rel)
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    files.append(_relative(child, repo_root))
            continue
        missing.append(rel)
    return sorted(dict.fromkeys(files)), sorted(dict.fromkeys(missing))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_rows(files: list[str], repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rel in files:
        path = repo_root / rel
        rows.append(
            {
                "path": rel,
                "sha256": _sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def _tree_summary(files: list[str], repo_root: Path = REPO_ROOT) -> dict[str, dict[str, int]]:
    grouped: dict[str, dict[str, int]] = {}
    for rel in files:
        root = rel.split("/", 1)[0]
        path = repo_root / rel
        payload = grouped.setdefault(root, {"file_count": 0, "total_bytes": 0})
        payload["file_count"] += 1
        payload["total_bytes"] += path.stat().st_size
    return dict(sorted(grouped.items()))


def build_archive_export(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    release_report = build_release_bundle(profile_id, repo_root=repo_root)
    release_manifest = build_release_manifest(profile_id, repo_root=repo_root)
    release_outputs = _release_output_paths(profile_id)

    archive_roots = list(release_manifest["package_paths"])
    archive_roots.extend(release_outputs.values())
    archive_files, missing_paths = _expand_package_paths(archive_roots, repo_root=repo_root)
    inventory = _inventory_rows(archive_files, repo_root=repo_root)
    total_bytes = sum(int(item["size_bytes"]) for item in inventory)

    blocking_issues = list(release_report.get("blocking_issues", []))
    warnings = list(release_report.get("warnings", []))
    if release_report["readiness"] != "ready":
        blocking_issues.append(f"release bundle {profile_id} is {release_report['readiness']}")
    if missing_paths:
        blocking_issues.extend(f"archive path is missing: {path}" for path in missing_paths)

    readiness = "ready" if not blocking_issues else "blocked"
    return {
        "profile_id": profile_id,
        "archive_id": f"{profile_id}_archive_v1",
        "readiness": readiness,
        "blocking_issues": sorted(dict.fromkeys(blocking_issues)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "release_bundle": {
            "profile_id": release_report["profile_id"],
            "readiness": release_report["readiness"],
            "report_json": release_outputs["report_json"],
            "report_md": release_outputs["report_md"],
            "manifest": release_outputs["manifest"],
        },
        "deposit_targets": ["zenodo", "osf"],
        "file_count": len(archive_files),
        "total_bytes": total_bytes,
        "tree_summary": _tree_summary(archive_files, repo_root=repo_root),
        "missing_paths": missing_paths,
        "inventory_files": archive_files,
        "inventory_rows": inventory,
    }


def build_archive_manifest(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = build_archive_export(profile_id, repo_root=repo_root)
    return {
        "package_id": report["archive_id"],
        "profile_id": profile_id,
        "readiness": report["readiness"],
        "release_bundle": report["release_bundle"],
        "deposit_targets": report["deposit_targets"],
        "file_count": report["file_count"],
        "total_bytes": report["total_bytes"],
        "tree_summary": report["tree_summary"],
        "inventory_path": f"workflows/release/checksums/{profile_id}_archive_sha256.txt",
        "deposit_notes": f"workflows/release/deposit/{profile_id}_deposit_notes.md",
        "inventory_files": report["inventory_files"],
    }


def render_archive_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['archive_id']}",
        "",
        f"- profile_id: `{report['profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- file_count: `{report['file_count']}`",
        f"- total_bytes: `{report['total_bytes']}`",
        f"- release bundle: `{report['release_bundle']['profile_id']}` / `{report['release_bundle']['readiness']}`",
        f"- deposit targets: `{', '.join(report['deposit_targets'])}`",
        "",
        "## Tree Summary",
        "",
    ]
    for root, payload in report["tree_summary"].items():
        lines.append(
            f"- `{root}`: `{payload['file_count']}` files / `{payload['total_bytes']}` bytes"
        )
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Frozen Inventory Files", ""])
    for rel in report["inventory_files"]:
        lines.append(f"- `{rel}`")
    return "\n".join(lines).rstrip() + "\n"


def render_checksum_inventory(report: dict[str, Any]) -> str:
    lines = [f"{item['sha256']}  {item['path']}" for item in report["inventory_rows"]]
    return "\n".join(lines).rstrip() + "\n"


def render_deposit_notes(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['archive_id']} Deposit Notes",
        "",
        "## Intended Targets",
        "",
    ]
    for target in report["deposit_targets"]:
        lines.append(f"- `{target}`")
    lines.extend(
        [
            "",
            "## Suggested Deposit Metadata",
            "",
            f"- title: `{report['release_bundle']['profile_id']}` archive export",
            "- description: frozen archive of the manuscript harness release package",
            "- artifact scope: manuscript, figures, references, review evidence, pathway provenance",
            "",
            "## Required Files",
            "",
            f"- release report: `{report['release_bundle']['report_md']}`",
            f"- release manifest: `{report['release_bundle']['manifest']}`",
            f"- checksum inventory: `workflows/release/checksums/{report['profile_id']}_archive_sha256.txt`",
            "",
            "## Notes",
            "",
            "- Upload the exact files listed in the checksum inventory or a tarball generated from that list.",
            "- Keep the checksum inventory alongside the deposited bundle so downstream users can verify file integrity.",
            "- If the venue requires anonymized exports, reconcile this archive against `workflows/release/anonymization_check.md` before deposit.",
        ]
    )
    if report["warnings"]:
        lines.extend(["", "## Current Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines).rstrip() + "\n"


def write_archive_outputs(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = build_archive_export(profile_id, repo_root=repo_root)
    manifest = build_archive_manifest(profile_id, repo_root=repo_root)
    report_json_path = ARCHIVE_REPORTS_DIR / f"{profile_id}_archive.json"
    report_md_path = ARCHIVE_REPORTS_DIR / f"{profile_id}_archive.md"
    manifest_path = ARCHIVE_MANIFESTS_DIR / f"{profile_id}_archive.json"
    checksum_path = CHECKSUMS_DIR / f"{profile_id}_archive_sha256.txt"
    deposit_notes_path = DEPOSIT_DIR / f"{profile_id}_deposit_notes.md"

    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    checksum_path.parent.mkdir(parents=True, exist_ok=True)
    deposit_notes_path.parent.mkdir(parents=True, exist_ok=True)

    write_text(report_md_path, render_archive_markdown(report))
    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    write_text(checksum_path, render_checksum_inventory(report))
    write_text(deposit_notes_path, render_deposit_notes(report))
    return {
        "report_json": _relative(report_json_path, repo_root),
        "report_md": _relative(report_md_path, repo_root),
        "manifest": _relative(manifest_path, repo_root),
        "checksum_inventory": _relative(checksum_path, repo_root),
        "deposit_notes": _relative(deposit_notes_path, repo_root),
    }
