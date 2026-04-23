# Scripts

This directory is for automation that should stay simple, inspectable, and versioned.

Current scripts:

- `check_scaffold.py`: validates that the core repository structure exists
- `check_agent_registry.py`: validates the tracked agent registry and its path/link integrity
- `check_generated_artifacts.py`: validates Phase 2 figure and table build outputs
- `build_phase2.py`: runs the figure build, table build, and generated-artifact checks without requiring `make`
- `build_phase2.py` now also refreshes the active `fgsea` profile before rebuilding figures so pathway figures can consume the latest enrichment output
- `build_figure_review.py`: generates an HTML QA surface for rendered figures, including renderer comparison, thumbnail diff, reveal slider, difference blend, font audit, clipping-risk audit, and small-size readability checks
- `figures_bundle.py`: validates tracked figure bundles, renders bundle-scoped review pages, summarizes bundle QA, and applies additive manuscript wiring into the managed Results block
- `venue_overlay.py`: resolves venue configs against the manuscript content registry, tracks venue-verification metadata, and builds readiness reports plus submission-package manifests
- `check_venue_readiness.py`: checks one or all venue overlays, optionally writes readiness/manifests, can fail strictly on blocked overlays, and can enforce current verification for real submission gating
- `confirm_venue_verification.py`: updates a tracked venue config after a human confirms the exact venue-year rules, clearing the submission-time confirmation flag
- `pre_submission_audit.py`: aggregates venue readiness, reference integrity, review evidence, review validation, and claim coverage into one go/no-go report
- `check_pre_submission_audit.py`: writes the cross-cutting pre-submission audit outputs, can fail strictly unless the whole repo is ready, and can separately enforce current venue verification for real submission gating
- `manuscript_scope_common.py`: validates tracked manuscript-scope metadata and builds the real-submission manuscript-scope gate
- `confirm_manuscript_scope.py`: marks the tracked manuscript scope as confirmed for the real manuscript once exemplar/demo content has been replaced
- `repo_maturity.py`: aggregates manuscript scope, audit, release, project, reference, benchmark, and acceptance evidence into one canonical repo-maturity report
- `check_repo_maturity.py`: evaluates repo maturity without running pytest or R itself, and can write canonical maturity reports/manifests by profile
- `run_repo_maturity_acceptance.py`: runs runtime, scaffold, full Python, and R figure acceptance, writes one evidence artifact with environment metadata plus per-step timings, and then renders the canonical repo-maturity report plus its manifest
- `check_repo_maturity_acceptance.py`: validates the acceptance artifact, companion repo-maturity report JSON/markdown/manifest set, and acceptance summary for lifecycle/status consistency and final-output completeness
- `repo_maturity_acceptance_summary.py`: renders a markdown summary from the acceptance artifact plus the repo-maturity report so CI surfaces both the evidence steps, their timings, and the top-level maturity result
- `run_repo_maturity_nightly.py`: runs the longer-lived repo-maturity monitoring sequence, combining the acceptance path, benchmark matrix, a sample public benchmark package run, and a dedicated single-run validation step into one nightly artifact bundle; each run gets a unique `session_id` and isolated `public_runs/nightly_session_<session_id>/` sample-run directory
- `check_repo_maturity_nightly.py`: validates the nightly artifact, summary, and step-output surface for lifecycle/status consistency and final-output completeness
- `harness_benchmark.py`: runs the tracked agent-evaluation suites for the manuscript system, scoring baseline readiness, author-input propagation, and guardrails
- `check_harness_benchmark.py`: executes a tracked agent-evaluation suite, writes markdown/json scorecards and a manifest, and can fail strictly unless every tracked case passes
- `check_harness_benchmark_matrix.py`: runs every tracked agent-evaluation suite and bundle together, writing an aggregate matrix scorecard and manifest
- `import_benchmark_bundle.py`: imports a local source-style benchmark package into the tracked benchmark-bundle format so external pre-writing materials can be scored through the adapter layer
- `run_public_benchmark_package.py`: evaluates a local public benchmark package directory or archive into a self-contained run folder with report, manifest, markdown summary, and source metadata
- `check_public_benchmark_run.py`: validates one local public benchmark run directory, checking artifact completeness plus report/manifest/metadata consistency
- `check_public_benchmark_runs.py`: summarizes local public benchmark run folders, highlighting ready, blocked, and invalid runs
- `submission_gate_summary.py`: renders the GitHub Actions submission-gate markdown summary from the venue/audit JSON payloads, exit-code files, and captured stderr artifacts
- `run_submission_gate.py`: runs the venue gate plus scoped pre-submission audit end to end, writes the tracked gate artifacts, renders the summary markdown, and returns the combined gate exit status
- `github_labels.py`: loads `.github/labels.yml` and computes create/update/delete actions against live GitHub labels
- `sync_github_labels.py`: syncs the tracked GitHub label manifest to the live repository, with `--dry-run`, `--prune`, `--json`, and `--strict` support
- `review_evidence.py`: derives a review-level evidence summary and package manifest from protocol, query, screening, extraction, bias, and PRISMA artifacts
- `bibliography_common.py`: shared BibTeX parsing, Better BibTeX source-manifest validation, CSL discovery, citation linting, and manuscript citation lookup helpers
- `confirm_bibliography_scope.py`: marks the tracked Better BibTeX export as confirmed for the real manuscript after the starter bibliography has been replaced
- `reference_graph_common.py`: shared bibliography-entry loading plus citation-graph and reference-integrity helpers
- `references_common.py`: deprecated compatibility alias that resolves to `bibliography_common.py` for older branches
- `reference_common.py`: deprecated compatibility alias that resolves to `reference_graph_common.py` for older branches
- `reference_integrity.py`: audits bibliography integrity, citation-graph coverage, and literature-intelligence suggestion separation
- `build_citation_graph.py`: synchronizes manuscript claim nodes into `manuscript/plans/citation_graph.json`
- `reference_mapping.py`: builds tracked claim-to-reference mapping scaffolds and can apply approved mappings into the citation graph
- `build_claim_reference_map.py`: writes claim-to-reference mapping JSON and markdown
- `apply_claim_reference_map.py`: projects accepted claim-to-reference mappings into `manuscript/plans/citation_graph.json`
- `check_reference_integrity.py`: writes reference audit outputs and can fail on blocked or fully non-ready states
- `fgsea_pipeline.py`: validates and orchestrates the optional `fgsea` preranked pathway-enrichment pipeline
- `run_fgsea_pipeline.R`: executes the `fgsea` pipeline itself, writing enrichment tables, summary JSON, and figure-ready pathway exports when the package is available
- `scaffold_fgsea_study.py`: scaffolds a study-local ranks file, GMT file, config, and results README so real data can be prepared without replacing the tracked active profile too early
- `prepare_fgsea_ranks.py`: converts DESeq2/edgeR/limma-style differential-expression tables into canonical `gene,stat` fgsea prerank CSV plus QC summaries
- `fgsea_study_dossier.py`: builds study-level pathway-analysis dossiers that connect raw DE input, rank-prep summaries, fgsea status, active-profile status, and figure 05 provenance
- `build_fgsea_study_dossier.py`: writes markdown/json dossier artifacts for a study fgsea config
- `check_fgsea_study_dossier.py`: checks dossier readiness and can fail strictly when a study handoff is still blocked
- `release_bundle.py`: assembles a top-level release bundle from venue, figure-bundle, review, reference, pathway, and manuscript drafting artifacts
- `build_release_bundle.py`: writes markdown/json release-bundle reports and manifests for a configured release profile
- `check_release_bundle.py`: checks release-bundle readiness and can fail strictly when the integrated handoff package is still blocked
- `archive_export.py`: expands a release bundle into a frozen archive inventory with SHA256 checksums, archive manifest, and deposit notes
- `build_archive_export.py`: writes archive-export reports, manifest, checksum inventory, and deposit notes for a release profile
- `check_archive_export.py`: checks archive-export readiness and can fail strictly when the frozen package is still blocked
- `export_bundle.py`: assembles deterministic tar/zip deliverables from the frozen archive inventory
- `build_export_bundle.py`: writes tar/zip exports plus export metadata for a release profile
- `check_export_bundle.py`: checks export-bundle readiness and can fail strictly when the physical deliverables are not ready
- `deposit_metadata.py`: builds deposit-ready metadata artifacts such as profile-scoped `CITATION.cff`, `codemeta.json`, and Zenodo/OSF metadata from the export layer
- `build_deposit_metadata.py`: writes deposit-ready metadata reports, manifests, and metadata files for a release profile
- `check_deposit_metadata.py`: checks deposit-metadata readiness and can fail strictly when the citation/deposit handoff is not ready
- `scaffold_msigdb_profile.py`: scaffolds an MSigDB-backed study profile, including expected local GMT placement and MSigDB source metadata
- `run_msigdb_profile.py`: validates an MSigDB-backed study profile, can prepare ranks from a raw DE table, activates it into the active fgsea config, optionally rebuilds figure/manuscript outputs, and writes both a provenance report and a study dossier
- `project_release.py`: scaffolds and evaluates real-project release tracks that pair a study profile with release metadata placeholders and onboarding guidance
- `scaffold_project_release.py`: creates a project-level release scaffold, an MSigDB-backed study profile, and a placeholder release profile entry
- `build_project_release.py`: writes project-level readiness reports for tracked or scaffolded project release entries
- `check_project_release.py`: checks project readiness, including MSigDB study status, release-metadata placeholders, and activation state
- `release_policy.py`: evaluates anonymization and data-sharing policy readiness for tracked project release entries
- `build_release_policy.py`: writes project-level anonymization/data-sharing policy readiness reports
- `check_release_policy.py`: checks whether blinded-review, data-sharing, and MSigDB license confirmations are ready enough for a real project handoff
- `anonymized_release.py`: builds blinded-review preview packages by redacting manuscript frontmatter and sensitive release metadata into a project-local anonymized bundle
- `build_anonymized_release.py`: writes anonymized release preview outputs for a tracked project
- `check_anonymized_release.py`: checks anonymized-release readiness for a tracked project and can be used before conference-style exports
- `project_handoff.py`: aggregates project readiness, policy readiness, and anonymized-preview readiness into one top-level onboarding handoff
- `build_project_handoff.py`: writes top-level project handoff reports for tracked or scaffolded projects
- `check_project_handoff.py`: checks whether a project onboarding package is ready enough to hand off as one surface
- `activate_fgsea_profile.py`: promotes a validated study config into `pathways/configs/fgsea_active.yml`, rewriting its outputs to the canonical active figure-backed export path
- `manuscript_claims.py`: builds claim-driven drafting packets that connect display items, fact sheets, legends, citation coverage, and optional author-supplied topic/claim notes
- `build_claim_packets.py`: writes manuscript claim packet JSON plus generated drafting markdown
- `check_claim_coverage.py`: checks claim-packet readiness and can fail when display-backed drafting contracts are broken
- `manuscript_section_briefs.py`: builds section-level drafting briefs from outline, claim packets, review evidence, and reference readiness
- `build_section_briefs.py`: writes manuscript section-brief JSON plus generated drafting markdown
- `check_section_briefs.py`: checks section-brief readiness and can fail when section-level drafting contracts are broken
- `manuscript_section_drafts.py`: builds section-level draft scaffolds from briefs, claim packets, and evidence/readiness context
- `build_section_drafts.py`: writes manuscript section-draft JSON plus generated drafting markdown
- `check_section_drafts.py`: checks section-draft readiness and can fail when scaffold-level drafting contracts are broken
- `manuscript_section_prose.py`: builds editable first-pass prose from section draft scaffolds without overwriting canonical manuscript sections
- `build_section_prose.py`: writes manuscript section-prose JSON plus markdown drafts, including per-section files under `manuscript/drafts/sections/`
- `check_section_prose.py`: checks section-prose readiness and can fail when prose-generation scaffolds are broken
- `apply_section_prose.py`: projects generated section prose into managed blocks inside canonical manuscript sections while keeping freeform author text outside the managed region
- `sync_manuscript_display_assets.py`: copies generated preview assets into the MyST project so manuscript pages can render them reliably
- `run_overnight_validation.py`: creates an isolated `/tmp` workspace and runs duration-based overnight local soak validation with reports under `reports/overnight/`; when local MyST static HTML export is blocked by the known port-bind limitation, it falls back to stable `_build/site` artifacts and records that in the summary
- `overnight_status.py`: shows the latest overnight run status from `reports/overnight/` without manually opening `events.log` or waiting for `summary.md`
- `overnight_digest.py`: produces a high-signal morning digest for the latest overnight run, including health classification, warning/drift triage, recent events, first paths to open, and figure QA follow-up targets; `run_overnight_validation.py` writes this automatically at run completion
- `check_overnight_report.py`: validates that the latest or selected overnight report finished healthy enough for deterministic acceptance, including baseline pass, no unexpected warnings, no artifact drift, a healthy morning digest, and real morning-check artifact paths
- `render_ci_soak_summary.py`: renders a concise markdown acceptance summary for GitHub Actions so the latest soak result is visible directly in the workflow step summary
- `run_ci_soak_acceptance.py`: runs the short deterministic soak, validates the resulting report, writes `latest-report-check.json`, renders `latest-ci-summary.md`, and optionally appends the summary to `$GITHUB_STEP_SUMMARY`

