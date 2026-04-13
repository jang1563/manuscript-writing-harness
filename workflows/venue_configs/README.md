# Venue Configs

These files define per-venue requirement stubs.

They are intentionally lightweight in Phase 1, but they are not free-form notes:

- required sections must resolve against `manuscript/content_registry.json`
- required special assets must resolve against `manuscript/content_registry.json`
- planned items are allowed at this stage, but they are surfaced as validation warnings

This keeps venue planning aligned with the manuscript model before full overlay generation exists.

The current overlay checker can be run with:

`python3 scripts/check_venue_readiness.py --all --write --strict`

This writes readiness reports under `workflows/release/reports/` and submission-package manifests under `workflows/release/manifests/`.
