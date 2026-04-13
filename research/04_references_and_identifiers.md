# Reference Management And Scholarly Identifiers

Reviewed: 2026-04-09

## Objective

Build a citation workflow that is authoritative, metadata-backed, stable across manuscript revisions, and compatible with multiple journal styles.

## Quality Bar

Top-tier reference workflows should provide:

- stable citation keys
- DOI or PMID-backed metadata wherever possible
- no manual bibliography editing in the manuscript source
- venue-switchable citation styles
- auditability for preprints, datasets, software, and web resources

## Recommended Stack

Primary authority:

- `Zotero` group library

Primary export bridge:

- `Better BibTeX for Zotero`

Metadata enrichment:

- `Crossref REST API`
- `Europe PMC`
- `PubMed E-utilities`
- optional `OpenAlex` for graph and author disambiguation support

Style layer:

- `CSL`

Identity layer:

- `ORCID` for authors
- `CRediT` contributor roles in manuscript metadata

## Recommended Workflow

### 1. Use Zotero as the canonical bibliography store

Why:

- best overall researcher ergonomics
- strong attachment and note handling
- mature ecosystem
- group-library support

### 2. Use Better BibTeX auto-export

Why:

- stable citation keys
- automatic `.bib` export
- reduced merge conflicts compared with manual bibliography editing

Best-practice rule:

- the `.bib` file is generated from Zotero, not edited by hand

### 3. Enrich incomplete records automatically

Add scripts that:

- fill missing DOI, PMID, PMCID, or publisher metadata where possible
- flag low-confidence or incomplete entries
- normalize page ranges, issue numbers, and preprint metadata

### 4. Support non-paper objects

The harness should cite:

- datasets
- software
- protocols
- preprints
- web resources when necessary

This matters for modern reproducibility expectations.

### 5. Add citation linting in CI

Detect:

- uncited references
- unresolved citation keys
- duplicate entries
- missing DOI or PMID where expected
- malformed URLs
- unapproved web-only sources in formal manuscripts

## Best-Practice Rules

- never invent metadata from memory
- prefer DOI-backed records
- keep preprints clearly labeled
- separate “background notes” from “citable references”
- require ORCID and contributor-role metadata for authorship records

## Journal Overlay Implications

- CSL styles should be switchable by venue
- reference ordering mode should be part of the overlay
- software and data citations should not be tacked on manually at the last minute

## Acceptance Criteria

- the manuscript can rebuild its bibliography entirely from exported authority files
- citation keys remain stable across revisions
- a new venue style can be applied without re-editing citations
- CI flags citation integrity issues before submission

## Sources

- Better BibTeX repo: https://github.com/retorquere/zotero-better-bibtex
- Zotero styles repository: https://www.zotero.org/styles
- Crossref REST API docs: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- Europe PMC REST API: https://europepmc.org/RestfulWebService
- NCBI E-utilities book: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- ORCID guidance: https://support.orcid.org/hc/en-us/articles/360006971573-Building-your-ORCID-record-and-connecting-your-iD
- CRediT taxonomy: https://credit.niso.org/