The release bundle layer is profile-driven through `workflows/release/profiles/profiles.yml`, so new submission or handoff tracks can be added without hard-coding them into the scripts.

For a cross-cutting submission audit, use:

```bash
python3 scripts/confirm_manuscript_scope.py --note "Confirmed against the finalized manuscript submission package." --dry-run --json
python3 scripts/check_pre_submission_audit.py --write --strict
python3 scripts/check_pre_submission_audit.py --venue neurips --json --strict
python3 scripts/check_pre_submission_audit.py --json --strict --require-current-venue-verification
python3 scripts/check_pre_submission_audit.py --json --strict --require-confirmed-manuscript-bibliography
python3 scripts/check_agent_registry.py --json
python3 scripts/check_repo_maturity.py --profile demo --json --strict
python3 scripts/check_repo_maturity.py --profile submission-framework --json
python3 scripts/check_repo_maturity.py --profile submission-ready --venue neurips --json
python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict
python3 scripts/run_repo_maturity_nightly.py --profile submission-framework --write-step-summary
python3 scripts/check_repo_maturity_nightly.py --profile submission-framework --json
```

The canonical maturity model is intentionally layered:

- `demo`: the tracked exemplar multi-agent manuscript system and its deterministic harness substrate are healthy
- `submission-framework`: the framework is professionally validated even if real manuscript inputs are still deferred
- `submission-ready`: real manuscript scope, bibliography scope, and target-venue confirmation are all satisfied

