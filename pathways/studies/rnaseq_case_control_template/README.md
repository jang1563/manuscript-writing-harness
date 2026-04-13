# rnaseq_case_control_template

This tracked template shows how to prepare a study-local preranked enrichment profile without disturbing the active fgsea profile too early.
The bundled demo inputs intentionally encode a simple synthetic signal:

- interferon-response genes are upregulated
- antigen-presentation genes are upregulated
- cell-cycle genes are downregulated

That makes the template useful both as a schema example and as a positive-control fgsea run.

Intended use:

1. Copy or rename this template into a study-specific directory.
2. Replace the placeholder raw differential-expression table under `inputs/raw/` with your real DESeq2/edgeR/limma-style results.
3. Adjust `configs/rank_prep.yml` if your source columns differ from the default DESeq2-style mapping.
4. Prepare the canonical `gene,stat` prerank CSV.
5. Replace the placeholder GMT with the pathway collection you want to use.
6. Validate and run the profile locally.
7. Activate it only when you want `figure_05_pathway_enrichment_dot` to consume the study-backed export.

Recommended commands:

- `python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/rnaseq_case_control_template/configs/rank_prep.yml --json`
- `python3 scripts/fgsea_pipeline.py validate --config pathways/studies/rnaseq_case_control_template/configs/fgsea.yml --json`
- `python3 scripts/fgsea_pipeline.py run --config pathways/studies/rnaseq_case_control_template/configs/fgsea.yml --allow-missing-package --json`
- `python3 scripts/activate_fgsea_profile.py --config pathways/studies/rnaseq_case_control_template/configs/fgsea.yml --json`

Default raw-input assumptions:

- source tool: `deseq2`
- expected columns: `gene`, `log2FoldChange`, `padj`

Expected canonical ranks contract:

- `gene`
- `stat`

Expected figure-export contract after the run:

- `pathway`
- `gene_ratio`
- `neg_log10_fdr`
- `gene_count`
- `direction`
- `highlight_order`
