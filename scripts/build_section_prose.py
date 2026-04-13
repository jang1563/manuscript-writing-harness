#!/usr/bin/env python3
"""Generate manuscript section prose drafts."""

from __future__ import annotations

import json
import sys

from manuscript_section_prose import write_section_prose_outputs


def main() -> int:
    payload = write_section_prose_outputs()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
