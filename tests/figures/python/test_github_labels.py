from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from contextlib import redirect_stdout


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import github_labels
import sync_github_labels


def test_load_label_manifest_validates_duplicates(tmp_path: Path) -> None:
    manifest = tmp_path / "labels.yml"
    manifest.write_text(
        """
- name: bug
  color: d73a4a
  description: Broken
- name: bug
  color: d73a4a
  description: Duplicate
""".strip()
        + "\n",
        encoding="utf-8",
    )

    try:
        github_labels.load_label_manifest(manifest)
    except ValueError as exc:
        assert "Duplicate label name" in str(exc)
    else:
        raise AssertionError("Expected duplicate label names to raise ValueError")


def test_sync_labels_plans_create_update_and_delete(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "labels.yml"
    manifest.write_text(
        """
- name: bug
  color: d73a4a
  description: Something is broken
- name: documentation
  color: 0075ca
  description: Docs updates
""".strip()
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        github_labels,
        "list_remote_labels",
        lambda repo=None: [
            {"name": "bug", "color": "cccccc", "description": "Old"},
            {"name": "legacy", "color": "ffffff", "description": "Old label"},
        ],
    )

    executed: list[list[str]] = []
    monkeypatch.setattr(
        github_labels,
        "_run_gh",
        lambda args: executed.append(args) or type("Completed", (), {"stdout": "[]"})(),
    )

    payload = github_labels.sync_labels(
        repo="jang1563/manuscript-writing-harness",
        manifest_path=manifest,
        dry_run=False,
        prune=True,
    )

    assert payload["created"] == ["documentation"]
    assert payload["updated"] == ["bug"]
    assert payload["deleted"] == ["legacy"]
    assert ["gh", "label", "edit", "bug", "--color", "d73a4a", "--description", "Something is broken", "--repo", "jang1563/manuscript-writing-harness"] in executed
    assert ["gh", "label", "create", "documentation", "--color", "0075ca", "--description", "Docs updates", "--repo", "jang1563/manuscript-writing-harness"] in executed
    assert ["gh", "label", "delete", "legacy", "--yes", "--repo", "jang1563/manuscript-writing-harness"] in executed


def test_sync_github_labels_cli_json(monkeypatch) -> None:
    monkeypatch.setattr(
        sync_github_labels,
        "sync_labels",
        lambda repo=None, dry_run=False, prune=False: {
            "repo": repo,
            "manifest_path": ".github/labels.yml",
            "dry_run": dry_run,
            "prune": prune,
            "desired_count": 4,
            "remote_count": 4,
            "created": [],
            "updated": ["documentation"],
            "deleted": [],
            "unchanged": ["bug", "enhancement", "licensing"],
            "operations": [{"action": "update", "name": "documentation"}],
        },
    )

    monkeypatch.setattr(sys, "argv", ["sync_github_labels.py", "--dry-run", "--json"])
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert sync_github_labels.main() == 0
    payload = json.loads(stdout.getvalue())
    assert payload["dry_run"] is True
    assert payload["updated"] == ["documentation"]


def test_has_pending_label_changes() -> None:
    assert github_labels.has_pending_label_changes({"operations": [{"action": "update", "name": "bug"}]}) is True
    assert github_labels.has_pending_label_changes({"operations": []}) is False
    assert github_labels.has_pending_label_changes({}) is False


def test_sync_github_labels_cli_strict_returns_nonzero_on_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        sync_github_labels,
        "sync_labels",
        lambda repo=None, dry_run=False, prune=False: {
            "repo": repo,
            "manifest_path": ".github/labels.yml",
            "dry_run": dry_run,
            "prune": prune,
            "desired_count": 4,
            "remote_count": 4,
            "created": [],
            "updated": ["documentation"],
            "deleted": [],
            "unchanged": ["bug", "enhancement", "licensing"],
            "operations": [{"action": "update", "name": "documentation"}],
        },
    )

    monkeypatch.setattr(sys, "argv", ["sync_github_labels.py", "--dry-run", "--strict"])
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert sync_github_labels.main() == 1
    output = stdout.getvalue()
    assert "Planned operations:" in output
    assert "- update: documentation" in output


def test_sync_github_labels_cli_strict_returns_zero_without_drift(monkeypatch) -> None:
    monkeypatch.setattr(
        sync_github_labels,
        "sync_labels",
        lambda repo=None, dry_run=False, prune=False: {
            "repo": repo,
            "manifest_path": ".github/labels.yml",
            "dry_run": dry_run,
            "prune": prune,
            "desired_count": 4,
            "remote_count": 4,
            "created": [],
            "updated": [],
            "deleted": [],
            "unchanged": ["bug", "enhancement", "documentation", "licensing"],
            "operations": [],
        },
    )

    monkeypatch.setattr(sys, "argv", ["sync_github_labels.py", "--dry-run", "--strict"])
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        assert sync_github_labels.main() == 0
