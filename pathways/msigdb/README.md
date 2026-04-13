# MSigDB Integration

This directory documents how to use locally downloaded MSigDB gene sets with the fgsea pathway branch.

Important constraints:

- MSigDB downloads require registration under the official MSigDB license terms.
- This repo does not vendor official MSigDB GMT files.
- The intended workflow is to download the GMT locally, place it into a study profile under `pathways/studies/<study_id>/inputs/msigdb/`, validate the config, and then activate that profile.

Recommended collections in this harness:

- `H` / `MH`: compact first-pass biology summaries
- `C2:CP` / `M2:CP`: curated canonical pathways
- `C5:BP` / `M5:BP`: broad biological-process enrichment
- `C7` / `M7`: immune-state and perturbation analyses

Suggested workflow:

1. Scaffold an MSigDB-backed study profile.

```bash
python3 scripts/scaffold_msigdb_profile.py \
  --study-id my_study \
  --species human \
  --collection H \
  --version 2026.1.Hs \
  --identifier-type gene_symbol \
  --json
```

2. Place the downloaded MSigDB GMT at the expected path inside the scaffolded study directory.

3. Validate and run the profile:

```bash
python3 scripts/fgsea_pipeline.py validate --config pathways/studies/my_study/configs/fgsea.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/studies/my_study/configs/fgsea.yml --allow-missing-package --json
```

4. Activate the study profile when you want the pathway figure layer to use it:

```bash
python3 scripts/activate_fgsea_profile.py --config pathways/studies/my_study/configs/fgsea.yml --json
```

Or run the whole MSigDB handoff in one step:

```bash
python3 scripts/run_msigdb_profile.py \
  --config pathways/studies/my_study/configs/fgsea.yml \
  --prepare-ranks \
  --build-phase2 \
  --json
```

That command prepares ranks from the raw DE table when `configs/rank_prep.yml` is present, validates the licensed GMT drop-in, promotes the study into `pathways/configs/fgsea_active.yml`, refreshes the active fgsea export, and writes both a study-level provenance report and a study dossier.
