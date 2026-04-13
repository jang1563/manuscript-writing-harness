repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_bin_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows$label_bin <- as.character(rows$label_bin)
  rows <- rows[order(rows$display_order, rows$mean_predicted), ]
  rows
}

load_metric_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows <- rows[order(rows$display_order), ]
  rows
}

build_source_data <- function(spec, bins, metrics) {
  mapping <- source_data_mapping(spec)
  metric_map <- split(metrics, metrics$model)
  reliability_rows <- data.frame()
  support_rows <- data.frame()
  for (i in seq_len(nrow(bins))) {
    row <- bins[i, , drop = FALSE]
    metric <- metric_map[[row$model]][1, , drop = FALSE]
    reliability_rows <- rbind(
      reliability_rows,
      data.frame(
        model = row$model,
        display_order = row$display_order,
        mean_predicted = row$mean_predicted,
        observed_rate = row$observed_rate,
        observed_lower = row$observed_lower,
        observed_upper = row$observed_upper,
        sample_count = row$sample_count,
        sample_fraction = row$sample_fraction,
        label_bin = row$label_bin,
        ece = metric$ece,
        max_calibration_gap = metric$max_calibration_gap,
        brier_score = metric$brier_score,
        stringsAsFactors = FALSE
      )
    )
    support_rows <- rbind(
      support_rows,
      data.frame(
        model = row$model,
        display_order = row$display_order,
        bin_center = row$bin_center,
        sample_fraction = row$sample_fraction,
        sample_count = row$sample_count,
        label_bin = row$label_bin,
        ece = metric$ece,
        max_calibration_gap = metric$max_calibration_gap,
        brier_score = metric$brier_score,
        stringsAsFactors = FALSE
      )
    )
  }
  reliability_rows <- reliability_rows[order(reliability_rows$display_order, reliability_rows$mean_predicted), ]
  support_rows <- support_rows[order(support_rows$display_order, support_rows$bin_center), ]
  write_source_csv(
    file.path(repo_root, mapping$a),
    reliability_rows,
    c(
      "model",
      "display_order",
      "mean_predicted",
      "observed_rate",
      "observed_lower",
      "observed_upper",
      "sample_count",
      "sample_fraction",
      "label_bin",
      "ece",
      "max_calibration_gap",
      "brier_score"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    support_rows,
    c(
      "model",
      "display_order",
      "bin_center",
      "sample_fraction",
      "sample_count",
      "label_bin",
      "ece",
      "max_calibration_gap",
      "brier_score"
    )
  )
  list(reliability = reliability_rows, support = support_rows)
}

style_maps <- function(theme, metrics) {
  colors <- c(
    theme$palette$categorical[[1]],
    theme$palette$categorical[[2]],
    theme$palette$categorical[[3]]
  )
  line_types <- c("solid", "dashed", "dotdash")
  shapes <- c(16, 15, 18)
  data.frame(
    model = metrics$model,
    color = colors[seq_len(nrow(metrics))],
    line_type = line_types[seq_len(nrow(metrics))],
    shape = shapes[seq_len(nrow(metrics))],
    stringsAsFactors = FALSE
  )
}

label_offsets <- function() {
  data.frame(
    model = c("Foundation model", "Hybrid GNN", "CNN baseline"),
    dx = c(0.025, 0.025, 0.025),
    dy = c(0.0, -0.03, -0.065),
    stringsAsFactors = FALSE
  )
}

summary_text <- function(metrics) {
  lines <- c("ECE summary")
  for (i in seq_len(nrow(metrics))) {
    lines <- c(lines, sprintf("%s: %.3f", metrics$model[[i]], metrics$ece[[i]]))
  }
  paste(lines, collapse = "\n")
}

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

  bins <- load_bin_rows(file.path(repo_root, spec$data_inputs[[1]]))
  metrics <- load_metric_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, bins, metrics)
  styles <- style_maps(theme, metrics)
  offsets <- label_offsets()

  reliability_rows <- merge(source_rows$reliability, styles, by = "model", sort = FALSE)
  reliability_labels <- merge(
    reliability_rows[reliability_rows$label_bin == "yes", ],
    offsets,
    by = "model",
    sort = FALSE
  )
  reliability_labels$label_x <- reliability_labels$mean_predicted + reliability_labels$dx
  reliability_labels$label_y <- reliability_labels$observed_rate + reliability_labels$dy

  support_rows <- merge(source_rows$support, styles, by = "model", sort = FALSE)

  plot_a <- ggplot2::ggplot(reliability_rows, ggplot2::aes(x = mean_predicted, y = observed_rate, color = model, linetype = model, group = model)) +
    ggplot2::geom_abline(intercept = 0, slope = 1, linetype = "dotted", linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = observed_lower, ymax = observed_upper, fill = model),
      alpha = 0.09,
      linewidth = 0,
      show.legend = FALSE
    ) +
    ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_point(ggplot2::aes(shape = model), size = 2.2, show.legend = FALSE) +
    ggplot2::geom_text(
      data = reliability_labels,
      ggplot2::aes(x = label_x, y = label_y, label = model),
      inherit.aes = FALSE,
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "label",
      x = 0.98,
      y = 0.03,
      label = summary_text(metrics),
      hjust = 1,
      vjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      label.size = 0.25,
      fill = "white",
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::scale_color_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_fill_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_linetype_manual(values = stats::setNames(styles$line_type, styles$model)) +
    ggplot2::scale_shape_manual(values = stats::setNames(styles$shape, styles$model)) +
    ggplot2::labs(title = "Reliability diagram", x = "Mean predicted probability", y = "Observed event rate") +
    ggplot2::coord_cartesian(xlim = c(0, 1), ylim = c(0, 1.02), clip = "off") +
    plot_theme

  plot_b <- ggplot2::ggplot(support_rows, ggplot2::aes(x = bin_center, y = sample_fraction, fill = model)) +
    ggplot2::geom_col(
      position = ggplot2::position_dodge(width = 0.08),
      width = 0.07,
      alpha = 0.75,
      color = theme$palette$neutral[[1]],
      linewidth = 0.3,
      show.legend = FALSE
    ) +
    ggplot2::scale_fill_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Confidence support by bin", x = "Predicted probability bin", y = "Sample fraction") +
    ggplot2::coord_cartesian(
      xlim = c(min(support_rows$bin_center) - 0.08, max(support_rows$bin_center) + 0.12),
      ylim = c(0, max(support_rows$sample_fraction) + 0.06)
    ) +
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
    metrics = metrics,
    bins = bins
  )
}

build_figure <- function(spec_path) {
  payload <- create_plot(spec_path)
  spec <- payload$spec
  theme <- payload$theme
  profile <- payload$profile
  resolved_font <- payload$resolved_font
  figure_plot <- payload$plot
  metrics <- payload$metrics
  bins <- payload$bins
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
      "reliability_diagram_with_identity_reference",
      "bin_level_uncertainty_intervals",
      "direct_labels_for_model_identity",
      "confidence_support_panel_for_coverage_context",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      direct_label_count = nrow(metrics),
      annotation_count = nrow(metrics) + 1,
      support_bin_count = nrow(bins),
      reference_line_count = 1,
      uncertainty_band_count = nrow(metrics)
    )
  )
  outputs
}
