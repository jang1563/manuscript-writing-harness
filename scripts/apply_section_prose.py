#!/usr/bin/env python3
"""Apply generated section prose into managed blocks in manuscript sections."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from manuscript_section_prose import write_section_prose_outputs


REPO_ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT_ROOT = REPO_ROOT / "manuscript"
SECTIONS_ROOT = MANUSCRIPT_ROOT / "sections"
START_MARKER = "<!-- GENERATED_PROSE_BLOCK_START -->"
END_MARKER = "<!-- GENERATED_PROSE_BLOCK_END -->"
SECTION_MAP = {
    "summary": "01_summary.md",
    "introduction": "02_introduction.md",
    "discussion": "04_discussion.md",
    "methods": "05_methods.md",
}


def _include_block(section_id: str) -> str:
    return (
        f"{START_MARKER}\n\n"
        f"```{{include}} ../drafts/section_bodies/{section_id}.md\n"
        f"```\n\n"
        f"{END_MARKER}"
    )


def _apply_one(section_id: str, relative_path: str) -> str:
    path = SECTIONS_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    block = _include_block(section_id)
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(block, text, count=1)
    else:
        lines = text.splitlines()
        if not lines:
            raise ValueError(f"{relative_path} is empty and cannot receive a managed prose block")
        updated = "\n".join([lines[0], "", block, "", *lines[1:]]).rstrip() + "\n"
    path.write_text(updated, encoding="utf-8")
    return str(path.relative_to(REPO_ROOT))


def apply_section_prose() -> dict[str, object]:
    writes = write_section_prose_outputs()
    updated = [
        _apply_one(section_id, relative_path)
        for section_id, relative_path in SECTION_MAP.items()
    ]
    return {"writes": writes, "updated_sections": updated}


def main() -> int:
    payload = apply_section_prose()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
