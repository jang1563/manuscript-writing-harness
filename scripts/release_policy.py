#!/usr/bin/env python3
"""Evaluate anonymization and data-sharing policy readiness for release profiles and projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

try:  # pragma: no cover
    from .deposit_metadata import _is_placeholder
    from .figures_common import REPO_ROOT, write_text
    from .project_release import _load_project
except ImportError:  # pragma: no cover
    from deposit_metadata import _is_placeholder
    from figures_common import REPO_ROOT, write_text
    from project_release import _load_project


POLICY_DIR = REPO_ROOT / "workflows" / "release" / "policies"


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _load_policy(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a policy object")
    return payload


def _policy_path(project_id: str, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / "workflows" / "release" / "policies" / f"{project_id}.yml"


def build_release_policy(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    project = _load_project(project_id, repo_root)
    policy_path = _policy_path(project_id, repo_root)
    if not policy_path.exists():
        raise ValueError(f"Missing release policy file at {_relative(policy_path, repo_root)}")

    policy = _load_policy(policy_path)
    if policy.get("project_id") != project_id:
        raise ValueError(f"policy {policy_path} has mismatched project_id")

    blocking_issues: list[str] = []
    warnings: list[str] = []

    review_model = str(policy.get("review_model", "unknown"))
    anonymization_required = bool(policy.get("anonymization_required", False))
    human_subject_data = bool(policy.get("human_subject_data", False))
    controlled_access_required = bool(policy.get("controlled_access_required", False))
    raw_data_release = str(policy.get("raw_data_release", "unknown"))
    code_release = str(policy.get("code_release", "unknown"))
    msigdb_license_confirmed = policy.get("msigdb_license_confirmed")
    deposit_contact = str(policy.get("deposit_contact", "")).strip()

    if _is_placeholder(deposit_contact):
        warnings.append("deposit_contact still contains a placeholder")

    if review_model not in {"non_anonymized", "single_blind", "double_blind"}:
        warnings.append(f"review_model is not recognized: {review_model}")

    if anonymization_required:
        for field in ("manuscript_identity_scrubbed", "supplement_identity_scrubbed", "metadata_identity_scrubbed"):
            if policy.get(field) is not True:
                warnings.append(f"{field} is not yet confirmed for anonymized review")
    if human_subject_data:
        if raw_data_release not in {"controlled", "summary_only"}:
            warnings.append("human-subject project should usually avoid public raw_data_release")
        if not controlled_access_required and raw_data_release == "controlled":
            warnings.append("controlled raw_data_release is set but controlled_access_required is false")
    if raw_data_release not in {"public", "controlled", "summary_only", "none"}:
        warnings.append(f"raw_data_release has an unrecognized value: {raw_data_release}")
    if code_release not in {"public", "private", "upon_request"}:
        warnings.append(f"code_release has an unrecognized value: {code_release}")

    pathway_strategy = project.get("pathway_strategy", {})
    if isinstance(pathway_strategy, dict) and pathway_strategy.get("provider") == "msigdb":
        if msigdb_license_confirmed is not True:
            warnings.append("msigdb_license_confirmed is not yet true for an MSigDB-backed project")

    readiness = "ready"
    if blocking_issues:
        readiness = "blocked"
    elif warnings:
        readiness = "provisional"

    return {
        "project_id": project_id,
        "policy_id": str(policy.get("policy_id", f"{project_id}_policy")),
        "profile_id": project.get("release_profile_id"),
        "readiness": readiness,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
        "review_model": review_model,
        "anonymization_required": anonymization_required,
        "human_subject_data": human_subject_data,
        "controlled_access_required": controlled_access_required,
        "raw_data_release": raw_data_release,
        "code_release": code_release,
        "msigdb_license_confirmed": msigdb_license_confirmed,
        "deposit_contact": deposit_contact,
        "package_paths": [
            _relative(policy_path, repo_root),
            _relative(repo_root / project["_project_path"], repo_root),
        ],
    }


def render_release_policy_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Release Policy Readiness: {report['project_id']}",
        "",
        f"- policy_id: `{report['policy_id']}`",
        f"- profile_id: `{report['profile_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- review_model: `{report['review_model']}`",
        f"- anonymization_required: `{report['anonymization_required']}`",
        f"- human_subject_data: `{report['human_subject_data']}`",
        f"- controlled_access_required: `{report['controlled_access_required']}`",
        f"- raw_data_release: `{report['raw_data_release']}`",
        f"- code_release: `{report['code_release']}`",
        f"- msigdb_license_confirmed: `{report['msigdb_license_confirmed']}`",
        f"- deposit_contact: `{report['deposit_contact']}`",
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
    return "\n".join(lines)


def write_release_policy_outputs(project_id: str, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    report = build_release_policy(project_id, repo_root)
    project_root = repo_root / "workflows" / "release" / "projects" / project_id
    report_json = project_root / "policy_readiness.json"
    report_md = project_root / "policy_readiness.md"
    write_text(report_json, json.dumps(report, indent=2) + "\n")
    write_text(report_md, render_release_policy_markdown(report))
    return {
        "report_json": _relative(report_json, repo_root),
        "report_md": _relative(report_md, repo_root),
    }
