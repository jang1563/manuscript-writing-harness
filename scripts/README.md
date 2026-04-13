# Scripts

This directory is for automation that should stay simple, inspectable, and versioned.

Current script:

- `check_scaffold.py`: validates that the core repository structure exists
- `check_generated_artifacts.py`: validates Phase 2 figure and table build outputs
- `build_phase2.py`: runs the figure build, table build, and generated-artifact checks without requiring `make`
- `build_phase2.py` now also refreshes the active `fgsea` profile before rebuilding figures so pathway figures can consume the latest enrichment output
- `build_figure_review.py`: generates an HTML QA surface for rendered figures, including renderer comparison, thumbnail diff, reveal slider, difference blend, font audit, clipping-risk audit, and small-size readability checks
- `figures_bundle.py`: validates tracked figure bundles, renders bundle-scoped review pages, summarizes bundle QA, and applies additive manuscript wiring into the managed Results block
- `venue_overlay.py`: resolves venue configs against the manuscript content registry and builds readiness reports plus submission-package manifests
- `check_venue_readiness.py`: checks one or all venue overlays, optionally writes readiness/manifests, and can fail strictly when any venue is still blocked
- `review_evidence.py`: derives a review-level evidence summary and package manifest from protocol, query, screening, extraction, bias, and PRISMA artifacts
- `reference_common.py`: shared bibliography and citation-graph helpers
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
- `activate_fgsea_profile.py`: promotes a validated study config into `pathways/configs/fgsea_active.yml`, rewriting its outputs to the canonical active figure-backed export path
- `manuscript_claims.py`: builds claim-driven drafting packets that connect display items, fact sheets, legends, and citation coverage
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
