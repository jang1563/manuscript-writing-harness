# Raw Differential-Expression Input

Place your DESeq2/edgeR/limma-style results table in this directory.

Default expected file: `rnaseq_case_control_template_differential_expression.csv`

The default rank-prep config assumes DESeq2-style columns:

- `gene`
- `log2FoldChange`
- `padj`

Edit `configs/rank_prep.yml` if your source table uses different names.
