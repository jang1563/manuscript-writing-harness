repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_rank_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$feature <- as.character(rows$feature)
  rows$feature_group <- as.character(rows$feature_group)
  rows$label_feature <- as.character(rows$label_feature)
  rows <- rows[order(rows$display_order), ]
  rows
}

load_effect_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$feature <- as.character(rows$feature)
  rows$feature_group <- as.character(rows$feature_group)
  rows$expected_direction <- as.character(rows$expected_direction)
  rows$label_feature <- as.character(rows$label_feature)
  rows <- rows[order(rows$display_order), ]
  rows
}

build_source_data <- function(spec, rank_rows, effect_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    rank_rows,
    c("feature", "feature_group", "display_order", "mean_abs_importance", "label_feature")
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    effect_rows,
    c(
      "feature",
      "feature_group",
      "display_order",
      "signed_effect",
      "expected_direction",
      "label_feature"
    )
  )
  list(rank = rank_rows, effect = effect_rows)
}

group_colors <- function(theme) {
  c(
    "Fibrotic remodeling" = theme$palette$categorical[[1]],
    "Inflammatory state" = theme$palette$categorical[[2]],
    "Proliferative state" = theme$palette$categorical[[3]],
    "Immune activation" = theme$palette$categorical[[4]],
    "Nuisance covariate" = theme$palette$neutral[[2]]
  )
}

direction_color <- function(theme, expected_direction, signed_effect) {
  if (expected_direction == "neutral") {
    return(theme$palette$neutral[[2]])
  }
  if (signed_effect >= 0) {
    return(theme$palette$categorical[[1]])
  }
  theme$palette$categorical[[2]]
}

importance_summary <- function(rank_rows) {
  total <- sum(rank_rows$mean_abs_importance)
  labeled <- sum(rank_rows$mean_abs_importance[rank_rows$label_feature == "yes"])
  nuisance <- sum(rank_rows$mean_abs_importance[rank_rows$feature_group == "Nuisance covariate"])
  sprintf("Labeled top features: %.0f%%\nNuisance covariates: %.0f%%", labeled / total * 100, nuisance / total * 100)
}

direction_summary <- function(effect_rows) {
  aligned <- 0
  labeled <- 0
  for (i in seq_len(nrow(effect_rows))) {
    row <- effect_rows[i, , drop = FALSE]
    if (row$label_feature != "yes") {
      next
    }
    labeled <- labeled + 1
    if ((row$expected_direction == "increases_response" && row$signed_effect > 0) ||
        (row$expected_direction == "decreases_response" && row$signed_effect < 0)) {
      aligned <- aligned + 1
    }
  }
  sprintf("Expected direction matched: %d/%d", aligned, labeled)
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
      plot.margin = ggplot2::margin(8, 18, 10, 8)
    )

  rank_rows <- load_rank_rows(file.path(repo_root, spec$data_inputs[[1]]))
  effect_rows <- load_effect_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, rank_rows, effect_rows)
  palette <- group_colors(theme)

  rank_plot_rows <- source_rows$rank[nrow(source_rows$rank):1, ]
  rank_plot_rows$feature <- factor(rank_plot_rows$feature, levels = rank_plot_rows$feature)
  rank_plot_rows$label_value <- sprintf("%.1f%%", rank_plot_rows$mean_abs_importance * 100)

  plot_a <- ggplot2::ggplot(rank_plot_rows, ggplot2::aes(x = mean_abs_importance, y = feature, fill = feature_group)) +
    ggplot2::geom_col(width = 0.72, color = theme$palette$neutral[[1]], linewidth = 0.35, alpha = 0.9) +
    ggplot2::geom_text(
      ggplot2::aes(label = label_value, x = mean_abs_importance + 0.005),
      hjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(rank_plot_rows$mean_abs_importance) + 0.075,
      y = 0.55,
      label = importance_summary(source_rows$rank),
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_fill_manual(values = palette) +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Feature importance rank", x = "Mean absolute importance", y = NULL) +
    ggplot2::coord_cartesian(xlim = c(0, max(rank_plot_rows$mean_abs_importance) + 0.08), clip = "off") +
    plot_theme +
    ggplot2::theme(
      axis.line.y = ggplot2::element_blank(),
      axis.ticks.y = ggplot2::element_blank()
    )

  effect_plot_rows <- source_rows$effect[nrow(source_rows$effect):1, ]
  effect_plot_rows$feature <- factor(effect_plot_rows$feature, levels = effect_plot_rows$feature)
  effect_plot_rows$fill_color <- vapply(
    seq_len(nrow(effect_plot_rows)),
    function(i) direction_color(theme, effect_plot_rows$expected_direction[[i]], effect_plot_rows$signed_effect[[i]]),
    character(1)
  )
  effect_plot_rows$label_value <- sprintf("%+.1f%%", effect_plot_rows$signed_effect * 100)

  plot_b <- ggplot2::ggplot(effect_plot_rows, ggplot2::aes(x = signed_effect, y = feature)) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_col(ggplot2::aes(fill = fill_color), width = 0.72, color = theme$palette$neutral[[1]], linewidth = 0.35, show.legend = FALSE) +
    ggplot2::geom_text(
      ggplot2::aes(
        label = label_value,
        x = ifelse(signed_effect >= 0, signed_effect + 0.006, signed_effect - 0.006),
        hjust = ifelse(signed_effect >= 0, 0, 1)
      ),
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(abs(effect_plot_rows$signed_effect)) + 0.06,
      y = 0.55,
      label = direction_summary(source_rows$effect),
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_fill_identity() +
    ggplot2::scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
    ggplot2::labs(title = "Signed effect on predicted response", x = "Signed effect", y = NULL) +
    ggplot2::coord_cartesian(
      xlim = c(-max(abs(effect_plot_rows$signed_effect)) - 0.07, max(abs(effect_plot_rows$signed_effect)) + 0.07),
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
      "ranked_feature_importance_panel",
      "signed_directional_effect_panel",
      "group_semantic_encoding",
      "zero_centered_effect_reference",
      "vector_first_export"
    ),
    list(
      panel_count = 2,
      highlight_label_count = 6,
      annotation_count = 14,
      reference_line_count = 1
    )
  )
  outputs
}
