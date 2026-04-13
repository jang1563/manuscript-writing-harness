#!/usr/bin/env python3
"""Check manuscript section prose draft readiness and optionally regenerate outputs."""

from __future__ import annotations

import argparse
import json
import sys

from manuscript_section_prose import build_section_prose, write_section_prose_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate section-prose outputs before checking.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless section prose is fully ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    writes = write_section_prose_outputs() if args.write else {}
    prose = build_section_prose()

    if args.json:
        print(json.dumps({"prose": prose, "writes": writes}, indent=2))
    else:
        print("# Section Prose Coverage")
        print()
        print(f"- overall_status: `{prose['overall_status']}`")
        print(f"- section_count: `{prose['section_count']}`")
        if writes:
            print()
            print("Generated outputs:")
            print(f"- `{writes['section_prose']}`")
            print(f"- `{writes['section_prose_markdown']}`")
            print(f"- `{writes['section_directory']}`")

    if args.strict:
        return 0 if prose["overall_status"] == "ready" else 1
    return 0 if prose["overall_status"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
