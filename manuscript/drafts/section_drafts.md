# Section Draft Scaffolds

- overall_status: `ready`
- section_count: `5`
- ready_section_count: `5`
- provisional_section_count: `0`
- blocked_section_count: `0`

## summary

- status: `ready`
- source: `manuscript/sections/01_summary.md`
- recommended_opening: Use one compact paragraph that names the question, the system, and the single strongest finding.
- topic: not set
- display_item_ids: `none`

### Subsection Plan

- paragraph 1: Name the scientific problem and study framing in one sentence.
- paragraph 2: State only the strongest display-backed result and keep it concrete.
- paragraph 3: Close with one sentence on why the finding matters.

## introduction

- status: `ready`
- source: `manuscript/sections/02_introduction.md`
- recommended_opening: Use 2 to 3 paragraphs: context, gap, then objective.
- topic: not set
- display_item_ids: `none`

### Subsection Plan

- paragraph 1: Open with the broader biological or modeling problem.
- paragraph 2: Describe the gap that existing methods or studies leave unresolved.
- paragraph 3: End with the exact study objective and what the manuscript contributes.

## results

- status: `ready`
- source: `manuscript/sections/03_results.md`
- recommended_opening: Use one subsection per display-backed claim cluster, following manuscript display order.
- topic: not set
- display_item_ids: `figure_01_example, figure_04_sample_pca, figure_03_ma_plot, figure_02_volcano_pathway, figure_05_pathway_enrichment_dot, figure_06_roc_pr_compound, figure_07_calibration_reliability, figure_08_training_dynamics, figure_09_confusion_matrix_normalized, figure_10_feature_importance_summary, figure_11_ablation_summary, table_01_main`

### Subsection Plan

- `claim_response_kinetics` via `figure_01_example`: The treated condition separates from control over time, with a larger mean normalized signal visible by the 4- and 6-hour measurements.
- `claim_endpoint_shift` via `figure_01_example`: At 6 hours, the treated condition has a higher endpoint response than control, and the replicate-level points show the effect is not driven by a single sample.
- `claim_condition_drives_primary_sample_separation` via `figure_04_sample_pca`: The primary sample separation occurs along PC1, where treatment samples occupy positive scores and control samples occupy negative scores while batch remains secondary.
- `claim_high_abundance_interferon_shift` via `figure_03_ma_plot`: Highly expressed interferon-response genes remain positively shifted in the MA plot, while negative fold changes cluster among proliferation-associated genes.
- `claim_interferon_gene_activation` via `figure_02_volcano_pathway`: The strongest positive differential-expression signals cluster in interferon-associated genes including CXCL10, IFIT1, and MX1, which exceed both the fold-change and false-discovery thresholds.
- `claim_cell_cycle_pathway_suppression` via `figure_02_volcano_pathway`: Negative enrichment scores for cell-cycle checkpoint, mitotic spindle, and DNA replication indicate coordinated suppression of proliferative programs relative to the upregulated immune-response pathways.
- `claim_pathway_effect_sizes_align_with_directionality` via `figure_05_pathway_enrichment_dot`: Pathways with larger gene ratios and stronger significance annotations are directionally consistent with the upregulated immune processes and downregulated cell-cycle programs, and the panel can be sourced directly from the active fgsea export rather than a hand-maintained summary table.
- `claim_foundation_model_improves_discrimination` via `figure_06_roc_pr_compound`: The foundation model yields the strongest ROC profile and the highest AUROC, maintaining higher true-positive rate than the comparator models across clinically relevant false-positive rates.
- `claim_foundation_model_retains_precision_under_imbalance` via `figure_06_roc_pr_compound`: Under class imbalance, the foundation model preserves precision better than the comparator models across the recall range and remains far above the prevalence baseline, yielding the highest AUPRC.
- `claim_foundation_model_best_calibrated` via `figure_07_calibration_reliability`: The foundation model tracks the identity line more closely than the comparator models across confidence bins and has the lowest expected calibration error.
- `claim_high_confidence_support_is_not_tail_only` via `figure_07_calibration_reliability`: The high-confidence calibration conclusion is supported by non-trivial prediction mass across upper-confidence bins rather than a sparse extreme tail.
- `claim_foundation_model_optimizes_stably` via `figure_08_training_dynamics`: The foundation model shows the lowest validation loss with minimal late-epoch divergence from training loss, indicating the most stable optimization profile among the compared models.
- `claim_foundation_model_reaches_higher_validation_auroc` via `figure_08_training_dynamics`: The foundation model improves validation AUROC faster and plateaus at the highest level, while the comparator models saturate earlier at lower performance.
- `claim_errors_are_localized_to_adjacent_states` via `figure_09_confusion_matrix_normalized`: Residual classifier errors are concentrated between inflammatory and proliferative states rather than being broadly distributed across all labels, indicating local ambiguity instead of global label collapse.
- `claim_terminal_states_remain_distinct` via `figure_09_confusion_matrix_normalized`: Healthy and fibrotic states retain the strongest diagonal mass, indicating that terminal phenotypes remain well separated even when intermediate inflammatory and proliferative states are occasionally confused.
- `claim_model_relies_on_biologically_salient_features` via `figure_10_feature_importance_summary`: The highest-ranked features are fibrosis, inflammatory, proliferative, and interferon-related programs, while nuisance covariates such as batch score remain much lower in importance.
- `claim_signed_feature_effects_align_with_domain_expectation` via `figure_10_feature_importance_summary`: The dominant feature effects point in biologically coherent directions: fibrosis, inflammatory, and interferon signals increase predicted response, while proliferative activity suppresses it.
- `claim_context_encoder_and_fusion_drive_primary_performance` via `figure_11_ablation_summary`: Removing the context encoder or multi-scale fusion causes the largest AUROC drops, indicating that architectural context integration is the main driver of top-line discrimination.
- `claim_calibration_loss_mainly_affects_probability_quality` via `figure_11_ablation_summary`: Removing the calibration loss causes only a modest AUROC drop but the largest increase in calibration error, indicating that this objective contributes more to probability quality than to raw discrimination.
- `claim_model_ranking` via `table_01_main`: The highest-ranked model by AUROC appears first after deterministic sorting, preserving a reproducible performance ordering.

## discussion

- status: `ready`
- source: `manuscript/sections/04_discussion.md`
- recommended_opening: Use 3 paragraphs: interpretation, comparison/limitations, then forward-looking implication.
- topic: not set
- display_item_ids: `none`

### Subsection Plan

- paragraph 1: Interpret the strongest results without repeating the Results text verbatim.
- paragraph 2: Compare to literature only where citation coverage is explicit and available.
- paragraph 3: Name limitations and next-step implications separately.

## methods

- status: `ready`
- source: `manuscript/sections/05_methods.md`
- recommended_opening: Use reproducibility-first ordering: data provenance, analysis pipeline, then runtime/export details.
- topic: not set
- display_item_ids: `none`

### Subsection Plan

- paragraph 1: Describe datasets, cohorts, or inputs and where they came from.
- paragraph 2: Describe the analysis/modeling pipeline in execution order.
- paragraph 3: Close with reproducibility assets, figure/table generation, and software/runtime details.
