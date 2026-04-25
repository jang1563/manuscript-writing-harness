#!/usr/bin/env python3
"""Build an HTML review surface for generated figures."""

from __future__ import annotations

import argparse
from collections import defaultdict
import html
import json
import os
from pathlib import Path
import re
from typing import Any

from PIL import Image

from figures_common import (
    REPO_ROOT,
    figure_spec_map,
    load_class_registry,
    load_yaml,
    manuscript_figure_items,
    resolve_specs,
)


FIGURE_OUTPUT_ROOT = REPO_ROOT / "figures/output"
REVIEW_ROOT = FIGURE_OUTPUT_ROOT / "review"
FONT_POLICY_PATH = REPO_ROOT / "figures/config/font_policy.yml"
SMALL_PREVIEW_WIDTHS = [320, 220, 140]


def relpath_from_review(path: str) -> str:
    return os.path.relpath(REPO_ROOT / path, REVIEW_ROOT)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def status_chip(label: str, tone: str) -> str:
    return f'<span class="status-pill {html.escape(tone)}">{html.escape(label)}</span>'


def _pixel_is_ink(pixel: Any) -> bool:
    if isinstance(pixel, int):
        red = green = blue = pixel
        alpha = 255
    elif len(pixel) == 4:
        red, green, blue, alpha = pixel
    elif len(pixel) == 3:
        red, green, blue = pixel
        alpha = 255
    else:
        return False
    if alpha < 24:
        return False
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
    return luminance < 0.97


def analyze_png(path: Path) -> dict[str, Any]:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")

    width, height = image.size
    pixels = image.load()

    def row_has_ink(y_pos: int) -> bool:
        for x_pos in range(width):
            if _pixel_is_ink(pixels[x_pos, y_pos]):
                return True
        return False

    def column_has_ink(x_pos: int) -> bool:
        for y_pos in range(height):
            if _pixel_is_ink(pixels[x_pos, y_pos]):
                return True
        return False

    top_gap = next((y for y in range(height) if row_has_ink(y)), height)
    bottom_gap = next((y for y in range(height) if row_has_ink(height - 1 - y)), height)
    left_gap = next((x for x in range(width) if column_has_ink(x)), width)
    right_gap = next((x for x in range(width) if column_has_ink(width - 1 - x)), width)

    margin = max(6, round(min(width, height) * 0.02))

    def strip_fraction(box: tuple[int, int, int, int]) -> float:
        strip = image.crop(box)
        strip_width, strip_height = strip.size
        total = strip_width * strip_height
        if total <= 0:
            return 0.0
        strip_pixels = strip.load()
        ink_pixels = sum(
            1
            for x_pos in range(strip_width)
            for y_pos in range(strip_height)
            if _pixel_is_ink(strip_pixels[x_pos, y_pos])
        )
        return ink_pixels / total

    edge_ink_fraction = {
        "top": strip_fraction((0, 0, width, margin)),
        "bottom": strip_fraction((0, max(0, height - margin), width, height)),
        "left": strip_fraction((0, 0, margin, height)),
        "right": strip_fraction((max(0, width - margin), 0, width, height)),
    }
    edge_gaps = {
        "top": top_gap,
        "bottom": bottom_gap,
        "left": left_gap,
        "right": right_gap,
    }

    severity_rank = {"low": 0, "moderate": 1, "high": 2}
    clipping_risk = "low"
    clipping_reasons: list[str] = []
    for edge, gap in edge_gaps.items():
        occupancy = edge_ink_fraction[edge]
        if gap <= 2 or occupancy >= 0.025:
            risk = "high"
        elif gap <= 8 or occupancy >= 0.012:
            risk = "moderate"
        else:
            risk = "low"
        if severity_rank[risk] > severity_rank[clipping_risk]:
            clipping_risk = risk
            clipping_reasons = [f"{edge} gap {gap}px", f"{edge} edge ink {occupancy:.3f}"]
        elif risk == clipping_risk and risk != "low":
            clipping_reasons.extend([f"{edge} gap {gap}px", f"{edge} edge ink {occupancy:.3f}"])

    hotspot_edge = min(edge_gaps, key=lambda edge: (edge_gaps[edge], -edge_ink_fraction[edge]))
    return {
        "width_px": width,
        "height_px": height,
        "edge_gaps_px": edge_gaps,
        "edge_ink_fraction": edge_ink_fraction,
        "hotspot_edge": hotspot_edge,
        "clipping_risk": clipping_risk,
        "clipping_reason": ", ".join(dict.fromkeys(clipping_reasons)) or "No clipping hotspot detected",
    }


