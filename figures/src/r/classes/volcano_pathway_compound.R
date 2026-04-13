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

  gene_rows <- read.csv(file.path(repo_root, spec$data_inputs[[1]]), stringsAsFactors = FALSE, check.names = FALSE)
  pathway_rows <- read.csv(file.path(repo_root, spec$data_inputs[[2]]), stringsAsFactors = FALSE, check.names = FALSE)
  gene_rows$neg_log10_padj <- -log10(pmax(gene_rows$padj, 1e-300))
  gene_rows$significance_category <- ifelse(
    gene_rows$log2_fc >= 1 & gene_rows$padj <= 0.05,
    "up_significant",
    ifelse(gene_rows$log2_fc <= -1 & gene_rows$padj <= 0.05, "down_significant", "background")
  )
  pathway_rows$fdr_label <- sprintf("FDR %.1e", pathway_rows$fdr)
  pathway_rows <- pathway_rows[order(pathway_rows$nes, decreasing = TRUE), ]
  pathway_rows$pathway <- factor(pathway_rows$pathway, levels = rev(pathway_rows$pathway))

  mapping <- source_data_mapping(spec)
  write_source_csv(
    file.path(repo_root, mapping$a),
    gene_rows,
    c(
      "gene",
      "log2_fc",
      "padj",
      "neg_log10_padj",
      "highlight_label",
      "significance_category"
    )
  )
  write_source_csv(
    file.path(repo_root, mapping$b),
    pathway_rows,
    c("pathway", "nes", "fdr", "direction", "highlight_order", "fdr_label")
  )

  label_positions <- data.frame(
    gene = c("CXCL10", "IFIT1", "MX1", "MKI67", "TOP2A", "CDK1"),
    label_dx = c(0.18, 0.16, 0.16, -0.18, -0.18, -0.18),
    label_dy = c(0.36, 0.12, -0.12, 0.34, 0.10, -0.14),
    stringsAsFactors = FALSE
  )
  gene_labels <- merge(gene_rows[gene_rows$highlight_label == "yes", ], label_positions, by = "gene", sort = FALSE)
  gene_labels$label_x <- gene_labels$log2_fc + gene_labels$label_dx
  gene_labels$label_y <- gene_labels$neg_log10_padj + gene_labels$label_dy
  threshold_y <- -log10(0.05)

  plot_a <- ggplot2::ggplot(gene_rows, ggplot2::aes(x = log2_fc, y = neg_log10_padj)) +
    ggplot2::geom_vline(xintercept = c(-1, 1), linewidth = 0.4, linetype = "dashed", color = theme$palette$neutral[[2]]) +
    ggplot2::geom_hline(yintercept = threshold_y, linewidth = 0.4, linetype = "dashed", color = theme$palette$neutral[[2]]) +
    ggplot2::geom_point(ggplot2::aes(color = significance_category, alpha = significance_category), size = 1.8) +
    ggplot2::scale_color_manual(values = c("background" = theme$palette$neutral[[3]], "down_significant" = theme$palette$categorical[[1]], "up_significant" = theme$palette$categorical[[2]])) +
    ggplot2::scale_alpha_manual(values = c("background" = 0.55, "down_significant" = 0.92, "up_significant" = 0.92)) +
    ggplot2::geom_segment(
      data = gene_labels,
      ggplot2::aes(x = log2_fc, y = neg_log10_padj, xend = label_x, yend = label_y),
      inherit.aes = FALSE,
      linewidth = 0.35,
      color = theme$palette$neutral[[2]]
    ) +
    ggplot2::geom_text(
      data = gene_labels,
      ggplot2::aes(x = label_x, y = label_y, label = gene, hjust = ifelse(label_dx >= 0, 0, 1)),
      inherit.aes = FALSE,
      size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845,
      color = theme$palette$neutral[[1]]
    ) +
    ggplot2::labs(title = "Differential expression volcano", x = "log2 fold change", y = "-log10 adjusted P") +
    ggplot2::coord_cartesian(xlim = c(-max(abs(gene_rows$log2_fc)) - 0.8, max(abs(gene_rows$log2_fc)) + 0.8), ylim = c(0, max(gene_rows$neg_log10_padj) + 1.1)) +
    plot_theme

  plot_b <- ggplot2::ggplot(pathway_rows, ggplot2::aes(x = nes, y = pathway, fill = direction)) +
    ggplot2::geom_vline(xintercept = 0, linewidth = 0.4, color = theme$palette$neutral[[2]]) +
    ggplot2::geom_col(width = 0.7, alpha = 0.9, color = theme$palette$neutral[[1]], linewidth = 0.35) +
    ggplot2::scale_fill_manual(values = c("down" = theme$palette$categorical[[1]], "up" = theme$palette$categorical[[2]])) +
    ggplot2::geom_text(ggplot2::aes(label = fdr_label, x = ifelse(nes >= 0, nes + 0.12, nes - 0.12), hjust = ifelse(nes >= 0, 0, 1)), size = as.numeric(theme$typography$annotation_font_size_pt) / 2.845, color = theme$palette$neutral[[2]]) +
    ggplot2::labs(title = "Pathway enrichment summary", x = "Normalized enrichment score", y = NULL) +
    ggplot2::coord_cartesian(xlim = c(-max(abs(pathway_rows$nes)) - 0.65, max(abs(pathway_rows$nes)) + 0.65)) +
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
    gene_rows = gene_rows
  )
}

build_figure <- function(spec_path) {
  payload <- create_plot(spec_path)
  spec <- payload$spec
  theme <- payload$theme
  profile <- payload$profile
  resolved_font <- payload$resolved_font
  figure_plot <- payload$plot
  gene_rows <- payload$gene_rows
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
      "threshold_guides_for_significance",
      "selective_gene_labels_for_extreme_points",
      "de_emphasized_nonsignificant_points",
      "signed_enrichment_panel",
      "vector_first_export"
    ),
    list(
      panel_count = length(spec$panels),
      highlight_label_count = sum(gene_rows$highlight_label == "yes"),
      threshold_line_count = 3,
      reference_line_count = 1
    )
  )
  outputs
}
