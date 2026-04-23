# Multi-Agent Manuscript System

An artifact-driven multi-agent manuscript system built on a deterministic harness substrate for:

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
- `workflows/agents/`: agent architecture notes and the machine-readable registry
- `benchmarks/`: tracked benchmark suites, score reports, and manifests
- `scripts/`: repo automation and lint helpers
- `env/`: environment definitions and install notes

## Current Phase

This repository is now in `Phase 3: Figure, Venue, And Review Systems`.

What exists:

- an explicit agent-architecture layer that maps the current repo into artifact-bounded specialized agents
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
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python scripts/check_runtime_support.py
python -m pip install -r env/requirements-myst.txt
python -m pip install -r env/requirements-phase2.txt
Rscript env/install_r_figure_deps.R
myst -v
```

If `node` is not already installed, the official PyPI-distributed `mystmd` tool can prompt to install a compatible local Node.js runtime the first time you run `myst`.

The same pinned MyST dependency file is used both locally and in CI.
If your system `python3` still resolves to Python 3.8 or older, point `-m venv` at an
explicit 3.10-3.12 interpreter first.

2. Validate the scaffold:

```bash
python3 scripts/check_scaffold.py
python3 scripts/check_agent_registry.py --json
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
python3 scripts/check_venue_readiness.py --all --json --strict --require-current-verification
python3 scripts/confirm_venue_verification.py --venue neurips --source-summary "Confirmed against the NeurIPS 2026 CFP" --dry-run --json
```

Each venue report now also records verification metadata such as `last_verified`, a stale-check window, and whether final submission-time confirmation is still required for the target venue and year.

Systematic-review evidence summaries and package manifests can be generated with:

```bash
python3 scripts/review_cli.py evidence
```

Reference-integrity audits and citation-graph synchronization can be generated with:

```bash
python3 scripts/build_claim_reference_map.py
python3 scripts/apply_claim_reference_map.py
python3 scripts/check_reference_integrity.py --write --sync-graph
python3 scripts/check_reference_integrity.py --json --require-confirmed-manuscript-bibliography
```

Top-level release bundles that assemble venue, figure-bundle, review, reference, pathway, and drafting artifacts can be generated with:

```bash
python3 scripts/build_release_bundle.py --profile integrated_demo_release --write
python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict
```

Cross-cutting go/no-go audits that combine venue readiness, reference integrity,
review evidence, review validation, and claim coverage can be generated with:

```bash
python3 scripts/check_pre_submission_audit.py --write --strict
python3 scripts/check_pre_submission_audit.py --venue neurips --json --strict
python3 scripts/check_pre_submission_audit.py --json --strict --require-current-venue-verification
python3 scripts/check_pre_submission_audit.py --json --strict --require-confirmed-manuscript-bibliography
```

Canonical repo-maturity reports now distinguish demo readiness, framework readiness,
and true submission readiness. The tracked manuscript-scope source of truth lives at
`manuscript/plans/manuscript_scope.json`.

```bash
python3 scripts/confirm_manuscript_scope.py --note "Confirmed against the finalized manuscript submission package." --dry-run --json
python3 scripts/check_repo_maturity.py --profile demo --json --strict
python3 scripts/check_repo_maturity.py --profile submission-framework --json
python3 scripts/check_repo_maturity.py --profile submission-ready --venue neurips --json
python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict
python3 scripts/check_repo_maturity_acceptance.py --profile submission-framework --json
python3 scripts/run_repo_maturity_nightly.py --profile submission-framework --write-step-summary
python3 scripts/check_repo_maturity_nightly.py --profile submission-framework --json
```

`check_repo_maturity.py` is the pure evaluator: it aggregates the current repo state plus
an optional acceptance artifact without running pytest or R itself.
`run_repo_maturity_acceptance.py` is the heavy acceptance runner: it executes runtime,
scaffold, full Python, and R figure validation, writes one acceptance artifact, and then
renders the final maturity report from that evidence.
`run_repo_maturity_nightly.py` is the ongoing canary runner: it exercises the acceptance
path plus the benchmark matrix and a sample public-package evaluation, then writes one
nightly summary bundle for CI artifacts or local monitoring.
`check_repo_maturity_nightly.py` validates that nightly bundle after the run completes, so
the monitoring workflow checks both execution and artifact integrity.
The nightly runner now keeps its acceptance manifest, summary, and repo-maturity report
under the selected nightly output directory instead of rewriting the tracked
`workflows/release/` report files. Its benchmark-matrix report and manifest are also written
inside that nightly output directory, so the monitoring path stays fully self-contained.
Each nightly run also allocates a unique `session_id` and writes its sample public benchmark
artifacts into a unique `public_runs/nightly_session_<session_id>/` directory, so reruns do
not inherit stale public-run siblings from earlier monitoring passes.

Structured benchmark scorecards for the manuscript drafting and integrity pipeline can be generated with:

```bash
python3 scripts/check_harness_benchmark.py --write --strict
python3 scripts/check_harness_benchmark.py --json --strict
python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_demo_v1 --json --strict
python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_heldout_v1 --json --strict
python3 scripts/check_harness_benchmark.py --bundle generic_author_input_demo_v1 --json --strict
python3 scripts/check_harness_benchmark.py --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 --json --strict
python3 scripts/check_harness_benchmark.py --package-archive /path/to/benchmark_package.zip --json --strict
python3 scripts/check_harness_benchmark_matrix.py --json --strict
python3 scripts/check_harness_benchmark_matrix.py --write --strict
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/generic_author_input_source_demo_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-archive /path/to/benchmark_package.zip --dry-run --json
python3 scripts/run_public_benchmark_package.py --package-archive /path/to/benchmark_package.zip --run-id my_public_package_run --json --strict
python3 scripts/check_public_benchmark_run.py --run-dir benchmarks/public_runs/<run_id> --json --strict
python3 scripts/check_public_benchmark_runs.py --runs-dir benchmarks/public_runs --json --strict
```

The default tracked suite is `benchmarks/suites/paper_writing_bench_like_internal_v1.json`.
It is intentionally `PaperWritingBench`-inspired rather than a claim of official external benchmark equivalence.
The adapter-ready demo bundle is `benchmarks/bundles/paperwritingbench_style_demo_v1.json`.
The held-out external-style sample bundle is `benchmarks/bundles/paperwritingbench_style_heldout_v1.json`.
The generic direct-author-input demo bundle is `benchmarks/bundles/generic_author_input_demo_v1.json`.
The source-style demo package that can regenerate that bundle is `benchmarks/packages/paperwritingbench_style_source_demo_v1/`.
The held-out source-style package is `benchmarks/packages/paperwritingbench_style_source_heldout_v1/`.
The second source-style demo package is `benchmarks/packages/generic_author_input_source_demo_v1/`.
The importer now accepts either an unpacked package directory or a local `.zip` archive, validates the package against the adapter contract before writing, and will not overwrite an existing bundle unless you pass `--force`.
`check_harness_benchmark.py` can now score those package directories and archives directly in dry-run mode without first importing them into the tracked bundle set.
`run_public_benchmark_package.py` can write a self-contained local run directory under `benchmarks/public_runs/<run_id>/` with report, manifest, and source provenance for a public package evaluation.
`check_public_benchmark_run.py` validates one of those run directories directly before you aggregate it with the broader run summary.
`check_public_benchmark_runs.py` summarizes those local run folders, highlights the latest and best runs, detects duplicate-source reruns, and can fail strictly if any public-package run is blocked or invalid.
Each public run now also records runtime metadata such as Python version, platform, exact invocation, and git state when available.
Both package archives and unpacked package directories now receive a stable `source_sha256` fingerprint in public run metadata.
The aggregate benchmark matrix is written to `benchmarks/reports/harness_benchmark_matrix.json`,
`benchmarks/reports/harness_benchmark_matrix.md`, and
`benchmarks/manifests/harness_benchmark_matrix.json`.

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

For a real-project scaffold that pairs an MSigDB study with release metadata placeholders:

```bash
python3 scripts/scaffold_project_release.py \
  --project-id my_project \
  --title "My Project Release" \
  --species human \
  --collection H \
  --json

