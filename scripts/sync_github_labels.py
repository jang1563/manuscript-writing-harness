#!/usr/bin/env python3
"""Sync .github/labels.yml with the live GitHub repository labels."""

from __future__ import annotations

import argparse
import json
import sys

from github_labels import has_pending_label_changes, sync_labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", help="Target repository in owner/name form. Defaults to the current gh repo context.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned label changes without editing GitHub.")
    parser.add_argument("--prune", action="store_true", help="Delete remote labels that are not present in .github/labels.yml.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when the live repository labels differ from .github/labels.yml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = sync_labels(repo=args.repo, dry_run=args.dry_run, prune=args.prune)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        target = payload["repo"] or "current gh repository"
        mode = "dry-run" if payload["dry_run"] else "applied"
        print(f"GitHub label sync {mode} for {target}")
        print(f"- manifest: `{payload['manifest_path']}`")
        print(f"- created: {len(payload['created'])}")
        print(f"- updated: {len(payload['updated'])}")
        print(f"- deleted: {len(payload['deleted'])}")
        print(f"- unchanged: {len(payload['unchanged'])}")
        if payload["operations"]:
            print("Planned operations:" if payload["dry_run"] else "Applied operations:")
            for operation in payload["operations"]:
                print(f"- {operation['action']}: {operation['name']}")
    if args.strict and has_pending_label_changes(payload):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
