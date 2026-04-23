#!/usr/bin/env python3
"""Check cross-cutting pre-submission readiness and optionally write outputs."""

from __future__ import annotations

import argparse
import json
import sys

from pre_submission_audit import (
    build_pre_submission_audit,
    render_pre_submission_markdown,
    write_pre_submission_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venue", help="Restrict the audit and submission gate to a single venue id.")
    parser.add_argument("--write", action="store_true", help="Write markdown/json audit outputs and manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the audit is fully ready.")
    parser.add_argument(
        "--require-current-venue-verification",
        action="store_true",
        help="Exit non-zero unless venue verification is current enough for real submission gating.",
    )
    parser.add_argument(
        "--require-confirmed-manuscript-bibliography",
        action="store_true",
        help="Exit non-zero unless the tracked bibliography export is confirmed for the real manuscript.",
    )
    return parser.parse_args()


def _emit_error(message: str, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message}, indent=2))
    else:
        print(f"Error: {message}", file=sys.stderr)
    return 2


def main() -> int:
    args = parse_args()
    selected_venues = [args.venue] if args.venue else None
    try:
        report = build_pre_submission_audit(selected_venues=selected_venues)
    except ValueError as exc:
        return _emit_error(str(exc), as_json=args.json)
    payload: dict[str, object] = {"report": report}

    if args.write:
        try:
            payload["writes"] = write_pre_submission_outputs(selected_venues=selected_venues)
        except ValueError as exc:
            return _emit_error(str(exc), as_json=args.json)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_pre_submission_markdown(report), end="")
        if args.write:
            writes = payload["writes"]
            assert isinstance(writes, dict)
            print("Generated outputs:")
            print(f"- `{writes['report_md']}`")
            print(f"- `{writes['report_json']}`")
            print(f"- `{writes['manifest']}`")
        if args.require_confirmed_manuscript_bibliography:
            print()
            print("Bibliography scope gate:")
            print(f"- status: `{report['bibliography_scope_gate']['status']}`")
            print(
                "- required_manuscript_scope_status: "
                f"`{report['bibliography_scope_gate']['required_manuscript_scope_status']}`"
            )
            print(
                "- current_manuscript_scope_status: "
                f"`{report['bibliography_scope_gate']['current_manuscript_scope_status']}`"
            )

    if args.strict and report["readiness"] != "ready":
        return 1
    if args.require_current_venue_verification and report["submission_gate"]["status"] != "ready":
        return 1
    if args.require_confirmed_manuscript_bibliography and report["bibliography_scope_gate"]["status"] != "ready":
        return 1
    return 0 if report["readiness"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
