#!/usr/bin/env python3
"""Check manuscript section-draft scaffold readiness and optionally regenerate outputs."""

from __future__ import annotations

import argparse
import json
import sys

from manuscript_section_drafts import build_section_drafts, write_section_draft_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate section-draft outputs before checking.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless section drafts are fully ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    writes = write_section_draft_outputs() if args.write else {}
    drafts = build_section_drafts()

    if args.json:
        print(json.dumps({"drafts": drafts, "writes": writes}, indent=2))
    else:
        print("# Section Draft Coverage")
        print()
        print(f"- overall_status: `{drafts['overall_status']}`")
        print(f"- section_count: `{drafts['section_count']}`")
        print(f"- ready_section_count: `{drafts['ready_section_count']}`")
        print(f"- provisional_section_count: `{drafts['provisional_section_count']}`")
        print(f"- blocked_section_count: `{drafts['blocked_section_count']}`")
        if writes:
            print()
            print("Generated outputs:")
            print(f"- `{writes['section_drafts']}`")
            print(f"- `{writes['section_drafts_markdown']}`")

    if args.strict:
        return 0 if drafts["overall_status"] == "ready" else 1
    return 0 if drafts["overall_status"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
