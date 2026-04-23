#!/usr/bin/env python3
"""Check project-level release readiness and optionally write outputs."""

from __future__ import annotations

import argparse
import json

from project_release import build_project_release, render_project_release_markdown, write_project_release_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project release scaffold id to check.")
    parser.add_argument("--write", action="store_true", help="Write project readiness report files.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless project readiness is ready.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_project_release(args.project)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_project_release_outputs(args.project)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_project_release_markdown(report))
    if args.strict and report["readiness"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
