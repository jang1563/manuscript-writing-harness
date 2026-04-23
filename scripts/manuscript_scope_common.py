#!/usr/bin/env python3
"""Shared helpers for tracked manuscript-scope metadata."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import path differs between script and package use.
    from .figures_common import REPO_ROOT
except ImportError:  # pragma: no cover
    from figures_common import REPO_ROOT


MANUSCRIPT_SCOPE_PATH = REPO_ROOT / "manuscript" / "plans" / "manuscript_scope.json"
ALLOWED_SCOPE_STATUSES = {"exemplar", "mixed", "real"}


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_manuscript_scope_payload(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    path = repo_root / "manuscript" / "plans" / "manuscript_scope.json"
    if not path.exists():
        raise ValueError(f"Missing manuscript scope metadata: {_relative(path, repo_root)}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manuscript scope metadata must be a JSON object: {_relative(path, repo_root)}")
    return payload


def build_manuscript_scope_status(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    path = repo_root / "manuscript" / "plans" / "manuscript_scope.json"
    payload = load_manuscript_scope_payload(repo_root)

    issues: list[str] = []
    warnings: list[str] = []

    scope_status = str(payload.get("scope_status", "")).strip()
    if scope_status not in ALLOWED_SCOPE_STATUSES:
        issues.append(
            "`scope_status` must be one of exemplar, mixed, or real"
        )

    note = str(payload.get("note", "")).strip()
    if not note:
        issues.append("`note` is required")

    confirmed_on_raw = payload.get("confirmed_on")
    confirmed_on_text = ""
    if confirmed_on_raw is not None:
        confirmed_on_text = str(confirmed_on_raw).strip()

    confirmed_on: str | None = None
    if confirmed_on_text:
        try:
            parsed = date.fromisoformat(confirmed_on_text)
        except ValueError:
            issues.append("`confirmed_on` must use YYYY-MM-DD format")
        else:
            if parsed > date.today():
                issues.append("`confirmed_on` must not be in the future")
            else:
                confirmed_on = confirmed_on_text
    elif scope_status == "real":
        issues.append("`confirmed_on` is required when `scope_status` is `real`")

    if scope_status == "mixed":
        warnings.append(
            "manuscript scope is mixed; some tracked manuscript content still depends on exemplar/demo inputs"
        )
    elif scope_status == "exemplar":
        warnings.append(
            "manuscript scope is exemplar; the tracked manuscript still reflects demo/exemplar content"
        )

    status = "ready"
    if issues:
        status = "invalid"
    elif scope_status != "real":
        status = "provisional"

    return {
        "status": status,
        "scope_status": scope_status,
        "confirmed_on": confirmed_on,
        "note": note,
        "issues": issues,
        "warnings": warnings,
        "manifest_path": _relative(path, repo_root),
    }


def build_manuscript_scope_gate(scope_status: dict[str, Any]) -> dict[str, Any]:
    current_scope_status = str(scope_status.get("scope_status", "unknown"))
    return {
        "status": "ready" if scope_status.get("status") == "ready" and current_scope_status == "real" else "blocked",
        "required_scope_status": "real",
        "current_scope_status": current_scope_status,
        "confirmed_on": scope_status.get("confirmed_on"),
        "note": scope_status.get("note"),
        "issues": list(scope_status.get("issues", [])),
        "warnings": list(scope_status.get("warnings", [])),
        "manifest_path": scope_status.get("manifest_path"),
    }
