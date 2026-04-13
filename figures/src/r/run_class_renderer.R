#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(jsonlite)
  library(systemfonts)
  library(yaml)
  library(ggplot2)
  library(patchwork)
  library(ragg)
  library(svglite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 4) {
  stop("Usage: run_class_renderer.R --class <class_id> --spec <spec_path>")
}

class_flag <- args[[1]]
class_id <- args[[2]]
spec_flag <- args[[3]]
spec_path_arg <- args[[4]]
if (!identical(class_flag, "--class") || !identical(spec_flag, "--spec")) {
  stop("Usage: run_class_renderer.R --class <class_id> --spec <spec_path>")
}

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script_arg) == 0) {
  stop("Unable to locate the current R script path")
}
script_path <- normalizePath(sub("^--file=", "", script_arg[[1]]), winslash = "/", mustWork = TRUE)
repo_root <- normalizePath(file.path(dirname(script_path), "..", "..", ".."), winslash = "/", mustWork = TRUE)
class_script <- file.path(repo_root, "figures", "src", "r", "classes", sprintf("%s.R", class_id))
if (!file.exists(class_script)) {
  stop(sprintf("Unknown R class renderer: %s", class_id))
}

options(manuscript.figure.repo_root = repo_root)
source(class_script)
build_figure(normalizePath(file.path(repo_root, spec_path_arg), winslash = "/", mustWork = TRUE))
