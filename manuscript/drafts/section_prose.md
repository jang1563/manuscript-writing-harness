# Section Prose Drafts

- overall_status: `ready`
- section_count: `5`

## Summary

We set out to test whether an artifact-driven multi-agent manuscript system, built on a deterministic harness substrate, can keep biological and AI/ML claims tightly bound to the figures, tables, and planning artifacts that support them.

Across the current example assets, the strongest display-backed findings include treatment-associated response divergence, interferon-skewed differential expression, and pathway-level directionality recovered through a reproducible fgsea export in the biological track, together with consistently better discrimination, calibration, and training stability in the foundation-model evaluation track.

Together, these outputs show how the manuscript system can surface result-ready claims before polishing narrative prose, while keeping figure provenance, pathway-analysis artifacts, and reference readiness visible as drafting constraints rather than hidden cleanup tasks.

## Introduction

Scientific manuscripts often lose traceability when the prose, figures, tables, pathway-analysis outputs, and literature context evolve separately. That problem becomes more acute when a project spans both bioinformatics-style evidence summaries and AI/ML model-evaluation figures, because the writing layer can drift away from the display items that actually carry the claim.

The present manuscript system is designed to reduce that drift by making planning artifacts, figure specifications, fact sheets, evidence summaries, citation graphs, and generated analysis exports explicit. Instead of asking the writer to reconstruct the evidence path from memory, it keeps display-backed claims visible at drafting time and exposes whether pathway summaries, review evidence, and citations are already ready.

Within that framing, the manuscript objective is not only to present biological and model-evaluation results but also to demonstrate a reproducible writing workflow in which figure bundles, evidence packages, fgsea-derived pathway summaries, and citation coverage remain inspectable throughout drafting.

## Results

### Response kinetics

The treated condition separates from control over time, with a larger mean normalized signal visible by the 4- and 6-hour measurements. This pattern is shown directly in `figure_01_example`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Endpoint shift

At 6 hours, the treated condition has a higher endpoint response than control, and the replicate-level points show the effect is not driven by a single sample. This pattern is shown directly in `figure_01_example`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Condition drives primary sample separation

The primary sample separation occurs along PC1, where treatment samples occupy positive scores and control samples occupy negative scores while batch remains secondary. This pattern is shown directly in `figure_04_sample_pca`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### High abundance interferon shift

Highly expressed interferon-response genes remain positively shifted in the MA plot, while negative fold changes cluster among proliferation-associated genes. This pattern is shown directly in `figure_03_ma_plot`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Interferon gene activation

The strongest positive differential-expression signals cluster in interferon-associated genes including CXCL10, IFIT1, and MX1, which exceed both the fold-change and false-discovery thresholds. This pattern is shown directly in `figure_02_volcano_pathway`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Cell cycle pathway suppression

Negative enrichment scores for cell-cycle checkpoint, mitotic spindle, and DNA replication indicate coordinated suppression of proliferative programs relative to the upregulated immune-response pathways. Because these summaries come from the preranked fgsea branch rather than an ad hoc pathway annotation step, the pathway-level suppression reinforces that proliferative programs are coherently downregulated at the gene-set level and not only at isolated genes.

### Pathway effect sizes align with directionality

Pathways with larger gene ratios and stronger significance annotations are directionally consistent with the upregulated immune processes and downregulated cell-cycle programs, and the panel can be sourced directly from the active fgsea export rather than a hand-maintained summary table. The fgsea-derived dot-plot export therefore acts as the downstream pathway summary of the ranked-expression analysis, preserving both effect magnitude and biological directionality in a format that stays aligned with the upstream gene-level figures.

### Foundation model improves discrimination

The foundation model yields the strongest ROC profile and the highest AUROC, maintaining higher true-positive rate than the comparator models across clinically relevant false-positive rates. This pattern is shown directly in `figure_06_roc_pr_compound`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Foundation model retains precision under imbalance

Under class imbalance, the foundation model preserves precision better than the comparator models across the recall range and remains far above the prevalence baseline, yielding the highest AUPRC. This pattern is shown directly in `figure_06_roc_pr_compound`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Foundation model best calibrated

The foundation model tracks the identity line more closely than the comparator models across confidence bins and has the lowest expected calibration error. This pattern is shown directly in `figure_07_calibration_reliability`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### High confidence support is not tail only

