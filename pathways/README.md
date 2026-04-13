# Pathway Analysis

This directory holds optional pathway-analysis pipelines that feed manuscript-ready enrichment summaries and figure exports.

The first integrated pathway backend is a preranked `fgsea` pipeline.

Core files:

- `configs/fgsea_active.yml`: active profile used by `build_phase2.py` and `figure_05_pathway_enrichment_dot`
- `configs/fgsea_demo.yml`: tracked demo configuration
- `data/fgsea_demo_ranks.csv`: example preranked statistics
- `data/fgsea_demo_pathways.gmt`: example pathway definitions
- `studies/README.md`: study-specific scaffold and activation workflow
- `studies/rnaseq_case_control_template/`: tracked starter template for a case-control RNA-seq style study profile
- `msigdb/README.md`: MSigDB-specific guidance for local GMT usage
- `msigdb/catalog.yml`: tracked recommendations for supported MSigDB collections in this harness
- `results/README.md`: notes about generated outputs

Validate the active or demo configuration:

```bash
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_active.yml --json
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_demo.yml --json
```

Run the active profile:

```bash
python3 scripts/fgsea_pipeline.py run --config pathways/configs/fgsea_active.yml --allow-missing-package --json
```

Behavior:

- if `fgsea` is installed, the pipeline writes full enrichment results and a figure-ready dot-plot export
- if `fgsea` is not installed, `--allow-missing-package` records `skipped_missing_package` instead of pretending the enrichment ran

The pathway-dot figure layer can consume the exported CSV contract:

- `pathway`
- `gene_ratio`
- `neg_log10_fdr`
- `gene_count`
- `direction`
- `highlight_order`

This keeps the enrichment-analysis step separate from the final visualization layer while still making the handoff reproducible.

For a real study profile:

```bash
python3 scripts/scaffold_fgsea_study.py --study-id my_study --json
python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/my_study/configs/rank_prep.yml --json
python3 scripts/check_fgsea_study_dossier.py --config pathways/studies/my_study/configs/fgsea.yml --write --json
python3 scripts/activate_fgsea_profile.py --config pathways/studies/my_study/configs/fgsea.yml --json
```

That activation step rewrites `configs/fgsea_active.yml` so the next `build_phase2.py` run regenerates the active figure-backed pathway export from the study profile instead of the tracked demo.

For an MSigDB-backed study profile:

```bash
python3 scripts/scaffold_msigdb_profile.py \
  --study-id my_msigdb_study \
  --species human \
  --collection H \
  --version 2026.1.Hs \
  --identifier-type gene_symbol \
  --json
```

Then place the downloaded MSigDB GMT at the scaffolded path under `inputs/msigdb/`, validate the config, and activate it with `scripts/activate_fgsea_profile.py`.

For a single-command handoff after the GMT is in place:

```bash
python3 scripts/run_msigdb_profile.py \
  --config pathways/studies/my_msigdb_study/configs/fgsea.yml \
  --prepare-ranks \
  --build-phase2 \
  --json
```

That handoff also writes `study_dossier.{json,md}` so the raw DE table, rank-prep summary, fgsea summary, active-profile status, and `figure_05` provenance can be reviewed in one place.
