repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_matrix_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$true_label <- as.character(rows$true_label)
  rows$predicted_label <- as.character(rows$predicted_label)
  rows$label_cell <- as.character(rows$label_cell)
  rows$is_diagonal <- as.character(rows$is_diagonal)
  rows <- rows[order(rows$true_order, rows$pred_order), ]
  rows
}

load_error_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$source_class <- as.character(rows$source_class)
  rows$target_class <- as.character(rows$target_class)
  rows$label_text <- as.character(rows$label_text)
  rows <- rows[order(rows$display_order), ]
  rows
}

build_source_data <- function(spec, matrix_rows, error_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    matrix_rows,
    c(
      "true_label",
      "predicted_label",
      "true_order",
      "pred_order",
      "rate",
      "count",
      "label_cell",
      "is_diagonal"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    error_rows,
    c("source_class", "target_class", "error_rate", "display_order", "label_text")
  )
  list(matrix = matrix_rows, errors = error_rows)
}

class_styles <- function(theme, labels) {
  colors <- c(
    theme$palette$categorical[[1]],
    theme$palette$categorical[[2]],
    theme$palette$categorical[[3]],
    theme$palette$categorical[[4]]
  )
  data.frame(
    class_label = labels,
    color = colors[seq_along(labels)],
    stringsAsFactors = FALSE
  )
}

macro_recall_text <- function(matrix_rows) {
  diagonal <- matrix_rows$rate[matrix_rows$is_diagonal == "yes"]
  sprintf("Macro recall: %.1f%%", mean(diagonal) * 100)
}

top_confusion_text <- function(error_rows) {
  top_row <- error_rows[which.max(error_rows$error_rate), , drop = FALSE][1, , drop = FALSE]
  sprintf("Top confusion: %s (%.0f%%)", top_row$label_text, top_row$error_rate * 100)
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
  plot_theme <- build_theme(theme, resolved_font) +
    ggplot2::theme(
      legend.position = "none",
      plot.margin = ggplot2::margin(8, 26, 10, 8)
    )

  matrix_rows <- load_matrix_rows(file.path(repo_root, spec$data_inputs[[1]]))
  error_rows <- load_error_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, matrix_rows, error_rows)

  labels <- unique(matrix_rows$true_label[order(matrix_rows$true_order)])
  styles <- class_styles(theme, labels)

  matrix_plot_rows <- source_rows$matrix
  matrix_plot_rows$true_label <- factor(matrix_plot_rows$true_label, levels = rev(labels))
  matrix_plot_rows$predicted_label <- factor(matrix_plot_rows$predicted_label, levels = labels)
  matrix_plot_rows$cell_label <- sprintf("%.0f%%\n(n=%d)", matrix_plot_rows$rate * 100, matrix_plot_rows$count)
  matrix_plot_rows$text_color <- ifelse(matrix_plot_rows$rate >= 0.58, "white", theme$palette$neutral[[1]])

  error_plot_rows <- merge(source_rows$errors, styles, by.x = "source_class", by.y = "class_label", sort = FALSE)
  error_plot_rows <- error_plot_rows[order(error_plot_rows$display_order, decreasing = TRUE), ]
  error_plot_rows$label_text <- factor(error_plot_rows$label_text, levels = error_plot_rows$label_text)

  plot_a <- ggplot2::ggplot(matrix_plot_rows, ggplot2::aes(x = predicted_label, y = true_label, fill = rate)) +
    ggplot2::geom_tile(color = "white", linewidth = 0.8) +
    ggplot2::geom_text(
      ggplot2::aes(label = cell_label, color = text_color),
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.9,
      lineheight = 0.9,
      show.legend = FALSE
    ) +
    ggplot2::scale_fill_gradient(
      low = "#F3F6FB",
      high = theme$palette$categorical[[1]],
      labels = scales::percent_format(accuracy = 1),
      limits = c(0, 1)
    ) +
    ggplot2::scale_color_identity() +
    ggplot2::labs(
      title = "Normalized confusion matrix",
      x = "Predicted label",
      y = "True label",
      fill = "Row-normalized rate"
    ) +
    ggplot2::annotate(
      "text",
      x = 1,
      y = 0.35,
      label = macro_recall_text(source_rows$matrix),
      hjust = 0,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::coord_equal(clip = "off") +
    plot_theme +
    ggplot2::theme(
      axis.text.x = ggplot2::element_text(angle = 25, hjust = 1),
      legend.key.height = grid::unit(18, "pt")
    )

  plot_b <- ggplot2::ggplot(error_plot_rows, ggplot2::aes(x = error_rate, y = label_text, fill = source_class)) +
    ggplot2::geom_col(width = 0.72, color = theme$palette$neutral[[1]], linewidth = 0.3, show.legend = FALSE) +
    ggplot2::geom_text(
      ggplot2::aes(label = sprintf("%.0f%%", error_rate * 100)),
      hjust = -0.1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::scale_fill_manual(values = stats::setNames(styles$color, styles$class_label)) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(
      title = "Dominant off-diagonal confusion",
      x = "Error rate",
      y = NULL
    ) +
    ggplot2::annotate(
      "text",
      x = max(error_plot_rows$error_rate) + 0.09,
      y = 0.55,
      label = top_confusion_text(source_rows$errors),
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::coord_cartesian(
      xlim = c(0, max(error_plot_rows$error_rate) + 0.12),
      clip = "off"
    ) +
    plot_theme +
    ggplot2::theme(
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  figure_plot <- (plot_a + plot_b + patchwork::plot_layout(ncol = 2, widths = c(1.15, 0.85))) +
    patchwork::plot_annotation(
      title = spec$title,
      tag_levels = "a"
    ) &
    ggplot2::theme(
      plot.title = ggplot2::element_text(
        size = as.numeric(theme$typography$title_font_size_pt),
        family = resolved_font$family,
        face = "bold",
        hjust = 0
      ),
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
      "row_normalized_confusion_heatmap",
      "annotated_cell_percentages",
      "off_diagonal_error_summary_panel",
      "class_level_error_interpretation",
      "vector_first_export"
    ),
    list(
      panel_count = 2,
      annotation_count = 21,
      diagonal_cell_count = 4,
      off_diagonal_summary_count = 4
    )
  )
  outputs
}