For ongoing CI monitoring on top of the canonical acceptance path, use:

```bash
python3 scripts/run_repo_maturity_nightly.py --profile submission-framework --write-step-summary
```

The nightly runner reuses the same `submission-framework` acceptance evidence, then adds the
tracked benchmark matrix plus a held-out sample public benchmark package evaluation and
summary so longer-lived drift is easier to spot in one place. Its acceptance manifest,
summary, and repo-maturity report are written inside the nightly output directory, so the
monitoring path does not need to rewrite the tracked `workflows/release/` artifacts. The
benchmark matrix report and manifest are also written inside that same nightly output tree
instead of the tracked `benchmarks/reports/` and `benchmarks/manifests/` locations.

The three real-submission promotion helpers are:

```bash
python3 scripts/confirm_manuscript_scope.py --note "Confirmed against the finalized manuscript submission package." --dry-run --json
python3 scripts/confirm_bibliography_scope.py --note "Confirmed against the accepted manuscript Zotero export." --dry-run --json
python3 scripts/confirm_venue_verification.py --venue neurips --source-summary "Confirmed against the NeurIPS 2026 CFP" --dry-run --json
```

For the tracked internal benchmark suite, use:

```bash
python3 scripts/check_harness_benchmark.py --write --strict
python3 scripts/check_harness_benchmark.py --json --strict
python3 scripts/check_harness_benchmark.py --list-suites
python3 scripts/check_harness_benchmark.py --list-bundles
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
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 --force --json
python3 scripts/run_public_benchmark_package.py --package-archive /path/to/benchmark_package.zip --run-id my_public_package_run --json --strict
python3 scripts/check_public_benchmark_runs.py --runs-dir benchmarks/public_runs --json --strict
```