The high-confidence calibration conclusion is supported by non-trivial prediction mass across upper-confidence bins rather than a sparse extreme tail. This pattern is shown directly in `figure_07_calibration_reliability`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Foundation model optimizes stably

The foundation model shows the lowest validation loss with minimal late-epoch divergence from training loss, indicating the most stable optimization profile among the compared models. This pattern is shown directly in `figure_08_training_dynamics`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Foundation model reaches higher validation auroc

The foundation model improves validation AUROC faster and plateaus at the highest level, while the comparator models saturate earlier at lower performance. This pattern is shown directly in `figure_08_training_dynamics`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Errors are localized to adjacent states

Residual classifier errors are concentrated between inflammatory and proliferative states rather than being broadly distributed across all labels, indicating local ambiguity instead of global label collapse. This pattern is shown directly in `figure_09_confusion_matrix_normalized`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Terminal states remain distinct

Healthy and fibrotic states retain the strongest diagonal mass, indicating that terminal phenotypes remain well separated even when intermediate inflammatory and proliferative states are occasionally confused. This pattern is shown directly in `figure_09_confusion_matrix_normalized`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Model relies on biologically salient features

The highest-ranked features are fibrosis, inflammatory, proliferative, and interferon-related programs, while nuisance covariates such as batch score remain much lower in importance. This pattern is shown directly in `figure_10_feature_importance_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Signed feature effects align with domain expectation

The dominant feature effects point in biologically coherent directions: fibrosis, inflammatory, and interferon signals increase predicted response, while proliferative activity suppresses it. This pattern is shown directly in `figure_10_feature_importance_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Context encoder and fusion drive primary performance

Removing the context encoder or multi-scale fusion causes the largest AUROC drops, indicating that architectural context integration is the main driver of top-line discrimination. This pattern is shown directly in `figure_11_ablation_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Calibration loss mainly affects probability quality

Removing the calibration loss causes only a modest AUROC drop but the largest increase in calibration error, indicating that this objective contributes more to probability quality than to raw discrimination. This pattern is shown directly in `figure_11_ablation_summary`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

### Model ranking

The highest-ranked model by AUROC appears first after deterministic sorting, preserving a reproducible performance ordering. This pattern is shown directly in `table_01_main`, so the immediate interpretation should stay close to the visible evidence before broader implications are introduced.

## Discussion

The current outputs suggest that the strongest value of the manuscript system is organizational rather than cosmetic: it keeps major claims anchored to explicit display items, and it makes figure provenance, pathway-analysis exports, and reference support inspectable while drafting.

That structure is especially useful when the manuscript mixes biological interpretation with AI/ML evaluation. The figure bundles and claim packets let us compare modalities without collapsing them into one undifferentiated narrative, while the fgsea-backed pathway branch shows how an upstream analysis artifact can be carried forward into a publication-quality figure without manual copy-paste.

The main limitation at this stage is no longer the bibliography layer, which is now tracked and ready, but the fact that the current figures and prose still revolve around exemplar datasets. The next submission-facing step is therefore to swap the demo inputs for study-specific data while preserving the same evidence path and review checks.

## Methods

The manuscript system is organized around tracked planning artifacts, script-generated figures and tables, explicit manuscript overlays, and an artifact-bounded agent graph built on a deterministic harness substrate. Display items are specified in registry-backed figure classes, rendered in both Python and R where supported, and reviewed through generated QA surfaces before they are wired into the manuscript.

For the bioinformatics demonstration branch, differential-expression style rankings are carried into pathway analysis through a scripted fgsea pipeline. Ranked statistics are read from a tracked CSV input, pathway definitions are loaded from a GMT file, fgsea is executed through an R wrapper, and the resulting preranked enrichment summary is exported as a normalized dot-plot table that is consumed directly by `figure_05_pathway_enrichment_dot`.

Systematic-review style evidence is summarized through protocol, query, screening, extraction, bias, and PRISMA artifacts, while the reference layer maintains a bibliography, citation graph, claim-to-reference mappings, and an integrity audit that expose whether each claim has usable literature support. Specialized agents then operate through those tracked artifacts: planning outputs summarize display-backed result statements, section-brief outputs translate those packets into section-level writing constraints, and section-prose outputs turn the resulting scaffolds into editable text artifacts without overwriting the canonical manuscript sections.
