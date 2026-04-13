`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || identical(x, "")) y else x

load_yaml <- function(path) yaml::yaml.load_file(path)

mm_to_inches <- function(value) value / 25.4

figure_repo_root <- function() {
  repo_root <- getOption("manuscript.figure.repo_root")
  if (is.null(repo_root)) {
    stop("manuscript.figure.repo_root option is required")
  }
  repo_root
}

md5_for_path <- function(path) unname(tools::md5sum(path))

semantic_csv_hash <- function(path) {
  rows <- utils::read.csv(
    path,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
  fieldnames <- sort(names(rows))
  header <- paste(fieldnames, collapse = "\u001f")
  if (length(fieldnames) == 0 || nrow(rows) == 0) {
    payload <- header
  } else {
    ordered <- rows[, fieldnames, drop = FALSE]
    row_strings <- vapply(seq_len(nrow(ordered)), function(index) {
      paste(
        vapply(fieldnames, function(column) format_csv_value(ordered[[column]][[index]]), character(1)),
        collapse = "\u001f"
      )
    }, character(1))
    payload <- paste(c(header, sort(row_strings)), collapse = "\u001e")
  }
  temp_path <- tempfile(pattern = "semantic_csv_hash_", fileext = ".txt")
  on.exit(unlink(temp_path), add = TRUE)
  writeChar(payload, temp_path, eos = NULL, useBytes = TRUE)
  unname(tools::md5sum(temp_path))
}

format_csv_value <- function(value) {
  if (is.null(value) || length(value) == 0 || is.na(value)) {
    return("")
  }
  if (is.numeric(value)) {
    if (abs(value - round(value)) < 1e-9) {
      return(as.character(as.integer(round(value))))
    }
    formatted <- formatC(value, format = "f", digits = 6)
    formatted <- sub("0+$", "", formatted)
    formatted <- sub("\\.$", "", formatted)
    return(formatted)
  }
  string_value <- as.character(value)
  if (grepl("[,\n\"]", string_value)) {
    escaped <- gsub("\"", "\"\"", string_value, fixed = TRUE)
    return(sprintf("\"%s\"", escaped))
  }
  string_value
}

write_source_csv <- function(path, rows, columns) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  header <- paste(columns, collapse = ",")
  if (nrow(rows) == 0) {
    writeLines(header, con = path, useBytes = TRUE)
    return(invisible(path))
  }
  ordered <- rows[, columns, drop = FALSE]
  body <- vapply(seq_len(nrow(ordered)), function(index) {
    paste(
      vapply(columns, function(column) format_csv_value(ordered[[column]][[index]]), character(1)),
      collapse = ","
    )
  }, character(1))
  writeLines(c(header, body), con = path, useBytes = TRUE)
  invisible(path)
}

source_data_mapping <- function(spec) {
  mapping <- spec$source_data_outputs
  if (is.null(mapping)) {
    mapping <- spec$source_data
  }
  if (is.null(mapping) || !is.list(mapping)) {
    stop("Spec must define source_data_outputs or legacy source_data")
  }
  mapping
}

resolve_data_input <- function(spec, index = 1) {
  generated <- spec$generated_data_inputs
  if (!is.null(generated) && length(generated) >= index) {
    generated_path <- file.path(figure_repo_root(), generated[[index]])
    if (file.exists(generated_path)) {
      return(generated_path)
    }
  }
  file.path(figure_repo_root(), spec$data_inputs[[index]])
}

resolved_data_inputs <- function(spec) {
  vapply(seq_along(spec$data_inputs), function(index) {
    resolve_data_input(spec, index)
  }, character(1))
}

display_repo_path <- function(path, repo_root = figure_repo_root()) {
  normalized <- normalizePath(path, winslash = "/", mustWork = FALSE)
  normalized_root <- normalizePath(repo_root, winslash = "/", mustWork = FALSE)
  if (startsWith(normalized, paste0(normalized_root, "/"))) {
    return(sub(paste0("^", normalized_root, "/"), "", normalized))
  }
  normalized
}

load_fgsea_summary_for_export <- function(export_path, repo_root = figure_repo_root()) {
  summary_path <- file.path(dirname(export_path), "fgsea_summary.json")
  if (!file.exists(summary_path)) {
    return(NULL)
  }
  payload <- jsonlite::fromJSON(summary_path, simplifyVector = FALSE)
  list(
    run_id = payload$run_id %||% NULL,
    status = payload$status %||% NULL,
    config = payload$config %||% NULL,
    source_profile = payload$source_profile %||% NULL,
    raw_input_table = payload$raw_input_table %||% NULL,
    rank_prep_summary = payload$rank_prep_summary %||% NULL,
    summary_json = payload$summary_json %||% display_repo_path(summary_path, repo_root),
    figure_export_csv = payload$figure_export_csv %||% display_repo_path(export_path, repo_root),
    pathways_gmt = payload$pathways_gmt %||% NULL,
    result_count = payload$result_count %||% NULL,
    figure_export_count = payload$figure_export_count %||% NULL,
    gene_set_source = payload$gene_set_source %||% NULL,
    top_pathways = payload$top_pathways %||% list()
  )
}

infer_pathway_provenance <- function(spec, repo_root = figure_repo_root()) {
  for (resolved_input in resolved_data_inputs(spec)) {
    if (basename(resolved_input) != "fgsea_pathway_dot_export.csv") {
      next
    }
    provenance <- load_fgsea_summary_for_export(resolved_input, repo_root)
    if (is.null(provenance)) {
      return(list(
        figure_export_csv = display_repo_path(resolved_input, repo_root),
        summary_json = display_repo_path(file.path(dirname(resolved_input), "fgsea_summary.json"), repo_root),
        status = "missing_summary"
      ))
    }
    return(provenance)
  }
  NULL
}

bundled_font_paths <- function(repo_root, family) {
  base_name <- switch(
    family,
    "DejaVu Sans" = "DejaVuSans",
    "DejaVu Sans Mono" = "DejaVuSansMono",
    NULL
  )
  if (is.null(base_name)) {
    return(NULL)
  }
  font_dirs <- Sys.glob(
    file.path(
      repo_root,
      ".venv",
      "lib",
      "*",
      "site-packages",
      "matplotlib",
      "mpl-data",
      "fonts",
      "ttf"
    )
  )
  if (length(font_dirs) == 0) {
    return(NULL)
  }
  font_dir <- font_dirs[[1]]
  plain <- file.path(font_dir, sprintf("%s.ttf", base_name))
  bold <- file.path(font_dir, sprintf("%s-Bold.ttf", base_name))
  italic_suffix <- if (identical(family, "DejaVu Sans")) "Oblique" else "Oblique"
  bold_italic_suffix <- if (identical(family, "DejaVu Sans")) "BoldOblique" else "BoldOblique"
  italic <- file.path(font_dir, sprintf("%s-%s.ttf", base_name, italic_suffix))
  bolditalic <- file.path(font_dir, sprintf("%s-%s.ttf", base_name, bold_italic_suffix))
  if (!file.exists(plain)) {
    return(NULL)
  }
  list(
    plain = plain,
    bold = if (file.exists(bold)) bold else plain,
    italic = if (file.exists(italic)) italic else plain,
    bolditalic = if (file.exists(bolditalic)) bolditalic else if (file.exists(bold)) bold else plain
  )
}

register_bundled_font <- function(repo_root, family) {
  font_paths <- bundled_font_paths(repo_root, family)
  if (is.null(font_paths)) {
    return(NULL)
  }
  alias <- sprintf("Manuscript %s", family)
  tryCatch(
    {
      systemfonts::register_font(
        name = alias,
        plain = font_paths$plain,
        bold = font_paths$bold,
        italic = font_paths$italic,
        bolditalic = font_paths$bolditalic
      )
      list(
        family = alias,
        path = font_paths$plain
      )
    },
    error = function(...) NULL
  )
}

resolve_font <- function(font_policy) {
  repo_root <- figure_repo_root()
  candidates <- c(
    font_policy$families$sans_preferred,
    font_policy$families$sans_fallbacks
  )
  for (candidate in candidates) {
    bundled <- register_bundled_font(repo_root, candidate)
    if (!is.null(bundled)) {
      return(list(
        family = bundled$family,
        path = bundled$path,
        candidates = candidates,
        source_family = candidate
      ))
    }
    match <- systemfonts::match_font(candidate)
    if (!is.null(match$path) && nzchar(match$path)) {
      return(list(
        family = candidate,
        path = match$path,
        candidates = candidates,
        source_family = candidate
      ))
    }
  }
  stop("Could not resolve any configured sans-serif font")
}

validate_common_contract <- function(spec, theme, font_policy, profile, class_entry) {
  required_spec_keys <- c(
    "figure_id", "class_id", "class_version", "title", "font_policy_id", "target_profile",
    "claim_ids", "fact_sheet", "visualization_plan", "legend_path", "qa_profile",
    "review_preset", "parity_status", "size", "renderers", "data_inputs"
  )
  missing <- setdiff(required_spec_keys, names(spec))
  if (length(missing) > 0) {
    stop(sprintf("figure spec is missing keys: %s", paste(missing, collapse = ", ")))
  }
  source_data_mapping(spec)

  requirements <- font_policy$requirements
  base_size <- as.numeric(theme$typography$base_font_size_pt)
  if (base_size < as.numeric(requirements$min_text_size_pt) ||
      base_size > as.numeric(requirements$max_text_size_pt)) {
    stop("base font size is outside the configured publication range")
  }

  panel_label_size <- as.numeric(theme$panel_labels$font_size_pt)
  if (!identical(panel_label_size, as.numeric(requirements$panel_label_font_size_pt))) {
    stop("panel label font size does not match the font policy")
  }
  if (!identical(theme$panel_labels$case, requirements$panel_label_case)) {
    stop("panel label case does not match the font policy")
  }

  if (as.numeric(spec$size$height_mm) > as.numeric(profile$max_height_mm)) {
    stop("figure height exceeds the selected venue profile")
  }
  if (as.numeric(spec$size$width_mm) > as.numeric(profile$width_mm)) {
    stop("figure width exceeds the selected venue profile")
  }
  if (!identical(spec$class_version, class_entry$class_version)) {
    stop("spec class_version does not match the class registry")
  }
  if (!identical(spec$qa_profile, class_entry$qa_profile)) {
    stop("spec qa_profile does not match the class registry")
  }
  if (!identical(spec$review_preset, class_entry$review_preset)) {
    stop("spec review_preset does not match the class registry")
  }
  if (!(spec$parity_status %in% c("dual", "authority_only"))) {
    stop("spec parity_status must be dual or authority_only")
  }
  if (identical(spec$parity_status, "authority_only") && is.null(spec$authority_renderer)) {
    stop("authority_only specs must define authority_renderer")
  }
}

build_theme <- function(theme, resolved_font) {
  base_family <- resolved_font$family
  ggplot2::theme_minimal(
    base_family = base_family,
    base_size = as.numeric(theme$typography$base_font_size_pt)
  ) +
    ggplot2::theme(
      panel.grid.minor = ggplot2::element_blank(),
      panel.grid.major.x = ggplot2::element_blank(),
      axis.line = ggplot2::element_line(
        colour = theme$palette$neutral[[1]],
        linewidth = as.numeric(theme$strokes$axis_line_width_pt)
      ),
      axis.ticks = ggplot2::element_line(
        colour = theme$palette$neutral[[1]],
        linewidth = as.numeric(theme$strokes$axis_line_width_pt)
      ),
      axis.title = ggplot2::element_text(size = as.numeric(theme$typography$axis_label_font_size_pt)),
      axis.text = ggplot2::element_text(size = as.numeric(theme$typography$tick_label_font_size_pt), colour = theme$palette$neutral[[1]]),
      plot.title = ggplot2::element_text(size = as.numeric(theme$typography$title_font_size_pt), face = "plain"),
      legend.position = "none"
    )
}

write_manifest <- function(repo_root, spec, profile, resolved_font, spec_path, renderer, outputs, design_features, qa_metrics = list()) {
  source_data <- source_data_mapping(spec)
  resolved_inputs <- resolved_data_inputs(spec)
  relative_resolved_inputs <- sub(paste0("^", repo_root, "/"), "", resolved_inputs)
  checksums <- list(
    data_inputs = setNames(
      lapply(file.path(repo_root, spec$data_inputs), md5_for_path),
      spec$data_inputs
    ),
    resolved_data_inputs = setNames(
      lapply(resolved_inputs, md5_for_path),
      relative_resolved_inputs
    ),
    source_data = setNames(
      lapply(file.path(repo_root, unlist(source_data)), md5_for_path),
      unlist(source_data)
    ),
    outputs = setNames(
      lapply(file.path(repo_root, unlist(outputs)), md5_for_path),
      unlist(outputs)
    )
  )
  semantic_checksums <- list(
    source_data = setNames(
      lapply(file.path(repo_root, unlist(source_data)), semantic_csv_hash),
      unlist(source_data)
    )
  )

  generated_inputs <- spec$generated_data_inputs
  if (is.null(generated_inputs)) {
    generated_inputs <- list()
  }

  manifest <- list(
    figure_id = spec$figure_id,
    class_id = spec$class_id,
    class_version = spec$class_version,
    renderer = renderer,
    title = spec$title,
    generated_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"),
    theme_id = spec$theme_id,
    font_policy_id = spec$font_policy_id,
    style_profile = spec$style_profile,
    target_profile = spec$target_profile,
    figure_size_mm = spec$size,
    profile_constraints = list(
      width_mm = profile$width_mm,
      max_height_mm = profile$max_height_mm,
      authoritative_formats = profile$authoritative_formats
    ),
    qa_profile = spec$qa_profile,
    review_preset = spec$review_preset,
    parity_status = spec$parity_status,
    authority_renderer = spec$authority_renderer,
    font_resolution = resolved_font,
    spec_path = sub(paste0("^", repo_root, "/"), "", spec_path),
    data_inputs = unname(as.list(spec$data_inputs)),
    generated_data_inputs = unname(as.list(generated_inputs)),
    resolved_data_inputs = unname(as.list(relative_resolved_inputs)),
    source_data = source_data,
    pathway_provenance = infer_pathway_provenance(spec, repo_root),
    claim_ids = unname(as.list(spec$claim_ids)),
    fact_sheet = spec$fact_sheet,
    visualization_plan = spec$visualization_plan,
    legend_path = spec$legend_path,
    outputs = outputs,
    checksums_md5 = checksums,
    checksums_semantic = semantic_checksums,
    caption_stub = spec$caption_stub,
    design_features = design_features,
    qa_metrics = qa_metrics
  )

  output_dir <- file.path(repo_root, spec$renderers[[renderer]]$output_dir)
  jsonlite::write_json(
    manifest,
    path = file.path(output_dir, sprintf("%s.manifest.json", spec$figure_id)),
    auto_unbox = TRUE,
    pretty = TRUE
  )
}
