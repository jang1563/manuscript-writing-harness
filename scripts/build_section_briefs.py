#!/usr/bin/env python3
"""Generate manuscript section-brief drafting artifacts."""

from __future__ import annotations

import json
import sys

from manuscript_section_briefs import write_section_brief_outputs


def main() -> int:
    payload = write_section_brief_outputs()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
