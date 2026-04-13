# Manuscript Writing Harness

A research-first, reproducible manuscript harness for:

- primary research papers
- reviews and systematic reviews
- figure and table generation
- reference management
- journal-specific submission packaging
- collaborative GitHub-based scientific writing

The current default architecture is:

- `MyST Markdown` for semantic manuscript authoring
- `Zotero + Better BibTeX` for reference authority
- script-generated figures and tables
- `PRISMA`, `PROSPERO`, `Cochrane`, and `ASReview` for review workflows
- `GitHub Actions` for builds, previews, and release packaging
- `python3 scripts/figures_cli.py` as the canonical figure-library interface
- `env/runtime_support.yml` plus CI matrix workflows for Python/R compatibility
- style-track preparation for both bulk-omics and AI/ML professional figures

## Repo Layout

- `research/`: research notes and architectural rationale
- `manuscript/`: MyST manuscript project and section files
- `manuscript/plans/`: planning artifacts linking claims, display items, and revision checks
- `references/`: bibliography, CSL styles, and metadata helpers
- `figures/`: figure source, configs, outputs, and source-data exports
- `tables/`: table source, schemas, and outputs
- `review/`: protocol, search, screening, extraction, bias, and PRISMA artifacts
- `pathways/`: optional pathway-analysis configs, inputs, and fgsea-oriented enrichment pipeline artifacts
- `workflows/`: venue configs, checklists, and release metadata
- `scripts/`: repo automation and lint helpers
- `env/`: environment definitions and install notes

## Current Phase

This repository is now in `Phase 3: Figure, Venue, And Review Systems`.

What exists:

- research notes for the overall system design
- a MyST-first manuscript skeleton
- a planning layer for outline, display-item mapping, citation graph, and revision checks
- venue configuration stubs for `nature`, `cell`, `science`, and `conference`
- a shared manuscript content registry used to sanity-check venue requirements
- a shared figure contract with Python and R renderers
- a class-based figure library with a registry-driven CLI
- a tracked figure-bundle engine that groups coherent figure sets above class and recipe layers
- a venue-overlay layer that converts venue configs plus the manuscript content registry into readiness reports and submission-package manifests
- a review-evidence layer that converts protocol, query, screening, extraction, bias, and PRISMA artifacts into a package-ready evidence summary
- a reference-integrity layer that audits `references/library.bib`, synchronizes the citation graph, and separates suggested literature candidates from accepted references
- a manuscript-claim layer that turns display items, fact sheets, legends, and citation coverage into draft-ready claim packets
- an example multi-panel figure pipeline with source-data exports, fact sheets, and venue-aware exports
- Wave 1 reusable bulk-omics figure classes for MA plots, sample PCA, and pathway-enrichment dot plots
- an AI/ML professional figure track with implemented ROC/PR, calibration-reliability, training-dynamics, normalized-confusion, feature-importance, and ablation classes plus roadmap entries for uncertainty-focused classes
- an example schema-backed main-table pipeline
- CI scaffolding for HTML manuscript builds
- structure and generated-artifact validation tooling

What still needs installation before local builds work:

- pinned `mystmd` from `env/requirements-myst.txt`
- pinned figure and table dependencies from `env/requirements-phase2.txt`
- R figure dependencies from `env/install_r_figure_deps.R`
- `node` v20+

## Quick Start

1. Install the manuscript build tools:

```bash
python3 -m pip install -r env/requirements-myst.txt
python3 -m pip install -r env/requirements-phase2.txt
Rscript env/install_r_figure_deps.R
myst -v
```

If `node` is not already installed, the official PyPI-distributed `mystmd` tool can prompt to install a compatible local Node.js runtime the first time you run `myst`.

The same pinned MyST dependency file is used both locally and in CI.

2. Validate the scaffold:

```bash
python3 scripts/check_scaffold.py
```

3. Build the Phase 2 figure and table artifacts:

```bash
python3 scripts/build_phase2.py
```

Or use the figure-library CLI directly:

```bash
python3 scripts/figures_cli.py list-classes
python3 scripts/figures_cli.py list-roadmap
python3 scripts/figures_cli.py list-bundles
python3 scripts/figures_cli.py build --all
python3 scripts/figures_cli.py review --all
python3 scripts/figures_cli.py validate --all
```

Bundle-native commands are available when you want to operate on a coherent figure set instead of individual figures:

```bash
python3 scripts/figures_cli.py show-bundle --bundle <bundle_id>
python3 scripts/figures_cli.py review-bundle --bundle <bundle_id>
python3 scripts/figures_cli.py validate-bundle --bundle <bundle_id>
python3 scripts/figures_cli.py apply-bundles --all
```

Venue-readiness checks and submission-package manifests can be generated with:

```bash
python3 scripts/check_venue_readiness.py --all --write --strict
```

Systematic-review evidence summaries and package manifests can be generated with:

```bash
python3 scripts/review_cli.py evidence
```

Reference-integrity audits and citation-graph synchronization can be generated with:

```bash
python3 scripts/build_claim_reference_map.py
python3 scripts/apply_claim_reference_map.py
python3 scripts/check_reference_integrity.py --write --sync-graph
```

Top-level release bundles that assemble venue, figure-bundle, review, reference, pathway, and drafting artifacts can be generated with:

```bash
python3 scripts/build_release_bundle.py --profile integrated_demo_release --write
python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict
```

Optional preranked pathway enrichment with `fgsea` can be validated or run with:

