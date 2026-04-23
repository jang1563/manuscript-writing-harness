# rnaseq_real_project_template

This tracked template demonstrates how to onboard a real MSigDB-backed project without touching the clean demo release profile.

It is intentionally `provisional`:

- the linked study profile still uses scaffold-style raw differential-expression input
- the licensed MSigDB GMT has not been placed yet
- the release metadata in `workflows/release/profiles/profiles.yml` still contains placeholders
- the release policy in `workflows/release/policies/rnaseq_real_project_template.yml` still contains onboarding placeholders

Use this template as a reference for the expected project-level handoff:

```bash
python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json
python3 scripts/check_anonymized_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_project_handoff.py --project rnaseq_real_project_template --write --json
```

After filling real metadata and real study inputs, rerun:

```bash
python3 scripts/run_msigdb_profile.py \
  --config pathways/studies/msigdb_hallmark_demo/configs/fgsea.yml \
  --prepare-ranks \
  --build-phase2 \
  --json
```
