#!/usr/bin/env Rscript

required_packages <- c(
  "BiocManager",
  "ggplot2",
  "patchwork",
  "svglite",
  "ragg",
  "yaml",
  "jsonlite",
  "systemfonts",
  "ggrepel",
  "testthat"
)

optional_packages <- c(
  "vdiffr"
)

packages <- c(required_packages, optional_packages)

install_github_actions_system_deps <- function() {
  if (!identical(Sys.getenv("GITHUB_ACTIONS"), "true")) {
    return(invisible(FALSE))
  }
  if (!identical(Sys.info()[["sysname"]], "Linux")) {
    return(invisible(FALSE))
  }
  if (!nzchar(Sys.which("sudo")) || !nzchar(Sys.which("apt-get"))) {
    return(invisible(FALSE))
  }

  system_packages <- c(
    "libfontconfig1-dev",
    "libfreetype6-dev",
    "libfribidi-dev",
    "libharfbuzz-dev",
    "libjpeg-dev",
    "libpng-dev",
    "libtiff-dev",
    "libuv1-dev"
  )
  status <- system2("sudo", c("apt-get", "update", "-y", "-qq"))
  if (!identical(as.integer(status), 0L)) {
    stop("apt-get update failed while preparing R system dependencies")
  }
  status <- system2(
    "sudo",
    c(
      "env",
      "DEBIAN_FRONTEND=noninteractive",
      "apt-get",
      "install",
      "-y",
      system_packages
    )
  )
  if (!identical(as.integer(status), 0L)) {
    stop("apt-get install failed while preparing R system dependencies")
  }
  invisible(TRUE)
}

install_github_actions_system_deps()

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

missing_required_after_install <- required_packages[
  !vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)
]
if (length(missing_required_after_install) > 0) {
  stop(
    sprintf(
      "Required R packages are unavailable after installation: %s",
      paste(missing_required_after_install, collapse = ", ")
    )
  )
}
