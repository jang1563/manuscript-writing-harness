#!/usr/bin/env python3
"""Scaffold a real-project release profile plus an MSigDB-backed study profile."""

from __future__ import annotations

import argparse
import json

from project_release import scaffold_project_release


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--venue-id", default="nature")
    parser.add_argument("--species", choices=["human", "mouse"], default="human")
    parser.add_argument("--collection", default="H")
    parser.add_argument("--version")
    parser.add_argument("--identifier-type", default="gene_symbol")
    parser.add_argument("--study-id")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = scaffold_project_release(
        args.project_id,
        title=args.title,
        venue_id=args.venue_id,
        species=args.species,
        collection=args.collection,
        version=args.version,
        identifier_type=args.identifier_type,
        study_id=args.study_id,
        overwrite=args.overwrite,
    )
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Scaffolded project release: {payload['project_root']}")
        print(f"Release profile: {payload['release_profile_id']}")
        print("Next steps:")
        for step in payload["next_steps"]:
            print(f"- {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
