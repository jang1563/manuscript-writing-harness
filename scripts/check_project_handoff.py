#!/usr/bin/env python3
"""Check top-level project handoff readiness."""

from __future__ import annotations

import argparse
import json

from project_handoff import build_project_handoff, render_project_handoff_markdown, write_project_handoff_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_project_handoff(args.project)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_project_handoff_outputs(args.project)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_project_handoff_markdown(report))
    if args.strict and report["readiness"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
