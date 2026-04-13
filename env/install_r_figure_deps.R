#!/usr/bin/env Rscript

packages <- c(
  "BiocManager",
  "ggplot2",
  "patchwork",
  "svglite",
  "ragg",
  "yaml",
  "jsonlite",
  "systemfonts",
  "ggrepel",
  "testthat",
  "vdiffr"
)

missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]

if (length(missing) > 0) {
  install.packages(
    missing,
    repos = c(CRAN = "https://cloud.r-project.org"),
    Ncpus = max(1L, parallel::detectCores(logical = TRUE) - 1L)
  )
}

bioc_packages <- c("fgsea")
missing_bioc <- bioc_packages[!vapply(bioc_packages, requireNamespace, logical(1), quietly = TRUE)]

if (length(missing_bioc) > 0 && requireNamespace("BiocManager", quietly = TRUE)) {
  tryCatch(
    {
      BiocManager::install(
        missing_bioc,
        ask = FALSE,
        update = FALSE
      )
    },
    error = function(err) {
      message("Bioconductor package install skipped: ", conditionMessage(err))
    }
  )
}

cat("R figure dependencies available:\n")
for (pkg in packages) {
  cat(sprintf("  - %s: %s\n", pkg, requireNamespace(pkg, quietly = TRUE)))
}
for (pkg in bioc_packages) {
  cat(sprintf("  - %s: %s\n", pkg, requireNamespace(pkg, quietly = TRUE)))
}