def analyze_svg(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    text_nodes = len(re.findall(r"<text\b", text))
    return {
        "text_nodes": text_nodes,
        "editable_text": text_nodes > 0,
    }


def analyze_font_resolution(manifest: dict[str, Any], font_policy: dict[str, Any]) -> dict[str, Any]:
    font_resolution = manifest.get("font_resolution", {})
    declared_family = str(font_resolution.get("family") or "unknown")
    resolved_path = str(font_resolution.get("path") or "")
    path_name = Path(resolved_path).name if resolved_path else "n/a"

    preferred_families = font_policy.get("families", {}).get("sans_preferred", [])
    fallback_families = font_policy.get("families", {}).get("sans_fallbacks", [])
    normalized_path = normalize_token(path_name)
    normalized_family = normalize_token(declared_family)

    if any(normalize_token(name) in normalized_path for name in fallback_families):
        status = "fallback"
        note = f"Resolved file {path_name} suggests fallback use."
    elif any(normalize_token(name) in normalized_path for name in preferred_families):
        status = "preferred"
        note = f"Resolved file {path_name} matches a preferred family."
    elif any(normalize_token(name) in normalized_family for name in preferred_families):
        status = "preferred"
        note = f"Declared family {declared_family} matches the preferred policy."
    elif any(normalize_token(name) in normalized_family for name in fallback_families):
        status = "fallback"
        note = f"Declared family {declared_family} is a configured fallback."
    else:
        status = "unresolved"
        note = "Could not match the resolved font against the configured policy."

    if status == "fallback" and declared_family and declared_family not in path_name:
        note = f"Declared family {declared_family}; resolved file {path_name} suggests fallback use."

    return {
        "declared_family": declared_family,
        "resolved_path": resolved_path,
        "resolved_name": path_name,
        "status": status,
        "note": note,
    }


def renderer_analysis(manifest: dict[str, Any], font_policy: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest["outputs"]
    return {
        "png": analyze_png(REPO_ROOT / outputs["png"]),
        "svg": analyze_svg(REPO_ROOT / outputs["svg"]),
        "font": analyze_font_resolution(manifest, font_policy),
    }


def discover_manifests(allowed_figure_ids: set[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for manifest_path in sorted(FIGURE_OUTPUT_ROOT.glob("*/*.manifest.json")):
        if manifest_path.parent.name == "review":
            continue
        manifest = load_json(manifest_path)
        if allowed_figure_ids is not None and str(manifest["figure_id"]) not in allowed_figure_ids:
            continue
        grouped[str(manifest["figure_id"])].append(manifest)
    return grouped


def renderer_card(
    manifest: dict[str, Any],
    spec: dict[str, Any],
    manuscript_item: dict[str, Any] | None,
    analysis: dict[str, Any],
) -> str:
    outputs = manifest["outputs"]
    figure_png = relpath_from_review(outputs["png"])
    figure_svg = relpath_from_review(outputs["svg"])
    figure_pdf = relpath_from_review(outputs["pdf"])
    manifest_link = relpath_from_review(
        f"figures/output/{manifest['renderer']}/{manifest['figure_id']}.manifest.json"
    )

    fact_sheet = relpath_from_review(manifest["fact_sheet"])
    visualization_plan = relpath_from_review(manifest["visualization_plan"])
    legend_path = relpath_from_review(manifest["legend_path"])
    source_links = "".join(
        f'<li><a href="{html.escape(relpath_from_review(path))}">{html.escape(name)}</a></li>'
        for name, path in sorted(manifest["source_data"].items())
    )
    declared_input_links = "".join(
        f'<li><a href="{html.escape(relpath_from_review(path))}">{html.escape(path)}</a></li>'
        for path in manifest.get("data_inputs", [])
    )
    resolved_input_links = "".join(
        f'<li><a href="{html.escape(relpath_from_review(path))}">{html.escape(path)}</a></li>'
        for path in manifest.get("resolved_data_inputs", manifest.get("data_inputs", []))
    )
    features = "".join(
        f"<li>{html.escape(feature)}</li>" for feature in manifest.get("design_features", [])
    )
    pathway_provenance = manifest.get("pathway_provenance") or {}

    manuscript_link = "<span class=\"status-chip muted\">Not embedded in manuscript</span>"
    if manuscript_item is not None:
        preview_asset = relpath_from_review(str(manuscript_item["preview_asset"]))
        manuscript_link = (
            f'<a href="{html.escape(preview_asset)}">Manuscript preview asset</a>'
        )

    png_analysis = analysis["png"]
    svg_analysis = analysis["svg"]
    font_analysis = analysis["font"]
    clipping_tone = {
        "low": "good",
        "moderate": "warn",
        "high": "bad",
    }[png_analysis["clipping_risk"]]
    font_tone = {
        "preferred": "good",
        "fallback": "warn",
        "unresolved": "bad",
    }[font_analysis["status"]]
    editable_text_tone = "good" if svg_analysis["editable_text"] else "bad"
    small_previews = "".join(
        f"""
        <figure class="mini-preview">
          <figcaption>{width_px}px check</figcaption>
          <div class="mini-preview-frame" style="--preview-width: {width_px}px;">
            <img src="{html.escape(figure_png)}" alt="{html.escape(manifest['figure_id'])} small-size preview at {width_px}px width">
          </div>
        </figure>
        """
        for width_px in SMALL_PREVIEW_WIDTHS
    )
    edge_rows = "".join(
        f"""
        <tr>
          <th>{html.escape(edge.title())}</th>
          <td>{png_analysis['edge_gaps_px'][edge]} px</td>
          <td>{png_analysis['edge_ink_fraction'][edge]:.3f}</td>
        </tr>
        """
        for edge in ("top", "right", "bottom", "left")
    )
    provenance_summary = ""
    if pathway_provenance:
        summary_link = pathway_provenance.get("summary_json")
        config_link = pathway_provenance.get("config")
        gmt_link = pathway_provenance.get("pathways_gmt")
        raw_input_link = pathway_provenance.get("raw_input_table")
        rank_prep_link = pathway_provenance.get("rank_prep_summary")
        source_profile = pathway_provenance.get("source_profile")
        gene_set_source = pathway_provenance.get("gene_set_source") or {}
        collection_label = gene_set_source.get("collection_label")
        collection_display = gene_set_source.get("collection") or "n/a"
        if collection_label:
            collection_display = f"{collection_display} ({collection_label})"
        provider_display = gene_set_source.get("provider") or "fgsea"
        version_display = gene_set_source.get("version") or "n/a"
        species_display = gene_set_source.get("species") or "n/a"
        identifier_display = gene_set_source.get("identifier_type") or "n/a"
        summary_link_html = (
            f'<a href="{html.escape(relpath_from_review(summary_link))}">fgsea summary</a>'
            if summary_link
            else '<span class="status-chip muted">fgsea summary unavailable</span>'
        )
        config_link_html = (
            f'<a href="{html.escape(relpath_from_review(config_link))}">{html.escape(config_link)}</a>'
            if config_link
            else '<span class="status-chip muted">config unavailable</span>'
        )
        gmt_link_html = (
            f'<a href="{html.escape(relpath_from_review(gmt_link))}">{html.escape(gmt_link)}</a>'
            if gmt_link
            else '<span class="status-chip muted">GMT unavailable</span>'
        )
        raw_input_link_html = (
            f'<a href="{html.escape(relpath_from_review(raw_input_link))}">{html.escape(raw_input_link)}</a>'
            if raw_input_link
            else '<span class="status-chip muted">raw DE table unavailable</span>'
        )
        rank_prep_link_html = (
            f'<a href="{html.escape(relpath_from_review(rank_prep_link))}">{html.escape(rank_prep_link)}</a>'
            if rank_prep_link
            else '<span class="status-chip muted">rank prep summary unavailable</span>'
        )
        source_profile_html = (
            f'<a href="{html.escape(relpath_from_review(source_profile))}">{html.escape(source_profile)}</a>'
            if source_profile
            else '<span class="status-chip muted">source profile unavailable</span>'
        )
        provenance_summary = f"""
        <section class="audit-card">
          <h4>Pathway provenance</h4>
          <ul class="audit-list">
            <li><strong>Run:</strong> <code>{html.escape(str(pathway_provenance.get('run_id') or 'n/a'))}</code></li>
            <li><strong>Status:</strong> {status_chip(str(pathway_provenance.get('status') or 'unknown'), 'good' if str(pathway_provenance.get('status')) == 'ready' else 'warn')}</li>
            <li><strong>Provider:</strong> {html.escape(provider_display)}</li>
            <li><strong>Collection:</strong> {html.escape(collection_display)}</li>
            <li><strong>Species:</strong> {html.escape(species_display)}</li>
            <li><strong>Version:</strong> {html.escape(version_display)}</li>
            <li><strong>Identifier type:</strong> {html.escape(identifier_display)}</li>
            <li><strong>Source profile:</strong> {source_profile_html}</li>
            <li><strong>Raw DE table:</strong> {raw_input_link_html}</li>
            <li><strong>Rank prep:</strong> {rank_prep_link_html}</li>
            <li><strong>Config:</strong> {config_link_html}</li>
            <li><strong>GMT:</strong> {gmt_link_html}</li>
            <li><strong>Summary:</strong> {summary_link_html}</li>
          </ul>
        </section>
        """

    return f"""
    <section class="renderer-card">
      <div class="renderer-header">
        <h3>{html.escape(manifest['renderer'].upper())} Renderer</h3>
        <p>Target profile: <code>{html.escape(manifest['target_profile'])}</code></p>
      </div>
      <div class="preview-frame">
        <img src="{html.escape(figure_png)}" alt="{html.escape(manifest['figure_id'])} rendered by {html.escape(manifest['renderer'])}">
      </div>
      <div class="link-grid">
        <a href="{html.escape(figure_png)}">PNG preview</a>
        <a href="{html.escape(figure_svg)}">SVG vector</a>
        <a href="{html.escape(figure_pdf)}">PDF vector</a>
        <a href="{html.escape(manifest_link)}">Manifest</a>
        <a href="{html.escape(fact_sheet)}">Fact sheet</a>
        <a href="{html.escape(visualization_plan)}">Visualization plan</a>
        <a href="{html.escape(legend_path)}">Legend</a>
        {manuscript_link}
      </div>
      <div class="qa-snapshot">
        {status_chip(f"editable text: {'yes' if svg_analysis['editable_text'] else 'no'}", editable_text_tone)}
        {status_chip(f"font audit: {font_analysis['status']}", font_tone)}
        {status_chip(f"clipping risk: {png_analysis['clipping_risk']}", clipping_tone)}
        {status_chip(f"hotspot edge: {png_analysis['hotspot_edge']}", 'muted')}
        {status_chip(f"raster size: {png_analysis['width_px']}x{png_analysis['height_px']}", 'muted')}
        {status_chip(
            "generated input" if manifest.get("resolved_data_inputs", manifest.get("data_inputs", [])) != manifest.get("data_inputs", []) else "declared input",
            "good" if manifest.get("resolved_data_inputs", manifest.get("data_inputs", [])) != manifest.get("data_inputs", []) else "muted"
        )}
      </div>
      <div class="audit-grid">
        <section class="audit-card">
          <h4>Small-size readability</h4>
          <div class="mini-preview-grid">
            {small_previews}
          </div>
        </section>
        <section class="audit-card">
          <h4>Font audit</h4>
          <ul class="audit-list">
            <li><strong>Declared family:</strong> {html.escape(font_analysis['declared_family'])}</li>
            <li><strong>Resolved file:</strong> {html.escape(font_analysis['resolved_name'])}</li>
            <li><strong>Status:</strong> {status_chip(font_analysis['status'], font_tone)}</li>
            <li>{html.escape(font_analysis['note'])}</li>
          </ul>
        </section>
        <section class="audit-card">
          <h4>Clipping risk</h4>
          <p class="audit-note">{html.escape(png_analysis['clipping_reason'])}</p>
          <table class="audit-table">
            <thead>
              <tr><th>Edge</th><th>Gap</th><th>Ink fraction</th></tr>
            </thead>
            <tbody>
              {edge_rows}
            </tbody>
          </table>
        </section>
        {provenance_summary}
      </div>
      <div class="meta">
        <div>
          <h4>Claims</h4>
          <ul>
            {''.join(f'<li><code>{html.escape(claim)}</code></li>' for claim in manifest.get('claim_ids', []))}
          </ul>
        </div>
        <div>
          <h4>Design Features</h4>
          <ul>
            {features}
          </ul>
        </div>
        <div>
          <h4>Inputs</h4>
          <ul>
            {declared_input_links}
          </ul>
          <h5>Resolved Inputs</h5>
          <ul>
            {resolved_input_links}
          </ul>
        </div>
        <div>
          <h4>Source Data</h4>
          <ul>
            {source_links}
          </ul>
        </div>
      </div>
    </section>
    """


def comparison_section(
    figure_id: str,
    manifests: list[dict[str, Any]],
    analyses: dict[str, dict[str, Any]],
) -> str:
    renderer_map = {str(manifest["renderer"]): manifest for manifest in manifests}
    if "python" not in renderer_map or "r" not in renderer_map:
        return ""

    python_manifest = renderer_map["python"]
    r_manifest = renderer_map["r"]
    python_png = relpath_from_review(python_manifest["outputs"]["png"])
    r_png = relpath_from_review(r_manifest["outputs"]["png"])
    python_analysis = analyses["python"]
    r_analysis = analyses["r"]

    if python_analysis["font"]["status"] == r_analysis["font"]["status"]:
        font_alignment = python_analysis["font"]["status"]
    else:
        font_alignment = "mismatch"
    if python_analysis["png"]["clipping_risk"] == r_analysis["png"]["clipping_risk"]:
        clipping_alignment = python_analysis["png"]["clipping_risk"]
    else:
        clipping_alignment = "mixed"

    comparison_id = html.escape(figure_id)
    audit_rows = [
        (
            "Font status",
            status_chip(python_analysis["font"]["status"], "good" if python_analysis["font"]["status"] == "preferred" else "warn"),
            status_chip(r_analysis["font"]["status"], "good" if r_analysis["font"]["status"] == "preferred" else "warn"),
        ),
        (
            "Resolved font",
            html.escape(python_analysis["font"]["resolved_name"]),
            html.escape(r_analysis["font"]["resolved_name"]),
        ),
        (
            "Clipping risk",
            status_chip(python_analysis["png"]["clipping_risk"], {"low": "good", "moderate": "warn", "high": "bad"}[python_analysis["png"]["clipping_risk"]]),
            status_chip(r_analysis["png"]["clipping_risk"], {"low": "good", "moderate": "warn", "high": "bad"}[r_analysis["png"]["clipping_risk"]]),
        ),
        (
            "Hotspot edge",
            html.escape(python_analysis["png"]["hotspot_edge"]),
            html.escape(r_analysis["png"]["hotspot_edge"]),
        ),
        (
            "Editable SVG text nodes",
            str(python_analysis["svg"]["text_nodes"]),
            str(r_analysis["svg"]["text_nodes"]),
        ),
    ]
    audit_table = "".join(
        f"<tr><th>{label}</th><td>{left}</td><td>{right}</td></tr>"
        for label, left, right in audit_rows
    )

    return f"""
    <section class="comparison-panel">
      <div class="comparison-header">
        <div>
          <h3>Renderer Comparison</h3>
          <p>Use the reduced thumbnails, reveal slider, and difference blend to spot parity drift quickly.</p>
        </div>
        <div class="comparison-status">
          {status_chip(f"font alignment: {font_alignment}", 'good' if font_alignment == 'preferred' else 'warn')}
          {status_chip(f"clipping alignment: {clipping_alignment}", 'good' if clipping_alignment == 'low' else 'warn')}
        </div>
      </div>
      <div class="comparison-layout">
        <div class="comparison-visuals">
          <section class="audit-card">
            <h4>Thumbnail diff</h4>
            <div class="thumbnail-strip">
              <figure class="thumbnail-card">
                <figcaption>Python</figcaption>
                <img src="{html.escape(python_png)}" alt="{comparison_id} python thumbnail">
              </figure>
              <figure class="thumbnail-card">
                <figcaption>R</figcaption>
                <img src="{html.escape(r_png)}" alt="{comparison_id} r thumbnail">
              </figure>
            </div>
          </section>
          <section class="audit-card">
            <h4>Reveal slider</h4>
            <div class="comparison-stage">
              <div class="comparison-overlay" style="--split: 50%;">
                <img class="base-image" src="{html.escape(python_png)}" alt="{comparison_id} python renderer">
                <div class="overlay-clip">
                  <img src="{html.escape(r_png)}" alt="{comparison_id} r renderer">
                </div>
              </div>
              <div class="comparison-labels">
                <span>Python</span>
                <span>R</span>
              </div>
              <input class="comparison-range" type="range" min="0" max="100" value="50"
                oninput="this.previousElementSibling.previousElementSibling.style.setProperty('--split', this.value + '%')">
            </div>
          </section>
          <section class="audit-card">
            <h4>Difference blend</h4>
            <div class="difference-stage">
              <img class="base-image" src="{html.escape(python_png)}" alt="{comparison_id} python base image">
              <img class="difference-image" src="{html.escape(r_png)}" alt="{comparison_id} difference image">
            </div>
          </section>
        </div>
        <section class="audit-card comparison-audit-card">
          <h4>Cross-renderer audit</h4>
          <table class="audit-table">
            <thead>
              <tr><th>Audit</th><th>Python</th><th>R</th></tr>
            </thead>
            <tbody>
              {audit_table}
            </tbody>
          </table>
        </section>
      </div>
    </section>
    """


def checklist_for_class(class_id: str) -> str:
    items = {
        "timecourse_endpoint": [
            "Are fonts legible and direct labels clear at journal scale?",
            "Are replicate-level endpoint points visible rather than hidden behind summary bars?",
            "Does the time-course panel avoid detached-legend scanning?",
        ],
        "volcano_pathway_compound": [
            "Are threshold guides visible without overpowering the data?",
            "Are highlighted labels selective and collision-free?",
            "Does the pathway panel preserve sign around zero and keep FDR annotations readable?",
        ],
        "ma_plot": [
            "Is the zero-centered abundance-vs-fold-change reference visually obvious?",
            "Are labeled genes limited to the strongest biologically relevant outliers?",
        ],
        "sample_pca": [
            "Are condition and batch encoded by distinct channels that remain easy to decode?",
            "Do direct sample labels avoid clutter while highlighting the intended points?",
        ],
        "pathway_enrichment_dot": [
            "Do size, color, and text annotations encode distinct information without competing?",
            "Are pathway names and significance annotations readable together?",
        ],
        "roc_pr_compound": [
            "Are ROC and precision-recall panels both present and ordered consistently across models?",
            "Do uncertainty ribbons and operating-point labels remain readable without overwhelming the curves?",
            "Does the precision-recall panel preserve the prevalence baseline so class imbalance remains visible?",
            "Can the model identities still be decoded without relying on color alone?",
        ],
        "calibration_reliability": [
            "Is the identity reference line visually obvious without dominating the data?",
            "Do confidence-support bars make it clear whether high-confidence calibration is well supported?",
            "Can model identity still be followed without a detached legend?",
        ],
        "training_dynamics": [
            "Are train and validation trajectories distinguishable without relying on color alone?",
            "Do direct labels and best-checkpoint markers stay readable at journal scale?",
            "Does the layout preserve the late-epoch behavior that matters for overfitting interpretation?",
        ],
        "confusion_matrix_normalized": [
            "Are diagonal strengths and dominant off-diagonal errors both legible at first glance?",
            "Do cell annotations remain readable without turning the heatmap into visual noise?",
            "Does the companion summary panel make the most important failure modes explicit rather than forcing manual matrix scanning?",
        ],
        "feature_importance_summary": [
            "Do the highest-ranked features read immediately without forcing a detached legend lookup?",
            "Does the signed-effect panel make directionality and zero-centered interpretation obvious?",
            "Are nuisance covariates clearly lower-priority than biologically salient features?",
        ],
        "embedding_projection": [
            "Are state labels sparse enough to avoid turning the embedding into a label cloud?",
            "Is domain encoded separately from biological state so cohort structure can be inspected?",
            "Does the support panel keep the projection from overclaiming geometry alone?",
        ],
        "uncertainty_abstention_curve": [
            "Does the curve show the full coverage-risk tradeoff instead of only one threshold?",
            "Are operating points and target-risk references visible enough to audit deployment choices?",
            "Does the retained-coverage panel prevent safety claims from hiding excessive abstention?",
        ],
        "ablation_summary": [
            "Do the largest primary-metric penalties stand out immediately against the full-model baseline?",
            "Does the secondary panel separate ranking penalties from calibration penalties rather than mixing them together?",
            "Can the reader decode ablation family and metric identity without relying on color alone?",
        ],
    }
    return "".join(f"<li>{html.escape(item)}</li>" for item in items.get(class_id, []))


def figure_section(
    class_id: str,
    class_entry: dict[str, Any],
    figure_id: str,
    manifests: list[dict[str, Any]],
    spec: dict[str, Any],
    manuscript_item: dict[str, Any] | None,
    font_policy: dict[str, Any],
) -> str:
    manifests = sorted(manifests, key=lambda item: str(item["renderer"]))
    first = manifests[0]
    analyses = {
        str(manifest["renderer"]): renderer_analysis(manifest, font_policy)
        for manifest in manifests
    }
    cards = "\n".join(
        renderer_card(manifest, spec, manuscript_item, analyses[str(manifest["renderer"])])
        for manifest in manifests
    )
    comparison = comparison_section(figure_id, manifests, analyses)
    parity_text = html.escape(str(spec["parity_status"]))
    authority_renderer = spec.get("authority_renderer") or "n/a"
    return f"""
    <article class="figure-block">
      <header class="figure-header">
        <div>
          <h2>{html.escape(figure_id)}</h2>
          <p>{html.escape(first['title'])}</p>
        </div>
        <div class="figure-summary">
          <span><strong>Class:</strong> <code>{html.escape(class_id)}</code></span>
          <span><strong>Family:</strong> <code>{html.escape(str(class_entry.get('family', 'n/a')))}</code></span>
          <span><strong>Expertise:</strong> <code>{html.escape(str(class_entry.get('expertise_track', 'n/a')))}</code></span>
          <span><strong>Parity:</strong> <code>{parity_text}</code></span>
          <span><strong>Authority:</strong> <code>{html.escape(str(authority_renderer))}</code></span>
          <span><strong>Style:</strong> <code>{html.escape(str(spec['style_profile']))}</code></span>
          <span><strong>QA profile:</strong> <code>{html.escape(str(spec['qa_profile']))}</code></span>
        </div>
      </header>
      <section class="human-review">
        <h3>Class QA Checklist</h3>
        <ul class="review-checklist">
          {checklist_for_class(class_id)}
        </ul>
      </section>
      {comparison}
      <section class="renderer-grid">
        {cards}
      </section>
    </article>
    """


def build_html(grouped: dict[str, list[dict[str, Any]]]) -> str:
    class_registry = load_class_registry()
    font_policy = load_yaml(FONT_POLICY_PATH)
    spec_map = figure_spec_map()
    manuscript_items = manuscript_figure_items()
    class_blocks: list[str] = []
    grouped_by_class: dict[str, list[str]] = defaultdict(list)
    for figure_id, manifests in grouped.items():
        spec = spec_map[figure_id]
        grouped_by_class[str(spec["class_id"])].append(figure_id)
    for class_id in sorted(grouped_by_class):
        class_entry = class_registry[class_id]
        figure_blocks = []
        for figure_id in sorted(grouped_by_class[class_id]):
            figure_blocks.append(
                figure_section(
                    class_id,
                    class_entry,
                    figure_id,
                    grouped[figure_id],
                    spec_map[figure_id],
                    manuscript_items.get(figure_id),
                    font_policy,
                )
            )
        class_blocks.append(
            f"""
            <section class="class-group">
              <header class="class-header">
                <h2>{html.escape(class_id)}</h2>
                <p>{html.escape(str(class_entry['intent']))}</p>
              </header>
              {''.join(figure_blocks)}
            </section>
            """
        )
    blocks = "\n".join(class_blocks)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Figure Review</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --card: #fffdfa;
      --ink: #1f1d1a;
      --muted: #6b645b;
      --accent: #124559;
      --border: #d8d0c3;
      --shadow: 0 20px 50px rgba(31, 29, 26, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(18, 69, 89, 0.10), transparent 32%),
        linear-gradient(180deg, #f8f5ef 0%, var(--bg) 100%);
    }}
    main {{ max-width: 1500px; margin: 0 auto; padding: 40px 24px 64px; }}
    .page-header, .class-header, .figure-block {{
      background: rgba(255, 253, 250, 0.95);
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .page-header {{ margin-bottom: 32px; padding: 28px 30px; }}
    .page-header h1 {{ margin: 0 0 10px; font-size: clamp(2rem, 4vw, 3rem); letter-spacing: -0.03em; }}
    .page-header p {{ margin: 0; color: var(--muted); max-width: 70ch; line-height: 1.5; }}
    .class-group {{ margin-bottom: 36px; }}
    .class-header {{ margin-bottom: 18px; padding: 18px 22px; }}
    .class-header h2 {{ margin: 0 0 6px; font-size: 1.4rem; }}
    .class-header p {{ margin: 0; color: var(--muted); }}
    .figure-block {{ margin-bottom: 24px; padding: 24px; }}
    .figure-header {{ display: flex; justify-content: space-between; gap: 18px; align-items: flex-start; margin-bottom: 20px; }}
    .figure-header h2 {{ margin: 0 0 6px; font-size: 1.5rem; }}
    .figure-header p {{ margin: 0; color: var(--muted); }}
    .figure-summary {{ display: grid; gap: 8px; font-size: 0.95rem; color: var(--muted); }}
    .human-review {{ padding: 16px 18px; margin-bottom: 20px; background: #f0ece3; border-left: 4px solid var(--accent); }}
    .human-review h3 {{ margin: 0 0 10px; font-size: 1rem; }}
    .review-checklist {{ margin: 0; padding-left: 18px; line-height: 1.5; }}
    .comparison-panel {{ margin-bottom: 20px; padding: 18px; background: #f7f3eb; border: 1px solid var(--border); }}
    .comparison-header {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 14px; }}
    .comparison-header h3 {{ margin: 0 0 6px; font-size: 1.05rem; }}
    .comparison-header p {{ margin: 0; color: var(--muted); }}
    .comparison-status {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .comparison-layout {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; }}
    .comparison-visuals {{ display: grid; gap: 14px; }}
    .thumbnail-strip {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
    .thumbnail-card {{ margin: 0; }}
    .thumbnail-card figcaption {{ margin-bottom: 8px; color: var(--muted); font-size: 0.88rem; }}
    .thumbnail-card img {{ width: 100%; display: block; border: 1px solid var(--border); background: #fff; }}
    .comparison-stage {{ display: grid; gap: 8px; }}
    .comparison-overlay, .difference-stage {{ position: relative; border: 1px solid var(--border); background: #fff; overflow: hidden; }}
    .comparison-overlay {{ aspect-ratio: 183 / 86; }}
    .comparison-overlay img, .difference-stage img {{ width: 100%; display: block; }}
    .comparison-overlay .base-image {{ position: absolute; inset: 0; height: 100%; object-fit: contain; }}
    .comparison-overlay .overlay-clip {{ position: absolute; inset: 0; width: var(--split); overflow: hidden; border-right: 2px solid rgba(18, 69, 89, 0.6); }}
    .comparison-overlay .overlay-clip img {{ height: 100%; object-fit: contain; }}
    .comparison-labels {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 0.88rem; }}
    .comparison-range {{ width: 100%; accent-color: var(--accent); }}
    .difference-stage {{ aspect-ratio: 183 / 86; }}
    .difference-stage .base-image {{ position: absolute; inset: 0; height: 100%; object-fit: contain; }}
    .difference-stage .difference-image {{ position: absolute; inset: 0; height: 100%; object-fit: contain; mix-blend-mode: difference; opacity: 1; }}
    .renderer-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; }}
    .renderer-card {{ border: 1px solid var(--border); background: var(--card); padding: 18px; }}
    .renderer-header h3 {{ margin: 0 0 4px; font-size: 1.05rem; }}
    .renderer-header p {{ margin: 0 0 14px; color: var(--muted); font-size: 0.92rem; }}
    .preview-frame {{ background: #ffffff; border: 1px solid var(--border); padding: 12px; margin-bottom: 14px; min-height: 280px; display: flex; align-items: center; justify-content: center; }}
    .preview-frame img {{ max-width: 100%; height: auto; display: block; }}
    .qa-snapshot {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
    .status-pill {{ display: inline-flex; align-items: center; padding: 4px 9px; border-radius: 999px; border: 1px solid var(--border); background: #f6f1e7; font-size: 0.82rem; }}
    .status-pill.good {{ color: #1d5c3f; border-color: #95bea7; background: #edf8f1; }}
    .status-pill.warn {{ color: #7a4e12; border-color: #e1c995; background: #fff7e5; }}
    .status-pill.bad {{ color: #8b2f2f; border-color: #e1aaaa; background: #fff0f0; }}
    .status-pill.muted {{ color: var(--muted); }}
    .audit-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 16px; }}
    .audit-card {{ padding: 14px; background: #fbf8f2; border: 1px solid var(--border); }}
    .audit-card h4 {{ margin: 0 0 10px; font-size: 0.95rem; }}
    .audit-list {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.5; }}
    .audit-note {{ margin: 0 0 10px; color: var(--muted); line-height: 1.45; }}
    .audit-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    .audit-table th, .audit-table td {{ text-align: left; padding: 6px 8px; border-top: 1px solid var(--border); vertical-align: top; }}
    .audit-table thead th {{ border-top: none; color: var(--muted); font-size: 0.82rem; }}
    .mini-preview-grid {{ display: grid; gap: 10px; }}
    .mini-preview {{ margin: 0; }}
    .mini-preview figcaption {{ margin-bottom: 6px; color: var(--muted); font-size: 0.82rem; }}
    .mini-preview-frame {{ max-width: min(100%, var(--preview-width)); border: 1px solid var(--border); background: #fff; overflow: hidden; }}
    .mini-preview-frame img {{ width: 100%; display: block; }}
    .link-grid {{ display: flex; flex-wrap: wrap; gap: 10px 14px; margin-bottom: 16px; }}
    .link-grid a, .status-chip {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    .status-chip.muted {{ color: var(--muted); }}
    .link-grid a:hover {{ text-decoration: underline; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; font-size: 0.92rem; }}
    .meta h4 {{ margin: 0 0 8px; font-size: 0.95rem; }}
    .meta ul {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.45; }}
    code {{ font-family: "SFMono-Regular", "Menlo", "Consolas", monospace; font-size: 0.92em; }}
    @media (max-width: 800px) {{
      main {{ padding: 24px 14px 40px; }}
      .figure-header {{ flex-direction: column; }}
      .comparison-header {{ flex-direction: column; }}
      .comparison-layout {{ grid-template-columns: 1fr; }}
      .renderer-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <header class="page-header">
      <h1>Generated Figure Review</h1>
      <p>
        This page is built automatically so we can review actual rendered figures by eye,
        not only inspect code, manifests, or specs. Figures are grouped by reusable class
        so we can judge consistency, renderer parity, and manuscript readiness at the library level.
      </p>
    </header>
    {blocks}
  </main>
</body>
</html>
"""


def build_review_page(figure_ids: list[str] | None = None) -> Path:
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    allowed_ids = None if not figure_ids else {spec["figure_id"] for spec in resolve_specs(figure_ids)}
    manifests = discover_manifests(allowed_ids)
    if not manifests:
        raise ValueError("No built figure manifests were found for the requested review target")
    html_path = REVIEW_ROOT / "index.html"
    html_path.write_text(build_html(manifests), encoding="utf-8")
    print(f"Built figure review page: {html_path.relative_to(REPO_ROOT)}")
    return html_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--figure",
        action="append",
        dest="figure_ids",
        help="Restrict the review page to the specified figure id. Repeatable.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Build the review page for all currently built figures.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_review_page(args.figure_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
