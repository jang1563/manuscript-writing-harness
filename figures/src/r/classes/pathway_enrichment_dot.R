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

  rows <- read.csv(resolve_data_input(spec, 1), stringsAsFactors = FALSE, check.names = FALSE)
  rows <- rows[order(rows$gene_ratio, decreasing = TRUE), ]
  if (nrow(rows) > 0) {
    rows$pathway <- factor(rows$pathway, levels = rev(rows$pathway))
  } else {
    rows <- data.frame(
      pathway = character(),
      gene_ratio = numeric(),
      neg_log10_fdr = numeric(),
      gene_count = integer(),
      direction = character(),
      highlight_order = integer(),
      stringsAsFactors = FALSE
    )
  }
  write_source_csv(
    file.path(repo_root, source_data_mapping(spec)$a),
    rows,
    c("pathway", "gene_ratio", "neg_log10_fdr", "gene_count", "direction", "highlight_order")
  )

  if (nrow(rows) > 0) {
    plot <- ggplot2::ggplot(rows, ggplot2::aes(x = gene_ratio, y = pathway, color = direction, size = gene_count)) +
      ggplot2::geom_point(alpha = 0.85) +
      ggplot2::scale_color_manual(values = c("up" = theme$palette$categorical[[2]], "down" = theme$palette$categorical[[1]])) +
      ggplot2::geom_text(
        ggplot2::aes(label = sprintf("%.1f", neg_log10_fdr), x = gene_ratio + 0.01),
        hjust = 0,
        size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
        color = theme$palette$neutral[[2]]
      ) +
      ggplot2::labs(title = "Pathway enrichment dot plot", x = "Gene ratio", y = NULL) +
      plot_theme +
      ggplot2::theme(
        plot.tag = ggplot2::element_text(size = as.numeric(theme$panel_labels$font_size_pt), face = theme$panel_labels$font_weight, family = resolved_font$family)
      )
  } else {
    plot <- ggplot2::ggplot() +
      ggplot2::annotate(
        "text",
        x = 0.5,
        y = 0.5,
        label = "No enriched pathways\nfor current fgsea profile",
        size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
        color = theme$palette$neutral[[2]],
        family = resolved_font$family
      ) +
      ggplot2::coord_cartesian(xlim = c(0, 1), ylim = c(0, 1), clip = "off") +
      ggplot2::labs(title = "Pathway enrichment dot plot", x = "Gene ratio", y = NULL) +
      plot_theme +
      ggplot2::theme(
        axis.text.y = ggplot2::element_blank(),
        axis.ticks.y = ggplot2::element_blank(),
        plot.tag = ggplot2::element_text(size = as.numeric(theme$panel_labels$font_size_pt), face = theme$panel_labels$font_weight, family = resolved_font$family)
      )
  }
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
      "dot_size_encodes_gene_count",
      "annotation_for_significance_strength",
      "direction_color_encoding",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      annotation_count = nrow(rows)
    )
  )
  outputs
}
