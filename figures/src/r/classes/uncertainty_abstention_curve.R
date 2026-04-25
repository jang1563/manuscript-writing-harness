repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

target_risk <- 0.08
target_coverage <- 0.80

load_curve_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows$operating_point <- as.character(rows$operating_point)
  rows <- rows[order(rows$display_order, rows$coverage), ]
  rows
}

load_summary_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows$label_model <- as.character(rows$label_model)
  rows <- rows[order(rows$display_order), ]
  rows
}

build_source_data <- function(spec, curve_rows, summary_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    curve_rows,
    c(
      "model",
      "display_order",
      "coverage",
      "risk",
      "risk_lower",
      "risk_upper",
      "operating_point"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    summary_rows,
    c(
      "model",
      "display_order",
      "risk_at_full_coverage",
      "risk_at_80_coverage",
      "coverage_at_target_risk",
      "abstained_fraction_at_target",
      "label_model"
    )
  )
  list(curves = curve_rows, summary = summary_rows)
}

style_maps <- function(theme, summary_rows) {
  colors <- c(
    theme$palette$categorical[[1]],
    theme$palette$categorical[[2]],
    theme$palette$categorical[[3]]
  )
  line_types <- c("solid", "dashed", "dotdash")
  shapes <- c(16, 15, 18)
  data.frame(
    model = summary_rows$model,
    color = colors[seq_len(nrow(summary_rows))],
    line_type = line_types[seq_len(nrow(summary_rows))],
    shape = shapes[seq_len(nrow(summary_rows))],
    stringsAsFactors = FALSE
  )
}

label_offsets <- function() {
  data.frame(
    model = c("Foundation model", "Hybrid GNN", "CNN baseline"),
    dx = c(0.018, 0.018, 0.018),
    dy = c(-0.010, 0.006, 0.012),
    stringsAsFactors = FALSE
  )
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

  curve_rows <- load_curve_rows(file.path(repo_root, spec$data_inputs[[1]]))
  summary_rows <- load_summary_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, curve_rows, summary_rows)
  styles <- style_maps(theme, source_rows$summary)
  offsets <- label_offsets()

  curve_plot_rows <- merge(source_rows$curves, styles, by = "model", sort = FALSE)
  curve_labels <- merge(
    curve_plot_rows[curve_plot_rows$operating_point == "yes", ],
    offsets,
    by = "model",
    sort = FALSE
  )
  curve_labels$label_x <- curve_labels$coverage + curve_labels$dx
  curve_labels$label_y <- curve_labels$risk + curve_labels$dy

  plot_theme <- build_theme(theme, resolved_font) +
    ggplot2::theme(
      legend.position = "none",
      plot.margin = ggplot2::margin(8, 18, 10, 8)
    )

  plot_a <- ggplot2::ggplot(
    curve_plot_rows,
    ggplot2::aes(x = coverage, y = risk, color = model, linetype = model, group = model)
  ) +
    ggplot2::geom_ribbon(
      ggplot2::aes(ymin = risk_lower, ymax = risk_upper, fill = model),
      alpha = 0.13,
      linewidth = 0,
      show.legend = FALSE
    ) +
    ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_hline(yintercept = target_risk, linetype = "dotted", linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_vline(xintercept = target_coverage, linetype = "dashed", linewidth = 0.35, color = theme$palette$neutral[[3]]) +
    ggplot2::geom_point(
      data = curve_plot_rows[curve_plot_rows$operating_point == "yes", ],
      ggplot2::aes(shape = model),
      size = 2.2,
      stroke = 0.35,
      fill = "white",
      show.legend = FALSE
    ) +
    ggplot2::geom_text(
      data = curve_labels,
      ggplot2::aes(x = label_x, y = label_y, label = model),
      inherit.aes = FALSE,
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = 0.50,
      y = target_risk + 0.006,
      label = "8% target risk",
      hjust = 0,
      vjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::annotate(
      "text",
      x = target_coverage + 0.012,
      y = 0.185,
      label = "80% coverage\noperating points",
      hjust = 0,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_color_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_fill_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_linetype_manual(values = stats::setNames(styles$line_type, styles$model)) +
    ggplot2::scale_shape_manual(values = stats::setNames(styles$shape, styles$model)) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::scale_y_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Coverage-risk curve", x = "Coverage retained", y = "Observed risk") +
    ggplot2::coord_cartesian(xlim = c(0.48, 1.02), ylim = c(0, 0.21), clip = "off") +
    plot_theme

  support_rows <- source_rows$summary[nrow(source_rows$summary):1, ]
  support_rows$model <- factor(support_rows$model, levels = support_rows$model)
  support_rows$label_value <- sprintf(
    "%.0f%% retained\nrisk@80%% %.1f%%",
    support_rows$coverage_at_target_risk * 100,
    support_rows$risk_at_80_coverage * 100
  )

  plot_b <- ggplot2::ggplot(support_rows, ggplot2::aes(x = coverage_at_target_risk, y = model, fill = model)) +
    ggplot2::geom_vline(xintercept = target_coverage, linewidth = 0.4, linetype = "dashed", color = theme$palette$neutral[[2]]) +
    ggplot2::geom_col(width = 0.68, color = theme$palette$neutral[[1]], linewidth = 0.35, alpha = 0.9, show.legend = FALSE) +
    ggplot2::geom_text(
      ggplot2::aes(label = label_value, x = coverage_at_target_risk + 0.015),
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = target_coverage,
      y = 0.42,
      label = "80% target coverage",
      hjust = 0.5,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_fill_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Target-risk coverage", x = "Coverage at risk <= 8%", y = NULL) +
    ggplot2::coord_cartesian(xlim = c(0, 1), clip = "off") +
    plot_theme +
    ggplot2::theme(
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  figure_plot <- (plot_a + plot_b + patchwork::plot_layout(ncol = 2, widths = c(1.15, 0.95))) +
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
    resolved_font = resolved_font,
    curves = source_rows$curves,
    summary = source_rows$summary
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
      "coverage_risk_curve_panel",
      "uncertainty_band_for_risk",
      "operating_point_markers_and_direct_labels",
      "target_risk_reference",
      "selective_prediction_summary_panel",
      "vector_first_export"
    ),
    list(
      panel_count = 2,
      reference_line_count = 3,
      annotation_count = 2 + nrow(payload$summary) + sum(payload$curves$operating_point == "yes"),
      operating_point_count = sum(payload$curves$operating_point == "yes"),
      uncertainty_band_count = nrow(payload$summary)
    )
  )
  outputs
}
