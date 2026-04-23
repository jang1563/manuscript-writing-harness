#!/usr/bin/env python3
"""Validate the expected multi-agent manuscript system scaffold."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from figures_bundle import load_bundle_manifests
from figures_common import (
    REPO_ROOT,
    class_module_path,
    enabled_renderers,
    load_class_registry,
    load_figure_specs,
    manuscript_figure_items,
)


STATIC_REQUIRED_PATHS = [
    "README.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "Makefile",
    "pytest.ini",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/documentation.yml",
    ".github/ISSUE_TEMPLATE/licensing.yml",
    ".github/pull_request_template.md",
    ".github/labels.yml",
    ".github/workflows/github-labels-acceptance.yml",
    ".github/workflows/build-manuscript.yml",
    ".github/workflows/submission-gate.yml",
    ".github/workflows/repo-maturity-acceptance.yml",
    ".github/workflows/repo-maturity-nightly.yml",
    ".github/workflows/runtime-compatibility.yml",
    "research/README.md",
    "research/12_ai_ml_professional_figure_track.md",
    "research/13_agent_system_positioning.md",
    "manuscript/myst.yml",
    "manuscript/index.md",
    "manuscript/content_registry.json",
    "manuscript/frontmatter/highlights.md",
    "manuscript/frontmatter/graphical_abstract.md",
    "manuscript/assets/generated/README.md",
    "manuscript/drafts/README.md",
    "manuscript/drafts/section_briefs.json",
    "manuscript/drafts/section_briefs.md",
    "manuscript/drafts/section_drafts.json",
    "manuscript/drafts/section_drafts.md",
    "manuscript/drafts/section_prose.json",
    "manuscript/drafts/section_prose.md",
    "manuscript/drafts/sections/introduction.md",
    "manuscript/drafts/sections/results.md",
    "manuscript/drafts/sections/discussion.md",
    "manuscript/drafts/sections/methods.md",
    "manuscript/drafts/section_bodies/introduction.md",
    "manuscript/drafts/section_bodies/summary.md",
    "manuscript/drafts/section_bodies/discussion.md",
    "manuscript/drafts/section_bodies/methods.md",
    "manuscript/plans/README.md",
    "manuscript/plans/claim_packets.json",
    "manuscript/plans/claim_coverage.json",
    "manuscript/plans/author_content_inputs.json",
    "manuscript/plans/manuscript_scope.json",
    "manuscript/plans/outline.json",
    "manuscript/plans/display_item_map.json",
    "manuscript/plans/citation_graph.json",
    "manuscript/plans/research_graph.json",
    "manuscript/plans/writing_plan.json",
    "manuscript/plans/revision_checks.json",
    "manuscript/display_items/README.md",
    "manuscript/display_items/_bundles/README.md",
    "manuscript/display_items/figure_01_example.md.txt",
    "manuscript/display_items/figure_02_volcano_pathway.md.txt",
    "manuscript/display_items/figure_03_ma_plot.md.txt",
    "manuscript/display_items/figure_04_sample_pca.md.txt",
    "manuscript/display_items/figure_05_pathway_enrichment_dot.md.txt",
    "manuscript/display_items/figure_06_roc_pr_compound.md.txt",
    "manuscript/display_items/figure_07_calibration_reliability.md.txt",
    "manuscript/display_items/figure_08_training_dynamics.md.txt",
    "manuscript/display_items/figure_09_confusion_matrix_normalized.md.txt",
    "manuscript/display_items/figure_10_feature_importance_summary.md.txt",
    "manuscript/display_items/figure_11_ablation_summary.md.txt",
    "manuscript/display_items/_bundles/bundle_bulk_omics_deg_exemplar.md.txt",
    "manuscript/display_items/_bundles/bundle_ai_ml_evaluation_exemplar.md.txt",
    "manuscript/display_items/table_01_main.md.txt",
    "manuscript/sections/01_summary.md",
    "manuscript/sections/02_introduction.md",
    "manuscript/sections/03_results.md",
    "manuscript/sections/04_discussion.md",
    "manuscript/sections/05_methods.md",
    "manuscript/sections/06_acknowledgements.md",
    "manuscript/sections/07_funding_and_statements.md",
    "manuscript/supplementary/extended_data/README.md",
    "manuscript/supplementary/supplemental_figures/README.md",
    "manuscript/supplementary/science_package/README.md",
    "manuscript/supplementary/conference_appendix/README.md",
    "manuscript/legends/table_01_main.md",
    "references/README.md",
    "references/library.bib",
    "references/manifests/README.md",
    "references/mappings/README.md",
    "references/mappings/claim_reference_map.json",
    "references/mappings/claim_reference_map.md",
    "references/metadata/bibliography_source.yml",
    "references/metadata/suggested_reference_candidates.json",
    "references/reports/README.md",
    "env/requirements-myst.txt",
    "env/requirements-phase2.txt",
    "env/install_r_figure_deps.R",
    "env/runtime_support.yml",
    "figures/README.md",
    "figures/__init__.py",
    "figures/src/__init__.py",
    "figures/bundles/README.md",
    "figures/bundles/bundles.yml",
    "figures/bundles/bundle_bulk_omics_deg_exemplar/README.md",
    "figures/bundles/bundle_bulk_omics_deg_exemplar/bundle.yml",
    "figures/bundles/bundle_bulk_omics_deg_exemplar/manuscript/display_item_map.fragment.json",
    "figures/bundles/bundle_bulk_omics_deg_exemplar/manuscript/writing_plan.fragment.json",
    "figures/bundles/bundle_bulk_omics_deg_exemplar/manuscript/results_fragment.md",
    "figures/bundles/bundle_ai_ml_evaluation_exemplar/README.md",
    "figures/bundles/bundle_ai_ml_evaluation_exemplar/bundle.yml",
    "figures/bundles/bundle_ai_ml_evaluation_exemplar/manuscript/display_item_map.fragment.json",
    "figures/bundles/bundle_ai_ml_evaluation_exemplar/manuscript/writing_plan.fragment.json",
    "figures/bundles/bundle_ai_ml_evaluation_exemplar/manuscript/results_fragment.md",
    "figures/config/project_theme.yml",
    "figures/config/font_policy.yml",
    "figures/config/style_profiles.yml",
    "figures/config/venue_profiles.yml",
    "figures/guides/README.md",
    "figures/guides/ai_ml_professional_figures.md",
    "figures/registry/README.md",
    "figures/registry/classes.yml",
    "figures/registry/roadmap.yml",
    "figures/plans/README.md",
    "figures/plans/visualization_plan.json",
    "figures/fact_sheets/README.md",
    "figures/src/build_example_figure.py",
    "figures/src/build_volcano_pathway_figure.py",
    "figures/src/python/__init__.py",
    "figures/src/python/common.py",
    "figures/src/python/run_class_renderer.py",
    "figures/src/python/build_example_figure.py",
    "figures/src/python/build_volcano_pathway_figure.py",
    "figures/src/r/common.R",
    "figures/src/r/run_class_renderer.R",
    "figures/src/r/build_example_figure.R",
    "figures/src/r/build_volcano_pathway_figure.R",
    "tables/fact_sheets/README.md",
    "tables/fact_sheets/table_01_main.json",
    "tables/key_resources/README.md",
    "tables/key_resources/key_resources_table.csv",
    "tables/key_resources/key_resources_table.md",
    "tables/key_resources/key_resources_table.json",
    "tables/schemas/main_table_schema.yml",
    "tables/data/example_main_table.csv",
    "tables/src/build_main_table.py",
    "review/README.md",
    "review/manifests/README.md",
    "review/protocol/README.md",
    "review/reports/README.md",
    "pathways/README.md",
    "pathways/msigdb/README.md",
    "pathways/msigdb/catalog.yml",
    "pathways/configs/fgsea_active.yml",
    "pathways/configs/fgsea_demo.yml",
    "pathways/data/fgsea_demo_pathways.gmt",
    "pathways/data/fgsea_demo_ranks.csv",
    "pathways/results/README.md",
    "pathways/studies/README.md",
    "pathways/studies/rnaseq_case_control_template/README.md",
    "pathways/studies/rnaseq_case_control_template/configs/fgsea.yml",
    "pathways/studies/rnaseq_case_control_template/configs/rank_prep.yml",
    "pathways/studies/rnaseq_case_control_template/inputs/rnaseq_case_control_template_ranks.csv",
    "pathways/studies/rnaseq_case_control_template/inputs/rnaseq_case_control_template_pathways.gmt",
    "pathways/studies/rnaseq_case_control_template/inputs/raw/README.md",
    "pathways/studies/rnaseq_case_control_template/inputs/raw/rnaseq_case_control_template_differential_expression.csv",
    "pathways/studies/rnaseq_case_control_template/results/README.md",
    "pathways/studies/rnaseq_case_control_template/results/study_dossier.json",
    "pathways/studies/rnaseq_case_control_template/results/study_dossier.md",
    "pathways/studies/msigdb_hallmark_demo/README.md",
    "pathways/studies/msigdb_hallmark_demo/configs/fgsea.yml",
    "pathways/studies/msigdb_hallmark_demo/configs/rank_prep.yml",
    "pathways/studies/msigdb_hallmark_demo/inputs/msigdb_hallmark_demo_ranks.csv",
    "pathways/studies/msigdb_hallmark_demo/inputs/raw/README.md",
    "pathways/studies/msigdb_hallmark_demo/inputs/raw/msigdb_hallmark_demo_differential_expression.csv",
    "pathways/studies/msigdb_hallmark_demo/inputs/msigdb/README.md",
    "pathways/studies/msigdb_hallmark_demo/results/README.md",
    "pathways/studies/msigdb_hallmark_demo/results/study_dossier.json",
    "pathways/studies/msigdb_hallmark_demo/results/study_dossier.md",
    "workflows/agents/README.md",
    "workflows/agents/agent_registry.json",
    "workflows/venue_configs/README.md",
    "workflows/venue_configs/nature.yml",
    "workflows/venue_configs/cell.yml",
    "workflows/venue_configs/science.yml",
    "workflows/venue_configs/conference.yml",
    "workflows/venue_configs/acm_sigconf.yml",
    "workflows/venue_configs/ieee_vis.yml",
    "workflows/venue_configs/neurips.yml",
    "workflows/venue_configs/icml.yml",
    "workflows/checklists/nature_submission.md",
    "workflows/checklists/cell_submission.md",
    "workflows/checklists/science_submission.md",
    "workflows/checklists/conference_submission.md",
    "workflows/checklists/acm_sigconf_submission.md",
    "workflows/checklists/ieee_vis_submission.md",
    "workflows/checklists/neurips_submission.md",
    "workflows/checklists/icml_submission.md",
    "workflows/release/anonymization_check.md",
    "workflows/release/checksums/README.md",
    "workflows/release/deposit/README.md",
    "workflows/release/exports/README.md",
    "workflows/release/policies/README.md",
    "workflows/release/policies/rnaseq_real_project_template.yml",
    "workflows/release/projects/README.md",
    "workflows/release/projects/rnaseq_real_project_template/README.md",
    "workflows/release/projects/rnaseq_real_project_template/project.yml",
    "workflows/release/projects/rnaseq_real_project_template/project_readiness.json",
    "workflows/release/projects/rnaseq_real_project_template/project_readiness.md",
    "workflows/release/projects/rnaseq_real_project_template/policy_readiness.json",
    "workflows/release/projects/rnaseq_real_project_template/policy_readiness.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized_release.json",
    "workflows/release/projects/rnaseq_real_project_template/anonymized_release.md",
    "workflows/release/projects/rnaseq_real_project_template/handoff.json",
    "workflows/release/projects/rnaseq_real_project_template/handoff.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/README.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/manuscript/index.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/manuscript/myst.yml",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/manuscript/sections/06_acknowledgements.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/manuscript/sections/07_funding_and_statements.md",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/metadata/release_metadata_redacted.json",
    "workflows/release/projects/rnaseq_real_project_template/anonymized/notes/blind_review_notes.md",
    "workflows/release/profiles/README.md",
    "workflows/release/profiles/profiles.yml",
    "workflows/release/manifests/README.md",
    "workflows/release/reports/README.md",
    "workflows/release/reports/integrated_demo_release_bundle.json",
    "workflows/release/reports/integrated_demo_release_bundle.md",
    "workflows/release/reports/pre_submission_audit.json",
    "workflows/release/reports/pre_submission_audit.md",
    "workflows/release/reports/repo_maturity_demo.json",
    "workflows/release/reports/repo_maturity_demo.md",
    "workflows/release/reports/repo_maturity_submission-framework.json",
    "workflows/release/reports/repo_maturity_submission-framework.md",
    "workflows/release/reports/repo_maturity_submission-framework_acceptance/summary.md",
    "workflows/release/reports/repo_maturity_submission-ready.json",
    "workflows/release/reports/repo_maturity_submission-ready.md",
    "workflows/release/manifests/integrated_demo_release_bundle.json",
    "workflows/release/manifests/pre_submission_audit.json",
    "workflows/release/manifests/repo_maturity_demo.json",
    "workflows/release/manifests/repo_maturity_submission-framework.json",
    "workflows/release/manifests/repo_maturity_submission-ready.json",
    "workflows/release/reports/integrated_demo_release_archive.json",
    "workflows/release/reports/integrated_demo_release_archive.md",
    "workflows/release/manifests/integrated_demo_release_archive.json",
    "workflows/release/checksums/integrated_demo_release_archive_sha256.txt",
    "workflows/release/deposit/integrated_demo_release_deposit_notes.md",
    "workflows/release/exports/integrated_demo_release_export.json",
    "workflows/release/exports/integrated_demo_release_export.md",
    "workflows/release/exports/integrated_demo_release_export_checksums.txt",
    "workflows/release/exports/integrated_demo_release_export_manifest.json",
    "workflows/release/reports/integrated_demo_release_deposit_metadata.json",
    "workflows/release/reports/integrated_demo_release_deposit_metadata.md",
    "workflows/release/manifests/integrated_demo_release_deposit_metadata.json",
    "workflows/release/deposit/integrated_demo_release_CITATION.cff",
    "workflows/release/deposit/integrated_demo_release_codemeta.json",
    "workflows/release/deposit/integrated_demo_release_zenodo_metadata.json",
    "workflows/release/deposit/integrated_demo_release_osf_metadata.json",
    "benchmarks/README.md",
    "benchmarks/suites/README.md",
    "benchmarks/suites/paper_writing_bench_like_internal_v1.json",
    "benchmarks/bundles/README.md",
    "benchmarks/bundles/paperwritingbench_style_demo_v1.json",
    "benchmarks/bundles/paperwritingbench_style_heldout_v1.json",
    "benchmarks/bundles/generic_author_input_demo_v1.json",
    "benchmarks/packages/README.md",
    "benchmarks/public_runs/README.md",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/package_manifest.json",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_authoring_from_prewriting_materials/idea_summary.json",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_authoring_from_prewriting_materials/experimental_log.md",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_authoring_from_prewriting_materials/guidelines.md",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_authoring_from_prewriting_materials/mapping.json",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_authoring_from_prewriting_materials/expect.json",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_unknown_claim_guardrail/idea_summary.json",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_unknown_claim_guardrail/experimental_log.md",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_unknown_claim_guardrail/guidelines.md",
    "benchmarks/packages/paperwritingbench_style_source_demo_v1/cases/bundle_unknown_claim_guardrail/mapping.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/package_manifest.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_calibration_authoring/idea_summary.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_calibration_authoring/experimental_log.md",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_calibration_authoring/guidelines.md",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_calibration_authoring/mapping.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_calibration_authoring/expect.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_unknown_claim_guardrail/idea_summary.json",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_unknown_claim_guardrail/experimental_log.md",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_unknown_claim_guardrail/guidelines.md",
    "benchmarks/packages/paperwritingbench_style_source_heldout_v1/cases/heldout_bundle_unknown_claim_guardrail/mapping.json",
    "benchmarks/packages/generic_author_input_source_demo_v1/package_manifest.json",
    "benchmarks/packages/generic_author_input_source_demo_v1/cases/generic_author_input_authoring/author_inputs.json",
    "benchmarks/packages/generic_author_input_source_demo_v1/cases/generic_author_input_authoring/brief.md",
    "benchmarks/packages/generic_author_input_source_demo_v1/cases/generic_author_input_authoring/expect.json",
    "benchmarks/packages/generic_author_input_source_demo_v1/cases/generic_author_input_unknown_claim/author_inputs.json",
    "benchmarks/packages/generic_author_input_source_demo_v1/cases/generic_author_input_unknown_claim/brief.md",
    "benchmarks/reports/README.md",
    "benchmarks/reports/paper_writing_bench_like_internal_v1.json",
    "benchmarks/reports/paper_writing_bench_like_internal_v1.md",
    "benchmarks/reports/paperwritingbench_style_demo_v1.json",
    "benchmarks/reports/paperwritingbench_style_demo_v1.md",
    "benchmarks/reports/paperwritingbench_style_heldout_v1.json",
    "benchmarks/reports/paperwritingbench_style_heldout_v1.md",
    "benchmarks/reports/generic_author_input_demo_v1.json",
    "benchmarks/reports/generic_author_input_demo_v1.md",
    "benchmarks/reports/harness_benchmark_matrix.json",
    "benchmarks/reports/harness_benchmark_matrix.md",
    "benchmarks/manifests/README.md",
    "benchmarks/manifests/paper_writing_bench_like_internal_v1.json",
    "benchmarks/manifests/paperwritingbench_style_demo_v1.json",
    "benchmarks/manifests/paperwritingbench_style_heldout_v1.json",
    "benchmarks/manifests/generic_author_input_demo_v1.json",
    "benchmarks/manifests/harness_benchmark_matrix.json",
    "scripts/__init__.py",
    "scripts/build_claim_packets.py",
    "scripts/build_section_briefs.py",
    "scripts/build_phase2.py",
    "scripts/build_section_briefs.py",
    "scripts/build_section_drafts.py",
    "scripts/build_section_prose.py",
    "scripts/apply_section_prose.py",
    "scripts/scaffold_fgsea_study.py",
    "scripts/scaffold_msigdb_profile.py",
    "scripts/run_msigdb_profile.py",
    "scripts/activate_fgsea_profile.py",
    "scripts/build_figure_review.py",
    "scripts/build_citation_graph.py",
    "scripts/build_claim_reference_map.py",
    "scripts/check_claim_coverage.py",
    "scripts/check_section_briefs.py",
    "scripts/check_generated_artifacts.py",
    "scripts/check_section_briefs.py",
    "scripts/check_section_drafts.py",
    "scripts/check_section_prose.py",
    "scripts/check_reference_integrity.py",
    "scripts/apply_claim_reference_map.py",
    "scripts/check_venue_readiness.py",
    "scripts/pre_submission_audit.py",
    "scripts/check_pre_submission_audit.py",
    "scripts/manuscript_scope_common.py",
    "scripts/confirm_manuscript_scope.py",
    "scripts/repo_maturity.py",
    "scripts/check_repo_maturity.py",
    "scripts/run_repo_maturity_acceptance.py",
    "scripts/check_repo_maturity_acceptance.py",
    "scripts/repo_maturity_acceptance_summary.py",
    "scripts/run_repo_maturity_nightly.py",
    "scripts/check_repo_maturity_nightly.py",
    "scripts/harness_benchmark.py",
    "scripts/check_harness_benchmark.py",
    "scripts/check_harness_benchmark_matrix.py",
    "scripts/import_benchmark_bundle.py",
    "scripts/run_public_benchmark_package.py",
    "scripts/check_public_benchmark_run.py",
    "scripts/check_public_benchmark_runs.py",
    "scripts/submission_gate_summary.py",
    "scripts/run_submission_gate.py",
    "scripts/confirm_bibliography_scope.py",
    "scripts/check_runtime_support.py",
    "scripts/check_scaffold.py",
    "scripts/check_agent_registry.py",
    "scripts/figures_bundle.py",
    "scripts/figures_cli.py",
    "scripts/figures_common.py",
    "scripts/github_labels.py",
    "scripts/manuscript_claims.py",
    "scripts/manuscript_section_briefs.py",
    "scripts/review_bias.py",
    "scripts/manuscript_section_briefs.py",
    "scripts/manuscript_section_drafts.py",
    "scripts/manuscript_section_prose.py",
    "scripts/overnight_digest.py",
    "scripts/confirm_venue_verification.py",
    "scripts/bibliography_common.py",
    "scripts/references_common.py",
    "scripts/reference_graph_common.py",
    "scripts/reference_common.py",
    "scripts/reference_integrity.py",
    "scripts/reference_mapping.py",
    "scripts/review_cli.py",
    "scripts/review_common.py",
    "scripts/review_evidence.py",
    "scripts/review_extract.py",
    "scripts/review_prisma.py",
    "scripts/review_retrieve.py",
    "scripts/review_screen.py",
    "scripts/run_overnight_validation.py",
    "scripts/sync_github_labels.py",
    "scripts/sync_manuscript_display_assets.py",
    "scripts/venue_overlay.py",
    "scripts/fgsea_pipeline.py",
    "scripts/prepare_fgsea_ranks.py",
    "scripts/fgsea_study_dossier.py",
    "scripts/build_fgsea_study_dossier.py",
    "scripts/check_fgsea_study_dossier.py",
    "scripts/release_bundle.py",
    "scripts/build_release_bundle.py",
    "scripts/check_release_bundle.py",
    "scripts/archive_export.py",
    "scripts/build_archive_export.py",
    "scripts/check_archive_export.py",
    "scripts/export_bundle.py",
    "scripts/build_export_bundle.py",
    "scripts/check_export_bundle.py",
    "scripts/deposit_metadata.py",
    "scripts/build_deposit_metadata.py",
    "scripts/check_deposit_metadata.py",
    "scripts/project_release.py",
    "scripts/scaffold_project_release.py",
    "scripts/build_project_release.py",
    "scripts/check_project_release.py",
    "scripts/release_policy.py",
    "scripts/build_release_policy.py",
    "scripts/check_release_policy.py",
    "scripts/anonymized_release.py",
    "scripts/build_anonymized_release.py",
    "scripts/check_anonymized_release.py",
    "scripts/project_handoff.py",
    "scripts/build_project_handoff.py",
    "scripts/check_project_handoff.py",
    "scripts/run_fgsea_pipeline.R",
    "reports/overnight/README.md",
    ".github/workflows/bundle-acceptance.yml",
    ".github/workflows/release-bundle-acceptance.yml",
    ".github/workflows/archive-export-acceptance.yml",
    ".github/workflows/export-bundle-acceptance.yml",
    ".github/workflows/deposit-metadata-acceptance.yml",
    ".github/workflows/manuscript-claims-acceptance.yml",
    ".github/workflows/fgsea-pipeline-acceptance.yml",
    ".github/workflows/reference-acceptance.yml",
    ".github/workflows/review-evidence-acceptance.yml",
    ".github/workflows/venue-overlay-acceptance.yml",
    "tests/figures/python/test_build_figure_review.py",
    "tests/figures/python/test_public_artifact_hygiene.py",
    "tests/figures/python/test_bundle_engine.py",
    "tests/figures/python/test_venue_overlay.py",
    "tests/figures/python/test_overnight_digest.py",
    "tests/figures/python/conftest.py",
    "tests/figures/python/test_overnight_validation.py",
    "tests/figures/python/test_registry_cli.py",
    "tests/figures/python/test_release_bundle.py",
    "tests/figures/python/test_github_labels.py",
    "tests/figures/python/test_archive_export.py",
    "tests/figures/python/test_export_bundle.py",
    "tests/figures/python/test_deposit_metadata.py",
    "tests/figures/python/test_pre_submission_audit.py",
    "tests/figures/python/test_repo_maturity.py",
    "tests/figures/python/test_run_repo_maturity_acceptance.py",
    "tests/figures/python/test_check_repo_maturity_acceptance.py",
    "tests/figures/python/test_repo_maturity_acceptance_summary.py",
    "tests/figures/python/test_repo_maturity_workflow.py",
    "tests/figures/python/test_run_repo_maturity_nightly.py",
    "tests/figures/python/test_check_repo_maturity_nightly.py",
    "tests/figures/python/test_repo_maturity_nightly_workflow.py",
    "tests/figures/python/test_confirm_venue_verification.py",
    "tests/figures/python/test_submission_gate_summary.py",
    "tests/figures/python/test_submission_gate_workflow.py",
    "tests/figures/python/test_run_submission_gate.py",
    "tests/figures/python/test_project_release.py",
    "tests/figures/python/test_release_policy.py",
    "tests/figures/python/test_anonymized_release.py",
    "tests/figures/python/test_visual_regression.py",
    "tests/figures/python/baseline/README.md",
    "tests/figures/r/testthat.R",
    "tests/figures/r/testthat/helper-figures.R",
    "tests/figures/r/testthat/test-renderers.R",
    "tests/pathways/test_fgsea_pipeline.py",
    "tests/pathways/test_fgsea_study_dossier.py",
    "tests/figures/r/_snaps/README.md",
    "tests/manuscript/test_claim_packets.py",
    "tests/manuscript/test_section_briefs.py",
    "tests/references/test_references.py",
    "tests/references/test_reference_integrity.py",
    "tests/references/test_reference_mapping.py",
    "tests/references/test_reference_aliases.py",
    "tests/references/test_confirm_bibliography_scope.py",
    "tests/manuscript/test_claim_packets.py",
    "tests/manuscript/test_section_briefs.py",
    "tests/manuscript/test_section_drafts.py",
    "tests/manuscript/test_section_prose.py",
    "tests/manuscript/test_apply_section_prose.py",
    "tests/manuscript/test_author_content_inputs.py",
    "tests/manuscript/test_manuscript_scope.py",
    "tests/manuscript/test_confirm_manuscript_scope.py",
    "tests/manuscript/test_agent_registry.py",
    "tests/manuscript/test_harness_benchmark.py",
    "tests/manuscript/test_harness_benchmark_matrix.py",
    "tests/manuscript/test_import_benchmark_bundle.py",
    "tests/manuscript/test_public_benchmark_run.py",
    "tests/manuscript/test_public_benchmark_runs.py",
    "tests/manuscript/test_run_public_benchmark_package.py",
    "tests/review/__init__.py",
    "tests/review/test_review_cli.py",
    "tests/review/test_review_evidence.py",
    "tests/review/test_review_pipeline.py",
    "tests/review/test_review_summaries.py",
    "tests/review/test_review_validation.py",
]

REQUIRED_TEXT = {
    "README.md": [
        "python3 scripts/figures_cli.py list-classes",
        "python3 scripts/figures_cli.py list-roadmap",
        "python3 scripts/figures_cli.py list-bundles",
        "python3 scripts/figures_cli.py review-bundle --bundle <bundle_id>",
        "python3 scripts/figures_cli.py apply-bundles --all",
        "python3 scripts/check_venue_readiness.py --all --write --strict",
        "python3 scripts/check_venue_readiness.py --all --json --strict --require-current-verification",
        "python3 scripts/confirm_venue_verification.py --venue neurips --source-summary",
        "python3 scripts/review_cli.py evidence",
        "python3 scripts/build_claim_reference_map.py",
        "python3 scripts/apply_claim_reference_map.py",
        "python3 scripts/check_reference_integrity.py --write --sync-graph",
        "python3 scripts/check_reference_integrity.py --json --require-confirmed-manuscript-bibliography",
        "python3 scripts/check_pre_submission_audit.py --write --strict",
        "python3 scripts/check_pre_submission_audit.py --venue neurips --json --strict",
        "python3 scripts/check_pre_submission_audit.py --json --strict --require-current-venue-verification",
        "python3 scripts/check_pre_submission_audit.py --json --strict --require-confirmed-manuscript-bibliography",
        "python3 scripts/check_agent_registry.py --json",
        "python3 scripts/check_repo_maturity.py --profile demo --json --strict",
        "python3 scripts/check_repo_maturity.py --profile submission-framework --json",
        "python3 scripts/check_repo_maturity.py --profile submission-ready --venue neurips --json",
        "python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict",
        "python3 scripts/run_repo_maturity_nightly.py --profile submission-framework --write-step-summary",
        "python3 scripts/check_repo_maturity_nightly.py --profile submission-framework --json",
        "python3 scripts/check_harness_benchmark.py --write --strict",
        "python3 scripts/check_harness_benchmark.py --json --strict",
        "python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_demo_v1 --json --strict",
        "python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_heldout_v1 --json --strict",
        "python3 scripts/check_harness_benchmark.py --bundle generic_author_input_demo_v1 --json --strict",
        "python3 scripts/check_harness_benchmark.py --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 --json --strict",
        "python3 scripts/check_harness_benchmark.py --package-archive /path/to/benchmark_package.zip --json --strict",
        "python3 scripts/check_harness_benchmark_matrix.py --json --strict",
        "python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 --dry-run --json",
        "python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 --dry-run --json",
        "python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/generic_author_input_source_demo_v1 --dry-run --json",
        "python3 scripts/import_benchmark_bundle.py --package-archive /path/to/benchmark_package.zip --dry-run --json",
        "python3 scripts/run_public_benchmark_package.py --package-archive /path/to/benchmark_package.zip --run-id my_public_package_run --json --strict",
        "python3 scripts/check_public_benchmark_run.py --run-dir benchmarks/public_runs/<run_id> --json --strict",
        "python3 scripts/check_public_benchmark_runs.py --runs-dir benchmarks/public_runs --json --strict",
        "benchmarks/reports/harness_benchmark_matrix.json",
        "benchmarks/manifests/harness_benchmark_matrix.json",
        "benchmarks/suites/paper_writing_bench_like_internal_v1.json",
        "benchmarks/bundles/paperwritingbench_style_demo_v1.json",
        "benchmarks/bundles/paperwritingbench_style_heldout_v1.json",
        "benchmarks/bundles/generic_author_input_demo_v1.json",
        "benchmarks/packages/paperwritingbench_style_source_demo_v1/",
        "benchmarks/packages/paperwritingbench_style_source_heldout_v1/",
        "benchmarks/packages/generic_author_input_source_demo_v1/",
        "python3 scripts/confirm_bibliography_scope.py --note",
        "python3 scripts/build_release_bundle.py --profile integrated_demo_release --write",
        "python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_archive_export.py --profile integrated_demo_release --write",
        "python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_export_bundle.py --profile integrated_demo_release --write",
        "python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_deposit_metadata.py --profile integrated_demo_release --write",
        "python3 scripts/check_deposit_metadata.py --profile integrated_demo_release --write --strict",
        "python3 scripts/scaffold_project_release.py --project-id my_project --title \"My Project Release\" --species human --collection H --json",
        "python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json",
        "python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json",
        "python3 scripts/check_anonymized_release.py --project rnaseq_real_project_template --write --json",
        "python3 scripts/check_project_handoff.py --project rnaseq_real_project_template --write --json",
        "manuscript/plans/author_content_inputs.json",
        "manuscript/plans/manuscript_scope.json",
        "python3 scripts/build_claim_packets.py",
        "python3 scripts/check_claim_coverage.py --write",
        "python3 scripts/build_section_briefs.py",
        "python3 scripts/check_section_briefs.py --write",
        "python3 scripts/build_section_drafts.py",
        "python3 scripts/check_section_drafts.py --write",
        "python3 scripts/build_section_prose.py",
        "python3 scripts/check_section_prose.py --write",
        "python3 scripts/apply_section_prose.py",
        "python3 scripts/build_phase2.py",
        "python3 scripts/check_runtime_support.py",
        "./.venv/bin/python scripts/run_overnight_validation.py",
        "python3 scripts/overnight_digest.py",
        "python3 scripts/sync_github_labels.py --dry-run --json",
        "## Security",
        "[SECURITY.md](SECURITY.md)",
        "## Community",
        "[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)",
    ],
    "CONTRIBUTING.md": [
        "Participation in this project is governed by the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).",
        "## Reporting security issues",
        "Follow [SECURITY.md](SECURITY.md) for the private reporting process.",
        "silveray1563@gmail.com",
    ],
    "CODE_OF_CONDUCT.md": [
        "# Contributor Covenant Code of Conduct",
        "## Our Pledge",
        "## Enforcement",
        "silveray1563@gmail.com",
    ],
    "SECURITY.md": [
        "# Security Policy",
        "Do not open a public GitHub issue, discussion, or pull request",
        "silveray1563@gmail.com",
        "acknowledgment within 5 business days",
    ],
    ".github/ISSUE_TEMPLATE/bug_report.yml": [
        "name: Bug report",
        "labels:",
        "- bug",
        "What happened?",
    ],
    ".github/ISSUE_TEMPLATE/feature_request.yml": [
        "name: Feature request",
        "labels:",
        "- enhancement",
        "Problem or goal",
    ],
    ".github/ISSUE_TEMPLATE/documentation.yml": [
        "name: Documentation improvement",
        "labels:",
        "- documentation",
        "Suggested improvement",
    ],
    ".github/ISSUE_TEMPLATE/licensing.yml": [
        "name: Licensing question",
        "labels:",
        "- licensing",
        "I reviewed LICENSE and COMMERCIAL-LICENSE.md first.",
    ],
    ".github/pull_request_template.md": [
        "## Summary",
        "## Validation",
        "./.venv/bin/python -m pytest tests/",
        "## Checklist",
    ],
    ".github/labels.yml": [
        "name: bug",
        "name: enhancement",
        "name: documentation",
        "name: licensing",
    ],
    "review/README.md": [
        "python review_cli.py demo",
        "python review_cli.py evidence",
        "python review_cli.py validate",
        "Produces: reports/evidence_summary.md, reports/evidence_summary.json, manifests/review_evidence_package.json",
    ],
    "references/README.md": [
        "python3 scripts/build_claim_reference_map.py",
        "python3 scripts/apply_claim_reference_map.py",
        "python3 scripts/build_citation_graph.py",
        "python3 scripts/check_reference_integrity.py --write --sync-graph",
        "metadata/bibliography_source.yml",
        "python3 scripts/references_cli.py validate",
        "metadata/suggested_reference_candidates.json",
        "What The Integrity Audit Checks",
    ],
    "references/mappings/README.md": [
        "claim_reference_map.json",
        "python3 scripts/build_claim_reference_map.py",
        "python3 scripts/apply_claim_reference_map.py",
    ],
    "scripts/README.md": [
        "manuscript_claims.py",
        "build_claim_packets.py",
        "check_claim_coverage.py",
        "manuscript_section_briefs.py",
        "build_section_briefs.py",
        "check_section_briefs.py",
        "manuscript_section_drafts.py",
        "build_section_drafts.py",
        "check_section_drafts.py",
        "manuscript_section_prose.py",
        "build_section_prose.py",
        "check_section_prose.py",
        "apply_section_prose.py",
        "review_evidence.py",
        "bibliography_common.py",
        "references_common.py",
        "reference_graph_common.py",
        "reference_common.py",
        "reference_integrity.py",
        "reference_mapping.py",
        "build_citation_graph.py",
        "build_claim_reference_map.py",
        "apply_claim_reference_map.py",
        "check_reference_integrity.py",
        "release_bundle.py",
        "build_release_bundle.py",
        "check_release_bundle.py",
        "archive_export.py",
        "build_archive_export.py",
        "check_archive_export.py",
        "export_bundle.py",
        "build_export_bundle.py",
        "check_export_bundle.py",
        "deposit_metadata.py",
        "build_deposit_metadata.py",
        "check_deposit_metadata.py",
        "venue_overlay.py",
        "check_venue_readiness.py",
        "confirm_venue_verification.py",
        "pre_submission_audit.py",
        "check_pre_submission_audit.py",
        "check_agent_registry.py",
        "manuscript_scope_common.py",
        "confirm_manuscript_scope.py",
        "repo_maturity.py",
        "check_repo_maturity.py",
        "run_repo_maturity_acceptance.py",
        "run_repo_maturity_nightly.py",
        "check_repo_maturity_nightly.py",
        "github_labels.py",
        "sync_github_labels.py",
        "run_ci_soak_acceptance.py",
    ],
    "figures/README.md": [
        "Python and R are both first-class renderers",
        "figures/bundles/bundles.yml",
        "figures/registry/roadmap.yml",
        "figures/config/style_profiles.yml",
        "python3 scripts/figures_cli.py list-bundles",
        "python3 scripts/figures_cli.py list-roadmap",
        "python3 scripts/figures_cli.py scaffold-bundle --recipe <recipe_id> --bundle-id <bundle_id> --prefix <bundle_prefix> --dry-run --json",
        "python3 scripts/figures_cli.py review-bundle --bundle <bundle_id>",
        "python3 scripts/figures_cli.py apply-bundles --all",
        "visualization plans and fact sheets connect figures to manuscript claims",
        "[guides/class_catalog.md](guides/class_catalog.md)",
        "[guides/cookbook.md](guides/cookbook.md)",
    ],
    "figures/guides/ai_ml_professional_figures.md": [
        "This guide prepares the figure layer for AI-for-science and AI/ML paper conventions.",
        "## Figure-Layer Implications",
        "the first implemented AI/ML class in this figure layer is `roc_pr_compound`",
    ],
    "manuscript/myst.yml": [
        "version:",
        "project:",
        "bibliography:",
    ],
    "manuscript/index.md": [
        "# Working Manuscript",
        "## Abstract",
        "## Sections",
        "sections/07_funding_and_statements.md",
    ],
    "manuscript/sections/01_summary.md": [
        "manuscript/plans/outline.json",
        "manuscript/plans/display_item_map.json",
        "<!-- GENERATED_PROSE_BLOCK_START -->",
        "../drafts/section_bodies/summary.md",
    ],
    "manuscript/sections/02_introduction.md": [
        "<!-- GENERATED_PROSE_BLOCK_START -->",
        "../drafts/section_bodies/introduction.md",
    ],
    "manuscript/sections/03_results.md": [
        "../display_items/figure_01_example.md.txt",
        "<!-- BUNDLE_MANAGED_BLOCK_START -->",
        "../display_items/_bundles/bundle_bulk_omics_deg_exemplar.md.txt",
        "../display_items/_bundles/bundle_ai_ml_evaluation_exemplar.md.txt",
        "<!-- BUNDLE_MANAGED_BLOCK_END -->",
        "../display_items/table_01_main.md.txt",
        "manuscript/plans/display_item_map.json",
        "figures/bundles/bundle_bulk_omics_deg_exemplar/bundle.yml",
        "figures/bundles/bundle_ai_ml_evaluation_exemplar/bundle.yml",
        "figures/fact_sheets/figure_01_example.json",
        "tables/fact_sheets/table_01_main.json",
    ],
    "manuscript/sections/04_discussion.md": [
        "<!-- GENERATED_PROSE_BLOCK_START -->",
        "../drafts/section_bodies/discussion.md",
    ],
    "manuscript/sections/05_methods.md": [
        "<!-- GENERATED_PROSE_BLOCK_START -->",
        "../drafts/section_bodies/methods.md",
    ],
    "manuscript/drafts/README.md": [
        "results_claim_packets.md",
        "author_content_inputs.json",
        "python3 scripts/build_claim_packets.py",
        "section_briefs.md",
        "python3 scripts/build_section_briefs.py",
        "section_drafts.md",
        "python3 scripts/build_section_drafts.py",
        "section_prose.md",
        "python3 scripts/build_section_prose.py",
        "section_bodies/",
        "python3 scripts/apply_section_prose.py",
    ],
    "manuscript/sections/07_funding_and_statements.md": [
        "## Funding",
        "## Data availability",
        "## Code availability",
        "## Data and code availability",
        "## Data and materials availability",
        "## Author contributions",
        "## Competing interests",
    ],
    ".github/workflows/build-manuscript.yml": [
        "python3 -m pip install -r env/requirements-myst.txt",
        "python3 -m pip install -r env/requirements-phase2.txt",
        "Rscript env/install_r_figure_deps.R",
        "python3 scripts/build_phase2.py",
        "python3 -m pytest tests/figures/python",
        "Rscript tests/figures/r/testthat.R",
        "myst build --html",
    ],
    ".github/workflows/runtime-compatibility.yml": [
        "python-version:",
        "r-version:",
        "python3 scripts/check_runtime_support.py",
        "python3 -m pytest tests/figures/python",
        "Rscript tests/figures/r/testthat.R",
    ],
    ".github/workflows/venue-overlay-acceptance.yml": [
        "python3 scripts/check_venue_readiness.py --all --write --strict",
        "python3 scripts/figures_cli.py apply-bundles --all",
        "myst build --html",
    ],
    ".github/workflows/submission-gate.yml": [
        "workflow_dispatch:",
        "inputs:",
        "python3 scripts/run_submission_gate.py",
        "--write-step-summary",
    ],
    ".github/workflows/repo-maturity-acceptance.yml": [
        "pull_request:",
        "python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict --write-step-summary",
        "python3 scripts/check_repo_maturity_acceptance.py --profile submission-framework --json",
        "workflows/release/manifests/repo_maturity_submission-framework_acceptance.json",
    ],
    ".github/workflows/repo-maturity-nightly.yml": [
        "schedule:",
        "workflow_dispatch:",
        "python3 scripts/run_repo_maturity_nightly.py",
        "python3 scripts/check_repo_maturity_nightly.py",
        "repo-maturity-nightly-artifacts",
    ],
    ".github/workflows/review-evidence-acceptance.yml": [
        "python3 scripts/review_cli.py demo",
        "python3 scripts/review_cli.py validate",
        "python3 scripts/review_cli.py evidence",
        "python3 -m pytest tests/review -q",
    ],
    ".github/workflows/reference-acceptance.yml": [
        "python3 scripts/build_citation_graph.py",
        "python3 scripts/build_claim_reference_map.py",
        "python3 scripts/apply_claim_reference_map.py",
        "python3 scripts/check_reference_integrity.py --write --sync-graph",
        "python3 -m pytest tests/references -q",
    ],
    ".github/workflows/manuscript-claims-acceptance.yml": [
        "python3 scripts/build_claim_packets.py",
        "python3 scripts/check_claim_coverage.py --write",
        "python3 scripts/build_section_briefs.py",
        "python3 scripts/check_section_briefs.py --write",
        "python3 scripts/build_section_drafts.py",
        "python3 scripts/check_section_drafts.py --write",
        "python3 scripts/build_section_prose.py",
        "python3 scripts/check_section_prose.py --write",
        "python3 scripts/apply_section_prose.py",
        "python3 -m pytest tests/manuscript -q",
    ],
    ".github/workflows/release-bundle-acceptance.yml": [
        "python3 scripts/build_phase2.py",
        "python3 scripts/review_cli.py evidence",
        "python3 scripts/check_reference_integrity.py --write --sync-graph",
        "python3 scripts/check_fgsea_study_dossier.py --config pathways/configs/fgsea_active.yml --write --json",
        "python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict",
        "myst build --html",
    ],
    ".github/workflows/archive-export-acceptance.yml": [
        "python3 scripts/build_phase2.py",
        "python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict",
        "python3 -m pytest tests/figures/python/test_archive_export.py -q",
        "myst build --html",
    ],
    ".github/workflows/export-bundle-acceptance.yml": [
        "python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict",
        "python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict",
        "python3 -m pytest tests/figures/python/test_export_bundle.py -q",
        "myst build --html",
    ],
    "workflows/venue_configs/README.md": [
        "required sections must resolve against `manuscript/content_registry.json`",
        "verification metadata records when each baseline was last checked",
        "--require-current-verification",
        "full overlay generation exists",
    ],
    "pathways/README.md": [
        "manuscript-ready enrichment summaries",
        "supported MSigDB collections in this manuscript system pathway layer",
        "python3 scripts/scaffold_msigdb_profile.py \\",
    ],
    "pathways/msigdb/README.md": [
        "Recommended collections for this manuscript system pathway layer:",
        "python3 scripts/scaffold_msigdb_profile.py \\",
        "python3 scripts/run_msigdb_profile.py \\",
    ],
    "workflows/release/README.md": [
        "python3 scripts/check_venue_readiness.py --all --json --strict --require-current-verification",
        "python3 scripts/check_pre_submission_audit.py --json --strict --require-current-venue-verification",
        "python3 scripts/confirm_venue_verification.py --venue neurips --source-summary",
        "python3 scripts/check_repo_maturity.py --profile demo --json --strict",
        "python3 scripts/check_repo_maturity.py --profile submission-framework --json",
        "python3 scripts/check_repo_maturity.py --profile submission-ready --venue neurips --json",
        "python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict",
        "python3 scripts/build_release_bundle.py --profile integrated_demo_release --write",
        "python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_archive_export.py --profile integrated_demo_release --write",
        "python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_export_bundle.py --profile integrated_demo_release --write",
        "python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/build_deposit_metadata.py --profile integrated_demo_release --write",
        "python3 scripts/check_deposit_metadata.py --profile integrated_demo_release --write --strict",
    ],
    "workflows/release/deposit/README.md": [
        "CITATION.cff",
        "codemeta.json",
        "Zenodo deposit metadata JSON",
        "OSF deposit metadata JSON",
    ],
    ".github/workflows/deposit-metadata-acceptance.yml": [
        "python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict",
        "python3 scripts/check_deposit_metadata.py --profile integrated_demo_release --write --strict",
        "python3 -m pytest tests/figures/python/test_deposit_metadata.py -q",
    ],
}

ALLOWED_STATUS = {"available", "generated", "mapped", "planned"}
ALLOWED_REVISION_STATUS = {"required", "planned", "completed"}


def _check_required_text(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, snippets in REQUIRED_TEXT.items():
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{relative_path} is missing expected text: {snippet!r}")
    return errors


def _parse_simple_yaml_list(path: Path, key: str) -> list[str]:
    items: list[str] = []
    in_block = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not in_block:
            if raw_line.strip() == f"{key}:":
                in_block = True
            continue
        if raw_line.startswith("  - "):
            items.append(raw_line.strip()[2:].strip())
            continue
        if raw_line.startswith(" ") or not raw_line.strip():
            continue
        break
    return items


def _load_registry(repo_root: Path) -> dict[str, dict[str, dict[str, object]]]:
    registry_path = repo_root / "manuscript/content_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for group_name in ("sections", "special_assets"):
        if group_name not in registry or not isinstance(registry[group_name], dict):
            raise ValueError(f"content registry must define an object for {group_name!r}")
        for item_name, metadata in registry[group_name].items():
            if not isinstance(metadata, dict):
                raise ValueError(f"registry item {group_name}.{item_name} must be an object")
            status = metadata.get("status")
            if status not in ALLOWED_STATUS:
                raise ValueError(
                    f"registry item {group_name}.{item_name} has invalid status {status!r}"
                )
    return registry


def _load_json_file(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_figure_library_alignment(repo_root: Path) -> list[str]:
    errors: list[str] = []
    registry = load_class_registry()
    specs = load_figure_specs()
    spec_ids = {spec["figure_id"] for spec in specs}
    mapped_items = manuscript_figure_items()

    for class_id in registry:
        for renderer in ("python", "r"):
            if renderer in registry[class_id]["supported_renderers"]:
                module_path = class_module_path(renderer, class_id)
                if not module_path.exists():
                    errors.append(f"missing class renderer {module_path.relative_to(repo_root)}")

    visualization_plan = _load_json_file(repo_root / "figures/plans/visualization_plan.json")
    plan_items = visualization_plan.get("figures", [])
    if not isinstance(plan_items, list) or not plan_items:
        errors.append("figures/plans/visualization_plan.json must define a non-empty figures list")
    else:
        plan_ids = {item.get("figure_id") for item in plan_items}
        if plan_ids != spec_ids:
            errors.append("visualization_plan.json must align exactly with the current figure specs")

    for spec in specs:
        figure_id = spec["figure_id"]
        for relative in (
            spec["_spec_path"],
            str(spec["fact_sheet"]),
            str(spec["legend_path"]),
            *spec["data_inputs"],
        ):
            if not (repo_root / relative).exists():
                errors.append(f"{figure_id} is missing required figure-library path {relative}")
        for renderer in enabled_renderers(spec):
            output_dir = spec["renderers"][renderer]["output_dir"]
            if not isinstance(output_dir, str) or not output_dir.startswith("figures/output/"):
                errors.append(f"{figure_id} has invalid output_dir for renderer {renderer!r}")

        mapped_item = mapped_items.get(figure_id)
        if mapped_item is not None:
            if mapped_item.get("spec_path") != spec["_spec_path"]:
                errors.append(f"display_item_map spec_path drift detected for {figure_id}")
            if mapped_item.get("fact_sheet") != spec["fact_sheet"]:
                errors.append(f"display_item_map fact_sheet drift detected for {figure_id}")
            if mapped_item.get("legend_path") != spec["legend_path"]:
                errors.append(f"display_item_map legend drift detected for {figure_id}")
            if mapped_item.get("claim_ids") != spec["claim_ids"]:
                errors.append(f"display_item_map claim_ids drift detected for {figure_id}")

    return errors


def _check_planning_alignment(repo_root: Path) -> list[str]:
    errors: list[str] = []
    outline = _load_json_file(repo_root / "manuscript/plans/outline.json")
    display_map = _load_json_file(repo_root / "manuscript/plans/display_item_map.json")
    citation_graph = _load_json_file(repo_root / "manuscript/plans/citation_graph.json")
    research_graph = _load_json_file(repo_root / "manuscript/plans/research_graph.json")
    writing_plan = _load_json_file(repo_root / "manuscript/plans/writing_plan.json")
    revision_checks = _load_json_file(repo_root / "manuscript/plans/revision_checks.json")
    figure_specs = {spec["figure_id"]: spec for spec in load_figure_specs()}
    table_fact_sheet = _load_json_file(repo_root / "tables/fact_sheets/table_01_main.json")

    sections = outline.get("sections")
    if not isinstance(sections, list) or not sections:
        errors.append("manuscript/plans/outline.json must define a non-empty sections list")
    else:
        section_ids = [item.get("section_id") for item in sections]
        for required in ("summary", "introduction", "results", "discussion", "methods"):
            if required not in section_ids:
                errors.append(f"outline.json is missing section_id {required!r}")

    display_items = display_map.get("items")
    if not isinstance(display_items, list) or not display_items:
        errors.append("display_item_map.json must contain at least one mapped display item")
    else:
        display_item_ids = [item.get("display_item_id") for item in display_items]
        if writing_plan.get("display_item_refs") != display_item_ids:
            errors.append("writing_plan.json display_item_refs do not match display_item_map.json")
        if outline.get("display_item_sequence") != display_item_ids:
            errors.append("outline.json display_item_sequence does not match display_item_map.json")
        for item in display_items:
            item_id = item.get("display_item_id")
            if item.get("type") == "figure":
                spec = figure_specs.get(str(item_id))
                if spec is None:
                    errors.append(f"display_item_map.json references unknown figure {item_id!r}")
                else:
                    if item.get("claim_ids") != spec.get("claim_ids"):
                        errors.append(f"display_item_map claim_ids drift detected for {item_id}")
                    if item.get("spec_path") != spec.get("_spec_path"):
                        errors.append(f"display_item_map spec_path drift detected for {item_id}")
                    if item.get("fact_sheet") != spec.get("fact_sheet"):
                        errors.append(f"display_item_map fact_sheet drift detected for {item_id}")
                    if item.get("legend_path") != spec.get("legend_path"):
                        errors.append(f"display_item_map legend drift detected for {item_id}")
                continue
            if item_id == "table_01_main" and item.get("claim_ids") != table_fact_sheet.get("claim_ids"):
                errors.append("table display-item claim_ids do not match the table fact sheet")

    reference_nodes = citation_graph.get("reference_nodes", [])
    edges = citation_graph.get("edges", [])
    reference_ids = {item.get("id") for item in reference_nodes}
    if not reference_ids:
        errors.append("citation_graph.json must include at least one reference node")
    if not edges:
        errors.append("citation_graph.json must define at least one edge")

    research_nodes = research_graph.get("nodes", [])
    research_ids = {item.get("id") for item in research_nodes}
    for required in (
        "idea_summary",
        "experimental_log",
        "display_item_map",
        "citation_graph",
        "claim_packets",
        "section_briefs",
        "section_drafts",
        "section_prose",
    ):
        if required not in research_ids:
            errors.append(f"research_graph.json is missing node {required!r}")

    checks = revision_checks.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("revision_checks.json must define a non-empty checks list")
    else:
        for check in checks:
            if check.get("status") not in ALLOWED_REVISION_STATUS:
                errors.append(
                    f"revision_checks.json has invalid status {check.get('status')!r}"
                )
    if writing_plan.get("claim_packet_path") != "manuscript/plans/claim_packets.json":
        errors.append("writing_plan.json must point claim_packet_path to manuscript/plans/claim_packets.json")
    if writing_plan.get("section_brief_path") != "manuscript/drafts/section_briefs.json":
        errors.append("writing_plan.json must point section_brief_path to manuscript/drafts/section_briefs.json")
    if writing_plan.get("section_draft_path") != "manuscript/drafts/section_drafts.json":
        errors.append("writing_plan.json must point section_draft_path to manuscript/drafts/section_drafts.json")
    if writing_plan.get("section_prose_path") != "manuscript/drafts/section_prose.json":
        errors.append("writing_plan.json must point section_prose_path to manuscript/drafts/section_prose.json")

    return errors


def _check_bundle_alignment(repo_root: Path) -> list[str]:
    errors: list[str] = []
    manifests = load_bundle_manifests(repo_root)
    display_map = _load_json_file(repo_root / "manuscript/plans/display_item_map.json")
    display_item_ids = [
        str(item.get("display_item_id"))
        for item in display_map.get("items", [])
        if isinstance(item, dict) and item.get("display_item_id")
    ]
    visualization_plan = _load_json_file(repo_root / "figures/plans/visualization_plan.json")
    plan_map = {
        str(item.get("figure_id")): item
        for item in visualization_plan.get("figures", [])
        if isinstance(item, dict) and item.get("figure_id")
    }
    results_text = (repo_root / "manuscript/sections/03_results.md").read_text(encoding="utf-8")

    for bundle_id, bundle in manifests.items():
        include_path = f"../display_items/_bundles/{bundle_id}.md.txt"
        if include_path not in results_text:
            errors.append(f"results section is missing managed include for {bundle_id}")
        figure_ids = [str(item["figure_id"]) for item in bundle["figures"]]
        if bundle.get("acceptance_tier") == "exemplar":
            missing = [figure_id for figure_id in figure_ids if figure_id not in display_item_ids]
            if missing:
                errors.append(f"{bundle_id} exemplar bundle is missing mapped figures {missing}")
            else:
                indices = [display_item_ids.index(figure_id) for figure_id in figure_ids]
                if indices != list(range(min(indices), max(indices) + 1)):
                    errors.append(
                        f"{bundle_id} exemplar bundle figures are not contiguous in display_item_map.json"
                    )
        for figure_id in figure_ids:
            plan_item = plan_map.get(figure_id)
            if plan_item is None:
                errors.append(f"{bundle_id} is missing visualization plan entry for {figure_id}")
                continue
            if plan_item.get("bundle_id") != bundle_id:
                errors.append(f"{bundle_id} visualization plan bundle_id drift detected for {figure_id}")
    return errors


def _check_venue_registry_alignment(repo_root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    registry = _load_registry(repo_root)
    venue_dir = repo_root / "workflows/venue_configs"

    for config_path in sorted(venue_dir.glob("*.yml")):
        required_sections = _parse_simple_yaml_list(config_path, "required_sections")
        required_assets = _parse_simple_yaml_list(config_path, "special_assets")

        for section in required_sections:
            metadata = registry["sections"].get(section)
            if metadata is None:
                errors.append(f"{config_path.name} references unknown section {section!r}")
                continue
            if metadata["status"] == "planned":
                warnings.append(f"{config_path.name} depends on planned section {section!r}")

        for asset in required_assets:
            metadata = registry["special_assets"].get(asset)
            if metadata is None:
                errors.append(f"{config_path.name} references unknown special asset {asset!r}")
                continue
            if metadata["status"] == "planned":
                warnings.append(
                    f"{config_path.name} depends on planned special asset {asset!r}"
                )

    return errors, warnings


def required_paths() -> list[str]:
    paths = list(STATIC_REQUIRED_PATHS)
    for spec in load_figure_specs():
        paths.extend(
            [
                str(spec["_spec_path"]),
                str(spec["fact_sheet"]),
                str(spec["legend_path"]),
                *spec["data_inputs"],
            ]
        )
    return sorted(set(paths))


def main() -> int:
    repo_root = REPO_ROOT
    try:
        missing = [path for path in required_paths() if not (repo_root / path).exists()]
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Scaffold check failed. Figure library metadata is invalid: {exc}")
        return 1

    if missing:
        print("Scaffold check failed. Missing required paths:")
        for path in missing:
            print(f"  - {path}")
        return 1

    text_errors = _check_required_text(repo_root)
    if text_errors:
        print("Scaffold check failed. Missing expected content:")
        for error in text_errors:
            print(f"  - {error}")
        return 1

    try:
        figure_errors = _check_figure_library_alignment(repo_root)
        planning_errors = _check_planning_alignment(repo_root)
        bundle_errors = _check_bundle_alignment(repo_root)
        venue_errors, venue_warnings = _check_venue_registry_alignment(repo_root)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"Scaffold check failed. Invalid planning or registry content: {exc}")
        return 1

    if figure_errors:
        print("Scaffold check failed. Figure-library drift detected:")
        for error in figure_errors:
            print(f"  - {error}")
        return 1

    if planning_errors:
        print("Scaffold check failed. Planning artifact drift detected:")
        for error in planning_errors:
            print(f"  - {error}")
        return 1

    if bundle_errors:
        print("Scaffold check failed. Bundle alignment drift detected:")
        for error in bundle_errors:
            print(f"  - {error}")
        return 1

    if venue_errors:
        print("Scaffold check failed. Venue configuration drift detected:")
        for error in venue_errors:
            print(f"  - {error}")
        return 1

    print("Scaffold check passed.")
    print(f"Validated {len(required_paths())} required paths.")
    if venue_warnings:
        print("Warnings:")
        for warning in venue_warnings:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