```bash
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_active.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/configs/fgsea_active.yml --allow-missing-package --json
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_demo.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/configs/fgsea_demo.yml --allow-missing-package --json
```

When the active `fgsea` output exists, the pathway-enrichment dot figure automatically prefers the generated export over the static demo CSV. `python3 scripts/build_phase2.py` now refreshes that active profile before rebuilding figures.

To prepare a study-specific profile without breaking the tracked demo:

```bash
python3 scripts/scaffold_fgsea_study.py --study-id my_study --json
python3 scripts/activate_fgsea_profile.py --config pathways/studies/my_study/configs/fgsea.yml --json
```

For an MSigDB-backed study profile:

```bash
python3 scripts/scaffold_msigdb_profile.py \
  --study-id my_msigdb_study \
  --species human \
  --collection H \
  --version 2026.1.Hs \
  --identifier-type gene_symbol \
  --json

python3 scripts/run_msigdb_profile.py \
  --config pathways/studies/my_msigdb_study/configs/fgsea.yml \
  --prepare-ranks \
  --build-phase2 \
  --json
```

For study handoff artifacts:

```bash
python3 scripts/check_fgsea_study_dossier.py --config pathways/studies/my_study/configs/fgsea.yml --write --json
```

Claim-driven drafting packets can be generated with:

```bash
python3 scripts/build_claim_packets.py
python3 scripts/check_claim_coverage.py --write
python3 scripts/build_section_briefs.py
python3 scripts/check_section_briefs.py --write
python3 scripts/build_section_drafts.py
python3 scripts/check_section_drafts.py --write
python3 scripts/build_section_prose.py
python3 scripts/check_section_prose.py --write
python3 scripts/apply_section_prose.py
```

After the build, review the actual rendered figures here:

```bash
open figures/output/review/index.html
```

If you do not want to use `open`, just navigate to `figures/output/review/index.html` in any browser. This page exists specifically for visual QA.

The manuscript preview uses synced assets under `manuscript/assets/generated/`, but the authoritative figure outputs remain under `figures/output/`.

Tracked Python visual-regression baselines live under `tests/figures/python/baseline/`, while R snapshot space is reserved under `tests/figures/r/_snaps/`.

4. Build the manuscript HTML:

```bash
cd manuscript
myst build --html
```

5. Start a local MyST preview server:

```bash
cd manuscript
myst start
```

Optional convenience targets are still available through `Makefile` on systems where `make` is installed and working.

Runtime-support metadata can be validated with:

```bash
python3 scripts/check_runtime_support.py
```

For a local overnight soak-validation run that keeps generated artifacts inside an isolated `/tmp` workspace:

```bash
./.venv/bin/python scripts/run_overnight_validation.py --max-hours 8 --light-interval-min 15 --full-interval-min 60 --myst-interval-min 120 --workspace-root /tmp/manuscript_overnight --report-root reports/overnight --keep-workspace
```

The morning summary will be written under `reports/overnight/<timestamp>/summary.md`.

To inspect the latest in-progress or completed overnight run:

```bash
python3 scripts/overnight_status.py
```

For a high-signal morning triage view:

```bash
python3 scripts/overnight_digest.py
```

For a machine-checkable acceptance gate on the latest completed overnight run:

```bash
python3 scripts/check_overnight_report.py
```

GitHub Actions also runs a deterministic short-soak acceptance workflow in [soak-acceptance.yml](.github/workflows/soak-acceptance.yml).

Bundle-level acceptance for the exemplar figure sets runs separately in [bundle-acceptance.yml](.github/workflows/bundle-acceptance.yml).

Venue overlay readiness and submission-package acceptance runs separately in [venue-overlay-acceptance.yml](.github/workflows/venue-overlay-acceptance.yml).

Systematic-review evidence acceptance runs separately in [review-evidence-acceptance.yml](.github/workflows/review-evidence-acceptance.yml).

Reference-integrity acceptance runs separately in [reference-acceptance.yml](.github/workflows/reference-acceptance.yml).

Top-level integrated release acceptance runs separately in [release-bundle-acceptance.yml](.github/workflows/release-bundle-acceptance.yml).

Archive/export acceptance runs separately in [archive-export-acceptance.yml](.github/workflows/archive-export-acceptance.yml).

To freeze a checksum-backed archive export from the integrated release bundle:

```bash
python3 scripts/build_archive_export.py --profile integrated_demo_release --write
python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict
```

To create deterministic tar/zip deliverables from that frozen archive:

```bash
python3 scripts/build_export_bundle.py --profile integrated_demo_release --write
python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict
```

To generate deposit-ready citation and repository metadata from that export:

```bash
python3 scripts/build_deposit_metadata.py --profile integrated_demo_release --write
python3 scripts/check_deposit_metadata.py --profile integrated_demo_release --write --strict
```

Manuscript-claim drafting acceptance runs separately in [manuscript-claims-acceptance.yml](.github/workflows/manuscript-claims-acceptance.yml).

Deposit-metadata acceptance runs separately in [deposit-metadata-acceptance.yml](.github/workflows/deposit-metadata-acceptance.yml).

The same CI acceptance sequence can be run locally with:

```bash
./.venv/bin/python scripts/run_ci_soak_acceptance.py
```

## Next Recommended Work

1. Confirm the authoring default remains `MyST-first`.
2. Add the first real manuscript metadata and section content.
3. Wire Zotero auto-export to `references/library.bib`.
4. Promote the current example outputs into manuscript-cited display items.
5. Validate the first `nature` and `cell` overlay rules against the example assets.
