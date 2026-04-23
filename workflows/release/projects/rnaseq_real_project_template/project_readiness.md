# Project Release Readiness: rnaseq_real_project_template

- title: `RNA-seq Real Project Template`
- release_profile_id: `rnaseq_real_project_template_release`
- study_id: `msigdb_hallmark_demo`
- readiness: `provisional`
- venue_id: `nature`

## Pathway Strategy

- provider: `msigdb`
- species: `human`
- collection: `H`
- version: `2026.1.Hs`
- identifier_type: `gene_symbol`

## Study Status

- study readiness: `provisional`
- active source: `False`
- figure_05 sync: `inactive`
- fgsea result_count: `n/a`
- fgsea figure_export_count: `n/a`

## Warnings

- rank preparation is ready; add the licensed MSigDB GMT to move this profile to ready
- pathways_gmt not found: pathways/studies/msigdb_hallmark_demo/inputs/msigdb/msigdb_hallmark_demo_H_2026.1.Hs_gene_symbol.gmt
- MSigDB GMT not found at pathways_gmt; download the licensed GMT and place it at the configured path
- release_metadata.creators[1].name still contains a placeholder
- release_metadata.creators[1].affiliation still contains a placeholder
- licensed MSigDB GMT has not been placed at the expected study path
- project study profile is not the active fgsea source yet

## Next Steps

- `python3 scripts/run_msigdb_profile.py --config pathways/studies/msigdb_hallmark_demo/configs/fgsea.yml --prepare-ranks --build-phase2 --json`
- `python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json`
