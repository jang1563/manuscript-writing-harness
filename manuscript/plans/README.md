# Manuscript Plans

This directory stores planning artifacts that sit between research outputs and final manuscript prose.

Recommended artifacts:

- `outline.json`
- `display_item_map.json`
- `citation_graph.json`
- `research_graph.json`
- `writing_plan.json`
- `revision_checks.json`
- `author_content_inputs.json`
- `manuscript_scope.json`

These files are meant to make planning explicit before drafting or refinement.

`author_content_inputs.json` is the tracked place for real manuscript topic notes,
section notes, and claim-level writing guidance keyed to existing `claim_id` values.

`manuscript_scope.json` is the tracked source of truth for whether the repo currently
represents exemplar/demo content, a mixed transition state, or a confirmed real manuscript.
Use `python3 scripts/confirm_manuscript_scope.py --note "..." --dry-run --json` to
preview or apply the final promotion to confirmed `real` scope once the tracked manuscript
content is no longer exemplar-only.
