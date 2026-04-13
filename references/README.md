# References

This directory contains the citation authority files and auxiliary metadata.

## Recommended Workflow

- Manage references in Zotero
- Export automatically to `library.bib` using Better BibTeX
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
├── metadata/       DOI enrichment, PMID mappings, dedup logs
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
```

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
