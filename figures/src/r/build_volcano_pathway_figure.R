#!/usr/bin/env Rscript

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) == 0) {
  stop("Unable to locate the current R script path")
}
script_path <- normalizePath(sub("^--file=", "", script_arg[[1]]), winslash = "/", mustWork = TRUE)
repo_root <- normalizePath(file.path(dirname(script_path), "..", "..", ".."), winslash = "/", mustWork = TRUE)
options(manuscript.figure.repo_root = repo_root)

source(file.path(repo_root, "figures", "src", "r", "classes", "volcano_pathway_compound.R"))
build_figure(normalizePath(file.path(repo_root, "figures/specs/figure_02_volcano_pathway.yml"), winslash = "/", mustWork = TRUE))
