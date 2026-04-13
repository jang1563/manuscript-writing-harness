#!/usr/bin/env python3
"""Build deterministic tar/zip exports from a release profile."""

from __future__ import annotations

import argparse
import json

from export_bundle import build_export_bundle, render_export_markdown, write_export_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="integrated_demo_release", help="Release profile id to export.")
    parser.add_argument("--write", action="store_true", help="Write tar/zip exports plus export metadata.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_export_bundle(args.profile)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_export_outputs(args.profile)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_export_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
