testthat::test_that("Wave 1 class renderers load in R", {
  for (class_id in c(
    "timecourse_endpoint",
    "volcano_pathway_compound",
    "ma_plot",
    "sample_pca",
    "pathway_enrichment_dot",
    "roc_pr_compound",
    "calibration_reliability",
    "training_dynamics",
    "confusion_matrix_normalized",
    "feature_importance_summary",
    "ablation_summary"
  )) {
    env <- new.env(parent = baseenv())
    sys.source(
      file.path(repo_root, "figures", "src", "r", "classes", sprintf("%s.R", class_id)),
      envir = env
    )
    testthat::expect_true(is.function(env$create_plot))
    testthat::expect_true(is.function(env$build_figure))
  }
})

testthat::test_that("vdiffr hooks are in place for Wave 1 figures", {
  testthat::skip_if_not_installed("vdiffr")
  testthat::skip("Snapshot approval is a manual step after baselines are reviewed.")
})
