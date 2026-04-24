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
cran_repos <- c(CRAN = "https://cloud.r-project.org")
cran_fallback_repos <- c(CRAN = "https://cran.r-project.org")
r_install_ncpus <- max(1L, parallel::detectCores(logical = TRUE) - 1L)

options(repos = cran_repos)

available <- function(pkg) {
  requireNamespace(pkg, quietly = TRUE)
}

install_cran_package <- function(pkg, required = TRUE) {
  if (available(pkg)) {
    return(invisible(TRUE))
  }

  install_errors <- character()
  for (repos in list(cran_repos, cran_fallback_repos)) {
    options(repos = repos)
    message(sprintf("Installing CRAN package %s from %s", pkg, repos[["CRAN"]]))
    tryCatch(
      {
        install.packages(
          pkg,
          repos = repos,
          dependencies = c("Depends", "Imports", "LinkingTo"),
          Ncpus = r_install_ncpus
        )
      },
      error = function(err) {
        install_errors <<- c(install_errors, conditionMessage(err))
      }
    )

    if (available(pkg)) {
      return(invisible(TRUE))
    }
  }

  if (required) {
    warning(
      sprintf(
        "Required CRAN package %s is unavailable after install attempts%s",
        pkg,
        if (length(install_errors) > 0) {
          paste0(": ", paste(install_errors, collapse = " | "))
        } else {
          ""
        }
      ),
      call. = FALSE
    )
  } else {
    message(sprintf("Optional CRAN package %s is unavailable; continuing", pkg))
  }
  invisible(FALSE)
}

install_bioc_package <- function(pkg) {
  if (available(pkg)) {
    return(invisible(TRUE))
  }
  if (!available("BiocManager")) {
    message(sprintf("Bioconductor package %s skipped because BiocManager is unavailable", pkg))
    return(invisible(FALSE))
  }

  old_repos <- getOption("repos")
  on.exit(options(repos = old_repos), add = TRUE)

  # fgsea currently needs Rcpp; install it from CRAN first so Bioconductor does
  # not inherit a transient or runner-specific CRAN mirror failure.
  if (!available("Rcpp")) {
    install_cran_package("Rcpp", required = FALSE)
  }

  tryCatch(
    {
      options(repos = cran_repos)
      BiocManager::install(
        pkg,
        ask = FALSE,
        update = FALSE,
        Ncpus = r_install_ncpus
      )
    },
    error = function(err) {
      message("Bioconductor package install skipped: ", conditionMessage(err))
    }
  )

  options(repos = cran_repos)
  invisible(available(pkg))
}

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

for (pkg in required_packages) {
  install_cran_package(pkg, required = TRUE)
}

for (pkg in optional_packages) {
  install_cran_package(pkg, required = FALSE)
}

bioc_packages <- c("fgsea")

for (pkg in bioc_packages) {
  install_bioc_package(pkg)
}

missing_required_after_install <- required_packages[
  !vapply(required_packages, available, logical(1))
]
if (length(missing_required_after_install) > 0) {
  message(
    "Retrying missing required R packages: ",
    paste(missing_required_after_install, collapse = ", ")
  )
  for (pkg in missing_required_after_install) {
    install_cran_package(pkg, required = TRUE)
  }
}

cat("R figure dependencies available:\n")
for (pkg in packages) {
  cat(sprintf("  - %s: %s\n", pkg, available(pkg)))
}
for (pkg in bioc_packages) {
  cat(sprintf("  - %s: %s\n", pkg, available(pkg)))
}

missing_required_after_install <- required_packages[
  !vapply(required_packages, available, logical(1))
]
if (length(missing_required_after_install) > 0) {
  stop(
    sprintf(
      "Required R packages are unavailable after installation: %s",
      paste(missing_required_after_install, collapse = ", ")
    )
  )
}
