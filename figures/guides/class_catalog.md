# Figure Library Catalog

- implemented classes: `13`
- figure instances: `13`

## ablation_summary

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel ablation figure combining primary-metric drops with secondary-metric shifts to justify architectural and training design choices.

Required inputs:
- `ablation_primary_metrics` (csv): variant, module_group, display_order, auroc, delta_auroc, label_variant
- `ablation_secondary_metrics` (csv): variant, module_group, display_order, metric, delta_value, label_variant

Instances:
- `figure_11_ablation_summary`: Ablation summary for architectural and training design choices (style `ai_ml_professional`, parity `dual`)

## calibration_reliability

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel calibration figure combining a reliability diagram with calibration-support distribution across confidence bins.

Required inputs:
- `calibration_bins` (csv): model, display_order, bin_center, mean_predicted, observed_rate, observed_lower, observed_upper, sample_fraction, sample_count, label_bin
- `metric_summary` (csv): model, display_order, ece, max_calibration_gap, brier_score

Instances:
- `figure_07_calibration_reliability`: Calibration reliability and confidence support for AI/ML models (style `ai_ml_professional`, parity `dual`)

## confusion_matrix_normalized

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel error-analysis figure combining a row-normalized confusion matrix with an off-diagonal confusion summary.

Required inputs:
- `confusion_matrix` (csv): true_label, predicted_label, true_order, pred_order, rate, count, label_cell, is_diagonal
- `off_diagonal_summary` (csv): source_class, target_class, error_rate, display_order, label_text

Instances:
- `figure_09_confusion_matrix_normalized`: Normalized confusion structure and dominant error pathways for phenotype classification (style `ai_ml_professional`, parity `dual`)

## embedding_projection

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel representation figure combining a density-aware embedding projection with state-level cross-domain support.

Required inputs:
- `embedding_coordinates` (csv): sample_id, biological_state, domain, embedding_1, embedding_2, local_density, highlight_label
- `cluster_summary` (csv): biological_state, centroid_x, centroid_y, display_order, sample_count, cross_domain_fraction, label_cluster

Instances:
- `figure_12_embedding_projection`: Embedding projection with representation structure and domain support (style `ai_ml_professional`, parity `dual`)

## feature_importance_summary

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel interpretation figure combining ranked feature importance with signed directional effects for domain-aligned model interpretation.

Required inputs:
- `ranked_feature_importance` (csv): feature, feature_group, display_order, mean_abs_importance, label_feature
- `signed_feature_effects` (csv): feature, feature_group, display_order, signed_effect, expected_direction, label_feature

Instances:
- `figure_10_feature_importance_summary`: Feature importance rank and directional effects for model interpretation (style `ai_ml_professional`, parity `dual`)

## ma_plot

- family: `bulk_omics`
- expertise: `bioinformatics`
- status: `implemented`
- style profile: `bulk_omics_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Single-panel mean-abundance versus log-fold-change figure with selective labels.

Required inputs:
- `ma_points` (csv): gene, mean_expression, log2_fc, padj, highlight_label

Instances:
- `figure_03_ma_plot`: Mean-abundance differential-signal summary (style `bulk_omics_professional`, parity `dual`)

## pathway_enrichment_dot

- family: `bulk_omics`
- expertise: `bioinformatics`
- status: `implemented`
- style profile: `bulk_omics_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Single-panel pathway enrichment dot plot using gene ratio, significance, and direction.

Required inputs:
- `pathway_enrichment` (csv): pathway, gene_ratio, neg_log10_fdr, gene_count, direction, highlight_order

Instances:
- `figure_05_pathway_enrichment_dot`: Pathway-enrichment dot-plot overview (style `bulk_omics_professional`, parity `dual`)

## roc_pr_compound

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel model-evaluation figure combining ROC and precision-recall curves with uncertainty bands and operating points.

Required inputs:
- `performance_curves` (csv): model, panel, x, y, y_lower, y_upper, operating_point
- `metric_summary` (csv): model, display_order, auroc, auprc, ece, brier_score, prevalence

Instances:
- `figure_06_roc_pr_compound`: ROC and precision-recall evaluation of AI/ML models (style `ai_ml_professional`, parity `dual`)

## sample_pca

- family: `bulk_omics`
- expertise: `bioinformatics`
- status: `implemented`
- style profile: `bulk_omics_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Single-panel principal-component scatter plot for sample-level separation.

Required inputs:
- `sample_scores` (csv): sample_id, condition, batch, pc1, pc2, highlight_label

Instances:
- `figure_04_sample_pca`: Sample-level principal component separation (style `bulk_omics_professional`, parity `dual`)

## timecourse_endpoint

- family: `bulk_omics`
- expertise: `bioinformatics`
- status: `implemented`
- style profile: `bulk_omics_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel longitudinal response figure with a time-course trend panel and endpoint summary.

Required inputs:
- `measurements` (csv): timepoint_hours, condition, replicate, response

Instances:
- `figure_01_example`: Example multi-panel response figure (style `bulk_omics_professional`, parity `dual`)

## training_dynamics

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel optimization figure combining loss trajectories with validation metric dynamics across epochs.

Required inputs:
- `loss_history` (csv): model, display_order, epoch, split, loss
- `validation_metric_history` (csv): model, display_order, epoch, auroc, label_epoch, best_epoch

Instances:
- `figure_08_training_dynamics`: Training and validation dynamics for AI/ML models (style `ai_ml_professional`, parity `dual`)

## uncertainty_abstention_curve

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- status: `implemented`
- style profile: `ai_ml_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel selective-prediction figure combining coverage-risk curves with target-risk retained-coverage summaries.

Required inputs:
- `coverage_risk_curves` (csv): model, display_order, coverage, risk, risk_lower, risk_upper, operating_point
- `abstention_summary` (csv): model, display_order, risk_at_full_coverage, risk_at_80_coverage, coverage_at_target_risk, abstained_fraction_at_target, label_model

Instances:
- `figure_13_uncertainty_abstention_curve`: Uncertainty-guided abstention and coverage-risk behavior (style `ai_ml_professional`, parity `dual`)

## volcano_pathway_compound

- family: `bulk_omics`
- expertise: `bioinformatics`
- status: `implemented`
- style profile: `bulk_omics_professional`
- renderers: `python, r`
- instance count: `1`
- intent: Two-panel omics figure combining a differential-expression volcano plot and a signed pathway summary.

Required inputs:
- `differential_expression` (csv): gene, log2_fc, padj, highlight_label
- `pathway_enrichment` (csv): pathway, nes, fdr, direction, highlight_order

Instances:
- `figure_02_volcano_pathway`: Differential expression and pathway-enrichment landscape (style `bulk_omics_professional`, parity `dual`)
