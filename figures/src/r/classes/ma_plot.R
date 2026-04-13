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
  rows$point_category <- ifelse(abs(rows$log2_fc) >= 1 & rows$padj <= 0.05, "highlighted", "background")
  write_source_csv(
    file.path(repo_root, source_data_mapping(spec)$a),
    rows,
    c("gene", "mean_expression", "log2_fc", "padj", "highlight_label", "point_category")
  )

  plot <- ggplot2::ggplot(rows, ggplot2::aes(x = mean_expression, y = log2_fc)) +
    ggplot2::geom_hline(yintercept = c(-1, 0, 1), linewidth = c(0.4, 0.5, 0.4), linetype = c("dashed", "solid", "dashed"), color = theme$palette$neutral[[2]]) +
    ggplot2::geom_point(ggplot2::aes(color = point_category, alpha = point_category), size = 1.8) +
    ggplot2::scale_color_manual(values = c("background" = theme$palette$neutral[[3]], "highlighted" = theme$palette$categorical[[2]])) +
    ggplot2::scale_alpha_manual(values = c("background" = 0.5, "highlighted" = 0.9)) +
    ggplot2::geom_text(
      data = rows[rows$highlight_label == "yes", ],
      ggplot2::aes(x = mean_expression + 0.25, y = log2_fc + 0.12, label = gene),
      inherit.aes = FALSE,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::labs(title = "MA plot", x = "Mean expression", y = "log2 fold change") +
    plot_theme +
    ggplot2::theme(
      plot.tag = ggplot2::element_text(size = as.numeric(theme$panel_labels$font_size_pt), face = theme$panel_labels$font_weight, family = resolved_font$family)
    )
  plot <- plot + patchwork::plot_annotation(tag_levels = "a")
  list(
    plot = plot,
    spec = spec,
    theme = theme,
    profile = profile,
    resolved_font = resolved_font,
    rows = rows
  )
}

build_figure <- function(spec_path) {
  payload <- create_plot(spec_path)
  spec <- payload$spec
  theme <- payload$theme
  profile <- payload$profile
  resolved_font <- payload$resolved_font
  plot <- payload$plot
  rows <- payload$rows
  output_dir <- file.path(repo_root, spec$renderers$r$output_dir)
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  stem <- spec$figure_id
  svg_path <- file.path(output_dir, sprintf("%s.svg", stem))
  pdf_path <- file.path(output_dir, sprintf("%s.pdf", stem))
  png_path <- file.path(output_dir, sprintf("%s.png", stem))
  width_in <- mm_to_inches(as.numeric(spec$size$width_mm))
  height_in <- mm_to_inches(as.numeric(spec$size$height_mm))

  svglite::svglite(file = svg_path, width = width_in, height = height_in, bg = theme$export_defaults$background, system_fonts = list(sans = resolved_font$family))
  print(plot)
  grDevices::dev.off()
  grDevices::cairo_pdf(file = pdf_path, width = width_in, height = height_in, bg = theme$export_defaults$background, family = resolved_font$family)
  print(plot)
  grDevices::dev.off()
  ragg::agg_png(filename = png_path, width = width_in, height = height_in, units = "in", res = as.numeric(profile$preview_dpi), background = theme$export_defaults$background)
  print(plot)
  grDevices::dev.off()

  outputs <- list(svg = sub(paste0("^", repo_root, "/"), "", svg_path), pdf = sub(paste0("^", repo_root, "/"), "", pdf_path), png = sub(paste0("^", repo_root, "/"), "", png_path))
  write_manifest(
    repo_root,
    spec,
    profile,
    resolved_font,
    spec_path,
    "r",
    outputs,
    list(
      "threshold_guides_for_mean_difference",
      "selective_gene_labels_for_extreme_points",
      "de_emphasized_background_points",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      highlight_label_count = sum(rows$highlight_label == "yes"),
      threshold_line_count = 2,
      reference_line_count = 1
    )
  )
  outputs
}
