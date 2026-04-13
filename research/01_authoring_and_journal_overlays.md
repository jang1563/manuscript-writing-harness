# Authoring And Journal Overlays

Reviewed: 2026-04-09

## Objective

Pick an authoring substrate that preserves scientific semantics and can be exported cleanly into multiple journal formats without rewriting the manuscript for every venue.

## Best-Practice Standard

The core manuscript source should:

- keep citations, figures, tables, equations, supplementary items, and metadata semantic
- support cross-references and numbered float handling
- separate authoring from publisher layout details
- make journal switching an overlay problem, not a rewrite problem
- support reproducible build pipelines in CI

## Strong Candidates

### 1. MyST Markdown plus jtex templates

Why it is strong:

- MyST is built around scientific and technical authoring rather than only notebook publishing.
- `jtex` is explicitly designed to render LaTeX journal templates from Jinja-style templates.
- the MyST ecosystem exposes a large template catalog through the `myst-templates` organization and template registry
- MyST handles figures, subfigures, citations, equations, cross-references, and structured metadata well

Risks:

- fewer lab groups use it today than plain LaTeX or Word, so onboarding is real work
- some niche journals may still require a small amount of custom template work

Recommendation:

- make this the primary authoring substrate for the harness

### 2. Quarto

Why it is strong:

- excellent notebook integration
- mature support for citations, tables, figures, and cross-references
- especially strong where computation and manuscript live side by side

Risks:

- it is better than most options for analysis-driven authoring, but less directly journal-template-centric than MyST plus jtex
- it can encourage notebook-first manuscript structure even when a paper needs tighter semantic control

Recommendation:

- keep Quarto as a companion workflow for exploratory analysis or computational appendices

### 3. Manubot

Why it is strong:

- very strong identifier-native citation workflow
- excellent for living reviews, collaborative review papers, and literature-dense writing
- GitHub-native authoring and automation model remains compelling

Risks:

- journal overlay flexibility is weaker than a MyST-first strategy
- less natural fit for complex venue packaging with multiple display-item conventions

Recommendation:

- consider as an optional secondary path for living review projects, not as the harness default

## Decision

Recommended default:

- `MyST-first`

Fallbacks:

- `Quarto-first` for analysis-heavy teams already standardized on Quarto
- `Manubot-first` only for citation-dense living review projects

## Journal Overlay Strategy

Do not encode journal formatting directly into the manuscript text.

Instead:

- keep one venue-agnostic manuscript source
- define per-journal output overlays
- store venue-specific front matter, float naming, required sections, and supplementary packaging in separate config/templates

## Overlay Requirements

### Nature overlay

The overlay should support:

- Nature-style title, abstract, main text, methods, references, acknowledgements, author contributions, competing interests, and correspondence fields
- `Data availability`
- `Code availability`
- `Reporting Summary`
- `Source Data`
- `Extended Data` figures and tables
- production figure checks and high-resolution export paths

Best-practice implication:

- design the repo so source data and extended data are first-class outputs, not afterthoughts

### Cell overlay

The overlay should support:

- manuscript body
- `STAR Methods`
- `Key Resources Table`
- `Lead Contact`
- `Materials Availability`
- `Data and Code Availability`
- `Highlights`
- `Graphical Abstract`
- main figures plus supplemental figures

Best-practice implication:

- Cell-ready projects need structured metadata earlier than most labs expect
- the harness should store resource identifiers, antibodies, software, datasets, and accession numbers in machine-readable tables

### Science overlay

The overlay should support:

- concise article structure
- acknowledgements, funding, author contributions, competing interests
- a `Data and materials availability` section
- supplementary materials bundle generation

Important note:

- the exact Science-family author guidance should be verified against the target journal at submission time
- the overlay should therefore be driven by a venue config file, not hard-coded assumptions

This is an inference from current published-article structure and AAAS ecosystem practice, not a complete substitute for target-journal validation.

### Conference overlay

The overlay should support:

- ACM `acmart`
- IEEE-style conference templates
- later additions for specific venues such as NeurIPS, ICML, ICLR, ISMB, RECOMB, or domain-specific bioinformatics venues

Best-practice implication:

- top-conference support should be treated as separate overlays with dedicated linting for page limits, anonymization, and supplementary artifact policy

## Best-Practice Build Plan

1. Create a venue-agnostic manuscript schema.
2. Define manuscript metadata in YAML or TOML.
3. Separate content files from venue overlays.
4. Add a build matrix that renders the manuscript under multiple overlays.
5. Add overlay-specific lint rules for required sections and asset packaging.
6. Keep a human-readable checklist for each venue.

## Acceptance Criteria

- one manuscript source can render to at least two venues without content rewriting
- references, figure numbering, and supplementary numbering remain stable across builds
- venue-required sections can be checked automatically
- the repo can emit an internal-review version and a submission-ready package

## Sources

- MyST `jtex`: https://mystmd.org/jtex
- MyST figure and scientific authoring guides: https://mystmd.org/guide/figures
- MyST GitHub repo: https://github.com/jupyter-book/mystmd
- MyST templates org: https://github.com/myst-templates/templates
- Quarto authoring docs: https://quarto.org/docs/authoring/tables.html
- Quarto cross-reference docs: https://quarto.org/docs/authoring/cross-references-custom.html
- Manubot rootstock: https://github.com/manubot/rootstock
- Nature formatting guide: https://www.nature.com/nature/for-authors/formatting-guide
- Nature data availability guidance: https://www.nature.com/documents/nr-data-availability-statements-data-citations.pdf
- Cell Press STAR Methods update: https://crosstalk.cell.com/blog/a-star-upgrade
- ACM `acmart` template landing page: https://www.acm.org/publications/proceedings-template
- CTAN `acmart` class: https://ctan.org/pkg/acmart

