repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

create_plot <- function(spec_path) {
  spec <- load_yaml(spec_path)
  theme <- load_yaml(file.path(repo_root, "figures/config/project_theme.yml"))
  font_policy <- load_yaml(file.path(repo_root, "figures/config/font_policy.yml"))
  profiles <- load_yaml(file.path(repo_root, "figures/config/venue_profiles.yml"))
  registry <- load_yaml(file.path(repo_root, "figures/registry/classes.yml"))$classes
  profile <- profiles$profiles[[spec$target_profile]]
  class_entry <- registry[[spec$class_id]]
  validate_common_contract(spec, theme, font_policy, profile, class_entry)
  resolved_font <- resolve_font(font_policy)
  plot_theme <- build_theme(theme, resolved_font)

  rows <- read.csv(file.path(repo_root, spec$data_inputs[[1]]), stringsAsFactors = FALSE, check.names = FALSE)
  mean_df <- aggregate(response ~ condition + timepoint_hours, rows, mean)
  sd_df <- aggregate(response ~ condition + timepoint_hours, rows, function(x) if (length(x) > 1) sd(x) else 0)
  n_df <- aggregate(response ~ condition + timepoint_hours, rows, length)
  names(mean_df)[3] <- "mean_response"
  names(sd_df)[3] <- "std_response"
  names(n_df)[3] <- "n"
  panel_summary <- Reduce(function(left, right) merge(left, right, by = c("condition", "timepoint_hours")), list(mean_df, sd_df, n_df))
  panel_summary <- panel_summary[order(panel_summary$condition, panel_summary$timepoint_hours), ]

  max_timepoint <- max(rows$timepoint_hours)
  endpoint_rows <- rows[rows$timepoint_hours == max_timepoint, ]
  endpoint_mean <- aggregate(response ~ condition, endpoint_rows, mean)
  endpoint_sd <- aggregate(response ~ condition, endpoint_rows, function(x) if (length(x) > 1) sd(x) else 0)
  names(endpoint_mean)[2] <- "mean_response"
  names(endpoint_sd)[2] <- "std_response"
  endpoint_summary <- merge(endpoint_mean, endpoint_sd, by = "condition")
  endpoint_summary$timepoint_hours <- max_timepoint
  endpoint_summary <- endpoint_summary[order(endpoint_summary$condition), ]

  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    panel_summary,
    c("condition", "timepoint_hours", "mean_response", "std_response", "n")
  )
  panel_b_rows <- endpoint_rows
  panel_b_rows$mean_response <- endpoint_summary$mean_response[match(panel_b_rows$condition, endpoint_summary$condition)]
  panel_b_rows$std_response <- endpoint_summary$std_response[match(panel_b_rows$condition, endpoint_summary$condition)]
  names(panel_b_rows)[names(panel_b_rows) == "timepoint_hours"] <- "endpoint_hours"
  write_source_csv(
    file.path(repo_root, mapping$b),
    panel_b_rows,
    c("condition", "endpoint_hours", "replicate", "response", "mean_response", "std_response")
  )

  colors <- c("Control" = theme$palette$categorical[[1]], "Treated" = theme$palette$categorical[[2]])
  label_data <- panel_summary[panel_summary$timepoint_hours == max(panel_summary$timepoint_hours), ]

  plot_a <- ggplot2::ggplot(panel_summary, ggplot2::aes(x = timepoint_hours, y = mean_response, color = condition, fill = condition)) +
    ggplot2::geom_ribbon(ggplot2::aes(ymin = mean_response - std_response, ymax = mean_response + std_response), alpha = 0.12, linewidth = 0, show.legend = FALSE) +
    ggplot2::geom_line(linewidth = as.numeric(theme$strokes$data_line_width_pt)) +
    ggplot2::geom_point(size = 1.6) +
    ggplot2::geom_text(
      data = label_data,
      ggplot2::aes(x = timepoint_hours + 0.35, y = mean_response, label = condition),
      inherit.aes = FALSE,
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::scale_color_manual(values = colors) +
    ggplot2::scale_fill_manual(values = colors) +
    ggplot2::scale_x_continuous(expand = ggplot2::expansion(mult = c(0.02, 0.18))) +
    ggplot2::labs(title = "Time-course response", x = "Time (hours)", y = "Normalized signal") +
    plot_theme

  endpoint_summary$x <- seq_len(nrow(endpoint_summary))
  endpoint_rows$x <- match(endpoint_rows$condition, endpoint_summary$condition) + c(-0.08, 0.0, 0.08)[endpoint_rows$replicate]
  plot_b <- ggplot2::ggplot(endpoint_summary, ggplot2::aes(x = x, y = mean_response, fill = condition)) +
    ggplot2::geom_col(width = 0.62, alpha = 0.88, color = theme$palette$neutral[[1]], linewidth = as.numeric(theme$strokes$errorbar_line_width_pt)) +
    ggplot2::geom_errorbar(ggplot2::aes(ymin = mean_response - std_response, ymax = mean_response + std_response), width = 0.12, linewidth = as.numeric(theme$strokes$errorbar_line_width_pt)) +
    ggplot2::geom_point(
      data = endpoint_rows,
      ggplot2::aes(x = x, y = response),
      inherit.aes = FALSE,
      shape = 21,
      fill = theme$export_defaults$background,
      color = theme$palette$neutral[[1]],
      stroke = as.numeric(theme$strokes$marker_edge_width_pt),
      size = 2.1
    ) +
    ggplot2::scale_fill_manual(values = colors) +
    ggplot2::scale_x_continuous(breaks = endpoint_summary$x, labels = endpoint_summary$condition) +
    ggplot2::labs(title = "Endpoint summary", x = "Condition", y = "Normalized signal at 6 h") +
    plot_theme

  figure_plot <- (plot_a + plot_b + patchwork::plot_layout(ncol = 2)) +
    patchwork::plot_annotation(tag_levels = "a") &
    ggplot2::theme(
      plot.tag = ggplot2::element_text(
        size = as.numeric(theme$panel_labels$font_size_pt),
        face = theme$panel_labels$font_weight,
        family = resolved_font$family
      )
    )
  list(
    plot = figure_plot,
    spec = spec,
    theme = theme,
    profile = profile,
    resolved_font = resolved_font,
    endpoint_rows = endpoint_rows
  )
}

