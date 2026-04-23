# Venue Configs

These files define per-venue requirement stubs and lightweight overlay baselines.

They are intentionally lightweight in Phase 1, but they are not free-form notes:

- required sections must resolve against `manuscript/content_registry.json`
- required special assets must resolve against `manuscript/content_registry.json`
- verification metadata records when each baseline was last checked and whether final submission-time confirmation is still required
- planned items are allowed at this stage, but they are surfaced as validation warnings

This keeps venue planning aligned with the manuscript model before full overlay generation exists.

The current tracked profiles include:

- `nature`, `cell`, and `science` for journal-family submission baselines
- `conference` as a generic fallback when a target venue is not yet specialized
- `acm_sigconf`, `ieee_vis`, `neurips`, and `icml` as conference-oriented baselines that should still be revalidated against the exact current CFP or author instructions

The current overlay checker can be run with:

`python3 scripts/check_venue_readiness.py --all --write --strict`

To turn venue verification into a real submission gate, use:

`python3 scripts/check_venue_readiness.py --all --json --strict --require-current-verification`

For a single target venue instead of the whole tracked catalog, use:

`python3 scripts/check_venue_readiness.py --venue neurips --json --strict --require-current-verification`

After a human confirms the exact venue-year rules, update the tracked config with:

`python3 scripts/confirm_venue_verification.py --venue neurips --source-summary "Confirmed against the NeurIPS 2026 CFP" --dry-run --json`

This writes readiness reports under `workflows/release/reports/` and submission-package manifests under `workflows/release/manifests/`.
