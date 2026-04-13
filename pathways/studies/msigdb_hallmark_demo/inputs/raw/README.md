# Raw Differential-Expression Input

Place your DESeq2/edgeR/limma-style study results in this directory before preparing fgsea ranks.

Default expected file: `msigdb_hallmark_demo_differential_expression.csv`

The default rank-prep config assumes DESeq2-style columns:

- `gene`
- `log2FoldChange`
- `padj`

Edit `configs/rank_prep.yml` if your source table uses different column names.
