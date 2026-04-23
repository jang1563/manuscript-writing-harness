# Draft Packets

This directory stores generated drafting aids that connect manuscript claims to display items, fact sheets, legends, and citation coverage.

Before regenerating these artifacts for a real manuscript, add topic and claim notes to
`manuscript/plans/author_content_inputs.json`.

Current primary artifact:

- `results_claim_packets.md`
- `section_briefs.md`
- `section_drafts.md`
- `section_prose.md`
- `sections/`
- `section_bodies/`

Regenerate with:

`python3 scripts/build_claim_packets.py`
`python3 scripts/build_section_briefs.py`
`python3 scripts/build_section_drafts.py`
`python3 scripts/build_section_prose.py`
`python3 scripts/apply_section_prose.py`
