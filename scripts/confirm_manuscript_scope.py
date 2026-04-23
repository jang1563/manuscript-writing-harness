#!/usr/bin/env python3
"""Mark the tracked manuscript scope as confirmed for real submission use."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

from figures_common import REPO_ROOT, write_text
from manuscript_scope_common import MANUSCRIPT_SCOPE_PATH


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _normalize_confirmed_on(value: str | None) -> str:
    confirmed_on = value or date.today().isoformat()
    parsed = date.fromisoformat(confirmed_on)
    if parsed > date.today():
        raise ValueError("confirmed_on must not be in the future")
    return parsed.isoformat()


def _load_scope_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Missing manuscript scope metadata: {_relative(path)}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manuscript scope metadata must be a JSON object")
    return payload


def confirm_manuscript_scope(
    *,
    note: str,
    confirmed_on: str | None = None,
    dry_run: bool = False,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    resolved_manifest_path = manifest_path or MANUSCRIPT_SCOPE_PATH
    payload = _load_scope_payload(resolved_manifest_path)
    confirmed_on_value = _normalize_confirmed_on(confirmed_on)
    normalized_note = note.strip()
    if not normalized_note:
        raise ValueError("note must not be blank")

    manuscript_scope_before = {
        "scope_status": payload.get("scope_status"),
        "confirmed_on": payload.get("confirmed_on"),
        "note": payload.get("note"),
    }
    manuscript_scope_after = {
        "scope_status": "real",
        "confirmed_on": confirmed_on_value,
        "note": normalized_note,
    }
    payload.update(manuscript_scope_after)

    rendered = json.dumps(payload, indent=2) + "\n"
    if not dry_run:
        write_text(resolved_manifest_path, rendered)

    return {
        "manifest_path": _relative(resolved_manifest_path),
        "dry_run": dry_run,
        "updated": not dry_run,
        "manuscript_scope_before": manuscript_scope_before,
        "manuscript_scope_after": manuscript_scope_after,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--note",
        required=True,
        help="Short note describing why the tracked manuscript now represents the real submission package.",
    )
    parser.add_argument(
        "--date",
        dest="confirmed_on",
        help="Confirmation date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview the updated manuscript scope without writing.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a plain-text summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = confirm_manuscript_scope(
        note=args.note,
        confirmed_on=args.confirmed_on,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        action = "Previewed" if payload["dry_run"] else "Updated"
        scope = payload["manuscript_scope_after"]
        print(f"{action} manuscript scope")
        print(f"- manifest: `{payload['manifest_path']}`")
        print(f"- scope_status: `{scope['scope_status']}`")
        print(f"- confirmed_on: `{scope['confirmed_on']}`")
        print(f"- note: {scope['note']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
