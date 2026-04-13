# fgsea Study Profiles

This directory is for study-specific preranked enrichment inputs that should not replace the tracked demo profile until they are ready.

Suggested workflow:

1. Scaffold a study profile:

```bash
python3 scripts/scaffold_fgsea_study.py --study-id my_study
```

2. Fill in the generated raw differential-expression table under `pathways/studies/my_study/inputs/raw/` and adjust `configs/rank_prep.yml` if your columns differ from the default.

3. Prepare ranks, then validate or run the study profile directly:

```bash
python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/my_study/configs/rank_prep.yml --json
python3 scripts/fgsea_pipeline.py validate --config pathways/studies/my_study/configs/fgsea.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/studies/my_study/configs/fgsea.yml --allow-missing-package --json
python3 scripts/check_fgsea_study_dossier.py --config pathways/studies/my_study/configs/fgsea.yml --write --json
```

4. When the study profile is ready, promote it to the active figure-backed profile:

```bash
python3 scripts/activate_fgsea_profile.py --config pathways/studies/my_study/configs/fgsea.yml --json
```

The active profile always writes to `pathways/results/active_fgsea/`, which is the default generated input consumed by `figure_05_pathway_enrichment_dot`.

Each study can also write a tracked `results/study_dossier.{json,md}` artifact so collaborators can review the raw DE input, rank-prep summary, fgsea status, and figure provenance without tracing multiple files by hand.

A tracked starter template is available at:

- `pathways/studies/rnaseq_case_control_template/`
