# AI/ML Professional Figures

This guide prepares the figure layer for AI-for-science and AI/ML paper conventions.

## Goals

- support top-conference and high-end methods-paper figure patterns
- make model-comparison figures readable at single-column and double-column widths
- preserve uncertainty, calibration, and ablation evidence rather than only headline metrics
- keep figures claim-backed and source-data-backed like the rest of the manuscript system

## Default visual rules

- use one visual channel for model identity and a different one for split, domain, or uncertainty
- do not encode more than one semantic dimension with color alone
- prefer compact legends for many models and direct labels only when the comparison set is small
- keep axis titles short and metric names canonical, for example `AUROC`, `AUPRC`, `ECE`, `Brier score`
- include confidence intervals, bootstrap intervals, or repeated-seed variation when performance claims depend on stability

## Figure classes to prioritize

- ROC/PR compound figures
- calibration and reliability diagrams
- confusion matrices with normalized rates
- training-dynamics panels for optimization behavior
- feature-importance or attribution summaries
- ablation summaries
- uncertainty and abstention curves
- embedding projections only when the narrative depends on representation geometry

## Common traps

- plotting ROC alone for imbalanced problems without PR
- hiding calibration when probabilistic predictions are central to the paper
- comparing many methods with visually indistinguishable colors
- annotating every point or every run in dense optimization curves
- using t-SNE or UMAP projections without clarifying what the geometry should and should not imply

## Figure-Layer Implications

- every AI/ML figure class should declare canonical metric ordering and naming
- manifests should record whether uncertainty, calibration, or repeated-seed evidence is shown
- review checklists should ask whether the figure supports deployment-relevant claims or only leaderboard claims
- future AI/ML classes should default to the `ai_ml_professional` style profile
- the first implemented AI/ML class in this figure layer is `roc_pr_compound`, which sets the expected pattern for paired ROC/PR evaluation with uncertainty and operating points
- `embedding_projection` should pair representation geometry with domain-support context so projections do not overclaim separation by eye alone
- `uncertainty_abstention_curve` should pair risk reduction with retained coverage so selective-prediction claims do not hide excessive abstention
