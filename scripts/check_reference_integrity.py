#!/usr/bin/env python3
"""Check bibliography integrity and citation-graph consistency."""

from __future__ import annotations

import argparse
import json
import sys

from reference_integrity import build_reference_report, render_reference_markdown, write_reference_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write markdown/json audit outputs and manifest.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless readiness is fully ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--sync-graph", action="store_true", help="Synchronize manuscript/plans/citation_graph.json claim nodes from display items.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_reference_report(sync_graph=args.sync_graph)

    if args.write:
        writes = write_reference_outputs(sync_graph=args.sync_graph)
    else:
        writes = {}

    if args.json:
        print(json.dumps({"report": report, "writes": writes}, indent=2))
    else:
        print(render_reference_markdown(report), end="")
        if writes:
            print("Generated outputs:")
            print(f"- `{writes['report_md']}`")
            print(f"- `{writes['report_json']}`")
            print(f"- `{writes['manifest']}`")

    if args.strict:
        return 0 if report["readiness"] == "ready" else 1
    return 0 if report["readiness"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
