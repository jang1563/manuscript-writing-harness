# AI/ML Professional Figure Track

Reviewed: 2026-04-09

## Purpose

Prepare the figure harness for AI-for-science, AI/ML methods, and top-conference style figures without weakening the existing publication-grade evidence contract.

## Main decision

Add an explicit `ai_ml_professional` style track alongside the current bulk-omics track.

This track should emphasize:

- metric clarity
- calibration and uncertainty visibility
- strong ablation communication
- compact, conference-grade readability
- reproducible source-data and claim linkage

## Planned figure classes

- `roc_pr_compound`
- `calibration_reliability`
- `confusion_matrix_normalized`
- `training_dynamics`
- `feature_importance_summary`
- `embedding_projection`
- `ablation_summary`
- `uncertainty_abstention_curve`

## Harness changes introduced now

- `figures/config/style_profiles.yml` defines `bulk_omics_professional` and `ai_ml_professional`
- `figures/registry/roadmap.yml` records implemented and planned figure families
- the class registry now carries family, expertise, status, and default style-profile metadata
- the `embedding_projection` class now covers representation-geometry diagnostics with domain-support context
- the `uncertainty_abstention_curve` class now covers selective-prediction safety claims with coverage-risk and retained-coverage panels
- specs and manifests now preserve `style_profile`
- the CLI can list the current implemented class library and the future roadmap separately

## Why this matters

AI/ML figure quality often fails in predictable ways:

- too much emphasis on leaderboard numbers without uncertainty
- calibration omitted even when deployment claims are made
- ablations shown in cluttered or non-comparable formats
- metric naming and ordering drifting across panels and tables

Preparing the harness now means future AI/ML figure classes can inherit a professional default instead of each class rediscovering those conventions.
