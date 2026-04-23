#!/usr/bin/env python3
"""Check venue readiness and optionally write submission-package manifests."""

from __future__ import annotations

import argparse
import json
import sys

try:  # pragma: no cover - import path differs between script and package use.
    from .venue_overlay import (
        VENUE_CONFIG_DIR,
        build_submission_gate,
        evaluate_venue,
        render_readiness_markdown,
        write_venue_outputs,
    )
except ImportError:  # pragma: no cover
    from venue_overlay import (
        VENUE_CONFIG_DIR,
        build_submission_gate,
        evaluate_venue,
        render_readiness_markdown,
        write_venue_outputs,
    )


def _available_venues() -> list[str]:
    return sorted(path.stem for path in VENUE_CONFIG_DIR.glob("*.yml"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--venue", help="Check one venue by id.")
    group.add_argument("--all", action="store_true", help="Check all venue configs.")
    parser.add_argument("--write", action="store_true", help="Write readiness reports and package manifests.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any venue is not ready.")
    parser.add_argument(
        "--require-current-verification",
        action="store_true",
        help="Exit non-zero unless every checked venue has current verification metadata for real submission use.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown summaries.")
    return parser.parse_args()


def _emit_error(message: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message}, indent=2))
    else:
        print(f"Error: {message}", file=sys.stderr)
    return 2


def main() -> int:
    args = parse_args()
    try:
        venues = _available_venues() if args.all else [str(args.venue)]
        reports = [evaluate_venue(venue_id) for venue_id in venues]
        submission_gate = build_submission_gate(reports)

        if args.write:
            writes = {venue_id: write_venue_outputs(venue_id) for venue_id in venues}
        else:
            writes = {}
    except ValueError as exc:
        return _emit_error(str(exc), as_json=args.json)

    if args.json:
        payload = {"venues": reports, "submission_gate": submission_gate, "writes": writes}
        print(json.dumps(payload, indent=2))
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            print(render_readiness_markdown(report), end="")
            if writes:
                paths = writes[report["venue"]]
                print("Generated outputs:")
                print(f"- `{paths['report_md']}`")
                print(f"- `{paths['report_json']}`")
                print(f"- `{paths['manifest']}`")
        if args.require_current_verification:
            print()
            print("Submission gate:")
            print(f"- status: `{submission_gate['status']}`")
            print(f"- required_verification_status: `{submission_gate['required_verification_status']}`")
            for item in submission_gate["failed_venues"]:
                print(
                    "- "
                    f"`{item['display_name']}` (`{item['venue']}`): "
                    f"`{item['verification_status']}`"
                )

    if args.strict and any(report["readiness"] != "ready" for report in reports):
        return 1
    if args.require_current_verification and submission_gate["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
