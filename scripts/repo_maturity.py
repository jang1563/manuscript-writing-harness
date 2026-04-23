#!/usr/bin/env python3
"""Build canonical repo-maturity reports from tracked repo evidence."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT, write_text
    from .harness_benchmark import build_harness_benchmark_matrix_report
    from .manuscript_scope_common import build_manuscript_scope_status
    from .pre_submission_audit import build_pre_submission_audit
    from .project_handoff import build_project_handoff
    from .project_release import build_project_release
    from .reference_integrity import build_reference_report
    from .release_bundle import build_release_bundle
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT, write_text
    from harness_benchmark import build_harness_benchmark_matrix_report
    from manuscript_scope_common import build_manuscript_scope_status
    from pre_submission_audit import build_pre_submission_audit
    from project_handoff import build_project_handoff
    from project_release import build_project_release
    from reference_integrity import build_reference_report
    from release_bundle import build_release_bundle


RELEASE_ROOT = REPO_ROOT / "workflows" / "release"
REPORTS_DIR = RELEASE_ROOT / "reports"
MANIFESTS_DIR = RELEASE_ROOT / "manifests"
DEFAULT_RELEASE_PROFILE_ID = "integrated_demo_release"
DEFAULT_PROJECT_ID = "rnaseq_real_project_template"
ALLOWED_PROFILES = {"demo", "submission-framework", "submission-ready"}
ACCEPTANCE_STEP_IDS = ("runtime_support", "scaffold", "python_suite", "r_figure_suite")
ALLOWED_ACCEPTANCE_STEP_STATUSES = {"ready", "blocked", "error", "not_run"}


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _maturity_stem(profile: str) -> str:
    if profile not in ALLOWED_PROFILES:
        raise ValueError(
            f"Unknown repo maturity profile '{profile}'. Expected one of: {', '.join(sorted(ALLOWED_PROFILES))}"
        )
    return f"repo_maturity_{profile}"


def _normalize_acceptance_step(step_id: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"acceptance step {step_id!r} must be an object")
    status = str(payload.get("status", "")).strip()
    if status not in ALLOWED_ACCEPTANCE_STEP_STATUSES - {"not_run"}:
        raise ValueError(
            f"acceptance step {step_id!r} has invalid status {status!r}; expected ready, blocked, or error"
        )
    return {
        "status": status,
        "command": payload.get("command"),
        "exit_code": payload.get("exit_code"),
        "stdout_path": payload.get("stdout_path"),
        "stderr_path": payload.get("stderr_path"),
    }


def _not_run_acceptance_step(step_id: str) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "status": "not_run",
        "command": None,
        "exit_code": None,
        "stdout_path": None,
        "stderr_path": None,
    }


def load_acceptance_artifact(path: Path, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    candidate = path.resolve()
    if not candidate.exists():
        raise ValueError(f"Acceptance artifact not found: {_relative(candidate, repo_root)}")
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(
            f"Acceptance artifact is not valid JSON: {_relative(candidate, repo_root)}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("Acceptance artifact must be a JSON object")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, dict):
        raise ValueError("Acceptance artifact must define a steps object")

    normalized_steps: dict[str, dict[str, Any]] = {}
    for step_id in ACCEPTANCE_STEP_IDS:
        if step_id not in raw_steps:
            raise ValueError(f"Acceptance artifact is missing required step {step_id!r}")
        normalized_steps[step_id] = _normalize_acceptance_step(step_id, raw_steps[step_id])
        normalized_steps[step_id]["step_id"] = step_id

    repo_maturity_step = raw_steps.get("repo_maturity")
    if repo_maturity_step is not None:
        normalized_steps["repo_maturity"] = _normalize_acceptance_step("repo_maturity", repo_maturity_step)
        normalized_steps["repo_maturity"]["step_id"] = "repo_maturity"

    return {
        "acceptance_id": str(payload.get("acceptance_id", "")),
        "profile": str(payload.get("profile", "")),
        "venue": str(payload.get("venue", "")),
        "generated_at_utc": str(payload.get("generated_at_utc", "")),
        "artifact_path": _relative(candidate, repo_root),
        "steps": normalized_steps,
    }


def _submission_blocker_from_manuscript_scope(gate: dict[str, Any]) -> dict[str, Any]:
    summary = (
        f"manuscript scope must be `{gate['required_scope_status']}` "
        f"(current: `{gate['current_scope_status']}`)"
    )
    issues = list(gate.get("issues", []))
    if issues:
        summary = f"{summary}; {issues[0]}"
    return {
        "gate": "manuscript_scope_gate",
        "status": str(gate.get("status", "unknown")),
        "summary": summary,
        "required_status": str(gate.get("required_scope_status", "real")),
        "current_status": str(gate.get("current_scope_status", "unknown")),
        "issues": issues,
    }


def _submission_blocker_from_bibliography(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate": "bibliography_scope_gate",
        "status": str(gate.get("status", "unknown")),
        "summary": (
            "bibliography manuscript scope must be "
            f"`{gate['required_manuscript_scope_status']}` "
            f"(current: `{gate['current_manuscript_scope_status']}`)"
        ),
        "required_status": str(gate.get("required_manuscript_scope_status", "confirmed")),
        "current_status": str(gate.get("current_manuscript_scope_status", "unknown")),
        "note": gate.get("note"),
    }


def _submission_blocker_from_venue(gate: dict[str, Any]) -> dict[str, Any]:
    failed_venues = list(gate.get("failed_venues", []))
    labels = [
        str(item.get("display_name") or item.get("venue") or "unknown")
        for item in failed_venues
    ]
    summary = (
        f"venue verification must be `{gate['required_verification_status']}` "
        f"(failed venues: {', '.join(labels) if labels else 'unknown'})"
    )
    return {
        "gate": "submission_gate",
        "status": str(gate.get("status", "unknown")),
        "summary": summary,
        "required_status": str(gate.get("required_verification_status", "current")),
        "failed_count": int(gate.get("failed_count", 0) or 0),
        "failed_venues": failed_venues,
    }


def _collect_submission_blockers(audit: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if audit["manuscript_scope_gate"]["status"] != "ready":
        blockers.append(_submission_blocker_from_manuscript_scope(audit["manuscript_scope_gate"]))
    if audit["bibliography_scope_gate"]["status"] != "ready":
        blockers.append(_submission_blocker_from_bibliography(audit["bibliography_scope_gate"]))
    if audit["submission_gate"]["status"] != "ready":
        blockers.append(_submission_blocker_from_venue(audit["submission_gate"]))
    return blockers


def _acceptance_step_issue(step_id: str, step: dict[str, Any]) -> str:
    exit_code = step.get("exit_code")
    exit_suffix = f" (exit {exit_code})" if exit_code not in (None, "") else ""
    return f"external validation step `{step_id}` is `{step['status']}`{exit_suffix}"


def _external_validation_evidence(
    acceptance_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    if acceptance_artifact is None:
        return {
            "artifact_path": None,
            "profile": None,
            "venue": None,
            "generated_at_utc": None,
            "steps": {
                step_id: _not_run_acceptance_step(step_id)
                for step_id in ACCEPTANCE_STEP_IDS
            },
        }
    return {
        "artifact_path": acceptance_artifact["artifact_path"],
        "profile": acceptance_artifact["profile"],
        "venue": acceptance_artifact["venue"],
        "generated_at_utc": acceptance_artifact["generated_at_utc"],
        "steps": {
            step_id: dict(acceptance_artifact["steps"][step_id])
            for step_id in ACCEPTANCE_STEP_IDS
        },
    }


def _repo_maturity_warnings(
    *,
    profile: str,
    project_release: dict[str, Any],
    project_handoff: dict[str, Any],
    release_bundle: dict[str, Any],
    reference_report: dict[str, Any],
    manuscript_scope: dict[str, Any],
    acceptance_artifact: dict[str, Any] | None,
) -> list[str]:
    warnings: list[str] = []
    if manuscript_scope["status"] == "provisional":
        warnings.append(
            f"tracked manuscript scope is `{manuscript_scope['scope_status']}` rather than `real`"
        )
    if project_release["readiness"] == "provisional":
        warnings.append(
            f"tracked project release `{project_release['project_id']}` remains provisional by design"
        )
    if project_handoff["readiness"] == "provisional":
        warnings.append(
            f"tracked project handoff `{project_handoff['project_id']}` remains provisional by design"
        )
    if release_bundle["readiness"] == "provisional":
        warnings.append(
            f"release bundle `{release_bundle['profile_id']}` is provisional"
        )
    if reference_report["readiness"] == "provisional":
        warnings.append("reference integrity is provisional")
    if acceptance_artifact is None and profile in {"submission-framework", "submission-ready"}:
        warnings.append(
            "external validation evidence was not provided; strict mode requires an acceptance artifact"
        )
    return sorted(dict.fromkeys(warnings))


def build_repo_maturity_report(
    profile: str,
    *,
    repo_root: Path = REPO_ROOT,
    acceptance_artifact: dict[str, Any] | None = None,
    selected_venues: list[str] | None = None,
) -> dict[str, Any]:
    if profile not in ALLOWED_PROFILES:
        raise ValueError(
            f"Unknown repo maturity profile '{profile}'. Expected one of: {', '.join(sorted(ALLOWED_PROFILES))}"
        )
    if acceptance_artifact is not None and acceptance_artifact["profile"] not in {"", profile}:
        raise ValueError(
            "Acceptance artifact profile does not match requested repo maturity profile"
        )
    if (
        acceptance_artifact is not None
        and selected_venues
        and len(selected_venues) == 1
        and acceptance_artifact["venue"] not in {"", selected_venues[0]}
    ):
        raise ValueError(
            "Acceptance artifact venue does not match the requested repo maturity venue scope"
        )

    manuscript_scope = build_manuscript_scope_status(repo_root)
    pre_submission_audit = build_pre_submission_audit(repo_root=repo_root, selected_venues=selected_venues)
    release_bundle = build_release_bundle(DEFAULT_RELEASE_PROFILE_ID, repo_root=repo_root)
    project_release = build_project_release(DEFAULT_PROJECT_ID, repo_root=repo_root)
    project_handoff = build_project_handoff(DEFAULT_PROJECT_ID, repo_root=repo_root)
    benchmark_matrix = build_harness_benchmark_matrix_report(repo_root=repo_root)
    reference_report = build_reference_report()
    external_validation = _external_validation_evidence(acceptance_artifact)

    blocking_issues: list[str] = []
    deferred_submission_blockers: list[dict[str, Any]] = []

    if manuscript_scope["status"] == "invalid":
        blocking_issues.extend(
            f"manuscript scope metadata: {issue}" for issue in manuscript_scope.get("issues", [])
        )
    if pre_submission_audit["readiness"] == "blocked":
        blocking_issues.append("pre-submission audit is blocked")
    if release_bundle["readiness"] == "blocked":
        blocking_issues.append(f"release bundle `{release_bundle['profile_id']}` is blocked")
    if reference_report["readiness"] == "blocked":
        blocking_issues.append("reference integrity is blocked")
    if benchmark_matrix["readiness"] != "ready":
        blocking_issues.append("agent evaluation benchmark matrix is blocked")
    if project_release["readiness"] == "blocked":
        blocking_issues.append(f"project release `{project_release['project_id']}` is blocked")
    if project_handoff["readiness"] == "blocked":
        blocking_issues.append(f"project handoff `{project_handoff['project_id']}` is blocked")

    submission_blockers = _collect_submission_blockers(pre_submission_audit)
    if profile == "submission-ready":
        blocking_issues.extend(item["summary"] for item in submission_blockers)
    else:
        deferred_submission_blockers = submission_blockers

    acceptance_steps = external_validation["steps"]
    if acceptance_artifact is not None:
        for step_id in ACCEPTANCE_STEP_IDS:
            step = acceptance_steps[step_id]
            if step["status"] != "ready":
                blocking_issues.append(_acceptance_step_issue(step_id, step))

    warnings = _repo_maturity_warnings(
        profile=profile,
        project_release=project_release,
        project_handoff=project_handoff,
        release_bundle=release_bundle,
        reference_report=reference_report,
        manuscript_scope=manuscript_scope,
        acceptance_artifact=acceptance_artifact,
    )

    package_paths = sorted(
        dict.fromkeys(
            [
                manuscript_scope["manifest_path"],
                *pre_submission_audit.get("package_paths", []),
                *release_bundle.get("package_paths", []),
                *project_release.get("package_paths", []),
                *project_handoff.get("package_paths", []),
                *benchmark_matrix.get("package_paths", []),
                *reference_report.get("package_paths", []),
                "scripts/manuscript_scope_common.py",
                "scripts/repo_maturity.py",
                "scripts/check_repo_maturity.py",
                "scripts/run_repo_maturity_acceptance.py",
            ]
        )
    )
    if acceptance_artifact is not None:
        package_paths.append(acceptance_artifact["artifact_path"])
        package_paths = sorted(dict.fromkeys(package_paths))

    report = {
        "profile": profile,
        "readiness": "blocked" if blocking_issues else "ready",
        "blocking_issues": sorted(dict.fromkeys(blocking_issues)),
        "deferred_submission_blockers": deferred_submission_blockers,
        "warnings": warnings,
        "target_venue_ids": pre_submission_audit["venue_scope"]["venue_ids"],
        "evidence": {
            "manuscript_scope": manuscript_scope,
            "pre_submission_audit": {
                "audit_id": pre_submission_audit["audit_id"],
                "readiness": pre_submission_audit["readiness"],
                "manuscript_scope_gate": pre_submission_audit["manuscript_scope_gate"],
                "bibliography_scope_gate": pre_submission_audit["bibliography_scope_gate"],
                "submission_gate": pre_submission_audit["submission_gate"],
            },
            "release_bundle": {
                "profile_id": release_bundle["profile_id"],
                "readiness": release_bundle["readiness"],
            },
            "project_release": {
                "project_id": project_release["project_id"],
                "readiness": project_release["readiness"],
            },
            "project_handoff": {
                "project_id": project_handoff["project_id"],
                "readiness": project_handoff["readiness"],
            },
            "benchmark_matrix": {
                "matrix_id": benchmark_matrix["matrix_id"],
                "readiness": benchmark_matrix["readiness"],
                "overall_score": benchmark_matrix["overall_score"],
            },
            "reference_integrity": {
                "readiness": reference_report["readiness"],
                "bibliography_scope_gate": reference_report["bibliography_scope_gate"],
            },
            "external_validation": external_validation,
        },
        "package_paths": package_paths,
        "repo_root": _relative(repo_root),
    }
    report["strict_requirement_issues"] = build_repo_maturity_strict_requirement_issues(report)
    return report


def build_repo_maturity_manifest(report: dict[str, Any]) -> dict[str, Any]:
    external_steps = report["evidence"]["external_validation"]["steps"]
    return {
        "package_id": f"{_maturity_stem(report['profile'])}_v1",
        "profile": report["profile"],
        "readiness": report["readiness"],
        "blocking_issue_count": len(report["blocking_issues"]),
        "deferred_submission_blocker_count": len(report["deferred_submission_blockers"]),
        "warning_count": len(report["warnings"]),
        "strict_requirement_issue_count": len(report["strict_requirement_issues"]),
        "manuscript_scope_status": report["evidence"]["manuscript_scope"]["status"],
        "manuscript_scope_gate_status": report["evidence"]["pre_submission_audit"]["manuscript_scope_gate"]["status"],
        "bibliography_scope_gate_status": report["evidence"]["pre_submission_audit"]["bibliography_scope_gate"]["status"],
        "submission_gate_status": report["evidence"]["pre_submission_audit"]["submission_gate"]["status"],
        "runtime_support_status": external_steps["runtime_support"]["status"],
        "scaffold_status": external_steps["scaffold"]["status"],
        "python_suite_status": external_steps["python_suite"]["status"],
        "r_figure_suite_status": external_steps["r_figure_suite"]["status"],
        "package_paths": report["package_paths"],
    }


def build_repo_maturity_strict_requirement_issues(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if report["readiness"] != "ready":
        issues.append(f"repo maturity profile `{report['profile']}` is `{report['readiness']}`")
    if report["profile"] in {"submission-framework", "submission-ready"}:
        for step_id, step in report["evidence"]["external_validation"]["steps"].items():
            if step["status"] != "ready":
                issues.append(_acceptance_step_issue(step_id, step))
    return sorted(dict.fromkeys(issues))


def render_repo_maturity_markdown(report: dict[str, Any]) -> str:
    external_steps = report["evidence"]["external_validation"]["steps"]
    lines = [
        "# Repo Maturity",
        "",
        f"- profile: `{report['profile']}`",
        f"- readiness: `{report['readiness']}`",
        f"- blocking_issue_count: `{len(report['blocking_issues'])}`",
        f"- deferred_submission_blocker_count: `{len(report['deferred_submission_blockers'])}`",
        f"- warning_count: `{len(report['warnings'])}`",
        f"- strict_requirement_issue_count: `{len(report['strict_requirement_issues'])}`",
        f"- target_venues: `{', '.join(report['target_venue_ids'])}`",
        f"- acceptance_artifact: `{report['evidence']['external_validation']['artifact_path'] or 'not provided'}`",
        f"- runtime_support: `{external_steps['runtime_support']['status']}`",
        f"- scaffold: `{external_steps['scaffold']['status']}`",
        f"- python_suite: `{external_steps['python_suite']['status']}`",
        f"- r_figure_suite: `{external_steps['r_figure_suite']['status']}`",
        "",
        "## Evidence",
        "",
        f"- manuscript_scope: `{report['evidence']['manuscript_scope']['status']}`",
        f"- pre_submission_audit: `{report['evidence']['pre_submission_audit']['readiness']}`",
        f"- release_bundle: `{report['evidence']['release_bundle']['readiness']}`",
        f"- project_release: `{report['evidence']['project_release']['readiness']}`",
        f"- project_handoff: `{report['evidence']['project_handoff']['readiness']}`",
        f"- benchmark_matrix: `{report['evidence']['benchmark_matrix']['readiness']}`",
        f"- reference_integrity: `{report['evidence']['reference_integrity']['readiness']}`",
        "",
    ]
    if report["blocking_issues"]:
        lines.extend(["## Blocking Issues", ""])
        lines.extend(f"- {issue}" for issue in report["blocking_issues"])
        lines.append("")
    if report["deferred_submission_blockers"]:
        lines.extend(["## Deferred Submission Blockers", ""])
        for item in report["deferred_submission_blockers"]:
            lines.append(f"- `{item['gate']}`: {item['summary']}")
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
        lines.append("")
    if report["strict_requirement_issues"]:
        lines.extend(["## Strict Requirement Issues", ""])
        lines.extend(f"- {issue}" for issue in report["strict_requirement_issues"])
        lines.append("")
    lines.extend(["## Package Paths", ""])
    for path in report["package_paths"]:
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_repo_maturity_outputs(
    profile: str,
    *,
    repo_root: Path = REPO_ROOT,
    report: dict[str, Any] | None = None,
    reports_dir: Path | None = None,
    manifests_dir: Path | None = None,
) -> dict[str, str]:
    report = report or build_repo_maturity_report(profile, repo_root=repo_root)
    reports_dir = reports_dir or REPORTS_DIR
    manifests_dir = manifests_dir or MANIFESTS_DIR
    stem = _maturity_stem(profile)
    report_json_path = reports_dir / f"{stem}.json"
    report_md_path = reports_dir / f"{stem}.md"
    manifest_path = manifests_dir / f"{stem}.json"

    write_text(report_json_path, json.dumps(report, indent=2) + "\n")
    write_text(report_md_path, render_repo_maturity_markdown(report))
    write_text(manifest_path, json.dumps(build_repo_maturity_manifest(report), indent=2) + "\n")

    return {
        "report_json": _relative(report_json_path, repo_root),
        "report_md": _relative(report_md_path, repo_root),
        "manifest": _relative(manifest_path, repo_root),
    }
