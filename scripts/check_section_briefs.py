#!/usr/bin/env python3
"""Check manuscript section-brief readiness and optionally regenerate outputs."""

from __future__ import annotations

import argparse
import json
import sys

from manuscript_section_briefs import build_section_briefs, write_section_brief_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate section-brief outputs before checking.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless section briefs are fully ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    writes = write_section_brief_outputs() if args.write else {}
    briefs = build_section_briefs()

    if args.json:
        print(json.dumps({"briefs": briefs, "writes": writes}, indent=2))
    else:
        print("# Section Brief Coverage")
        print()
        print(f"- overall_status: `{briefs['overall_status']}`")
        print(f"- section_count: `{briefs['section_count']}`")
        print(f"- ready_section_count: `{briefs['ready_section_count']}`")
        print(f"- provisional_section_count: `{briefs['provisional_section_count']}`")
        print(f"- blocked_section_count: `{briefs['blocked_section_count']}`")
        if writes:
            print()
            print("Generated outputs:")
            print(f"- `{writes['section_briefs']}`")
            print(f"- `{writes['section_briefs_markdown']}`")

    if args.strict:
        return 0 if briefs["overall_status"] == "ready" else 1
    return 0 if briefs["overall_status"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
