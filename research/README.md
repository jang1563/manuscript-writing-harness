# Multi-Agent Manuscript System Research Index

Reviewed: 2026-04-09

## Goal

Design a research-first multi-agent manuscript system, built on a deterministic harness substrate, that can support:

- high-end primary manuscripts
- review and systematic review workflows
- figure and table production
- reference management
- journal-specific submission packaging
- reproducible GitHub-based collaboration

The quality target is:

- Cell
- Nature
- Science
- top conferences where strict submission formatting and artifact traceability matter

## Recommended Backbone

Current recommendation:

- semantic authoring in `MyST Markdown`
- journal-specific export via `jtex` / MyST templates
- optional computational companion notebooks in `Quarto` or Jupyter
- reference authority in `Zotero` with `Better BibTeX`
- figures in Python and/or R from source data only
- tables generated from code, never maintained manually in Word/Excel as the manuscript source of truth
- systematic review workflow anchored in `PRISMA 2020`, `PROSPERO`, `Cochrane`, and `ASReview`
- CI/CD on GitHub Actions with artifact publication and release archiving

Why this backbone:

- MyST is the strongest fit for a journal-agnostic semantic manuscript source with a large template ecosystem and explicit scientific publishing intent.
- Quarto remains excellent for computational notebooks and exploratory analysis, but the manuscript system should not depend on a notebook-first authoring model for final papers.
- Manubot remains valuable for citation-heavy or continuously updated review articles, but is less attractive as the one universal substrate for multiple journal overlays.

## Research Notes

- [01_authoring_and_journal_overlays.md](./01_authoring_and_journal_overlays.md)
- [02_figures.md](./02_figures.md)
- [03_tables.md](./03_tables.md)
- [04_references_and_identifiers.md](./04_references_and_identifiers.md)
- [05_systematic_review_and_meta_analysis.md](./05_systematic_review_and_meta_analysis.md)
- [06_literature_intelligence_models.md](./06_literature_intelligence_models.md)
- [07_github_ci_release_ops.md](./07_github_ci_release_ops.md)
- [08_repo_blueprint_and_roadmap.md](./08_repo_blueprint_and_roadmap.md)
- [09_scientific_figure_generation_harness_deep_dive.md](./09_scientific_figure_generation_harness_deep_dive.md)
- [10_public_bioinformatics_agents_for_figure_generation.md](./10_public_bioinformatics_agents_for_figure_generation.md)
- [11_paperorchestra_review.md](./11_paperorchestra_review.md)
- [12_ai_ml_professional_figure_track.md](./12_ai_ml_professional_figure_track.md)
- [13_agent_system_positioning.md](./13_agent_system_positioning.md)

## Working Principles

- Keep one semantic source of truth for the manuscript.
- Treat every figure and table as a build artifact.
- Treat every citation as metadata-backed, not handwritten.
- Keep literature harvesting and screening logs versioned.
- Separate journal-independent scientific content from journal-specific formatting.
- Make every important output rebuildable in CI.
- Store research decisions in markdown so the repo itself captures rationale, not just implementation.

## Immediate Build Order

1. Create the repository scaffold and choose the primary authoring engine.
2. Add citation authority and manuscript metadata schemas.
3. Add figure and table pipelines with source-data exports.
4. Add journal overlay builds for `nature`, `cell`, `science`, and `conference`.
5. Add systematic review modules and evidence-tracking tables.
6. Add CI, preview artifacts, release snapshots, and archival DOI wiring.
