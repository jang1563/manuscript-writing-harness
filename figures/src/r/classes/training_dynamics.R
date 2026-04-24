repo_root <- getOption("manuscript.figure.repo_root")
if (is.null(repo_root)) {
  stop("manuscript.figure.repo_root option is required")
}
source(file.path(repo_root, "figures", "src", "r", "common.R"))

load_loss_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows$split <- as.character(rows$split)
  rows <- rows[order(rows$display_order, rows$split != "train", rows$epoch), ]
  rows
}

load_metric_rows <- function(path) {
  rows <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  rows$model <- as.character(rows$model)
  rows$label_epoch <- as.character(rows$label_epoch)
  rows$best_epoch <- as.character(rows$best_epoch)
  rows <- rows[order(rows$display_order, rows$epoch), ]
  rows
}

build_source_data <- function(spec, loss_rows, metric_rows) {
  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    loss_rows,
    c("model", "display_order", "epoch", "split", "loss")
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    metric_rows,
    c("model", "display_order", "epoch", "auroc", "label_epoch", "best_epoch")
  )
  list(loss = loss_rows, metric = metric_rows)
}

style_maps <- function(theme, models) {
  colors <- c(
    theme$palette$categorical[[1]],
    theme$palette$categorical[[2]],
    theme$palette$categorical[[3]]
  )
  shapes <- c(16, 15, 18)
  data.frame(
    model = models,
    color = colors[seq_along(models)],
    shape = shapes[seq_along(models)],
    stringsAsFactors = FALSE
  )
}

label_offsets <- function() {
  data.frame(
    model = c("Foundation model", "Hybrid GNN", "CNN baseline"),
    dx = c(1.18, 1.18, 1.18),
    dy = c(0.0, -0.02, -0.04),
    stringsAsFactors = FALSE
  )
}

summary_text <- function(metric_rows, models) {
  lines <- c("Best validation AUROC")
  for (model in models) {
    subset <- metric_rows[metric_rows$model == model, ]
    best <- subset[which.max(subset$auroc), , drop = FALSE][1, , drop = FALSE]
    lines <- c(lines, sprintf("%s: %.2f", model, best$auroc))
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
  plot_theme <- build_theme(theme, resolved_font) +
    ggplot2::theme(
      legend.position = "none",
      plot.margin = ggplot2::margin(5.5, 22, 5.5, 5.5)
    )

  loss_rows <- load_loss_rows(file.path(repo_root, spec$data_inputs[[1]]))
  metric_rows <- load_metric_rows(file.path(repo_root, spec$data_inputs[[2]]))
  source_rows <- build_source_data(spec, loss_rows, metric_rows)

  models <- unique(metric_rows$model)
  styles <- style_maps(theme, models)
  offsets <- label_offsets()

  loss_plot_rows <- merge(source_rows$loss, styles, by = "model", sort = FALSE)
  loss_labels <- merge(
    loss_plot_rows[loss_plot_rows$split == "validation" & loss_plot_rows$epoch == max(loss_plot_rows$epoch), ],
    offsets,
    by = "model",
    sort = FALSE
  )
  loss_labels$label_x <- loss_labels$epoch + loss_labels$dx
  loss_labels$label_y <- loss_labels$loss + loss_labels$dy

  plot_a <- ggplot2::ggplot(loss_plot_rows, ggplot2::aes(x = epoch, y = loss, color = model, group = interaction(model, split))) +
    ggplot2::geom_line(ggplot2::aes(linetype = split, alpha = split), linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_text(
      data = loss_labels,
      ggplot2::aes(x = label_x, y = label_y, label = model),
      inherit.aes = FALSE,
      hjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(loss_plot_rows$epoch) + 1.18,
      y = max(loss_plot_rows$loss) - 0.04,
      label = "solid = validation",
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::annotate(
      "text",
      x = max(loss_plot_rows$epoch) + 1.18,
      y = max(loss_plot_rows$loss) - 0.12,
      label = "dashed = train",
      hjust = 1,
      vjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::scale_color_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_linetype_manual(values = c("train" = "dashed", "validation" = "solid")) +
    ggplot2::scale_alpha_manual(values = c("train" = 0.65, "validation" = 0.95)) +
    ggplot2::labs(title = "Training and validation loss", x = "Epoch", y = "Loss") +
    ggplot2::coord_cartesian(xlim = c(min(loss_plot_rows$epoch), max(loss_plot_rows$epoch) + 1.3), ylim = c(0.2, max(loss_plot_rows$loss) + 0.12), clip = "off") +
    plot_theme

  metric_plot_rows <- merge(source_rows$metric, styles, by = "model", sort = FALSE)
  metric_labels <- merge(
    metric_plot_rows[metric_plot_rows$label_epoch == "yes", ],
    offsets,
    by = "model",
    sort = FALSE
  )
  metric_labels$label_x <- metric_labels$epoch + metric_labels$dx
  metric_labels$label_y <- metric_labels$auroc + metric_labels$dy / 2
  best_rows <- metric_plot_rows[metric_plot_rows$best_epoch == "yes", ]

  plot_b <- ggplot2::ggplot(metric_plot_rows, ggplot2::aes(x = epoch, y = auroc, color = model, group = model)) +
    ggplot2::geom_line(linewidth = 0.8, show.legend = FALSE) +
    ggplot2::geom_point(ggplot2::aes(shape = model), size = 2.2, show.legend = FALSE) +
    ggplot2::geom_point(
      data = best_rows,
      ggplot2::aes(x = epoch, y = auroc, color = model),
      inherit.aes = FALSE,
      shape = 8,
      size = 3.2,
      show.legend = FALSE
    ) +
    ggplot2::geom_text(
      data = metric_labels,
      ggplot2::aes(x = label_x, y = label_y, label = model),
      inherit.aes = FALSE,
      hjust = 1,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::annotate(
      "label",
      x = max(metric_plot_rows$epoch) + 0.9,
      y = min(metric_plot_rows$auroc) + 0.02,
      label = summary_text(metric_plot_rows, models),
      hjust = 1,
      vjust = 0,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      label.size = 0.25,
      fill = "white",
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::scale_color_manual(values = stats::setNames(styles$color, styles$model)) +
    ggplot2::scale_shape_manual(values = stats::setNames(styles$shape, styles$model)) +
    ggplot2::labs(title = "Validation AUROC trajectory", x = "Epoch", y = "Validation AUROC") +
    ggplot2::coord_cartesian(xlim = c(min(metric_plot_rows$epoch), max(metric_plot_rows$epoch) + 1.3), ylim = c(0.5, max(metric_plot_rows$auroc) + 0.05), clip = "off") +
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
      "paired_loss_and_metric_panels",
      "split_encoding_not_color_only",
      "direct_labels_at_final_epoch",
      "best_checkpoint_markers",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      direct_label_count = 6,
      annotation_count = 9,
      best_checkpoint_count = 3
    )
  )
  outputs
}
