#!/usr/bin/env python3
"""Build anonymized/blinded-review preview outputs for a project."""

from __future__ import annotations

import argparse
import json

from anonymized_release import build_anonymized_release, render_anonymized_release_markdown, write_anonymized_release_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_anonymized_release(args.project)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_anonymized_release_outputs(args.project)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_anonymized_release_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
