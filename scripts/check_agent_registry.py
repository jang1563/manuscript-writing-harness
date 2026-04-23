#!/usr/bin/env python3
"""Validate the tracked agent registry for the multi-agent manuscript system."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_REGISTRY_PATH = REPO_ROOT / "workflows" / "agents" / "agent_registry.json"
REQUIRED_TOP_LEVEL_FIELDS = {
    "system_id",
    "display_name",
    "external_positioning",
    "internal_substrate",
    "orchestration_model",
    "authoritative_truths",
    "agents",
}
REQUIRED_AGENT_FIELDS = {
    "agent_id",
    "display_name",
    "purpose",
    "implementation_status",
    "runtime_mode",
    "entrypoints",
    "consumes",
    "produces",
    "validators",
    "upstream_agents",
    "downstream_agents",
    "authoritative_outputs",
    "public_description",
}
ALLOWED_IMPLEMENTATION_STATUS = {"implemented", "partial", "planned"}
ALLOWED_RUNTIME_MODE = {"deterministic", "hybrid", "planned"}
PATH_FIELDS = ("entrypoints", "consumes", "produces", "validators", "authoritative_outputs")
GENERATED_ARTIFACT_PATTERNS = (
    "figures/output/*",
    "manuscript/_build/*",
    "pathways/results/*",
    "pathways/studies/*/results/*",
    "reports/overnight/*",
    "workflows/release/exports/*",
    "workflows/release/manifests/*",
    "workflows/release/reports/*",
)


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_agent_registry(path: Path = AGENT_REGISTRY_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"agent registry must be a JSON object: {_relative(path)}")
    return payload


def _coerce_string_list(
    value: Any,
    *,
    field: str,
    context: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{context}: {field} must be a list")
        return []
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{context}: {field}[{index}] must be a non-empty string")
            continue
        normalized.append(item.strip())
    return normalized


def _repo_path(path_str: str) -> Path:
    return (REPO_ROOT / path_str).resolve()


def _is_generated_artifact_path(path_str: str) -> bool:
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in GENERATED_ARTIFACT_PATTERNS)


def _validate_repo_path(
    path_str: str,
    *,
    field: str,
    context: str,
    errors: list[str],
    require_existing_file: bool = True,
) -> None:
    candidate = _repo_path(path_str)
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError:
        errors.append(f"{context}: {field} path escapes repo root: {path_str}")
        return
    if not require_existing_file:
        if candidate.exists() and not candidate.is_file():
            errors.append(f"{context}: {field} generated path must point to a file: {path_str}")
        return
    if not candidate.exists():
        errors.append(f"{context}: {field} path does not exist: {path_str}")
        return
    if not candidate.is_file():
        errors.append(f"{context}: {field} path must point to a tracked file: {path_str}")


def _validate_entrypoint_path(path_str: str, *, context: str, errors: list[str]) -> None:
    parts = PurePosixPath(path_str).parts
    suffix = PurePosixPath(path_str).suffix
    is_script = bool(parts) and parts[0] == "scripts" and suffix in {".py", ".R"}
    is_doc = suffix == ".md"
    if not is_script and not is_doc:
        errors.append(f"{context}: entrypoints must point to tracked scripts or docs: {path_str}")


def _validate_validator_path(path_str: str, *, context: str, errors: list[str]) -> None:
    parts = PurePosixPath(path_str).parts
    suffix = PurePosixPath(path_str).suffix
    if not parts or parts[0] != "scripts" or suffix not in {".py", ".R"}:
        errors.append(f"{context}: validators must point to tracked scripts: {path_str}")


def _validate_authoritative_output(
    path_str: str,
    *,
    context: str,
    allowed_paths: set[str],
    errors: list[str],
) -> None:
    pure_path = PurePosixPath(path_str)
    if path_str not in allowed_paths:
        errors.append(
            f"{context}: authoritative_outputs must be drawn from consumes or produces: {path_str}"
        )
    if "reports" in pure_path.parts:
        errors.append(
            f"{context}: authoritative_outputs must avoid derivative report paths when source artifacts exist: {path_str}"
        )
    if pure_path.suffix == ".md":
        errors.append(
            f"{context}: authoritative_outputs should be machine-readable tracked artifacts, not markdown summaries: {path_str}"
        )


def validate_agent_registry(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    missing_top_level = sorted(REQUIRED_TOP_LEVEL_FIELDS - payload.keys())
    if missing_top_level:
        errors.append(f"registry is missing required top-level fields: {missing_top_level}")

    authoritative_truths = _coerce_string_list(
        payload.get("authoritative_truths", []),
        field="authoritative_truths",
        context="registry",
        errors=errors,
    )
    if not authoritative_truths:
        errors.append("registry: authoritative_truths must not be empty")

    raw_agents = payload.get("agents", [])
    if not isinstance(raw_agents, list):
        errors.append("registry: agents must be a list")
        raw_agents = []

    seen_ids: set[str] = set()
    normalized_agents: list[dict[str, Any]] = []
    for index, raw_agent in enumerate(raw_agents):
        context = f"agent[{index}]"
        if not isinstance(raw_agent, dict):
            errors.append(f"{context}: agent entry must be an object")
            continue
        missing_agent_fields = sorted(REQUIRED_AGENT_FIELDS - raw_agent.keys())
        if missing_agent_fields:
            errors.append(f"{context}: missing required fields {missing_agent_fields}")
        agent_id = str(raw_agent.get("agent_id", "")).strip()
        if not agent_id:
            errors.append(f"{context}: agent_id must be a non-empty string")
            continue
        if agent_id in seen_ids:
            errors.append(f"{context}: duplicate agent_id {agent_id!r}")
            continue
        seen_ids.add(agent_id)
        agent_context = f"agent {agent_id}"

        implementation_status = str(raw_agent.get("implementation_status", "")).strip()
        if implementation_status not in ALLOWED_IMPLEMENTATION_STATUS:
            errors.append(
                f"{agent_context}: implementation_status must be one of {sorted(ALLOWED_IMPLEMENTATION_STATUS)}"
            )

        runtime_mode = str(raw_agent.get("runtime_mode", "")).strip()
        if runtime_mode not in ALLOWED_RUNTIME_MODE:
            errors.append(
                f"{agent_context}: runtime_mode must be one of {sorted(ALLOWED_RUNTIME_MODE)}"
            )

        normalized_agent: dict[str, Any] = dict(raw_agent)
        for field in PATH_FIELDS:
            values = _coerce_string_list(raw_agent.get(field, []), field=field, context=agent_context, errors=errors)
            normalized_agent[field] = values
            for value in values:
                require_existing_file = (
                    field in {"entrypoints", "validators"}
                    or not _is_generated_artifact_path(value)
                )
                _validate_repo_path(
                    value,
                    field=field,
                    context=agent_context,
                    errors=errors,
                    require_existing_file=require_existing_file,
                )
                if field == "entrypoints":
                    _validate_entrypoint_path(value, context=agent_context, errors=errors)
                if field == "validators":
                    _validate_validator_path(value, context=agent_context, errors=errors)
            if field in {"entrypoints", "validators"} and not values:
                errors.append(f"{agent_context}: {field} must not be empty")

        for field in ("upstream_agents", "downstream_agents"):
            normalized_agent[field] = _coerce_string_list(
                raw_agent.get(field, []),
                field=field,
                context=agent_context,
                errors=errors,
            )

        if not str(raw_agent.get("display_name", "")).strip():
            errors.append(f"{agent_context}: display_name must be a non-empty string")
        if not str(raw_agent.get("purpose", "")).strip():
            errors.append(f"{agent_context}: purpose must be a non-empty string")
        if not str(raw_agent.get("public_description", "")).strip():
            errors.append(f"{agent_context}: public_description must be a non-empty string")

        allowed_authoritative_paths = set(normalized_agent["consumes"]) | set(normalized_agent["produces"])
        for value in normalized_agent["authoritative_outputs"]:
            _validate_authoritative_output(
                value,
                context=agent_context,
                allowed_paths=allowed_authoritative_paths,
                errors=errors,
            )

        for field in PATH_FIELDS:
            values = normalized_agent[field]
            duplicates = sorted({value for value in values if values.count(value) > 1})
            if duplicates:
                warnings.append(f"{agent_context}: duplicate {field} entries detected: {duplicates}")

        normalized_agents.append(normalized_agent)

    agent_lookup = {
        str(agent["agent_id"]): agent
        for agent in normalized_agents
        if isinstance(agent, dict) and agent.get("agent_id")
    }

    for agent_id, agent in agent_lookup.items():
        for upstream_agent in agent["upstream_agents"]:
            if upstream_agent not in agent_lookup:
                errors.append(f"agent {agent_id}: upstream_agents references unknown id {upstream_agent!r}")
                continue
            if agent_id not in agent_lookup[upstream_agent]["downstream_agents"]:
                errors.append(
                    f"agent {agent_id}: upstream link from {upstream_agent!r} is not mirrored in downstream_agents"
                )
        for downstream_agent in agent["downstream_agents"]:
            if downstream_agent not in agent_lookup:
                errors.append(f"agent {agent_id}: downstream_agents references unknown id {downstream_agent!r}")
                continue
            if agent_id not in agent_lookup[downstream_agent]["upstream_agents"]:
                errors.append(
                    f"agent {agent_id}: downstream link to {downstream_agent!r} is not mirrored in upstream_agents"
                )

    return {
        "registry_path": _relative(AGENT_REGISTRY_PATH),
        "status": "ready" if not errors else "blocked",
        "agent_count": len(agent_lookup),
        "agent_ids": sorted(agent_lookup),
        "errors": sorted(dict.fromkeys(errors)),
        "warnings": sorted(dict.fromkeys(warnings)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of plain text.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = load_agent_registry()
        report = validate_agent_registry(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        if args.json:
            print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Registry: {report['registry_path']}")
        print(f"Status: {report['status']}")
        print(f"Agents: {report['agent_count']}")
        if report["errors"]:
            print("Errors:")
            for item in report["errors"]:
                print(f"- {item}")
        if report["warnings"]:
            print("Warnings:")
            for item in report["warnings"]:
                print(f"- {item}")

    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
