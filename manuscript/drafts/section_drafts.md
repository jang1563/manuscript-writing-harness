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
- display_item_ids: `figure_01_example, figure_04_sample_pca, figure_03_ma_plot, figure_02_volcano_pathway, figure_05_pathway_enrichment_dot, figure_06_roc_pr_compound, figure_07_calibration_reliability, figure_08_training_dynamics, figure_09_confusion_matrix_normalized, figure_10_feature_importance_summary, figure_11_ablation_summary, figure_12_embedding_projection, figure_13_uncertainty_abstention_curve, table_01_main`

### Subsection Plan

- `cluster_response_trajectory` (Response trajectory separates early kinetics and endpoint shift) via `figure_01_example`: The treated condition separates from control over time, with a larger mean normalized signal visible by the 4- and 6-hour measurements.
- `cluster_sample_separation` (Condition drives primary sample separation) via `figure_04_sample_pca`: The primary sample separation occurs along PC1, where treatment samples occupy positive scores and control samples occupy negative scores while batch remains secondary.
- `cluster_abundance_shift` (High-abundance genes show an interferon-skewed shift) via `figure_03_ma_plot`: Highly expressed interferon-response genes remain positively shifted in the MA plot, while negative fold changes cluster among proliferation-associated genes.
- `cluster_interferon_and_cell_cycle` (Interferon activation coincides with cell-cycle suppression) via `figure_02_volcano_pathway`: The strongest positive differential-expression signals cluster in interferon-associated genes including CXCL10, IFIT1, and MX1, which exceed both the fold-change and false-discovery thresholds.
- `cluster_pathway_directionality` (Pathway effect sizes preserve biological directionality) via `figure_05_pathway_enrichment_dot`: Pathways with larger gene ratios and stronger significance annotations are directionally consistent with the upregulated immune processes and downregulated cell-cycle programs, and the panel can be sourced directly from the active fgsea export rather than a hand-maintained summary table.
- `cluster_discrimination_and_precision` (Foundation-model discrimination remains strong under imbalance) via `figure_06_roc_pr_compound`: The foundation model yields the strongest ROC profile and the highest AUROC, maintaining higher true-positive rate than the comparator models across clinically relevant false-positive rates.
- `cluster_calibration_and_confidence` (Calibration improves without relying only on tail confidence) via `figure_07_calibration_reliability`: The foundation model tracks the identity line more closely than the comparator models across confidence bins and has the lowest expected calibration error.
- `cluster_training_dynamics` (Optimization is stable and reaches higher validation AUROC) via `figure_08_training_dynamics`: The foundation model shows the lowest validation loss with minimal late-epoch divergence from training loss, indicating the most stable optimization profile among the compared models.
- `cluster_error_topology` (Errors localize to adjacent states while terminal states stay distinct) via `figure_09_confusion_matrix_normalized`: Residual classifier errors are concentrated between inflammatory and proliferative states rather than being broadly distributed across all labels, indicating local ambiguity instead of global label collapse.
- `cluster_feature_attribution` (Feature attribution highlights biologically salient and directionally coherent signals) via `figure_10_feature_importance_summary`: The highest-ranked features are fibrosis, inflammatory, proliferative, and interferon-related programs, while nuisance covariates such as batch score remain much lower in importance.
- `cluster_ablation_sensitivity` (Context encoding and fusion drive performance more than calibration loss) via `figure_11_ablation_summary`: Removing the context encoder or multi-scale fusion causes the largest AUROC drops, indicating that architectural context integration is the main driver of top-line discrimination.
- `cluster_embedding_structure` (Embedding structure preserves state organization with cross-domain support) via `figure_12_embedding_projection`: The projection organizes quiescent, inflammatory, proliferative, and fibrotic samples into compact regions with density-aware direct labels rather than relying on a detached legend alone.
- `cluster_uncertainty_abstention` (Uncertainty-guided abstention reduces risk while preserving coverage) via `figure_13_uncertainty_abstention_curve`: Risk declines monotonically as lower-confidence predictions are abstained, with operating points marked at 80% coverage for each model.
- `cluster_model_ranking` (Aggregate model ranking favors the foundation model) via `table_01_main`: The highest-ranked model by AUROC appears first after deterministic sorting, preserving a reproducible performance ordering.

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
