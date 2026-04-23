# References

This directory contains the citation authority files and auxiliary metadata.

## Recommended Workflow

- Manage references in Zotero
- Export automatically to `library.bib` using Better BibTeX
- Track the expected Better BibTeX auto-export settings in `metadata/bibliography_source.yml`
- Never hand-edit `library.bib` except for emergency repair with a tracked follow-up back to Zotero
- Keep suggested literature candidates separate from accepted bibliography authority in `metadata/suggested_reference_candidates.json`
- Keep claim-to-reference linkage scaffolds in `mappings/claim_reference_map.json` until real bibliography keys are approved

## Directory Structure

```
references/
├── library.bib     Main bibliography (exported from Zotero)
├── csl/            Venue-specific citation styles
│   ├── nature.csl
│   ├── cell.csl
│   └── science.csl
├── metadata/       DOI enrichment, source manifest, PMID mappings, dedup logs
└── mappings/       claim-to-reference linkage scaffolds
```

## CLI Usage

Integrity and graph operations are available through the repo scripts:

```bash
# Synchronize manuscript claim nodes into the citation graph
python3 scripts/build_citation_graph.py

# Write bibliography and citation-graph audit outputs
python3 scripts/check_reference_integrity.py --write --sync-graph

# Generate claim-to-reference mapping scaffolds
python3 scripts/build_claim_reference_map.py

# Apply approved claim-to-reference mappings into the citation graph
python3 scripts/apply_claim_reference_map.py

# Fail unless the reference layer is fully ready
python3 scripts/check_reference_integrity.py --write --sync-graph --strict

# Validate the tracked Better BibTeX source manifest plus bibliography health
python3 scripts/references_cli.py validate

# Fail unless the bibliography export has been confirmed for the real manuscript
python3 scripts/check_reference_integrity.py --json --require-confirmed-manuscript-bibliography
```

## Better BibTeX Auto-Export Wiring

The repo-side contract for Zotero export lives in `references/metadata/bibliography_source.yml`.

Use it as the checklist for Zotero setup:

1. Install the Better BibTeX Zotero plugin.
2. Create or choose the Zotero collection that represents accepted manuscript references.
3. Configure Better BibTeX auto-export for that collection in `Keep updated` mode.
4. Point the export target at `references/library.bib`.
5. Keep `references/metadata/bibliography_source.yml` aligned with the actual Zotero export settings.
6. After replacing the starter bibliography with the accepted manuscript export, confirm the tracked manuscript scope:

```bash
python3 scripts/confirm_bibliography_scope.py \
  --note "Confirmed against the accepted manuscript Zotero Better BibTeX export." \
  --dry-run \
  --json
```

`python3 scripts/references_cli.py status` and `python3 scripts/references_cli.py validate` now surface whether the tracked source manifest still matches the expected repo output, and whether the current export has been confirmed as the real manuscript bibliography.

## What The Integrity Audit Checks

- Duplicate citation keys and duplicate DOI-backed entries
- Citation-graph references missing from `library.bib`
- Placeholder bibliography entries
- Article-like entries without DOI or PMID
- Bibliography entries not linked from the manuscript citation graph
- Claim nodes without citation edges
- Claim-to-reference mapping scaffold coverage

## CSL Styles

Three venue-specific CSL styles are included:

| Style | Citation Format | Venue |
|-------|----------------|-------|
| nature | Numeric superscript | Nature family journals |
| cell | Author-date | Cell Press journals |
| science | Numeric parenthetical | AAAS Science family |

These are referenced by the venue overlay system in `workflows/venue_configs/`.

## Testing

```bash
python -m pytest tests/references/ -v
```
