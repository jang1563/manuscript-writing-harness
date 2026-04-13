#!/usr/bin/env python3
"""Check deposit-metadata readiness for a release profile."""

from __future__ import annotations

import argparse
import json

from deposit_metadata import build_deposit_metadata, render_deposit_markdown, write_deposit_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="integrated_demo_release", help="Release profile id.")
    parser.add_argument("--write", action="store_true", help="Write deposit metadata outputs.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless readiness is ready.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_deposit_metadata(args.profile)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_deposit_outputs(args.profile)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_deposit_markdown(report))
    if args.strict and report["readiness"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
