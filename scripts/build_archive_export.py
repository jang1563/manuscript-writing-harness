#!/usr/bin/env python3
"""Build an archive-ready export bundle from a release profile."""

from __future__ import annotations

import argparse
import json

from archive_export import build_archive_export, render_archive_markdown, write_archive_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="integrated_demo_release", help="Release profile id to archive.")
    parser.add_argument("--write", action="store_true", help="Write archive report, manifest, and checksums.")
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_archive_export(args.profile)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_archive_outputs(args.profile)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_archive_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
