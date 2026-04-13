repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_curve_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$panel <- as.character(rows$panel)
  rows$model <- as.character(rows$model)
  rows$operating_point <- as.character(rows$operating_point)
  rows
}

load_metric_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows <- rows[order(rows$display_order), ]
  rows$model <- as.character(rows$model)
  rows
}

build_source_data <- function(spec, curves, metrics) {
  mapping <- source_data_mapping(spec)
  metric_map <- split(metrics, metrics$model)
  roc_rows <- data.frame()
  pr_rows <- data.frame()
  for (i in seq_len(nrow(curves))) {
    row <- curves[i, , drop = FALSE]
    metric <- metric_map[[row$model]][1, , drop = FALSE]
    base <- data.frame(
      model = row$model,
      display_order = metric$display_order,
      operating_point = row$operating_point,
      ece = metric$ece,
      brier_score = metric$brier_score,
      stringsAsFactors = FALSE
    )
    if (identical(row$panel, "roc")) {
      roc_rows <- rbind(
        roc_rows,
        cbind(
          base,
          false_positive_rate = row$x,
          true_positive_rate = row$y,
          true_positive_rate_lower = row$y_lower,
          true_positive_rate_upper = row$y_upper,
          auroc = metric$auroc,
          stringsAsFactors = FALSE
        )
      )
    } else if (identical(row$panel, "pr")) {
      pr_rows <- rbind(
        pr_rows,
        cbind(
          base,
          recall = row$x,
          precision = row$y,
          precision_lower = row$y_lower,
          precision_upper = row$y_upper,
          auprc = metric$auprc,
          prevalence = metric$prevalence,
          stringsAsFactors = FALSE
        )
      )
    }
  }
  write_source_csv(
    file.path(repo_root, mapping$a),
    roc_rows,
    c(
      "model",
      "display_order",
      "false_positive_rate",
      "true_positive_rate",
      "true_positive_rate_lower",
      "true_positive_rate_upper",
      "operating_point",
      "auroc",
      "ece",
      "brier_score"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    pr_rows,
    c(
      "model",
      "display_order",
      "recall",
      "precision",
      "precision_lower",
      "precision_upper",
      "operating_point",
      "auprc",
      "prevalence",
      "ece",
      "brier_score"
    )
  )
  list(roc = roc_rows, pr = pr_rows)
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
    panel = c("roc", "roc", "roc", "pr", "pr", "pr"),
    model = c(
      "Foundation model",
      "Hybrid GNN",
      "CNN baseline",
      "Foundation model",
      "Hybrid GNN",
      "CNN baseline"
    ),
    dx = c(0.03, 0.03, 0.03, 0.035, 0.035, 0.035),
    dy = c(0.055, -0.03, -0.055, 0.045, -0.015, -0.05),
    stringsAsFactors = FALSE
  )
}

summary_text <- function(metrics, metric_column, title) {
  lines <- c(title)
  for (i in seq_len(nrow(metrics))) {
    lines <- c(lines, sprintf("%s: %.3f", metrics$model[[i]], metrics[[metric_column]][[i]]))
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

  curves <- load_curve_rows(file.path(repo_root, spec$data_inputs[[1]]))
  metrics <- load_metric_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, curves, metrics)
  styles <- style_maps(theme, metrics)
  offsets <- label_offsets()

  roc_rows <- merge(source_rows$roc, styles, by = "model", sort = FALSE)
  roc_labels <- merge(
    roc_rows[roc_rows$operating_point == "yes", ],
    offsets[offsets$panel == "roc", c("model", "dx", "dy")],
    by = "model",
    sort = FALSE
  )
  roc_labels$label_x <- roc_labels$false_positive_rate + roc_labels$dx
  roc_labels$label_y <- roc_labels$true_positive_rate + roc_labels$dy

  pr_rows <- merge(source_rows$pr, styles, by = "model", sort = FALSE)
  pr_labels <- merge(
    pr_rows[pr_rows$operating_point == "yes", ],
    offsets[offsets$panel == "pr", c("model", "dx", "dy")],
    by = "model",
    sort = FALSE
  )
  pr_labels$label_x <- pr_labels$recall + pr_labels$dx
  pr_labels$label_y <- pr_labels$precision + pr_labels$dy
  prevalence <- metrics$prevalence[[1]]

  plot_theme <- build_theme(theme, resolved_font) +
    ggplot2::theme(
      legend.position = "none",
      plot.margin = ggplot2::margin(5.5, 18, 5.5, 5.5)
    )

  plot_a <- ggplot2::ggplot(roc_rows, ggplot2::aes(x = false_positive_rate, y = true_positive_rate, color = model, linetype = model, group = model)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = true_positive_rate_lower, ymax = true_positive_rate_upper, fill = model),
      alpha = 0.12,
      linewidth = 0,
      show.legend = FALSE
    ) +
    ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_abline(intercept = 0, slope = 1, linetype = "dotted", linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_point(
      data = roc_rows[roc_rows$operating_point == "yes", ],
      ggplot2::aes(shape = model),
      size = 2.2,
      stroke = 0.35,
      fill = "white",
      show.legend = FALSE
    ) +
    ggplot2::geom_text(
      data = roc_labels,
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
      label = summary_text(metrics, "auroc", "AUROC summary"),
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
    ggplot2::labs(title = "ROC discrimination", x = "False positive rate", y = "True positive rate") +
    ggplot2::coord_cartesian(xlim = c(0, 1), ylim = c(0, 1.02), clip = "off") +
    plot_theme

  plot_b <- ggplot2::ggplot(pr_rows, ggplot2::aes(x = recall, y = precision, color = model, linetype = model, group = model)) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = precision_lower, ymax = precision_upper, fill = model),
      alpha = 0.12,
      linewidth = 0,
      show.legend = FALSE
    ) +
    ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_hline(yintercept = prevalence, linetype = "dotted", linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::annotate(
      "text",
      x = 0.02,
      y = prevalence + 0.025,
      label = "Prevalence baseline",
      hjust = 0,
      vjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::geom_point(
      data = pr_rows[pr_rows$operating_point == "yes", ],
      ggplot2::aes(shape = model),
      size = 2.2,
      stroke = 0.35,
      fill = "white",
      show.legend = FALSE
    ) +
    ggplot2::geom_text(
      data = pr_labels,
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
      label = summary_text(metrics, "auprc", "AUPRC summary"),
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
    ggplot2::labs(title = "Precision-recall under imbalance", x = "Recall", y = "Precision") +
    ggplot2::coord_cartesian(xlim = c(0, 1), ylim = c(0, 1.02), clip = "off") +
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
    resolved_font = resolved_font
  )
}

build_figure <- function(spec_path) {
  payload <- create_plot(spec_path)
  spec <- payload$spec
  theme <- payload$theme
  profile <- payload$profile
  resolved_font <- payload$resolved_font
  figure_plot <- payload$plot
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
      "paired_roc_and_pr_panels",
      "uncertainty_ribbons_for_curve_stability",
      "operating_point_markers_and_direct_labels",
      "prevalence_baseline_in_pr_panel",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      reference_line_count = 2,
      annotation_count = 8,
      operating_point_count = 6,
      uncertainty_band_count = 6
    )
  )
  outputs
}
