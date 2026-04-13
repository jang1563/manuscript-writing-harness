#!/usr/bin/env Rscript

`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || identical(x, "")) y else x

suppressPackageStartupMessages({
  library(yaml)
  library(jsonlite)
})

parse_args <- function(args) {
  out <- list(
    config = NULL,
    validate_only = FALSE,
    allow_missing_package = FALSE,
    output_dir = NULL
  )
  i <- 1
  while (i <= length(args)) {
    arg <- args[[i]]
    if (arg == "--config") {
      i <- i + 1
      out$config <- args[[i]]
    } else if (arg == "--validate-only") {
      out$validate_only <- TRUE
    } else if (arg == "--allow-missing-package") {
      out$allow_missing_package <- TRUE
    } else if (arg == "--output-dir") {
      i <- i + 1
      out$output_dir <- args[[i]]
    } else {
      stop(sprintf("Unknown argument: %s", arg))
    }
    i <- i + 1
  }
  out
}

raw_args <- commandArgs(trailingOnly = FALSE)
file_arg <- raw_args[grepl("^--file=", raw_args)]
script_path <- if (length(file_arg)) sub("^--file=", "", file_arg[[1]]) else file.path(getwd(), "scripts/run_fgsea_pipeline.R")
repo_root <- normalizePath(file.path(dirname(script_path), ".."), winslash = "/", mustWork = FALSE)

resolve_repo_path <- function(path) {
  if (grepl("^/", path)) {
    normalizePath(path, winslash = "/", mustWork = FALSE)
  } else {
    normalizePath(file.path(repo_root, path), winslash = "/", mustWork = FALSE)
  }
}

relative_repo_path <- function(path) {
  normalized <- normalizePath(path, winslash = "/", mustWork = FALSE)
  sub(paste0("^", normalizePath(repo_root, winslash = "/", mustWork = FALSE), "/"), "", normalized)
}

read_gmt <- function(path) {
  lines <- readLines(path, warn = FALSE)
  pathways <- list()
  for (line in lines) {
    if (!nzchar(trimws(line))) next
    parts <- strsplit(line, "\t", fixed = TRUE)[[1]]
    if (length(parts) < 3) next
    pathways[[parts[[1]]]] <- unique(parts[3:length(parts)])
  }
  pathways
}

normalize_ranks <- function(path) {
  table <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  if (!all(c("gene", "stat") %in% names(table))) {
    stop("Ranks CSV must contain `gene` and `stat` columns")
  }
  table <- table[!is.na(table$gene) & !is.na(table$stat), c("gene", "stat")]
  table <- table[order(-table$stat, table$gene), ]
  dedup <- !duplicated(table$gene)
  table <- table[dedup, , drop = FALSE]
  stats <- table$stat
  names(stats) <- table$gene
  list(table = table, stats = stats)
}

build_figure_export <- function(results_df, output_path, top_n_per_direction) {
  results_df$leading_edge_size <- vapply(results_df$leadingEdge, length, integer(1))
  results_df$gene_ratio <- pmin(1, results_df$leading_edge_size / pmax(results_df$size, 1))
  results_df$neg_log10_fdr <- -log10(pmax(results_df$padj, .Machine$double.xmin))
  results_df$direction <- ifelse(results_df$NES >= 0, "up", "down")

  up <- results_df[results_df$NES >= 0, , drop = FALSE]
  down <- results_df[results_df$NES < 0, , drop = FALSE]
  up <- up[order(up$padj, -up$NES, up$pathway), , drop = FALSE]
  down <- down[order(down$padj, down$NES, down$pathway), , drop = FALSE]

  selected <- rbind(
    head(up, top_n_per_direction),
    head(down, top_n_per_direction)
  )

  if (nrow(selected) == 0) {
    figure_df <- data.frame(
      pathway = character(),
      gene_ratio = numeric(),
      neg_log10_fdr = numeric(),
      gene_count = integer(),
      direction = character(),
      highlight_order = integer(),
      stringsAsFactors = FALSE
    )
  } else {
    selected$highlight_order <- seq_len(nrow(selected))
    figure_df <- data.frame(
      pathway = selected$pathway,
      gene_ratio = round(selected$gene_ratio, 6),
      neg_log10_fdr = round(selected$neg_log10_fdr, 6),
      gene_count = selected$leading_edge_size,
      direction = selected$direction,
      highlight_order = selected$highlight_order,
      stringsAsFactors = FALSE
    )
  }

  write.csv(figure_df, output_path, row.names = FALSE, quote = TRUE)
  figure_df
}

write_json <- function(path, payload) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  writeLines(
    jsonlite::toJSON(payload, auto_unbox = TRUE, pretty = TRUE, null = "null"),
    con = path
  )
}

main <- function() {
  args <- parse_args(commandArgs(trailingOnly = TRUE))
  if (is.null(args$config)) {
    stop("--config is required")
  }

  config_path <- resolve_repo_path(args$config)
  cfg <- yaml::read_yaml(config_path)

  ranks_path <- resolve_repo_path(cfg$ranks_csv)
  gmt_path <- resolve_repo_path(cfg$pathways_gmt)
  output_dir <- resolve_repo_path(args$output_dir %||% cfg$output_dir)
  figure_export_path <- if (is.null(args$output_dir)) {
    resolve_repo_path(cfg$figure_export_csv)
  } else {
    file.path(output_dir, basename(cfg$figure_export_csv))
  }

  fgsea_available <- requireNamespace("fgsea", quietly = TRUE)
  validation <- list(
    run_id = cfg$run_id,
    config = relative_repo_path(config_path),
    source_profile = cfg$source_profile %||% relative_repo_path(config_path),
    raw_input_table = cfg$raw_input_table %||% NULL,
    rank_prep_summary = cfg$rank_prep_summary %||% NULL,
    ranks_csv = relative_repo_path(ranks_path),
    pathways_gmt = relative_repo_path(gmt_path),
    output_dir = relative_repo_path(output_dir),
    figure_export_csv = relative_repo_path(figure_export_path),
    gene_set_source = cfg$gene_set_source %||% NULL,
    fgsea_available = fgsea_available,
    status = if (fgsea_available) "validated" else "validated_missing_package"
  )

  if (args$validate_only) {
    cat(jsonlite::toJSON(validation, auto_unbox = TRUE, pretty = TRUE, null = "null"))
    return(invisible(NULL))
  }

  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  summary_path <- file.path(output_dir, "fgsea_summary.json")
  results_path <- file.path(output_dir, "fgsea_results.csv")

  if (!fgsea_available) {
    payload <- validation
    payload$status <- "skipped_missing_package"
    payload$summary_json <- relative_repo_path(summary_path)
    payload$results_csv <- NULL
    payload$figure_export_csv <- NULL
    payload$message <- "fgsea package is not installed; rerun after BiocManager::install('fgsea') or use env/install_r_figure_deps.R"
    write_json(summary_path, payload)
    cat(jsonlite::toJSON(payload, auto_unbox = TRUE, pretty = TRUE, null = "null"))
    if (isTRUE(args$allow_missing_package)) {
      return(invisible(NULL))
    }
    quit(save = "no", status = 1)
  }

  set.seed(as.integer(cfg$parameters$seed %||% 42))
  normalized <- normalize_ranks(ranks_path)
  pathways <- read_gmt(gmt_path)
  fgsea_res <- fgsea::fgsea(
    pathways = pathways,
    stats = normalized$stats,
    minSize = as.integer(cfg$parameters$min_size),
    maxSize = as.integer(cfg$parameters$max_size),
    scoreType = as.character(cfg$parameters$score_type),
    eps = as.numeric(cfg$parameters$eps)
  )

  fgsea_res <- fgsea_res[order(fgsea_res$padj, -abs(fgsea_res$NES), fgsea_res$pathway), ]
  results_df <- as.data.frame(fgsea_res, stringsAsFactors = FALSE)
  results_df$leading_edge_size <- vapply(results_df$leadingEdge, length, integer(1))
  results_export_df <- results_df
  results_export_df$leadingEdge_genes <- vapply(
    results_export_df$leadingEdge,
    function(items) paste(items, collapse = ";"),
    character(1)
  )
  results_export_df$leadingEdge <- NULL
  write.csv(results_export_df, results_path, row.names = FALSE, quote = TRUE)

  figure_df <- build_figure_export(
    results_df,
    figure_export_path,
    as.integer(cfg$parameters$top_n_per_direction %||% 3)
  )

  payload <- validation
  payload$status <- "ready"
  payload$summary_json <- relative_repo_path(summary_path)
  payload$results_csv <- relative_repo_path(results_path)
  payload$figure_export_csv <- relative_repo_path(figure_export_path)
  payload$result_count <- nrow(results_df)
  payload$figure_export_count <- nrow(figure_df)
  payload$top_pathways <- head(results_df$pathway, 5)
  write_json(summary_path, payload)
  cat(jsonlite::toJSON(payload, auto_unbox = TRUE, pretty = TRUE, null = "null"))
  invisible(NULL)
}

main()
