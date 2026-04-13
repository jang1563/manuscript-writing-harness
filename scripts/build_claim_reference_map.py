#!/usr/bin/env python3
"""Generate claim-to-reference mapping scaffolds."""

from __future__ import annotations

import json
import sys

from reference_mapping import write_claim_reference_map


def main() -> int:
    payload = write_claim_reference_map(sync_graph=True)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
