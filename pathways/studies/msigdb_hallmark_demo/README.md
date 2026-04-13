# msigdb_hallmark_demo

This study profile is scaffolded for an MSigDB-backed fgsea run using collection `H` (human, 2026.1.Hs).

Steps:

1. Replace the placeholder raw differential-expression table under `inputs/raw/` with your real study results.
2. Run `python3 scripts/prepare_fgsea_ranks.py --config pathways/studies/msigdb_hallmark_demo/configs/rank_prep.yml --json`.
3. Download the MSigDB GMT for this collection and place it at `pathways/studies/msigdb_hallmark_demo/inputs/msigdb/msigdb_hallmark_demo_H_2026.1.Hs_gene_symbol.gmt`.
4. Validate and run the profile locally.
5. Activate it only when you want the pathway figure layer to use this study profile.
