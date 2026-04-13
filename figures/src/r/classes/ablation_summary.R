repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_primary_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$variant <- as.character(rows$variant)
  rows$module_group <- as.character(rows$module_group)
  rows$label_variant <- as.character(rows$label_variant)
  rows <- rows[order(rows$display_order), ]
  rows
}

load_secondary_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$variant <- as.character(rows$variant)
  rows$module_group <- as.character(rows$module_group)
  rows$metric <- as.character(rows$metric)
  rows$label_variant <- as.character(rows$label_variant)
  rows <- rows[order(rows$display_order, rows$metric), ]
  rows
}

build_source_data <- function(spec, primary_rows, secondary_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    primary_rows,
    c("variant", "module_group", "display_order", "auroc", "delta_auroc", "label_variant")
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    secondary_rows,
    c("variant", "module_group", "display_order", "metric", "delta_value", "label_variant")
  )
  list(primary = primary_rows, secondary = secondary_rows)
}

group_colors <- function(theme) {
  c(
    "Full system" = theme$palette$neutral[[1]],
    "Architectural module" = theme$palette$categorical[[1]],
    "Training recipe" = theme$palette$categorical[[3]],
    "Objective design" = theme$palette$categorical[[2]],
    "Auxiliary input" = theme$palette$categorical[[4]]
  )
}

summary_text <- function(primary_rows, secondary_rows) {
  largest_drop <- primary_rows[primary_rows$display_order != 1, ][which.min(primary_rows$delta_auroc[primary_rows$display_order != 1]), , drop = FALSE][1, , drop = FALSE]
  ece_rows <- secondary_rows[secondary_rows$metric == "ECE" & secondary_rows$display_order != 1, ]
  worst_ece <- ece_rows[which.max(ece_rows$delta_value), , drop = FALSE][1, , drop = FALSE]
  sprintf("Largest AUROC loss:\n%s\nWorst ECE increase:\n%s", largest_drop$variant, worst_ece$variant)
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

  primary_rows <- load_primary_rows(file.path(repo_root, spec$data_inputs[[1]]))
  secondary_rows <- load_secondary_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, primary_rows, secondary_rows)
  palette <- group_colors(theme)

  primary_plot_rows <- source_rows$primary[nrow(source_rows$primary):1, ]
  primary_plot_rows$variant <- factor(primary_plot_rows$variant, levels = primary_plot_rows$variant)
  primary_plot_rows$auroc_label <- sprintf("%.3f", primary_plot_rows$auroc)

  plot_a <- ggplot2::ggplot(primary_plot_rows, ggplot2::aes(x = delta_auroc, y = variant, fill = module_group)) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_col(width = 0.72, color = theme$palette$neutral[[1]], linewidth = 0.35, alpha = 0.9) +
    ggplot2::geom_text(
      ggplot2::aes(
        label = auroc_label,
        x = ifelse(delta_auroc < 0, delta_auroc - 0.003, delta_auroc + 0.003),
        hjust = ifelse(delta_auroc < 0, 1, 0)
      ),
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::scale_fill_manual(values = palette) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "AUROC drop vs full model", x = "AUROC drop vs full model", y = NULL) +
    ggplot2::coord_cartesian(xlim = c(min(primary_plot_rows$delta_auroc) - 0.018, 0.02), clip = "off") +
    plot_theme +
    ggplot2::theme(
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  secondary_plot_rows <- source_rows$secondary
  variant_levels <- primary_plot_rows$variant
  secondary_plot_rows$variant <- factor(secondary_plot_rows$variant, levels = levels(variant_levels))
  secondary_plot_rows$metric <- factor(secondary_plot_rows$metric, levels = c("AUPRC", "ECE"))
  secondary_plot_rows$label_value <- sprintf("%+.1f%%", secondary_plot_rows$delta_value * 100)

  plot_b <- ggplot2::ggplot(secondary_plot_rows, ggplot2::aes(x = delta_value, y = variant, color = module_group, shape = metric)) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_segment(
      ggplot2::aes(x = 0, xend = delta_value, yend = variant),
      linewidth = 0.5,
      position = ggplot2::position_dodge(width = 0.45),
      alpha = 0.7
    ) +
    ggplot2::geom_point(size = 2.4, stroke = 0.4, position = ggplot2::position_dodge(width = 0.45)) +
    ggplot2::annotate(
      "text",
      x = max(abs(secondary_plot_rows$delta_value)) + 0.017,
      y = 0.55,
      label = summary_text(source_rows$primary, source_rows$secondary),
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(abs(secondary_plot_rows$delta_value)) + 0.015,
      y = 1.2,
      label = "circle = AUPRC",
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(abs(secondary_plot_rows$delta_value)) + 0.015,
      y = 1.65,
      label = "triangle = ECE",
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_color_manual(values = palette) +
    ggplot2::scale_shape_manual(values = c("AUPRC" = 16, "ECE" = 17)) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Secondary metric shifts", x = "Secondary metric shift", y = NULL) +
    ggplot2::coord_cartesian(
      xlim = c(-max(abs(secondary_plot_rows$delta_value)) - 0.02, max(abs(secondary_plot_rows$delta_value)) + 0.02),
      clip = "off"
    ) +
    plot_theme +
    ggplot2::theme(
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  figure_plot <- (plot_a + plot_b + patchwork::plot_layout(ncol = 2)) +
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
      "ranked_primary_metric_drop_panel",
      "secondary_metric_shift_panel",
      "group_semantic_encoding",
      "metric_shape_encoding_not_color_only",
      "zero_centered_effect_reference",
      "vector_first_export"
    ),
    list(
      panel_count = 2,
      highlight_label_count = 5,
      annotation_count = 10,
      reference_line_count = 2
    )
  )
  outputs
}
