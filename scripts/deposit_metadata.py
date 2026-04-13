#!/usr/bin/env python3
"""Build deposit-ready citation and repository metadata from release exports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

try:  # pragma: no cover - import path differs between script and package use.
    from .export_bundle import build_export_bundle, write_export_outputs
    from .figures_common import REPO_ROOT, load_yaml, write_text
except ImportError:  # pragma: no cover
    from export_bundle import build_export_bundle, write_export_outputs
    from figures_common import REPO_ROOT, load_yaml, write_text


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
DEPOSIT_DIR = RELEASE_ROOT / "deposit"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"
PROFILE_PATH = RELEASE_ROOT / "profiles" / "profiles.yml"
MANUSCRIPT_INDEX_PATH = REPO_ROOT / "manuscript" / "index.md"
MYST_CONFIG_PATH = REPO_ROOT / "manuscript" / "myst.yml"


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _load_manuscript_frontmatter(path: Path = MANUSCRIPT_INDEX_PATH) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, remainder = text.split("---\n", 1)
    frontmatter, _, _ = remainder.partition("\n---\n")
    data = yaml.safe_load(frontmatter) or {}
    return data if isinstance(data, dict) else {}


def _split_name(name: str) -> tuple[str, str]:
    tokens = [token for token in name.strip().split() if token]
    if not tokens:
        return "", ""
    if len(tokens) == 1:
        return "", tokens[0]
    return " ".join(tokens[:-1]), tokens[-1]


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return (
        normalized.startswith("add ")
        or "placeholder" in normalized
        or normalized in {"working manuscript", "lead.author@example.org", "add institution"}
    )


def _load_profile(profile_id: str) -> dict[str, Any]:
    payload = load_yaml(PROFILE_PATH)
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict) or profile_id not in profiles:
        raise ValueError(f"unknown release profile {profile_id!r}")
    profile = profiles[profile_id]
    if not isinstance(profile, dict):
        raise ValueError(f"release profile {profile_id!r} must be an object")
    return profile


def _metadata_core(profile_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    profile = _load_profile(profile_id)
    frontmatter = _load_manuscript_frontmatter()
    myst = load_yaml(MYST_CONFIG_PATH)
    return profile, frontmatter, myst


def _release_metadata(profile: dict[str, Any]) -> dict[str, Any]:
    metadata = profile.get("release_metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _normalize_creators(
    profile: dict[str, Any], frontmatter: dict[str, Any], myst: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    release_metadata = _release_metadata(profile)
    release_creators = release_metadata.get("creators")
    if isinstance(release_creators, list) and release_creators:
        raw_authors = release_creators
    else:
        frontmatter_authors = frontmatter.get("authors")
        use_frontmatter = isinstance(frontmatter_authors, list) and bool(frontmatter_authors)
        if use_frontmatter:
            frontmatter_names = [
                str(item.get("name", "")).strip()
                for item in frontmatter_authors
                if isinstance(item, dict)
            ]
            if frontmatter_names and all(_is_placeholder(name) for name in frontmatter_names):
                use_frontmatter = False
        raw_authors = frontmatter_authors if use_frontmatter else myst.get("project", {}).get("authors", [])

    affiliations = frontmatter.get("affiliations", [])
    affiliation_map = {}
    if isinstance(affiliations, list):
        for item in affiliations:
            if isinstance(item, dict) and item.get("id"):
                affiliation_map[str(item["id"])] = str(item.get("institution", "")).strip()

    creators: list[dict[str, Any]] = []
    if not isinstance(raw_authors, list) or not raw_authors:
        warnings.append("manuscript author metadata is missing; deposit creators fall back to an empty list")
        return creators, warnings

    for idx, entry in enumerate(raw_authors, start=1):
        if isinstance(entry, dict):
            name = str(entry.get("name", "")).strip()
            email = str(entry.get("email", "")).strip()
            aff_value = entry.get("affiliation") or entry.get("affiliations")
            affiliation = ""
            if isinstance(aff_value, str):
                affiliation = affiliation_map.get(aff_value, aff_value)
            elif isinstance(aff_value, list) and aff_value:
                first = str(aff_value[0])
                affiliation = affiliation_map.get(first, first)
            elif idx == 1 and affiliation_map:
                affiliation = next(iter(affiliation_map.values()))
        else:
            name = str(entry).strip()
            email = ""
            affiliation = next(iter(affiliation_map.values()), "")

        given_names, family_names = _split_name(name)
        creator = {
            "name": name or f"Author {idx}",
            "given_names": given_names,
            "family_names": family_names,
            "affiliation": affiliation,
            "email": email,
        }
        creators.append(creator)

        if _is_placeholder(name):
            warnings.append(f"creator metadata contains a placeholder name: {name or f'author_{idx}'}")
        if affiliation and _is_placeholder(affiliation):
            warnings.append(f"creator metadata contains a placeholder affiliation: {affiliation}")
        if email and email.endswith("@example.org"):
            warnings.append(f"creator metadata contains an example email: {email}")

    return creators, warnings
def _description(profile: dict[str, Any], frontmatter: dict[str, Any], myst: dict[str, Any]) -> str:
    release_metadata = _release_metadata(profile)
    release_description = str(release_metadata.get("description", "")).strip()
    if release_description and not _is_placeholder(release_description):
        return release_description
    subtitle = str(frontmatter.get("subtitle", "")).strip()
    if subtitle and not _is_placeholder(subtitle):
        return subtitle
    return str(myst.get("project", {}).get("description", "")).strip()


def _keywords(profile: dict[str, Any], frontmatter: dict[str, Any], myst: dict[str, Any]) -> list[str]:
    values: list[str] = []
    release_metadata = _release_metadata(profile)
    for candidate in (
        release_metadata.get("keywords", []),
        frontmatter.get("keywords", []),
        myst.get("project", {}).get("keywords", []),
    ):
        if isinstance(candidate, list):
            for item in candidate:
                text = str(item).strip()
                if text and not _is_placeholder(text):
                    values.append(text)
    return list(dict.fromkeys(values))


def _title(frontmatter: dict[str, Any], profile: dict[str, Any], myst: dict[str, Any]) -> str:
    release_metadata = _release_metadata(profile)
    release_title = str(release_metadata.get("title", "")).strip()
    if release_title and not _is_placeholder(release_title):
        return release_title
    frontmatter_title = str(frontmatter.get("title", "")).strip()
    if frontmatter_title and not _is_placeholder(frontmatter_title):
        return frontmatter_title
    profile_title = str(profile.get("title", "")).strip()
    if profile_title:
        return profile_title
    return str(myst.get("project", {}).get("title", "")).strip()


def _version_tag(export_id: str) -> str:
    if "_v" in export_id:
        return export_id.rsplit("_", 1)[-1]
    return "v1"


def _citation_cff_payload(
    title: str,
    version: str,
    date_released: str,
    description: str,
    keywords: list[str],
    creators: list[dict[str, Any]],
    profile_id: str,
) -> dict[str, Any]:
    authors = []
    for creator in creators:
        item: dict[str, Any] = {}
        if creator["family_names"]:
            item["family-names"] = creator["family_names"]
        if creator["given_names"]:
            item["given-names"] = creator["given_names"]
        if not item:
            item["name"] = creator["name"]
        if creator["affiliation"]:
            item["affiliation"] = creator["affiliation"]
        if creator["email"]:
            item["email"] = creator["email"]
        authors.append(item)
    return {
        "cff-version": "1.2.0",
        "message": "If you use this release, please cite it using the metadata below.",
        "title": title,
        "version": version,
        "date-released": date_released,
        "type": "software",
        "authors": authors,
        "keywords": keywords,
        "abstract": description,
        "identifiers": [
            {
                "type": "other",
                "value": f"{profile_id}_deposit_metadata_v1",
                "description": "Internal deposit metadata identifier",
            }
        ],
    }


def _codemeta_payload(
    title: str,
    version: str,
    date_released: str,
    description: str,
    keywords: list[str],
    creators: list[dict[str, Any]],
    profile_id: str,
) -> dict[str, Any]:
    authors: list[dict[str, Any]] = []
    for creator in creators:
        author: dict[str, Any] = {"@type": "Person", "name": creator["name"]}
        if creator["given_names"]:
            author["givenName"] = creator["given_names"]
        if creator["family_names"]:
            author["familyName"] = creator["family_names"]
        if creator["email"]:
            author["email"] = creator["email"]
        if creator["affiliation"]:
            author["affiliation"] = {"@type": "Organization", "name": creator["affiliation"]}
        authors.append(author)
    return {
        "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
        "@type": "SoftwareSourceCode",
        "identifier": f"{profile_id}_deposit_metadata_v1",
        "name": title,
        "version": version,
        "description": description,
        "datePublished": date_released,
        "keywords": keywords,
        "author": authors,
    }


def _zenodo_payload(
    title: str,
    version: str,
    description: str,
    keywords: list[str],
    creators: list[dict[str, Any]],
    profile_id: str,
) -> dict[str, Any]:
    zenodo_creators = []
    for creator in creators:
        if creator["family_names"] and creator["given_names"]:
            name = f"{creator['family_names']}, {creator['given_names']}"
        else:
            name = creator["name"]
        item: dict[str, Any] = {"name": name}
        if creator["affiliation"]:
            item["affiliation"] = creator["affiliation"]
        zenodo_creators.append(item)
    return {
        "metadata": {
            "title": title,
            "upload_type": "software",
            "publication_type": "other",
            "description": description,
            "creators": zenodo_creators,
            "keywords": keywords,
            "version": version,
            "notes": f"Generated from release profile {profile_id}",
        }
    }


def _osf_payload(
    title: str,
    description: str,
    keywords: list[str],
    creators: list[dict[str, Any]],
    profile_id: str,
) -> dict[str, Any]:
    contributors = []
    for creator in creators:
        item: dict[str, Any] = {"name": creator["name"], "bibliographic": True}
        if creator["email"]:
            item["email"] = creator["email"]
        if creator["affiliation"]:
            item["affiliation"] = creator["affiliation"]
        contributors.append(item)
    return {
        "title": title,
        "description": description,
        "category": "project",
        "tags": keywords,
        "contributors": contributors,
        "node_metadata": {
            "profile_id": profile_id,
            "resource_type": "software",
        },
    }


def build_deposit_metadata(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    profile, frontmatter, myst = _metadata_core(profile_id)
    export_report = build_export_bundle(profile_id, repo_root=repo_root)
    blocking_issues = list(export_report.get("blocking_issues", []))
    warnings = list(export_report.get("warnings", []))
    if export_report["readiness"] != "ready":
        blocking_issues.append(f"export bundle {profile_id} is {export_report['readiness']}")

    creators, creator_warnings = _normalize_creators(profile, frontmatter, myst)
    warnings.extend(creator_warnings)

    title = _title(frontmatter, profile, myst)
    description = _description(profile, frontmatter, myst)
    keywords = _keywords(profile, frontmatter, myst)
    release_metadata = _release_metadata(profile)
    date_released = str(release_metadata.get("date_released", "")).strip() or str(frontmatter.get("date", "")).strip() or "2026-04-13"
    version = _version_tag(export_report["export_id"])

    if _is_placeholder(title):
        warnings.append(f"deposit title still looks like a placeholder: {title}")
    if not description:
        warnings.append("deposit description is empty; using minimal software-release metadata")
    if not keywords:
        warnings.append("keyword metadata is empty; add manuscript or project keywords before deposit")

    citation_cff = _citation_cff_payload(
        title=title,
        version=version,
        date_released=date_released,
        description=description,
        keywords=keywords,
        creators=creators,
        profile_id=profile_id,
    )
    codemeta = _codemeta_payload(
        title=title,
        version=version,
        date_released=date_released,
        description=description,
        keywords=keywords,
        creators=creators,
        profile_id=profile_id,
    )
    zenodo = _zenodo_payload(
        title=title,
        version=version,
        description=description,
        keywords=keywords,
        creators=creators,
        profile_id=profile_id,
    )
    osf = _osf_payload(
        title=title,
        description=description,
        keywords=keywords,
        creators=creators,
        profile_id=profile_id,
    )

    readiness = "ready" if not blocking_issues else "blocked"
    stem = f"{profile_id}_deposit_metadata"
    return {
        "profile_id": profile_id,
        "deposit_metadata_id": f"{stem}_v1",
        "readiness": readiness,
        "blocking_issues": sorted(dict.fromkeys(blocking_issues)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "release_title": title,
        "description": description,
        "version": version,
        "date_released": date_released,
        "keyword_count": len(keywords),
        "creators_count": len(creators),
        "targets": ["citation_cff", "codemeta", "zenodo", "osf"],
        "export_bundle": {
            "export_id": export_report["export_id"],
            "readiness": export_report["readiness"],
            "report_json": f"workflows/release/exports/{profile_id}_export.json",
            "manifest": f"workflows/release/exports/{profile_id}_export_manifest.json",
            "tar_gz": export_report["tar_gz"],
            "zip": export_report["zip"],
        },
        "files": {
            "report_json": f"workflows/release/reports/{stem}.json",
            "report_md": f"workflows/release/reports/{stem}.md",
            "manifest": f"workflows/release/manifests/{stem}.json",
            "citation_cff": f"workflows/release/deposit/{profile_id}_CITATION.cff",
            "codemeta": f"workflows/release/deposit/{profile_id}_codemeta.json",
            "zenodo": f"workflows/release/deposit/{profile_id}_zenodo_metadata.json",
            "osf": f"workflows/release/deposit/{profile_id}_osf_metadata.json",
        },
        "metadata_payloads": {
            "citation_cff": citation_cff,
            "codemeta": codemeta,
            "zenodo": zenodo,
            "osf": osf,
        },
    }


def build_deposit_manifest(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    report = build_deposit_metadata(profile_id, repo_root=repo_root)
    return {
        "package_id": report["deposit_metadata_id"],
        "profile_id": profile_id,
        "readiness": report["readiness"],
        "release_title": report["release_title"],
        "version": report["version"],
        "date_released": report["date_released"],
        "targets": report["targets"],
        "export_bundle": report["export_bundle"],
        "files": report["files"],
    }


def render_deposit_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# {report['deposit_metadata_id']}",
        "",
        f"- profile_id: `{report['profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- release_title: `{report['release_title']}`",
        f"- version: `{report['version']}`",
        f"- date_released: `{report['date_released']}`",
        f"- creators_count: `{report['creators_count']}`",
        f"- keyword_count: `{report['keyword_count']}`",
        f"- export bundle: `{report['export_bundle']['export_id']}` / `{report['export_bundle']['readiness']}`",
        "",
        "## Metadata Targets",
        "",
    ]
    for target in report["targets"]:
        lines.append(f"- `{target}` -> `{report['files'][target]}`")
    if report["blocking_issues"]:
        lines.extend(["", "## Blocking Issues", ""])
        for issue in report["blocking_issues"]:
            lines.append(f"- {issue}")
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    lines.extend(["", "## Export Deliverables", ""])
    lines.append(f"- tar.gz: `{report['export_bundle']['tar_gz']}`")
    lines.append(f"- zip: `{report['export_bundle']['zip']}`")
    return "\n".join(lines).rstrip() + "\n"


def write_deposit_outputs(profile_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    write_export_outputs(profile_id, repo_root=repo_root)
    report = build_deposit_metadata(profile_id, repo_root=repo_root)
    manifest = build_deposit_manifest(profile_id, repo_root=repo_root)
    stem = f"{profile_id}_deposit_metadata"

    report_json_path = REPORTS_DIR / f"{stem}.json"
    report_md_path = REPORTS_DIR / f"{stem}.md"
    manifest_path = MANIFESTS_DIR / f"{stem}.json"
    citation_cff_path = DEPOSIT_DIR / f"{profile_id}_CITATION.cff"
    codemeta_path = DEPOSIT_DIR / f"{profile_id}_codemeta.json"
    zenodo_path = DEPOSIT_DIR / f"{profile_id}_zenodo_metadata.json"
    osf_path = DEPOSIT_DIR / f"{profile_id}_osf_metadata.json"

    for path in (
        report_json_path,
        report_md_path,
        manifest_path,
        citation_cff_path,
        codemeta_path,
        zenodo_path,
        osf_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    write_text(report_md_path, render_deposit_markdown(report))
    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(manifest_path, json.dumps(manifest, indent=2) + "\n")
    write_text(
        citation_cff_path,
        yaml.safe_dump(report["metadata_payloads"]["citation_cff"], sort_keys=False, allow_unicode=True),
    )
    write_text(codemeta_path, json.dumps(report["metadata_payloads"]["codemeta"], indent=2) + "\n")
    write_text(zenodo_path, json.dumps(report["metadata_payloads"]["zenodo"], indent=2) + "\n")
    write_text(osf_path, json.dumps(report["metadata_payloads"]["osf"], indent=2) + "\n")
    return {
        "report_json": _relative(report_json_path, repo_root),
        "report_md": _relative(report_md_path, repo_root),
        "manifest": _relative(manifest_path, repo_root),
        "citation_cff": _relative(citation_cff_path, repo_root),
        "codemeta": _relative(codemeta_path, repo_root),
        "zenodo": _relative(zenodo_path, repo_root),
        "osf": _relative(osf_path, repo_root),
    }
