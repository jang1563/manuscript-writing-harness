# Project Release Scaffolds

This directory is for real-project onboarding on top of the demo multi-agent manuscript system.

Each project scaffold should contain:

- `project.yml`: project-level metadata, linked study id, release profile id, and MSigDB strategy
- `README.md`: human handoff instructions
- `project_readiness.json` / `project_readiness.md`: generated readiness reports

Recommended workflow:

```bash
python3 scripts/scaffold_project_release.py \
  --project-id my_project \
  --title "My Project Release" \
  --species human \
  --collection H \
  --json
```

Then:

1. Fill the scaffolded DE table under `pathways/studies/<study_id>/inputs/raw/`.
2. Add the licensed MSigDB GMT under `pathways/studies/<study_id>/inputs/msigdb/`.
3. Run:

```bash
python3 scripts/run_msigdb_profile.py \
  --config pathways/studies/<study_id>/configs/fgsea.yml \
  --prepare-ranks \
  --build-phase2 \
  --json
```

4. Replace the placeholder release metadata in `workflows/release/profiles/profiles.yml`.
5. Review and update the project policy file under `workflows/release/policies/`.
5. Review project readiness:

```bash
python3 scripts/check_project_release.py --project my_project --write --json
python3 scripts/check_release_policy.py --project my_project --write --json
python3 scripts/check_anonymized_release.py --project my_project --write --json
python3 scripts/check_project_handoff.py --project my_project --write --json
```
