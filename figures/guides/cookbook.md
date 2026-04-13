# Figure Recipe Cookbook

- recipes: `2`

## ai_ml_evaluation_story

- family: `ai_ml_professional`
- expertise: `ai_for_science`
- figure count: `6`
- intent: Professional AI/ML evaluation bundle covering discrimination, calibration, optimization, failure modes, interpretation, and ablation.

Recommended sequence:
- `discrimination` -> `roc_pr_compound`: Primary model discrimination and class-imbalance evaluation
- `calibration` -> `calibration_reliability`: Probability calibration and confidence support
- `optimization` -> `training_dynamics`: Training stability and convergence behavior
- `error_modes` -> `confusion_matrix_normalized`: Structured failure-mode inspection
- `interpretation` -> `feature_importance_summary`: Feature-level interpretation summary
- `design_justification` -> `ablation_summary`: Ablation support for architectural and training choices

Notes:
- Use this when the paper needs a top-conference or methods-paper evaluation arc.
- At minimum, discrimination and calibration should appear together for probabilistic models.

## bulk_omics_deg_story

- family: `bulk_omics`
- expertise: `bioinformatics`
- figure count: `4`
- intent: Core RNA-seq or proteomics differential-signal story that moves from sample structure to differential signal to pathway interpretation.

Recommended sequence:
- `sample_structure` -> `sample_pca`: QC and cohort-separation overview
- `ma_overview` -> `ma_plot`: Global differential-signal overview
- `de_pathway_story` -> `volcano_pathway_compound`: Main differential-expression and pathway interpretation figure
- `pathway_focus` -> `pathway_enrichment_dot`: Focused pathway-enrichment follow-up

Notes:
- Use this when the paper narrative is sample QC -> DE signal -> pathway interpretation.
- The volcano-pathway compound figure is usually the main Results figure in this bundle.
