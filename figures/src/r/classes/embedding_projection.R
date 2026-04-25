repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_coordinate_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$sample_id <- as.character(rows$sample_id)
  rows$biological_state <- as.character(rows$biological_state)
  rows$domain <- as.character(rows$domain)
  rows$highlight_label <- as.character(rows$highlight_label)
  rows <- rows[order(rows$biological_state, rows$domain, rows$sample_id), ]
  rows
}

load_summary_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$biological_state <- as.character(rows$biological_state)
  rows$label_cluster <- as.character(rows$label_cluster)
  rows <- rows[order(rows$display_order), ]
  rows
}

build_source_data <- function(spec, coordinate_rows, summary_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    coordinate_rows,
    c(
      "sample_id",
      "biological_state",
      "domain",
      "embedding_1",
      "embedding_2",
      "local_density",
      "highlight_label"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    summary_rows,
    c(
      "biological_state",
      "centroid_x",
      "centroid_y",
      "display_order",
      "sample_count",
      "cross_domain_fraction",
      "label_cluster"
    )
  )
  list(coordinates = coordinate_rows, summary = summary_rows)
}

state_colors <- function(theme) {
  c(
    "Quiescent" = theme$palette$categorical[[1]],
    "Inflammatory" = theme$palette$categorical[[2]],
    "Proliferative" = theme$palette$categorical[[3]],
    "Fibrotic" = theme$palette$categorical[[4]]
  )
}

support_label <- function(rows) {
  sprintf("%.0f%% / n=%d", rows$cross_domain_fraction * 100, rows$sample_count)
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
      legend.position = "bottom",
      legend.box = "horizontal",
      plot.margin = ggplot2::margin(8, 14, 10, 8)
    )

  coordinate_rows <- load_coordinate_rows(file.path(repo_root, spec$data_inputs[[1]]))
  summary_rows <- load_summary_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, coordinate_rows, summary_rows)
  palette <- state_colors(theme)

  labels <- source_rows$summary[source_rows$summary$label_cluster == "yes", ]
  labels$cluster_label <- sprintf("%s\nn=%d", labels$biological_state, labels$sample_count)

  plot_a <- ggplot2::ggplot(
    source_rows$coordinates,
    ggplot2::aes(
      x = embedding_1,
      y = embedding_2,
      color = biological_state,
      shape = domain,
      size = local_density
    )
  ) +
    ggplot2::geom_hline(yintercept = 0, linewidth = 0.3, color = theme$palette$neutral[[3]]) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.3, color = theme$palette$neutral[[3]]) +
    ggplot2::geom_point(alpha = 0.88, stroke = 0.45) +
    ggplot2::geom_label(
      data = labels,
      ggplot2::aes(x = centroid_x, y = centroid_y + 0.28, label = cluster_label),
      inherit.aes = FALSE,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      label.size = 0.18,
      label.padding = grid::unit(0.10, "lines"),
      fill = theme$export_defaults$background,
      color = theme$palette$neutral[[1]],
      alpha = 0.88
    ) +
    ggplot2::scale_color_manual(values = palette) +
    ggplot2::scale_shape_manual(values = c("Cohort A" = 16, "Cohort B" = 15, "Cohort C" = 17)) +
    ggplot2::scale_size_continuous(range = c(1.6, 3.5), guide = "none") +
    ggplot2::labs(title = "Embedding projection", x = "UMAP 1", y = "UMAP 2", color = "State", shape = "Domain") +
    plot_theme +
    ggplot2::theme(legend.title = ggplot2::element_text(size = as.numeric(theme$typography$annotation_font_size_pt)))

  support_rows <- source_rows$summary[nrow(source_rows$summary):1, ]
  support_rows$biological_state <- factor(support_rows$biological_state, levels = support_rows$biological_state)
  support_rows$label_value <- support_label(support_rows)

  plot_b <- ggplot2::ggplot(support_rows, ggplot2::aes(x = cross_domain_fraction, y = biological_state, fill = biological_state)) +
    ggplot2::geom_vline(xintercept = 0.5, linewidth = 0.4, linetype = "dashed", color = theme$palette$neutral[[2]]) +
    ggplot2::geom_col(width = 0.68, color = theme$palette$neutral[[1]], linewidth = 0.35, alpha = 0.9, show.legend = FALSE) +
    ggplot2::geom_text(
      ggplot2::aes(label = label_value, x = cross_domain_fraction + 0.015),
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = 0.5,
      y = 0.42,
      label = "50% mixed-domain reference",
      hjust = 0.5,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_fill_manual(values = palette) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Cross-domain support", x = "Cross-domain support", y = NULL) +
    ggplot2::coord_cartesian(xlim = c(0, 0.82), clip = "off") +
    plot_theme +
    ggplot2::theme(
      legend.position = "none",
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  figure_plot <- (plot_a + plot_b + patchwork::plot_layout(ncol = 2, widths = c(1.25, 0.95))) +
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
    coordinates = source_rows$coordinates,
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
      "density_aware_cluster_labels",
      "domain_shape_encoding",
      "state_color_encoding_not_geometry_only",
      "cross_domain_support_panel",
      "vector_first_export"
    ),
    list(
      panel_count = 2,
      highlight_label_count = sum(payload$summary$label_cluster == "yes"),
      annotation_count = sum(payload$summary$label_cluster == "yes") + nrow(payload$summary) + 1,
      reference_line_count = 3,
      domain_count = length(unique(payload$coordinates$domain))
    )
  )
  outputs
}
