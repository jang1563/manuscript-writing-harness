# Pathway Results

Generated `fgsea` outputs are written under this directory and are intentionally gitignored, except for this README.

For the tracked profiles, the expected output directories are:

- `pathways/results/demo_fgsea/`
- `pathways/results/active_fgsea/`

Typical outputs:

- `fgsea_summary.json`
- `fgsea_results.csv`
- `fgsea_pathway_dot_export.csv`

The dot-export CSV is designed to match the pathway figure contract used by the pathway-enrichment dot plot figure class.

The active profile is the one consumed by `figure_05_pathway_enrichment_dot` during `build_phase2.py`.
