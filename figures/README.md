# Figures

This directory is for publication-grade figure generation.

Principles:

- Python and R are both first-class renderers behind one figure contract.
- the canonical interface is `python3 scripts/figures_cli.py`
- reusable figure classes live in `figures/registry/classes.yml`
- tracked manuscript-facing bundles live in `figures/bundles/bundles.yml`
- family-level implemented/planned roadmap lives in `figures/registry/roadmap.yml`
- per-instance figure specs live in `figures/specs/`
- style profiles live in `figures/config/style_profiles.yml`
- implemented AI/ML professional classes currently include `roc_pr_compound`, `calibration_reliability`, `training_dynamics`, `confusion_matrix_normalized`, `feature_importance_summary`, and `ablation_summary`
- every figure is generated from source data
- multi-panel layout is reproducible
- source-data exports are emitted automatically
- styling, fonts, and export profiles are centralized
- R renderers can resolve a bundled DejaVu Sans path from the project environment so font audits can stay aligned with Python even on machines without a global DejaVu install
- visualization plans and fact sheets connect figures to manuscript claims
- the review page now includes renderer comparison, thumbnail diff, reveal slider, difference blend, font audit, clipping-risk audit, and small-size readability checks
- pathway figures can now be driven by an optional `fgsea` preranked enrichment pipeline under `pathways/`, which can export dot-plot-ready CSVs for enrichment-focused figure classes
- `figure_05_pathway_enrichment_dot` now prefers the tracked `fgsea` demo export when it exists, while still falling back to the static demo CSV if the enrichment pipeline has not been run

Core commands:

- `python3 scripts/figures_cli.py list-classes`
- `python3 scripts/figures_cli.py list-instances`
- `python3 scripts/figures_cli.py list-roadmap`
- `python3 scripts/figures_cli.py list-recipes`
- `python3 scripts/figures_cli.py list-bundles`
- `python3 scripts/figures_cli.py catalog`
- `python3 scripts/figures_cli.py cookbook`
- `python3 scripts/figures_cli.py show-recipe --recipe <recipe_id>`
- `python3 scripts/figures_cli.py show-bundle --bundle <bundle_id>`
- `python3 scripts/figures_cli.py scaffold --class <class_id> --figure-id <figure_id>`
- `python3 scripts/figures_cli.py scaffold --class <class_id> --figure-id <figure_id> --dry-run --json`
- `python3 scripts/figures_cli.py scaffold-recipe --recipe <recipe_id> --prefix <bundle_prefix> --dry-run --json`
- `python3 scripts/figures_cli.py scaffold-bundle --recipe <recipe_id> --bundle-id <bundle_id> --prefix <bundle_prefix> --dry-run --json`
- `python3 scripts/figures_cli.py build --all`
- `python3 scripts/figures_cli.py review --all`
- `python3 scripts/figures_cli.py validate --all`
- `python3 scripts/figures_cli.py review-bundle --bundle <bundle_id>`
- `python3 scripts/figures_cli.py validate-bundle --bundle <bundle_id>`
- `python3 scripts/figures_cli.py apply-bundles --all`

Human-readable catalog:

- tracked snapshot: [guides/class_catalog.md](guides/class_catalog.md)
- regenerate with `python3 scripts/figures_cli.py catalog --write figures/guides/class_catalog.md`
- tracked cookbook: [guides/cookbook.md](guides/cookbook.md)
- regenerate with `python3 scripts/figures_cli.py cookbook --write figures/guides/cookbook.md`