python3 scripts/check_project_release.py --project my_project --write --json
python3 scripts/check_release_policy.py --project my_project --write --json
python3 scripts/check_anonymized_release.py --project my_project --write --json
python3 scripts/check_project_handoff.py --project my_project --write --json
```

Exact one-line forms used by scaffold validation:

```bash
python3 scripts/scaffold_project_release.py --project-id my_project --title "My Project Release" --species human --collection H --json
python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json
python3 scripts/check_anonymized_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_project_handoff.py --project rnaseq_real_project_template --write --json
```

For study handoff artifacts:

```bash
python3 scripts/check_fgsea_study_dossier.py --config pathways/studies/my_study/configs/fgsea.yml --write --json
```

Claim-driven drafting packets can be generated with:

```bash
# Optional: add real manuscript topic and claim notes in
# manuscript/plans/author_content_inputs.json before regenerating drafting artifacts.
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

GitHub Actions also runs a deterministic short-soak acceptance workflow in [soak-acceptance.yml](.github/workflows/soak-acceptance.yml) and a scheduled repo-maturity monitoring workflow in [repo-maturity-nightly.yml](.github/workflows/repo-maturity-nightly.yml).

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

Repository collaboration metadata can be kept in Git and then synced to the live GitHub repo with:

```bash
python3 scripts/sync_github_labels.py --dry-run --json
python3 scripts/sync_github_labels.py --dry-run --json --strict
python3 scripts/sync_github_labels.py
```