The default suite lives at `benchmarks/suites/paper_writing_bench_like_internal_v1.json`
and is designed as a `PaperWritingBench`-inspired internal scorecard for this repo's
structured drafting pipeline.

The adapter-ready demo bundle lives at `benchmarks/bundles/paperwritingbench_style_demo_v1.json`
and shows how pre-writing materials can be mapped into this repo's author-input surface
without claiming official support for the external benchmark package itself.

The corresponding source package lives at
`benchmarks/packages/paperwritingbench_style_source_demo_v1/` and can be re-imported into
the tracked bundle with `import_benchmark_bundle.py`. The importer validates package paths
against the package root, accepts local `.zip` archives through `--package-archive`, and
refuses to overwrite an existing bundle unless `--force` is used.

The held-out companion bundle, `benchmarks/bundles/paperwritingbench_style_heldout_v1.json`,
uses the same adapter family but shifts the emphasis to a different Results claim so the
tracked matrix is not just repeating the original response-kinetics path. Its source package
lives at `benchmarks/packages/paperwritingbench_style_source_heldout_v1/`.

You can also score unpacked package directories or local `.zip` archives directly with
`check_harness_benchmark.py`, which uses the importer path in dry-run mode without mutating
the tracked bundle files.

If you want persisted local outputs for a public package run without adding it to the tracked
bundle inventory, use `run_public_benchmark_package.py`, which writes into
`benchmarks/public_runs/<run_id>/`.
You can validate one of those run directories directly with
`check_public_benchmark_run.py --run-dir benchmarks/public_runs/<run_id> --json --strict`,
then summarize multiple local runs together with `check_public_benchmark_runs.py`, which
surfaces latest-run, best-run, and duplicate-source signals. The aggregate summary now
reuses the same stricter run-level validation logic, so a run with corrupted or inconsistent
artifacts is marked `invalid` there too.
Each public run also captures runtime metadata in `run_metadata.json`, including Python,
platform, invocation, and git context when available.
Unpacked package directories are fingerprinted from their evaluated benchmark contents rather than
every incidental file in the folder, so `source_sha256` and duplicate-source detection stay stable
even if Finder or OS metadata files appear alongside the package inputs.

The second demo bundle, `benchmarks/bundles/generic_author_input_demo_v1.json`, shows a
more generic external package shape built around direct author inputs rather than
benchmark-specific pre-writing field names. Its source package lives at
`benchmarks/packages/generic_author_input_source_demo_v1/`.

The aggregate tracked matrix lives at `benchmarks/reports/harness_benchmark_matrix.md`
and summarizes all tracked suites and bundles in one place.

For real-manuscript bibliography confirmation on top of the tracked Better BibTeX wiring, use:

```bash
python3 scripts/references_cli.py validate
python3 scripts/check_reference_integrity.py --json --require-confirmed-manuscript-bibliography
python3 scripts/confirm_bibliography_scope.py --note "Confirmed against the accepted manuscript Zotero export." --dry-run --json
```

For results-first manuscript drafting with real topic and claim inputs, fill in
`manuscript/plans/author_content_inputs.json` before regenerating the claim-packet and
section-drafting artifacts.

For real-project onboarding, use:

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
