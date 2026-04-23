#!/usr/bin/env python3
"""Build a project-level release readiness report."""

from __future__ import annotations

import argparse
import json

from project_release import build_project_release, render_project_release_markdown, write_project_release_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project release scaffold id to build.")
    parser.add_argument("--write", action="store_true", help="Write project readiness report files.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
