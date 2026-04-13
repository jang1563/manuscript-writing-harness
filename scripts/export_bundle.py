#!/usr/bin/env python3
"""Build deterministic tar/zip exports from archive-export inventories."""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
from typing import Any
import zipfile

try:  # pragma: no cover - import path differs between script and package use.
    from .archive_export import build_archive_export, write_archive_outputs
    from .figures_common import REPO_ROOT, write_text
except ImportError:  # pragma: no cover
    from archive_export import build_archive_export, write_archive_outputs
    from figures_common import REPO_ROOT, write_text


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
EXPORTS_DIR = RELEASE_ROOT / "exports"


@dataclass(frozen=True)
class ExportEntry:
    source: Path
    archive_path: str


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _export_paths(profile_id: str) -> dict[str, Path]:
    return {
        "report_json": EXPORTS_DIR / f"{profile_id}_export.json",
        "report_md": EXPORTS_DIR / f"{profile_id}_export.md",
        "checksums": EXPORTS_DIR / f"{profile_id}_export_checksums.txt",
        "tar_gz": EXPORTS_DIR / f"{profile_id}_export.tar.gz",
        "zip": EXPORTS_DIR / f"{profile_id}_export.zip",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_inputs(profile_id: str, repo_root: Path = REPO_ROOT) -> tuple[dict[str, Any], list[ExportEntry]]:
    archive_writes = write_archive_outputs(profile_id, repo_root=repo_root)
    archive_report = build_archive_export(profile_id, repo_root=repo_root)
    prefix = f"{profile_id}_export"

    supplemental = [
        archive_writes["report_json"],
        archive_writes["report_md"],
        archive_writes["manifest"],
        archive_writes["checksum_inventory"],
        archive_writes["deposit_notes"],
    ]
    included_paths = list(archive_report["inventory_files"]) + supplemental
    seen: set[str] = set()
    entries: list[ExportEntry] = []
    for rel in included_paths:
        if rel in seen:
            continue
        seen.add(rel)
        source = repo_root / rel
        if not source.is_file():
            raise ValueError(f"export input is missing or not a file: {rel}")
        entries.append(ExportEntry(source=source, archive_path=f"{prefix}/{rel}"))
    return archive_writes, entries


def _write_tar_gz(path: Path, entries: list[ExportEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as gz_handle:
            with tarfile.open(fileobj=gz_handle, mode="w") as tar_handle:
                for entry in sorted(entries, key=lambda item: item.archive_path):
                    data = entry.source.read_bytes()
                    info = tarfile.TarInfo(name=entry.archive_path)
                    info.size = len(data)
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = 0o644
                    tar_handle.addfile(info, io.BytesIO(data))


def _write_zip(path: Path, entries: list[ExportEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for entry in sorted(entries, key=lambda item: item.archive_path):
            info = zipfile.ZipInfo(entry.archive_path)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            handle.writestr(info, entry.source.read_bytes())


def build_export_bundle(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    archive_report = build_archive_export(profile_id, repo_root=repo_root)
    blocking_issues = list(archive_report.get("blocking_issues", []))
    warnings = list(archive_report.get("warnings", []))
    if archive_report["readiness"] != "ready":
        blocking_issues.append(f"archive export {profile_id} is {archive_report['readiness']}")

    paths = _export_paths(profile_id)
    prefix = f"{profile_id}_export"
    included_files = list(archive_report["inventory_files"]) + [
        f"workflows/release/reports/{profile_id}_archive.json",
        f"workflows/release/reports/{profile_id}_archive.md",
        f"workflows/release/manifests/{profile_id}_archive.json",
        f"workflows/release/checksums/{profile_id}_archive_sha256.txt",
        f"workflows/release/deposit/{profile_id}_deposit_notes.md",
    ]
    included_files = sorted(dict.fromkeys(included_files))

    tar_exists = paths["tar_gz"].exists()
    zip_exists = paths["zip"].exists()
    export_checksums = {
        "tar_gz": _sha256(paths["tar_gz"]) if tar_exists else None,
        "zip": _sha256(paths["zip"]) if zip_exists else None,
    }

    readiness = "ready" if not blocking_issues else "blocked"
    return {
        "profile_id": profile_id,
        "export_id": f"{profile_id}_export_v1",
        "readiness": readiness,
        "blocking_issues": sorted(dict.fromkeys(blocking_issues)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "archive_export": {
            "archive_id": archive_report["archive_id"],
            "readiness": archive_report["readiness"],
            "report_json": f"workflows/release/reports/{profile_id}_archive.json",
            "manifest": f"workflows/release/manifests/{profile_id}_archive.json",
        },
        "archive_prefix": prefix,
        "included_file_count": len(included_files),
        "included_files": included_files,
        "tar_gz": _relative(paths["tar_gz"], repo_root),
        "zip": _relative(paths["zip"], repo_root),
        "export_checksums": export_checksums,
    }


def build_export_manifest(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = build_export_bundle(profile_id, repo_root=repo_root)
    return {
        "package_id": report["export_id"],
        "profile_id": profile_id,
        "readiness": report["readiness"],
        "archive_export": report["archive_export"],
        "archive_prefix": report["archive_prefix"],
        "included_file_count": report["included_file_count"],
        "tar_gz": report["tar_gz"],
        "zip": report["zip"],
        "export_checksums": report["export_checksums"],
    }


def render_export_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['export_id']}",
        "",
        f"- profile_id: `{report['profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- archive export: `{report['archive_export']['archive_id']}` / `{report['archive_export']['readiness']}`",
        f"- archive prefix: `{report['archive_prefix']}`",
        f"- included_file_count: `{report['included_file_count']}`",
        f"- tar_gz: `{report['tar_gz']}`",
        f"- zip: `{report['zip']}`",
        "",
        "## Export Checksums",
        "",
        f"- tar_gz sha256: `{report['export_checksums']['tar_gz']}`",
        f"- zip sha256: `{report['export_checksums']['zip']}`",
    ]
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Included Files", ""])
    for rel in report["included_files"]:
        lines.append(f"- `{rel}`")
    return "\n".join(lines).rstrip() + "\n"


def render_export_checksums(report: dict[str, Any]) -> str:
    return (
        f"{report['export_checksums']['tar_gz']}  {report['tar_gz']}\n"
        f"{report['export_checksums']['zip']}  {report['zip']}\n"
    )


def write_export_outputs(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    _, entries = _archive_inputs(profile_id, repo_root=repo_root)
    paths = _export_paths(profile_id)

    _write_tar_gz(paths["tar_gz"], entries)
    _write_zip(paths["zip"], entries)

    report = build_export_bundle(profile_id, repo_root=repo_root)
    manifest = build_export_manifest(profile_id, repo_root=repo_root)

    paths["report_json"].parent.mkdir(parents=True, exist_ok=True)
    write_text(paths["report_md"], render_export_markdown(report))
    write_text(paths["report_json"], json.dumps(report, indent=2) + "\n")
    write_text(paths["checksums"], render_export_checksums(report))
    manifest_path = EXPORTS_DIR / f"{profile_id}_export_manifest.json"
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    return {
        "report_json": _relative(paths["report_json"], repo_root),
        "report_md": _relative(paths["report_md"], repo_root),
        "checksums": _relative(paths["checksums"], repo_root),
        "tar_gz": _relative(paths["tar_gz"], repo_root),
        "zip": _relative(paths["zip"], repo_root),
        "manifest": _relative(manifest_path, repo_root),
    }
