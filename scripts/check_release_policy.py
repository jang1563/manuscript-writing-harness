#!/usr/bin/env python3
"""Check anonymization and data-sharing policy readiness for a project."""

from __future__ import annotations

import argparse
import json

from release_policy import build_release_policy, render_release_policy_markdown, write_release_policy_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_release_policy(args.project)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_release_policy_outputs(args.project)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_release_policy_markdown(report))
    if args.strict and report["readiness"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
