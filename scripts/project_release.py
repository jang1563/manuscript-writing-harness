#!/usr/bin/env python3
"""Scaffold and evaluate real-project release profiles on top of the demo multi-agent manuscript system."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

try:  # pragma: no cover - import path differs between script and package use.
    from .deposit_metadata import _is_placeholder
    from .fgsea_study_dossier import build_fgsea_study_dossier
    from .figures_common import REPO_ROOT, load_yaml, write_text
    from .release_bundle import load_release_profile
    from .scaffold_msigdb_profile import scaffold_msigdb_profile
except ImportError:  # pragma: no cover
    from deposit_metadata import _is_placeholder
    from fgsea_study_dossier import build_fgsea_study_dossier
    from figures_common import REPO_ROOT, load_yaml, write_text
    from release_bundle import load_release_profile
    from scaffold_msigdb_profile import scaffold_msigdb_profile


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
PROJECTS_DIR = RELEASE_ROOT / "projects"
PROFILE_PATH = RELEASE_ROOT / "profiles" / "profiles.yml"
POLICY_DIR = RELEASE_ROOT / "policies"


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _load_profiles() -> dict[str, Any]:
    return load_yaml(PROFILE_PATH)


def _write_profiles(payload: dict[str, Any]) -> None:
    write_text(PROFILE_PATH, yaml.safe_dump(payload, sort_keys=False))


def _default_release_profile(
    profile_id: str,
    title: str,
    venue_id: str,
    study_id: str,
) -> dict[str, Any]:
    template = copy.deepcopy(load_release_profile("integrated_demo_release"))
    template["profile_id"] = profile_id
    template["title"] = title
    template["venue_id"] = venue_id
    template["release_metadata"] = {
        "title": title,
        "description": f"Replace with a project-specific release summary for {title}.",
        "date_released": "2026-04-13",
        "keywords": [
            "manuscript",
            "scientific writing",
            "bioinformatics",
            "fgsea",
            "msigdb",
        ],
        "creators": [
            {
                "name": "Add Lead Author",
                "affiliation": "Add Institution",
            }
        ],
    }
    template["project_context"] = {
        "study_id": study_id,
        "notes": "Update release metadata and activate the project study profile before generating a final release bundle.",
    }
    return template


def _placeholder_release_warnings(profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    metadata = profile.get("release_metadata", {})
    if not isinstance(metadata, dict):
        return ["release_metadata is missing or invalid"]
    for field in ("title", "description", "date_released"):
        value = str(metadata.get(field, "")).strip()
        if _is_placeholder(value):
            warnings.append(f"release_metadata.{field} still contains a placeholder")
    creators = metadata.get("creators", [])
    if not isinstance(creators, list) or not creators:
        warnings.append("release_metadata.creators is empty")
    else:
        for idx, creator in enumerate(creators, start=1):
            if not isinstance(creator, dict):
                warnings.append(f"release_metadata.creators[{idx}] is invalid")
                continue
            name = str(creator.get("name", "")).strip()
            affiliation = str(creator.get("affiliation", "")).strip()
            if _is_placeholder(name):
                warnings.append(f"release_metadata.creators[{idx}].name still contains a placeholder")
            if _is_placeholder(affiliation):
                warnings.append(f"release_metadata.creators[{idx}].affiliation still contains a placeholder")
    return warnings


def _looks_like_scaffold_raw_table(path: Path) -> bool:
    if not path.exists():
        return False
    rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) <= 3:
        return True
    sample = "\n".join(rows[:4])
    return "GENE_A" in sample and "GENE_B" in sample


def _load_project(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    project_path = repo_root / "workflows" / "release" / "projects" / project_id / "project.yml"
    if not project_path.exists():
        raise ValueError(f"Unknown project release scaffold {project_id!r}")
    payload = load_yaml(project_path)
    if payload.get("project_id") != project_id:
        raise ValueError(f"project manifest {project_path} has a mismatched project_id")
    payload["_project_path"] = _relative(project_path, repo_root)
    return payload


def scaffold_project_release(
    project_id: str,
    *,
    title: str,
    venue_id: str = "nature",
    species: str = "human",
    collection: str = "H",
    version: str | None = None,
    identifier_type: str = "gene_symbol",
    study_id: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    resolved_study_id = study_id or project_id
    release_profile_id = f"{project_id}_release"
    study_payload = scaffold_msigdb_profile(
        resolved_study_id,
        species=species,
        collection=collection,
        version=version,
        identifier_type=identifier_type,
        overwrite=overwrite,
    )

    project_root = PROJECTS_DIR / project_id
    project_manifest = {
        "project_id": project_id,
        "title": title,
        "release_profile_id": release_profile_id,
        "study_id": resolved_study_id,
        "venue_id": venue_id,
        "pathway_strategy": {
            "provider": "msigdb",
            "species": species,
            "collection": collection,
            "version": version or load_yaml(REPO_ROOT / "pathways" / "msigdb" / "catalog.yml")["current_versions"][species],
            "identifier_type": identifier_type,
        },
        "notes": {
            "status": "scaffolded",
            "release_summary": "Replace with a project-specific summary before deposit.",
            "activation": "Activate the project study profile after validating the licensed MSigDB GMT and fgsea results.",
        },
    }
    write_text(project_root / "project.yml", yaml.safe_dump(project_manifest, sort_keys=False))
    write_text(
        project_root / "README.md",
        "\n".join(
            [
                f"# {project_id}",
                "",
                f"This project scaffold wraps the MSigDB-backed study profile `{resolved_study_id}` and the release profile `{release_profile_id}`.",
                "",
                "Recommended workflow:",
                "",
                f"1. Replace the placeholder DE table under `pathways/studies/{resolved_study_id}/inputs/raw/`.",
                f"2. Add the licensed MSigDB GMT at `pathways/studies/{resolved_study_id}/inputs/msigdb/`.",
                f"3. Run `python3 scripts/run_msigdb_profile.py --config pathways/studies/{resolved_study_id}/configs/fgsea.yml --prepare-ranks --build-phase2 --json`.",
                f"4. Fill in release metadata placeholders inside `workflows/release/profiles/profiles.yml` for `{release_profile_id}`.",
                f"5. Review readiness with `python3 scripts/check_project_release.py --project {project_id} --write --json`.",
                f"6. Build the top-level handoff with `python3 scripts/check_project_handoff.py --project {project_id} --write --json`.",
                "",
            ]
        )
        + "\n"
    )
    policy_manifest = {
        "policy_id": f"{project_id}_policy",
        "project_id": project_id,
        "review_model": "double_blind" if venue_id == "conference" else "non_anonymized",
        "anonymization_required": venue_id == "conference",
        "manuscript_identity_scrubbed": False if venue_id == "conference" else True,
        "supplement_identity_scrubbed": False if venue_id == "conference" else True,
        "metadata_identity_scrubbed": False if venue_id == "conference" else True,
        "human_subject_data": False,
        "controlled_access_required": False,
        "raw_data_release": "public",
        "code_release": "public",
        "msigdb_license_confirmed": False,
        "deposit_contact": "Add release contact",
    }
    write_text(POLICY_DIR / f"{project_id}.yml", yaml.safe_dump(policy_manifest, sort_keys=False))

    profiles_payload = _load_profiles()
    profiles = profiles_payload.setdefault("profiles", {})
    if not isinstance(profiles, dict):
        raise ValueError("workflows/release/profiles/profiles.yml must define a profiles mapping")
    if release_profile_id in profiles and not overwrite:
        raise FileExistsError(f"release profile {release_profile_id!r} already exists")
    profiles[release_profile_id] = _default_release_profile(release_profile_id, title, venue_id, resolved_study_id)
    _write_profiles(profiles_payload)

    return {
        "project_id": project_id,
        "project_root": _relative(project_root),
        "project_manifest": _relative(project_root / "project.yml"),
        "project_readme": _relative(project_root / "README.md"),
        "policy_manifest": _relative(POLICY_DIR / f"{project_id}.yml"),
        "release_profile_id": release_profile_id,
        "study_id": resolved_study_id,
        "study_payload": study_payload,
        "next_steps": [
            f"python3 scripts/run_msigdb_profile.py --config pathways/studies/{resolved_study_id}/configs/fgsea.yml --prepare-ranks --build-phase2 --json",
            f"python3 scripts/check_project_release.py --project {project_id} --write --json",
        ],
    }


def build_project_release(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    project = _load_project(project_id, repo_root)
    release_profile_id = str(project["release_profile_id"])
    study_id = str(project["study_id"])
    study_config_path = repo_root / "pathways" / "studies" / study_id / "configs" / "fgsea.yml"
    project_root = repo_root / "workflows" / "release" / "projects" / project_id

    blocking_issues: list[str] = []
    warnings: list[str] = []

    if not study_config_path.exists():
        blocking_issues.append(f"study config is missing at {_relative(study_config_path, repo_root)}")
        study_report: dict[str, Any] | None = None
    else:
        study_report = build_fgsea_study_dossier(study_config_path)
        warnings.extend(study_report.get("warnings", []))
        if str(study_report.get("readiness", "blocked")) == "blocked":
            blocking_issues.extend(study_report.get("blocking_issues", []))
        else:
            warnings.extend(study_report.get("blocking_issues", []))

    profile = load_release_profile(release_profile_id, repo_root)
    warnings.extend(_placeholder_release_warnings(profile))
    policy_path = repo_root / "workflows" / "release" / "policies" / f"{project_id}.yml"
    if policy_path.exists():
        package_policy_path = _relative(policy_path, repo_root)
    else:
        package_policy_path = None
        warnings.append("release policy file is missing")

    raw_input_path = repo_root / f"pathways/studies/{study_id}/inputs/raw/{study_id}_differential_expression.csv"
    if raw_input_path.exists() and _looks_like_scaffold_raw_table(raw_input_path):
        warnings.append("raw differential-expression input still looks like the scaffold placeholder")

    gmt_path = repo_root / f"pathways/studies/{study_id}/inputs/msigdb/{study_id}_{project['pathway_strategy']['collection']}_{project['pathway_strategy']['version']}_{project['pathway_strategy']['identifier_type']}.gmt"
    if not gmt_path.exists():
        warnings.append("licensed MSigDB GMT has not been placed at the expected study path")

    active_ready = bool(study_report and study_report.get("active_profile", {}).get("is_active_source"))
    if not active_ready:
        warnings.append("project study profile is not the active fgsea source yet")

    readiness = "ready"
    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"

    package_paths = [
        str(project["_project_path"]),
        _relative(project_root / "README.md", repo_root),
        _relative(study_config_path, repo_root),
        f"pathways/studies/{study_id}/configs/rank_prep.yml",
        f"pathways/studies/{study_id}/inputs/raw/{study_id}_differential_expression.csv",
        f"pathways/studies/{study_id}/inputs/msigdb/README.md",
        f"workflows/release/profiles/profiles.yml",
    ]
    if package_policy_path:
        package_paths.append(package_policy_path)
    if study_report is not None:
        package_paths.extend(
            [
                str(study_report.get("config", "")),
                str(study_report.get("fgsea", {}).get("summary_json", "")),
                str(study_report.get("figure_05", {}).get("review_page", "")),
            ]
        )
    package_paths = sorted(path for path in dict.fromkeys(package_paths) if path)

    return {
        "project_id": project_id,
        "title": str(project["title"]),
        "release_profile_id": release_profile_id,
        "study_id": study_id,
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "venue_id": str(project["venue_id"]),
        "pathway_strategy": project["pathway_strategy"],
        "release_metadata": profile.get("release_metadata", {}),
        "study_report": study_report,
        "package_paths": package_paths,
        "next_steps": [
            f"python3 scripts/run_msigdb_profile.py --config pathways/studies/{study_id}/configs/fgsea.yml --prepare-ranks --build-phase2 --json",
            f"python3 scripts/check_project_release.py --project {project_id} --write --json",
        ],
    }


def render_project_release_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Project Release Readiness: {report['project_id']}",
        "",
        f"- title: `{report['title']}`",
        f"- release_profile_id: `{report['release_profile_id']}`",
        f"- study_id: `{report['study_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- venue_id: `{report['venue_id']}`",
        "",
        "## Pathway Strategy",
        "",
    ]
    for key, value in (report.get("pathway_strategy") or {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")

    study_report = report.get("study_report") or {}
    if study_report:
        lines.extend(
            [
                "## Study Status",
                "",
                f"- study readiness: `{study_report.get('readiness', 'missing')}`",
                f"- active source: `{study_report.get('active_profile', {}).get('is_active_source', False)}`",
                f"- figure_05 sync: `{study_report.get('active_profile', {}).get('figure_05_sync', {}).get('status', 'unknown')}`",
                f"- fgsea result_count: `{study_report.get('fgsea', {}).get('result_count', 'n/a')}`",
                f"- fgsea figure_export_count: `{study_report.get('fgsea', {}).get('figure_export_count', 'n/a')}`",
                "",
            ]
        )

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


def write_project_release_outputs(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = build_project_release(project_id, repo_root=repo_root)
    project_root = repo_root / "workflows" / "release" / "projects" / project_id
    report_json = project_root / "project_readiness.json"
    report_md = project_root / "project_readiness.md"
    write_text(report_json, json.dumps(report, indent=2) + "\n")
    write_text(report_md, render_project_release_markdown(report))
    return {
        "report_json": _relative(report_json, repo_root),
        "report_md": _relative(report_md, repo_root),
    }
