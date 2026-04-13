# Repo Blueprint And Roadmap

Reviewed: 2026-04-09

## Objective

Turn the best-practice research notes into a staged implementation plan for this repository.

## Recommended Repo Shape

```text
.
├── research/
├── manuscript/
│   ├── sections/
│   ├── frontmatter/
│   ├── legends/
│   ├── supplementary/
│   └── templates/
├── references/
│   ├── library.bib
│   ├── csl/
│   └── metadata/
├── figures/
│   ├── src/
│   ├── config/
│   ├── data/
│   ├── output/
│   └── source_data/
├── tables/
│   ├── src/
│   ├── schemas/
│   ├── data/
│   └── output/
├── review/
│   ├── protocol/
│   ├── queries/
│   ├── retrieval/
│   ├── screening/
│   ├── extraction/
│   ├── bias/
│   └── prisma/
├── workflows/
│   ├── venue_configs/
│   ├── checklists/
│   └── release/
├── scripts/
├── env/
└── .github/
    └── workflows/
```

## Phase Plan

### Phase 0. Research Freeze

Deliverables:

- research notes committed
- decision on primary authoring engine
- decision on Python-only versus Python-plus-R figure/table stack

Exit criteria:

- team agrees on substrate and scope

### Phase 1. Core Scaffold

Deliverables:

- manuscript skeleton
- reference authority files
- venue config skeletons
- build entry points

Exit criteria:

- a tiny sample manuscript builds end to end

### Phase 2. Figures And Tables

Deliverables:

- canonical figure and table directory structure
- one example multi-panel figure pipeline
- one example main table pipeline
- source-data export convention

Exit criteria:

- figures and tables can be rebuilt in CI

### Phase 3. Journal Overlays

Deliverables:

- `nature` overlay
- `cell` overlay
- `science` overlay
- generic `conference` overlay

Exit criteria:

- one sample manuscript renders under at least two overlays

### Phase 4. Review Workflow

Deliverables:

- protocol template
- query files
- dedup logs
- screening schema
- PRISMA count generation
- risk-of-bias visualization pipeline

Exit criteria:

- a synthetic review project can move from query to PRISMA-ready logs

### Phase 5. CI And Release Hardening

Deliverables:

- build matrix in GitHub Actions
- preview artifacts
- release bundle generation
- archival DOI integration

Exit criteria:

- pull requests show previews and releases produce archival packages

## Strategic Recommendation

Build the harness in this order:

1. `MyST-first manuscript core`
2. `Zotero + Better BibTeX`
3. `figure and table build system`
4. `Nature and Cell overlays`
5. `systematic review module`
6. `Science and conference overlays`
7. `release and DOI archiving`

Why this order:

- it gets the semantic substrate right first
- it reduces rework in references and figure organization
- it handles the most structurally demanding journal families early

## Early Risks

- choosing too many authoring systems at once
- mixing manual and scripted figure workflows
- letting Word or spreadsheet edits become authoritative
- over-automating systematic review judgments without enough human controls
- hard-coding a single journal’s exact layout into the manuscript source

## Success Definition

The harness is successful when:

- a serious manuscript can be authored, reviewed, and reformatted without rewriting
- figures and tables are build artifacts
- citations are authoritative and linted
- a systematic review can be audited end to end
- a tagged GitHub release can produce a submission package and archival snapshot

## Sources

- index note: ./README.md
- authoring note: ./01_authoring_and_journal_overlays.md
- figure note: ./02_figures.md
- table note: ./03_tables.md
- reference note: ./04_references_and_identifiers.md
- review note: ./05_systematic_review_and_meta_analysis.md
- model note: ./06_literature_intelligence_models.md
- ops note: ./07_github_ci_release_ops.md
