#!/usr/bin/env python3
"""Generate manuscript section draft scaffolds."""

from __future__ import annotations

import json
import sys

from manuscript_section_drafts import write_section_draft_outputs


def main() -> int:
    payload = write_section_draft_outputs()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