Tracked label drift is also checked automatically in [.github/workflows/github-labels-acceptance.yml](.github/workflows/github-labels-acceptance.yml).

The bibliography layer also tracks its Zotero Better BibTeX auto-export contract in [references/metadata/bibliography_source.yml](references/metadata/bibliography_source.yml); `python3 scripts/references_cli.py validate` now checks that repo-side wiring alongside bibliography health, and `python3 scripts/confirm_bibliography_scope.py --note ... --dry-run --json` marks when the current export has been confirmed as the real manuscript bibliography. The manuscript-scope layer now has a matching promotion helper: `python3 scripts/confirm_manuscript_scope.py --note ... --dry-run --json` updates `manuscript/plans/manuscript_scope.json` once the tracked manuscript content is no longer exemplar/demo only.

## Next Recommended Work

1. Confirm the authoring default remains `MyST-first`.
2. Add the first real manuscript metadata and section content.
3. Replace the starter bibliography contents with the real accepted Zotero export for your manuscript.
4. Promote the current example outputs into manuscript-cited display items.
5. Validate the first `nature` and `cell` overlay rules against the example assets.

## License

This project is dual-licensed.

- **Noncommercial use** (academic research, non-profit organizations, students, hobbyists, government institutions): free under the [PolyForm Noncommercial License 1.0.0](LICENSE).
- **Commercial use** (for-profit companies, commercial products, paid consulting, SaaS): requires a separate commercial license. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) for terms and how to obtain one.

If you are a university researcher, non-profit lab, or government scientist, you can use this software without contacting anyone -- the LICENSE covers your use.

For-profit organizations should review [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md) before deploying this software internally or building products on top of it.

Third-party components bundled or referenced by this project are listed with their respective licenses in [NOTICE](NOTICE).

## Security

Do not report undisclosed vulnerabilities in a public GitHub issue or pull request. Use the private reporting instructions in [SECURITY.md](SECURITY.md).

## Community

Project participation is covered by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
