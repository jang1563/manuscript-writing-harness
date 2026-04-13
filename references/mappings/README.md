# Claim Reference Mappings

This directory stores tracked claim-to-reference linkage scaffolds.

Primary artifacts:

- `claim_reference_map.json`
- `claim_reference_map.md`

Recommended workflow:

- regenerate the current scaffold with `python3 scripts/build_claim_reference_map.py`
- replace placeholder or empty `accepted_reference_ids` with real bibliography keys from `references/library.bib`
- apply the approved mappings with `python3 scripts/apply_claim_reference_map.py`
- rerun `python3 scripts/check_reference_integrity.py --write --sync-graph`
