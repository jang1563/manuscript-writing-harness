# Project Handoff: rnaseq_real_project_template

- title: `RNA-seq Real Project Template`
- release_profile_id: `rnaseq_real_project_template_release`
- readiness: `provisional`
- project_readiness: `provisional`
- policy_readiness: `provisional`
- anonymized_preview: `provisional`

## Warnings

- MSigDB GMT not found at pathways_gmt; download the licensed GMT and place it at the configured path
- deposit_contact still contains a placeholder
- licensed MSigDB GMT has not been placed at the expected study path
- manuscript_identity_scrubbed is not yet confirmed for anonymized review
- metadata_identity_scrubbed is not yet confirmed for anonymized review
- msigdb_license_confirmed is not yet true for an MSigDB-backed project
- pathways_gmt not found: pathways/studies/msigdb_hallmark_demo/inputs/msigdb/msigdb_hallmark_demo_H_2026.1.Hs_gene_symbol.gmt
- project study profile is not the active fgsea source yet
- rank preparation is ready; add the licensed MSigDB GMT to move this profile to ready
- release_metadata.creators[1].affiliation still contains a placeholder
- release_metadata.creators[1].name still contains a placeholder
- supplement_identity_scrubbed is not yet confirmed for anonymized review

## Next Steps

- `python3 scripts/run_msigdb_profile.py --config pathways/studies/msigdb_hallmark_demo/configs/fgsea.yml --prepare-ranks --build-phase2 --json`
- `python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json`
- `python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json`
- `python3 scripts/check_anonymized_release.py --project rnaseq_real_project_template --write --json`
