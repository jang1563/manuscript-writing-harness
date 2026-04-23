#!/usr/bin/env python3
"""Mark a venue config as currently verified for real submission use."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

import yaml

from figures_common import REPO_ROOT
from venue_overlay import DEFAULT_STALE_AFTER_DAYS, VENUE_CONFIG_DIR


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _normalize_verified_on(value: str | None) -> str:
    verified_on = value or date.today().isoformat()
    parsed = date.fromisoformat(verified_on)
    if parsed > date.today():
        raise ValueError("verified_on must not be in the future")
    return parsed.isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def confirm_venue_verification(
    venue_id: str,
    *,
    source_summary: str,
    verified_on: str | None = None,
    stale_after_days: int | None = None,
    dry_run: bool = False,
    config_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Update a venue config so its verification state becomes current."""

    config_root = config_dir or VENUE_CONFIG_DIR
    resolved_repo_root = repo_root or REPO_ROOT
    config_path = config_root / f"{venue_id}.yml"
    if not config_path.exists():
        raise ValueError(f"Unknown venue {venue_id!r}")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid venue config for {venue_id!r}")

    verified_on_value = _normalize_verified_on(verified_on)
    if stale_after_days is None:
        existing = payload.get("verification", {}).get("stale_after_days")
        stale_after_days = existing if isinstance(existing, int) and existing >= 0 else DEFAULT_STALE_AFTER_DAYS
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")
    summary = source_summary.strip()
    if not summary:
        raise ValueError("source_summary must not be blank")

    verification_before = payload.get("verification", {})
    if not isinstance(verification_before, dict):
        verification_before = {}
    verification_after = dict(verification_before)
    verification_after.update(
        {
            "last_verified": verified_on_value,
            "stale_after_days": int(stale_after_days),
            "final_confirmation_required": False,
            "source_summary": summary,
        }
    )
    payload["verification"] = verification_after

    rendered = yaml.safe_dump(payload, sort_keys=False)
    if not dry_run:
        config_path.write_text(rendered, encoding="utf-8")

    return {
        "venue": venue_id,
        "config_path": _relative(config_path, resolved_repo_root),
        "dry_run": dry_run,
        "updated": not dry_run,
        "verification_before": _json_safe(verification_before),
        "verification_after": _json_safe(verification_after),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", required=True, help="Venue id to mark as currently verified.")
    parser.add_argument(
        "--source-summary",
        required=True,
        help="Short note describing what current venue-year source was checked.",
    )
    parser.add_argument("--date", dest="verified_on", help="Verification date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument(
        "--stale-after-days",
        type=int,
        help="Override the verification freshness window in days. Defaults to the current config value.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview the updated verification block without writing the config.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a plain-text summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = confirm_venue_verification(
        args.venue,
        source_summary=args.source_summary,
        verified_on=args.verified_on,
        stale_after_days=args.stale_after_days,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        action = "Previewed" if payload["dry_run"] else "Updated"
        print(f"{action} venue verification for `{payload['venue']}`")
        print(f"- config: `{payload['config_path']}`")
        print(f"- last_verified: `{payload['verification_after']['last_verified']}`")
        print(f"- stale_after_days: `{payload['verification_after']['stale_after_days']}`")
        print(
            "- final_confirmation_required: "
            f"`{payload['verification_after']['final_confirmation_required']}`"
        )
        print(f"- source_summary: {payload['verification_after']['source_summary']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
