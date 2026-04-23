#!/usr/bin/env python3
"""Sync tracked GitHub labels with the live repository."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = REPO_ROOT / ".github" / "labels.yml"


def load_label_manifest(path: Path = LABELS_PATH) -> list[dict[str, str]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of labels in {path}")

    labels: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Each label entry in {path} must be a mapping")
        name = str(item.get("name", "")).strip()
        color = str(item.get("color", "")).strip().lower()
        description = str(item.get("description", "")).strip()
        if not name:
            raise ValueError(f"Label entry in {path} is missing a name")
        if not color or len(color) != 6:
            raise ValueError(f"Label {name!r} in {path} must use a 6-character hex color")
        if name in seen_names:
            raise ValueError(f"Duplicate label name {name!r} in {path}")
        seen_names.add(name)
        labels.append({"name": name, "color": color, "description": description})
    return labels


def _run_gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, capture_output=True, text=True)


def list_remote_labels(repo: str | None = None) -> list[dict[str, str]]:
    command = ["gh", "label", "list", "--limit", "1000", "--json", "name,color,description"]
    if repo:
        command.extend(["--repo", repo])
    completed = _run_gh(command)
    payload = json.loads(completed.stdout)
    labels: list[dict[str, str]] = []
    for item in payload:
        labels.append(
            {
                "name": str(item.get("name", "")).strip(),
                "color": str(item.get("color", "")).strip().lower(),
                "description": str(item.get("description", "")).strip(),
            }
        )
    return labels


def sync_labels(
    repo: str | None = None,
    manifest_path: Path = LABELS_PATH,
    dry_run: bool = False,
    prune: bool = False,
) -> dict[str, Any]:
    desired_labels = load_label_manifest(manifest_path)
    remote_labels = list_remote_labels(repo=repo)
    remote_by_name = {label["name"]: label for label in remote_labels}
    desired_by_name = {label["name"]: label for label in desired_labels}

    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []
    deleted: list[str] = []
    operations: list[dict[str, str]] = []

    for label in desired_labels:
        name = label["name"]
        current = remote_by_name.get(name)
        if current is None:
            operations.append({"action": "create", "name": name})
            created.append(name)
            if not dry_run:
                command = ["gh", "label", "create", name, "--color", label["color"], "--description", label["description"]]
                if repo:
                    command.extend(["--repo", repo])
                _run_gh(command)
            continue

        if current["color"] != label["color"] or current["description"] != label["description"]:
            operations.append({"action": "update", "name": name})
            updated.append(name)
            if not dry_run:
                command = ["gh", "label", "edit", name, "--color", label["color"], "--description", label["description"]]
                if repo:
                    command.extend(["--repo", repo])
                _run_gh(command)
        else:
            unchanged.append(name)

    if prune:
        for name in sorted(remote_by_name):
            if name in desired_by_name:
                continue
            operations.append({"action": "delete", "name": name})
            deleted.append(name)
            if not dry_run:
                command = ["gh", "label", "delete", name, "--yes"]
                if repo:
                    command.extend(["--repo", repo])
                _run_gh(command)

    try:
        manifest_display_path = str(manifest_path.relative_to(REPO_ROOT))
    except ValueError:
        manifest_display_path = str(manifest_path)

    return {
        "repo": repo,
        "manifest_path": manifest_display_path,
        "dry_run": dry_run,
        "prune": prune,
        "desired_count": len(desired_labels),
        "remote_count": len(remote_labels),
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
        "operations": operations,
    }


def has_pending_label_changes(payload: Mapping[str, Any]) -> bool:
    """Return True when a label sync payload indicates drift."""

    operations = payload.get("operations")
    return isinstance(operations, list) and bool(operations)
