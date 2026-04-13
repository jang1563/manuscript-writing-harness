#!/usr/bin/env python3
"""Apply the tracked claim-to-reference map into the citation graph."""

from __future__ import annotations

import json
import sys

from reference_mapping import apply_claim_reference_map


def main() -> int:
    payload = apply_claim_reference_map(sync_graph=True)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
