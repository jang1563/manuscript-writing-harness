#!/usr/bin/env python3
"""Generate manuscript claim packets and drafting markdown."""

from __future__ import annotations

import json
import sys

from manuscript_claims import write_claim_outputs


def main() -> int:
    payload = write_claim_outputs()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
