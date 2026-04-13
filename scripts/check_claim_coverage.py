#!/usr/bin/env python3
"""Check manuscript claim-packet coverage and optionally regenerate outputs."""

from __future__ import annotations

import argparse
import json
import sys

from manuscript_claims import build_claim_coverage, build_claim_packets, render_results_claim_packets_markdown, write_claim_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate claim packet outputs before checking.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless coverage is fully ready.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown-like summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    writes = write_claim_outputs() if args.write else {}
    packets = build_claim_packets()
    coverage = build_claim_coverage(packets)

    if args.json:
        print(json.dumps({"coverage": coverage, "writes": writes}, indent=2))
    else:
        print("# Claim Coverage")
        print()
        print(f"- overall_status: `{coverage['overall_status']}`")
        print(f"- claim_count: `{coverage['claim_count']}`")
        print(f"- ready_claim_count: `{coverage['ready_claim_count']}`")
        print(f"- provisional_claim_count: `{coverage['provisional_claim_count']}`")
        print(f"- blocked_claim_count: `{coverage['blocked_claim_count']}`")
        if coverage["provisional_claim_ids"]:
            print(f"- provisional_claim_ids: `{', '.join(coverage['provisional_claim_ids'])}`")
        if coverage["blocked_claim_ids"]:
            print(f"- blocked_claim_ids: `{', '.join(coverage['blocked_claim_ids'])}`")
        if writes:
            print()
            print("Generated outputs:")
            print(f"- `{writes['claim_packets']}`")
            print(f"- `{writes['claim_coverage']}`")
            print(f"- `{writes['draft_markdown']}`")

    if args.strict:
        return 0 if coverage["overall_status"] == "ready" else 1
    return 0 if coverage["overall_status"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
