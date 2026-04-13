#!/usr/bin/env python3
"""Build a top-level release bundle report and manifest."""

from __future__ import annotations

import argparse
import json

from release_bundle import build_release_bundle, render_release_markdown, write_release_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="integrated_demo_release", help="Release profile id to build.")
    parser.add_argument("--write", action="store_true", help="Write release report and manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_release_bundle(args.profile)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_release_outputs(args.profile)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_release_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
