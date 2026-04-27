### Response trajectory separates early kinetics and endpoint shift

The treated condition separates from control over time, with a larger mean normalized signal visible by the 4- and 6-hour measurements. This pattern is shown directly in `figure_01_example`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Tie the early trajectory and endpoint claims together as one response-pattern result.

### Condition drives primary sample separation

The primary sample separation occurs along PC1, where treatment samples occupy positive scores and control samples occupy negative scores while batch remains secondary. This pattern is shown directly in `figure_04_sample_pca`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. State the sample-level separation before moving into gene-level contrasts.

### High-abundance genes show an interferon-skewed shift

Highly expressed interferon-response genes remain positively shifted in the MA plot, while negative fold changes cluster among proliferation-associated genes. This pattern is shown directly in `figure_03_ma_plot`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Keep the interpretation close to the abundance-dependent differential-expression display.

### Interferon activation coincides with cell-cycle suppression

The strongest positive differential-expression signals cluster in interferon-associated genes including CXCL10, IFIT1, and MX1, which exceed both the fold-change and false-discovery thresholds. This pattern is shown directly in `figure_02_volcano_pathway`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Present the activated and suppressed programs as one coordinated biological contrast.

### Pathway effect sizes preserve biological directionality

Pathways with larger gene ratios and stronger significance annotations are directionally consistent with the upregulated immune processes and downregulated cell-cycle programs, and the panel can be sourced directly from the active fgsea export rather than a hand-maintained summary table. The fgsea-derived dot-plot export therefore acts as the downstream pathway summary of the ranked-expression analysis, preserving both effect magnitude and biological directionality in a format that stays aligned with the upstream gene-level figures.

### Foundation-model discrimination remains strong under imbalance

The foundation model yields the strongest ROC profile and the highest AUROC, maintaining higher true-positive rate than the comparator models across clinically relevant false-positive rates. This pattern is shown directly in `figure_06_roc_pr_compound`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Combine discrimination and imbalanced precision evidence into a single model-performance result.

### Calibration improves without relying only on tail confidence

The foundation model tracks the identity line more closely than the comparator models across confidence bins and has the lowest expected calibration error. This pattern is shown directly in `figure_07_calibration_reliability`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Tie calibration quality to the high-confidence support pattern.

### Optimization is stable and reaches higher validation AUROC

The foundation model shows the lowest validation loss with minimal late-epoch divergence from training loss, indicating the most stable optimization profile among the compared models. This pattern is shown directly in `figure_08_training_dynamics`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Connect stable optimization behavior with the validation AUROC trajectory.

### Errors localize to adjacent states while terminal states stay distinct

Residual classifier errors are concentrated between inflammatory and proliferative states rather than being broadly distributed across all labels, indicating local ambiguity instead of global label collapse. This pattern is shown directly in `figure_09_confusion_matrix_normalized`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Describe the confusion-matrix pattern as structured error rather than diffuse failure.

### Feature attribution highlights biologically salient and directionally coherent signals

The highest-ranked features are fibrosis, inflammatory, proliferative, and interferon-related programs, while nuisance covariates such as batch score remain much lower in importance. This pattern is shown directly in `figure_10_feature_importance_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Pair salience and signed directionality while avoiding claims beyond the attribution display.

### Context encoding and fusion drive performance more than calibration loss

Removing the context encoder or multi-scale fusion causes the largest AUROC drops, indicating that architectural context integration is the main driver of top-line discrimination. This pattern is shown directly in `figure_11_ablation_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Separate primary performance drivers from probability-quality effects.

### Embedding structure preserves state organization with cross-domain support

The projection organizes quiescent, inflammatory, proliferative, and fibrotic samples into compact regions with density-aware direct labels rather than relying on a detached legend alone. This pattern is shown directly in `figure_12_embedding_projection`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Connect state separation in the projection with cross-domain support fractions.

### Uncertainty-guided abstention reduces risk while preserving coverage

Risk declines monotonically as lower-confidence predictions are abstained, with operating points marked at 80% coverage for each model. This pattern is shown directly in `figure_13_uncertainty_abstention_curve`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Tie the risk-coverage curve to retained coverage at the target risk threshold.

### Aggregate model ranking favors the foundation model

The highest-ranked model by AUROC appears first after deterministic sorting, preserving a reproducible performance ordering. This pattern is shown directly in `table_01_main`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced. Use the table as the compact ranking summary rather than introducing new evidence.
