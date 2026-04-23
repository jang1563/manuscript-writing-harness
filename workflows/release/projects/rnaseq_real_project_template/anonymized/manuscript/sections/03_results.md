## Results

This section demonstrates the intended display-item-backed writing pattern for the multi-agent manuscript system.

The standalone demonstration figure and table remain directly embedded below. Bundle-managed figure sets are injected only inside the managed block so repeated `apply-bundles --all` runs can refresh the Results flow without overwriting surrounding prose.

Within the bulk-omics bundle, the evidence path now runs from sample-level separation to gene-level differential-expression summaries and then into an fgsea-backed pathway export, so the pathway dot plot is no longer a disconnected illustration but the downstream summary of a tracked enrichment step.

### Claim 1. Treatment-associated response kinetics diverge over time

The treated condition separates from control over time, and by the late measurements the gap is visually obvious without requiring the reader to decode a detached legend. The key evidence is carried by the multi-panel figure, with panel a showing the time-course divergence and panel b preserving replicate-level endpoint observations.

```{include} ../display_items/figure_01_example.md.txt
```

<!-- BUNDLE_MANAGED_BLOCK_START -->

```{include} ../display_items/_bundles/bundle_bulk_omics_deg_exemplar.md.txt
```

```{include} ../display_items/_bundles/bundle_ai_ml_evaluation_exemplar.md.txt
```

<!-- BUNDLE_MANAGED_BLOCK_END -->




### Claim 9. Deterministic tabular outputs should preserve the evidence path behind ranking claims

The example table shows how an artifact-driven multi-agent manuscript system should present ranked model-performance summaries: the ordering is deterministic, the JSON output remains machine-readable, and the fact sheet captures the specific claim the table is expected to support.

```{include} ../display_items/table_01_main.md.txt
```

Working rules for this section:

1. state the result claim
2. point to the supporting figure or table
3. provide only the necessary interpretation

Do not bury key quantitative evidence only inside legends or supplementary files.

Planning artifacts that should stay aligned with this section:

- `manuscript/plans/display_item_map.json`
- `figures/bundles/bundle_bulk_omics_deg_exemplar/bundle.yml`
- `figures/bundles/bundle_ai_ml_evaluation_exemplar/bundle.yml`
- `figures/fact_sheets/figure_01_example.json`
- `tables/fact_sheets/table_01_main.json`