build_figure <- function(spec_path) {
  payload <- create_plot(spec_path)
  spec <- payload$spec
  theme <- payload$theme
  profile <- payload$profile
  resolved_font <- payload$resolved_font
  figure_plot <- payload$plot
  endpoint_rows <- payload$endpoint_rows
  output_dir <- file.path(repo_root, spec$renderers$r$output_dir)
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  stem <- spec$figure_id
  svg_path <- file.path(output_dir, sprintf("%s.svg", stem))
  pdf_path <- file.path(output_dir, sprintf("%s.pdf", stem))
  png_path <- file.path(output_dir, sprintf("%s.png", stem))
  width_in <- mm_to_inches(as.numeric(spec$size$width_mm))
  height_in <- mm_to_inches(as.numeric(spec$size$height_mm))

  svglite::svglite(file = svg_path, width = width_in, height = height_in, bg = theme$export_defaults$background, system_fonts = list(sans = resolved_font$family))
  print(figure_plot)
  grDevices::dev.off()
  grDevices::cairo_pdf(file = pdf_path, width = width_in, height = height_in, bg = theme$export_defaults$background, family = resolved_font$family)
  print(figure_plot)
  grDevices::dev.off()
  ragg::agg_png(filename = png_path, width = width_in, height = height_in, units = "in", res = as.numeric(profile$preview_dpi), background = theme$export_defaults$background)
  print(figure_plot)
  grDevices::dev.off()

  outputs <- list(
    svg = sub(paste0("^", repo_root, "/"), "", svg_path),
    pdf = sub(paste0("^", repo_root, "/"), "", pdf_path),
    png = sub(paste0("^", repo_root, "/"), "", png_path)
  )
  write_manifest(
    repo_root,
    spec,
    profile,
    resolved_font,
    spec_path,
    "r",
    outputs,
    list(
      "direct_labels_for_small_number_of_series",
      "replicate_level_points_in_endpoint_panel",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      direct_label_count = 2,
      endpoint_replicate_count = nrow(endpoint_rows)
    )
  )
  outputs
}
