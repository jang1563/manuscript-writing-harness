# GitHub, CI, Release, And Reproducibility Operations

Reviewed: 2026-04-09

## Objective

Make the manuscript harness behave like a serious research software project:

- reproducible builds
- previewable artifacts
- clear review workflows
- archival release snapshots

## Quality Bar

The repo should:

- build manuscripts automatically
- test figures and tables automatically
- surface preview artifacts on every pull request
- archive release outputs with stable identifiers

## Recommended Operational Model

### 1. GitHub as the collaboration spine

Use GitHub for:

- pull-request review
- issue-based work planning
- artifact previews
- release tagging

### 2. GitHub Actions for build automation

Core workflows should cover:

- manuscript build
- figure build
- table build
- reference lint
- systematic-review artifact build
- venue matrix builds

### 3. Pages or artifact previews for review

Publish:

- HTML manuscript previews
- figure galleries
- supplementary preview indexes

This sharply reduces the friction of scientific review inside the team.

### 4. Archival releases

At milestone releases:

- build final manuscript packages
- archive them with a DOI through Zenodo integration
- preserve source data, supplementary outputs, and environment metadata

## Environment Strategy

Because this harness will likely mix Python, R, and publisher tooling, use a split but explicit environment model:

- Python dependencies managed with `uv` or `conda`-compatible lockfiles
- R dependencies managed with `renv`
- manuscript build tools version-pinned in project config or CI

For a strongly cross-language bioinformatics stack, a `conda-lock` or `pixi`-style base environment may be preferable if system libraries become difficult.

## CI Checks To Add

- unresolved citations
- missing required venue sections
- figure existence and source-data pairing
- table schema checks
- broken internal cross-references
- stale generated artifacts
- non-reproducible environment drift where feasible

## Release Artifacts

Each release should be able to emit:

- `PDF`
- `HTML`
- optional `DOCX`
- figure archive
- table archive
- supplementary materials bundle
- source-data bundle
- machine-readable citation export

## Review And Governance Best Practices

- require PR review before merging manuscript-critical changes
- separate prose edits from pipeline edits when possible
- tag issues by manuscript component
- keep submission checklists in version control

## Acceptance Criteria

- a pull request can produce a reviewable manuscript preview
- a tagged release can produce an archival submission package
- CI catches missing references, missing figures, and missing venue sections
- the repo records enough metadata to reproduce a build later

## Sources

- GitHub Pages docs: https://docs.github.com/articles/creating-project-pages-using-the-command-line
- GitHub Actions docs: https://docs.github.com/actions
- Zenodo GitHub integration documentation record: https://zenodo.org/records/14917262
- Manubot rootstock as workflow inspiration: https://github.com/manubot/rootstock
- Quarto CLI repo: https://github.com/quarto-dev/quarto-cli

