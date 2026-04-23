#!/usr/bin/env python3
"""Mark the tracked bibliography export as confirmed for the real manuscript."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from bibliography_common import BIBLIOGRAPHY_SOURCE_MANIFEST, load_bibliography_source


def _normalize_confirmed_on(value: str | None) -> str:
    confirmed_on = value or date.today().isoformat()
    parsed = date.fromisoformat(confirmed_on)
    if parsed > date.today():
        raise ValueError("confirmed_on must not be in the future")
    return parsed.isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def confirm_bibliography_scope(
    *,
    note: str,
    confirmed_on: str | None = None,
    dry_run: bool = False,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    resolved_manifest_path = manifest_path or BIBLIOGRAPHY_SOURCE_MANIFEST
    payload = load_bibliography_source(resolved_manifest_path)
    confirmed_on_value = _normalize_confirmed_on(confirmed_on)
    normalized_note = note.strip()
    if not normalized_note:
        raise ValueError("note must not be blank")

    manuscript_scope_before = payload.get("manuscript_scope", {})
    if not isinstance(manuscript_scope_before, dict):
        manuscript_scope_before = {}

    manuscript_scope_after = dict(manuscript_scope_before)
    manuscript_scope_after.update(
        {
            "confirmed": True,
            "note": normalized_note,
            "confirmed_on": confirmed_on_value,
        }
    )
    payload["manuscript_scope"] = manuscript_scope_after

    rendered = yaml.safe_dump(payload, sort_keys=False)
    if not dry_run:
        resolved_manifest_path.write_text(rendered, encoding="utf-8")

    return {
        "manifest_path": str(resolved_manifest_path),
        "dry_run": dry_run,
        "updated": not dry_run,
        "manuscript_scope_before": _json_safe(manuscript_scope_before),
        "manuscript_scope_after": _json_safe(manuscript_scope_after),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--note",
        required=True,
        help="Short note describing why the current Better BibTeX export matches the target manuscript bibliography.",
    )
    parser.add_argument(
        "--date",
        dest="confirmed_on",
        help="Confirmation date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview the updated manuscript-scope block without writing.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a plain-text summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = confirm_bibliography_scope(
        note=args.note,
        confirmed_on=args.confirmed_on,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        action = "Previewed" if payload["dry_run"] else "Updated"
        scope = payload["manuscript_scope_after"]
        print(f"{action} bibliography manuscript scope")
        print(f"- manifest: `{payload['manifest_path']}`")
        print(f"- confirmed: `{scope['confirmed']}`")
        print(f"- confirmed_on: `{scope['confirmed_on']}`")
        print(f"- note: {scope['note']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
