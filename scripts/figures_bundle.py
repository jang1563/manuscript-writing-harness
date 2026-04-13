#!/usr/bin/env python3
"""Helpers for tracked figure bundles and additive manuscript wiring."""

from __future__ import annotations

from collections import Counter
import html
import json
import os
from pathlib import Path
import re
from typing import Any

import yaml

try:  # pragma: no cover - import path differs between script and package use.
    from .build_figure_review import analyze_font_resolution, analyze_png
    from .figures_common import (
        REPO_ROOT,
        enabled_renderers,
        figure_output_paths,
        figure_spec_map,
        load_class_registry,
        load_figure_recipes,
        load_yaml,
        preview_renderer,
        source_data_mapping,
    )
except ImportError:  # pragma: no cover
    from build_figure_review import analyze_font_resolution, analyze_png
    from figures_common import (
        REPO_ROOT,
        enabled_renderers,
        figure_output_paths,
        figure_spec_map,
        load_class_registry,
        load_figure_recipes,
        load_yaml,
        preview_renderer,
        source_data_mapping,
    )


BUNDLE_ROOT = REPO_ROOT / "figures" / "bundles"
BUNDLE_REGISTRY_PATH = BUNDLE_ROOT / "bundles.yml"
FONT_POLICY_PATH = REPO_ROOT / "figures" / "config" / "font_policy.yml"
RESULTS_SECTION_PATH = REPO_ROOT / "manuscript" / "sections" / "03_results.md"
DISPLAY_ITEM_MAP_PATH = REPO_ROOT / "manuscript" / "plans" / "display_item_map.json"
WRITING_PLAN_PATH = REPO_ROOT / "manuscript" / "plans" / "writing_plan.json"
OUTLINE_PATH = REPO_ROOT / "manuscript" / "plans" / "outline.json"
MANAGED_RESULTS_START = "<!-- BUNDLE_MANAGED_BLOCK_START -->"
MANAGED_RESULTS_END = "<!-- BUNDLE_MANAGED_BLOCK_END -->"

BUNDLE_REGISTRY_REQUIRED_FIELDS = {
    "bundle_id",
    "path",
    "recipe_id",
    "acceptance_tier",
}
BUNDLE_REQUIRED_FIELDS = {
    "bundle_id",
    "recipe_id",
    "family",
    "expertise_track",
    "acceptance_tier",
    "target_manuscript_section",
    "wiring_mode",
    "figure_order",
    "figures",
    "bundle_outputs",
    "manuscript_fragments",
}
BUNDLE_FIGURE_REQUIRED_FIELDS = {
    "slot_id",
    "class_id",
    "figure_id",
    "role",
    "display_order",
    "claim_ids",
    "spec_path",
    "fact_sheet",
    "legend_path",
    "source_data",
}
BUNDLE_FRAGMENT_REQUIRED_FIELDS = {
    "display_item_map",
    "writing_plan",
    "results_fragment",
    "managed_include",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _rel(repo_root: Path, path: Path) -> str:
    return str(path.relative_to(repo_root))


def load_bundle_registry(repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    payload = load_yaml(repo_root / "figures" / "bundles" / "bundles.yml")
    bundles = payload.get("bundles", {})
    if not isinstance(bundles, dict) or not bundles:
        raise ValueError("figures/bundles/bundles.yml must define a non-empty bundles object")
    recipes = load_figure_recipes()
    normalized: dict[str, dict[str, Any]] = {}
    for bundle_id, metadata in bundles.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"bundle registry entry {bundle_id!r} must be an object")
        missing = sorted(BUNDLE_REGISTRY_REQUIRED_FIELDS - metadata.keys())
        if missing:
            raise ValueError(f"bundle registry entry {bundle_id!r} is missing {missing}")
        if metadata.get("bundle_id") != bundle_id:
            raise ValueError(f"bundle registry entry {bundle_id!r} has a mismatched bundle_id")
        recipe_id = metadata.get("recipe_id")
        if recipe_id not in recipes:
            raise ValueError(
                f"bundle registry entry {bundle_id!r} references unknown recipe_id {recipe_id!r}"
            )
        normalized[bundle_id] = metadata
    return normalized


def _validate_bundle_manifest(
    bundle: dict[str, Any],
    bundle_id: str,
    repo_root: Path,
    registry_entry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    missing = sorted(BUNDLE_REQUIRED_FIELDS - bundle.keys())
    if missing:
        raise ValueError(f"bundle manifest {bundle_id!r} is missing {missing}")
    if bundle.get("bundle_id") != bundle_id:
        raise ValueError(f"bundle manifest {bundle_id!r} has a mismatched bundle_id")
    if bundle.get("recipe_id") != registry_entry["recipe_id"]:
        raise ValueError(f"bundle manifest {bundle_id!r} has recipe drift")
    if bundle.get("acceptance_tier") != registry_entry["acceptance_tier"]:
        raise ValueError(f"bundle manifest {bundle_id!r} has acceptance_tier drift")
    if bundle.get("target_manuscript_section") != "results":
        raise ValueError(f"bundle manifest {bundle_id!r} must target the results section in v1")
    if bundle.get("wiring_mode") != "additive_drafts":
        raise ValueError(f"bundle manifest {bundle_id!r} must use additive_drafts wiring")

    recipes = load_figure_recipes()
    recipe = recipes[bundle["recipe_id"]]
    if bundle.get("family") != recipe.get("family"):
        raise ValueError(f"bundle manifest {bundle_id!r} family does not match its recipe")
    if bundle.get("expertise_track") != recipe.get("expertise_track"):
        raise ValueError(f"bundle manifest {bundle_id!r} expertise_track does not match its recipe")

    figures = bundle.get("figures")
    if not isinstance(figures, list) or not figures:
        raise ValueError(f"bundle manifest {bundle_id!r} must define a non-empty figures list")
    figure_order = bundle.get("figure_order")
    if not isinstance(figure_order, list) or not figure_order:
        raise ValueError(f"bundle manifest {bundle_id!r} must define a non-empty figure_order")

    fragments = bundle.get("manuscript_fragments")
    if not isinstance(fragments, dict):
        raise ValueError(f"bundle manifest {bundle_id!r} manuscript_fragments must be an object")
    missing_fragments = sorted(BUNDLE_FRAGMENT_REQUIRED_FIELDS - fragments.keys())
    if missing_fragments:
        raise ValueError(
            f"bundle manifest {bundle_id!r} manuscript_fragments is missing {missing_fragments}"
        )
    for value in bundle["bundle_outputs"].values():
        if not isinstance(value, str):
            raise ValueError(f"bundle manifest {bundle_id!r} has invalid bundle_outputs entries")
    for value in fragments.values():
        if not isinstance(value, str):
            raise ValueError(
                f"bundle manifest {bundle_id!r} has invalid manuscript_fragments entries"
            )

    spec_map = figure_spec_map()
    recipe_items = recipe.get("recommended_sequence", [])
    if len(recipe_items) != len(figures):
        raise ValueError(f"bundle manifest {bundle_id!r} does not cover its recipe slots")

    by_figure_id: dict[str, dict[str, Any]] = {}
    display_orders: list[int] = []
    shared_claims = set(bundle.get("shared_claim_ids", []))
    all_claim_ids: list[str] = []
    for recipe_item, figure in zip(recipe_items, figures):
        if not isinstance(figure, dict):
            raise ValueError(f"bundle manifest {bundle_id!r} figure entries must be objects")
        missing_figure_fields = sorted(BUNDLE_FIGURE_REQUIRED_FIELDS - figure.keys())
        if missing_figure_fields:
            raise ValueError(
                f"bundle manifest {bundle_id!r} figure entry is missing {missing_figure_fields}"
            )
        figure_id = str(figure["figure_id"])
        if figure["slot_id"] != recipe_item["slot_id"]:
            raise ValueError(f"bundle manifest {bundle_id!r} slot order drift detected")
        if figure["class_id"] != recipe_item["class_id"]:
            raise ValueError(f"bundle manifest {bundle_id!r} class_id drift detected")
        if figure_id not in spec_map:
            raise ValueError(f"bundle manifest {bundle_id!r} references unknown figure {figure_id!r}")
        spec = spec_map[figure_id]
        if figure["class_id"] != spec["class_id"]:
            raise ValueError(f"bundle manifest {bundle_id!r} class mismatch for {figure_id}")
        if figure["claim_ids"] != spec["claim_ids"]:
            raise ValueError(f"bundle manifest {bundle_id!r} claim drift detected for {figure_id}")
        if figure["spec_path"] != spec["_spec_path"]:
            raise ValueError(f"bundle manifest {bundle_id!r} spec_path drift detected for {figure_id}")
        if figure["fact_sheet"] != spec["fact_sheet"]:
            raise ValueError(f"bundle manifest {bundle_id!r} fact_sheet drift detected for {figure_id}")
        if figure["legend_path"] != spec["legend_path"]:
            raise ValueError(f"bundle manifest {bundle_id!r} legend drift detected for {figure_id}")
        if figure["source_data"] != list(source_data_mapping(spec).values()):
            raise ValueError(f"bundle manifest {bundle_id!r} source-data drift detected for {figure_id}")
        by_figure_id[figure_id] = figure
        display_orders.append(int(figure["display_order"]))
        all_claim_ids.extend(str(item) for item in figure["claim_ids"])

    if figure_order != [item["figure_id"] for item in figures]:
        raise ValueError(f"bundle manifest {bundle_id!r} figure_order does not match figures list")
    if sorted(display_orders) != list(range(1, len(figures) + 1)):
        raise ValueError(f"bundle manifest {bundle_id!r} display_order must be 1..N")

    claim_counts = Counter(all_claim_ids)
    duplicates = sorted(claim_id for claim_id, count in claim_counts.items() if count > 1 and claim_id not in shared_claims)
    if duplicates:
        raise ValueError(f"bundle manifest {bundle_id!r} has duplicate claim_ids {duplicates}")

    for fragment_key in ("display_item_map", "writing_plan", "results_fragment"):
        fragment_path = repo_root / fragments[fragment_key]
        if not fragment_path.exists():
            raise ValueError(f"bundle manifest {bundle_id!r} is missing fragment {fragments[fragment_key]}")
    return by_figure_id


def load_bundle_manifest(
    bundle_id: str,
    repo_root: Path = REPO_ROOT,
    registry: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry = registry or load_bundle_registry(repo_root)
    if bundle_id not in registry:
        raise ValueError(f"Unknown bundle_id {bundle_id!r}")
    entry = registry[bundle_id]
    manifest_path = repo_root / str(entry["path"])
    if not manifest_path.exists():
        raise ValueError(f"Bundle manifest is missing: {entry['path']}")
    bundle = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        raise ValueError(f"bundle manifest {bundle_id!r} must be an object")
    by_figure_id = _validate_bundle_manifest(bundle, bundle_id, repo_root, entry)
    normalized = dict(bundle)
    normalized["_bundle_path"] = _rel(repo_root, manifest_path)
    normalized["_bundle_dir"] = _rel(repo_root, manifest_path.parent)
    normalized["_registry_entry"] = entry
    normalized["_figures_by_id"] = by_figure_id
    normalized["figures"] = sorted(
        normalized["figures"],
        key=lambda item: int(item["display_order"]),
    )
    return normalized


def load_bundle_manifests(repo_root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    registry = load_bundle_registry(repo_root)
    return {
        bundle_id: load_bundle_manifest(bundle_id, repo_root=repo_root, registry=registry)
        for bundle_id in sorted(registry)
    }


def bundle_figure_ids(bundle: dict[str, Any]) -> list[str]:
    return [str(item["figure_id"]) for item in bundle["figures"]]


def bundle_output_paths(bundle: dict[str, Any], repo_root: Path = REPO_ROOT) -> dict[str, Path]:
    outputs = bundle["bundle_outputs"]
    return {
        "review_page": repo_root / str(outputs["review_page"]),
        "summary_json": repo_root / str(outputs["summary_json"]),
    }


def _display_items_from_fragment(bundle: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    fragment_path = repo_root / str(bundle["manuscript_fragments"]["display_item_map"])
    payload = _load_json(fragment_path)
    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError(f"{bundle['bundle_id']} display_item_map.fragment.json must define items")
    ids = [item.get("display_item_id") for item in items]
    if ids != bundle_figure_ids(bundle):
        raise ValueError(
            f"{bundle['bundle_id']} display_item_map.fragment.json must align exactly with bundle figure order"
        )
    return items


def _writing_refs_from_fragment(bundle: dict[str, Any], repo_root: Path) -> list[str]:
    fragment_path = repo_root / str(bundle["manuscript_fragments"]["writing_plan"])
    payload = _load_json(fragment_path)
    refs = payload.get("display_item_refs", [])
    if refs != bundle_figure_ids(bundle):
        raise ValueError(
            f"{bundle['bundle_id']} writing_plan.fragment.json must align exactly with bundle figure order"
        )
    return [str(item) for item in refs]


def _results_fragment_text(bundle: dict[str, Any], repo_root: Path) -> str:
    fragment_path = repo_root / str(bundle["manuscript_fragments"]["results_fragment"])
    text = fragment_path.read_text(encoding="utf-8")
    for figure_id in bundle_figure_ids(bundle):
        expected = f"../{figure_id}.md.txt"
        if expected not in text:
            raise ValueError(
                f"{bundle['bundle_id']} results_fragment.md must include {expected}"
            )
    return text


def _canonical_display_order(existing_items: list[dict[str, Any]], bundles: list[dict[str, Any]]) -> list[str]:
    bundle_ids = [figure_id for bundle in bundles for figure_id in bundle_figure_ids(bundle)]
    bundle_set = set(bundle_ids)
    existing_ids = [str(item.get("display_item_id")) for item in existing_items]
    existing_bundle_positions = [index for index, item_id in enumerate(existing_ids) if item_id in bundle_set]
    if existing_bundle_positions:
        prefix_cutoff = min(existing_bundle_positions)
        suffix_cutoff = max(existing_bundle_positions)
        prefix = [item_id for item_id in existing_ids[:prefix_cutoff] if item_id not in bundle_set]
        suffix = [item_id for item_id in existing_ids[suffix_cutoff + 1 :] if item_id not in bundle_set]
    else:
        prefix = [item_id for item_id in existing_ids if item_id not in bundle_set]
        suffix = []
    return prefix + bundle_ids + suffix


def _merge_display_item_map(
    existing_payload: dict[str, Any],
    bundles: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    existing_items = existing_payload.get("items", [])
    if not isinstance(existing_items, list):
        raise ValueError("manuscript/plans/display_item_map.json must define an items list")
    existing_by_id = {
        str(item["display_item_id"]): item
        for item in existing_items
        if isinstance(item, dict) and item.get("display_item_id")
    }
    for bundle in bundles:
        for item in _display_items_from_fragment(bundle, repo_root):
            existing_by_id[str(item["display_item_id"])] = item
    ordered_ids = _canonical_display_order(existing_items, bundles)
    merged_items = [existing_by_id[item_id] for item_id in ordered_ids if item_id in existing_by_id]
    payload = dict(existing_payload)
    payload["items"] = merged_items
    return payload


def _merge_writing_plan(
    existing_payload: dict[str, Any],
    merged_display_map: dict[str, Any],
) -> dict[str, Any]:
    refs = [str(item["display_item_id"]) for item in merged_display_map.get("items", [])]
    payload = dict(existing_payload)
    payload["display_item_refs"] = refs
    return payload


def _merge_outline(
    existing_payload: dict[str, Any],
    merged_display_map: dict[str, Any],
) -> dict[str, Any]:
    refs = [str(item["display_item_id"]) for item in merged_display_map.get("items", [])]
    payload = dict(existing_payload)
    payload["display_item_sequence"] = refs
    return payload


def _managed_bundle_block(bundle_ids: list[str]) -> str:
    lines = [MANAGED_RESULTS_START, ""]
    for bundle_id in bundle_ids:
        lines.append(f"```{{include}} ../display_items/_bundles/{bundle_id}.md.txt")
        lines.append("```")
        lines.append("")
    lines.append(MANAGED_RESULTS_END)
    return "\n".join(lines).rstrip() + "\n"


def _replace_managed_results_block(results_text: str, bundle_ids: list[str]) -> str:
    pattern = re.compile(
        rf"{re.escape(MANAGED_RESULTS_START)}.*?{re.escape(MANAGED_RESULTS_END)}",
        re.DOTALL,
    )
    replacement = _managed_bundle_block(bundle_ids)
    if pattern.search(results_text):
        return pattern.sub(replacement, results_text)
    raise ValueError("Results section is missing the managed bundle block markers")


def apply_bundles_to_repo(
    bundle_ids: list[str],
    repo_root: Path = REPO_ROOT,
    write: bool = True,
) -> dict[str, Any]:
    manifests = load_bundle_manifests(repo_root)
    bundles = [manifests[bundle_id] for bundle_id in bundle_ids]

    display_item_map = _load_json(repo_root / "manuscript" / "plans" / "display_item_map.json")
    writing_plan = _load_json(repo_root / "manuscript" / "plans" / "writing_plan.json")
    outline = _load_json(repo_root / "manuscript" / "plans" / "outline.json")
    results_text = (repo_root / "manuscript" / "sections" / "03_results.md").read_text(
        encoding="utf-8"
    )

    merged_display_map = _merge_display_item_map(display_item_map, bundles, repo_root)
    merged_writing_plan = _merge_writing_plan(writing_plan, merged_display_map)
    merged_outline = _merge_outline(outline, merged_display_map)
    managed_results = _replace_managed_results_block(results_text, bundle_ids)

    managed_include_paths: list[str] = []
    for bundle in bundles:
        include_path = repo_root / str(bundle["manuscript_fragments"]["managed_include"])
        include_text = _results_fragment_text(bundle, repo_root)
        managed_include_paths.append(_rel(repo_root, include_path))
        if write:
            _write_text(include_path, include_text)

    if write:
        _write_json(repo_root / "manuscript" / "plans" / "display_item_map.json", merged_display_map)
        _write_json(repo_root / "manuscript" / "plans" / "writing_plan.json", merged_writing_plan)
        _write_json(repo_root / "manuscript" / "plans" / "outline.json", merged_outline)
        _write_text(repo_root / "manuscript" / "sections" / "03_results.md", managed_results)

    return {
        "display_item_map": merged_display_map,
        "writing_plan": merged_writing_plan,
        "outline": merged_outline,
        "results_text": managed_results,
        "managed_include_paths": managed_include_paths,
    }


def _relpath_from(bundle_review_root: Path, target: str) -> str:
    return os.path.relpath(REPO_ROOT / target, bundle_review_root)


def bundle_wiring_status(bundle: dict[str, Any], repo_root: Path = REPO_ROOT) -> str:
    display_map = _load_json(repo_root / "manuscript" / "plans" / "display_item_map.json")
    mapped_ids = {
        str(item.get("display_item_id"))
        for item in display_map.get("items", [])
        if isinstance(item, dict)
    }
    if not set(bundle_figure_ids(bundle)).issubset(mapped_ids):
        return "draft_only"
    include_path = f"../display_items/_bundles/{bundle['bundle_id']}.md.txt"
    results_text = (repo_root / "manuscript" / "sections" / "03_results.md").read_text(
        encoding="utf-8"
    )
    if include_path not in results_text:
        return "fragment_only"
    return "applied"


def build_bundle_summary(bundle_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    bundle = load_bundle_manifest(bundle_id, repo_root)
    spec_map = figure_spec_map()
    font_policy = load_yaml(repo_root / "figures" / "config" / "font_policy.yml")
    outputs = bundle_output_paths(bundle, repo_root)
    font_counts: Counter[str] = Counter()
    clipping_counts: Counter[str] = Counter()
    renderers_present: set[str] = set()
    members: list[dict[str, Any]] = []
    for item in bundle["figures"]:
        figure_id = str(item["figure_id"])
        spec = spec_map[figure_id]
        renderer_map: dict[str, dict[str, Any]] = {}
        for renderer in enabled_renderers(spec):
            manifest_path = repo_root / figure_output_paths(spec, renderer)["manifest"]
            if not manifest_path.exists():
                continue
            manifest = _load_json(manifest_path)
            renderer_map[renderer] = manifest
            renderers_present.add(renderer)
            analysis = {
                "font": analyze_font_resolution(manifest, font_policy),
                "png": analyze_png(repo_root / manifest["outputs"]["png"]),
            }
            font_counts[analysis["font"]["status"]] += 1
            clipping_counts[analysis["png"]["clipping_risk"]] += 1
        members.append(
            {
                "figure_id": figure_id,
                "slot_id": item["slot_id"],
                "role": item["role"],
                "renderers": sorted(renderer_map),
            }
        )
    return {
        "bundle_id": bundle_id,
        "recipe_id": bundle["recipe_id"],
        "member_count": len(bundle["figures"]),
        "figure_ids": bundle_figure_ids(bundle),
        "renderers_present": sorted(renderers_present),
        "font_status_counts": dict(font_counts),
        "clipping_risk_counts": dict(clipping_counts),
        "manuscript_wiring_status": bundle_wiring_status(bundle, repo_root),
        "review_page": _rel(repo_root, outputs["review_page"]),
        "summary_json": _rel(repo_root, outputs["summary_json"]),
        "members": members,
    }


def build_bundle_review_page(bundle_id: str, repo_root: Path = REPO_ROOT) -> Path:
    bundle = load_bundle_manifest(bundle_id, repo_root)
    spec_map = figure_spec_map()
    outputs = bundle_output_paths(bundle, repo_root)
    review_root = outputs["review_page"].parent
    review_root.mkdir(parents=True, exist_ok=True)
    summary = build_bundle_summary(bundle_id, repo_root)

    member_cards: list[str] = []
    for item in bundle["figures"]:
        figure_id = str(item["figure_id"])
        spec = spec_map[figure_id]
        renderer = preview_renderer(spec)
        render_paths = figure_output_paths(spec, renderer)
        member_cards.append(
            f"""
            <section class="member-card">
              <header>
                <div>
                  <h3>{html.escape(figure_id)}</h3>
                  <p><strong>Slot:</strong> <code>{html.escape(str(item['slot_id']))}</code> |
                  <strong>Role:</strong> {html.escape(str(item['role']))}</p>
                </div>
                <div class="meta-pills">
                  <span><strong>Class:</strong> <code>{html.escape(str(item['class_id']))}</code></span>
                  <span><strong>Order:</strong> <code>{html.escape(str(item['display_order']))}</code></span>
                </div>
              </header>
              <div class="preview">
                <img src="{html.escape(os.path.relpath(repo_root / render_paths['png'], review_root))}" alt="{html.escape(figure_id)} preview">
              </div>
              <div class="links">
                <a href="{html.escape(os.path.relpath(repo_root / str(item['spec_path']), review_root))}">Spec</a>
                <a href="{html.escape(os.path.relpath(repo_root / str(item['fact_sheet']), review_root))}">Fact sheet</a>
                <a href="{html.escape(os.path.relpath(repo_root / str(item['legend_path']), review_root))}">Legend</a>
                <a href="{html.escape(os.path.relpath(repo_root / render_paths['svg'], review_root))}">SVG</a>
                <a href="{html.escape(os.path.relpath(repo_root / render_paths['pdf'], review_root))}">PDF</a>
                <a href="{html.escape(os.path.relpath(repo_root / render_paths['manifest'], review_root))}">Manifest</a>
              </div>
              <ul class="sources">
                {''.join(f'<li><a href="{html.escape(os.path.relpath(repo_root / source, review_root))}">{html.escape(source)}</a></li>' for source in item['source_data'])}
              </ul>
            </section>
            """
        )

    slot_rows = "".join(
        f"<tr><td>{html.escape(str(item['display_order']))}</td><td><code>{html.escape(str(item['slot_id']))}</code></td><td>{html.escape(str(item['figure_id']))}</td><td>{html.escape(str(item['role']))}</td></tr>"
        for item in bundle["figures"]
    )
    font_bits = "".join(
        f"<li>{html.escape(status)}: {count}</li>"
        for status, count in sorted(summary["font_status_counts"].items())
    )
    clipping_bits = "".join(
        f"<li>{html.escape(status)}: {count}</li>"
        for status, count in sorted(summary["clipping_risk_counts"].items())
    )
    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(bundle_id)} review</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; background: #f7f4ee; color: #1f1d1a; margin: 0; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 32px 20px 64px; }}
    .panel {{ background: #fffdfa; border: 1px solid #d8d0c3; padding: 18px 20px; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; }}
    .member-card {{ background: #fffdfa; border: 1px solid #d8d0c3; padding: 16px; }}
    .member-card header {{ display: flex; justify-content: space-between; gap: 16px; margin-bottom: 12px; }}
    .meta-pills {{ display: grid; gap: 6px; font-size: 0.92rem; color: #6b645b; }}
    .preview {{ border: 1px solid #d8d0c3; background: #ffffff; padding: 10px; margin-bottom: 12px; min-height: 210px; display: flex; align-items: center; justify-content: center; }}
    .preview img {{ max-width: 100%; height: auto; display: block; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 10px 14px; margin-bottom: 10px; }}
    a {{ color: #124559; text-decoration: none; font-weight: 600; }}
    a:hover {{ text-decoration: underline; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px 10px; border-top: 1px solid #d8d0c3; }}
    thead th {{ border-top: none; }}
    ul {{ margin: 0; padding-left: 18px; }}
    code {{ font-family: Menlo, Consolas, monospace; }}
  </style>
</head>
<body>
  <main>
    <section class="panel">
      <h1>{html.escape(bundle_id)}</h1>
      <p><strong>Recipe:</strong> <code>{html.escape(str(bundle['recipe_id']))}</code> |
      <strong>Family:</strong> <code>{html.escape(str(bundle['family']))}</code> |
      <strong>Expertise:</strong> <code>{html.escape(str(bundle['expertise_track']))}</code> |
      <strong>Wiring:</strong> <code>{html.escape(str(bundle['wiring_mode']))}</code></p>
      <p><strong>Acceptance tier:</strong> <code>{html.escape(str(bundle['acceptance_tier']))}</code> |
      <strong>Manuscript wiring:</strong> <code>{html.escape(str(summary['manuscript_wiring_status']))}</code></p>
    </section>
    <section class="panel">
      <h2>Bundle QA Summary</h2>
      <div class="grid">
        <div>
          <p><strong>Members:</strong> {summary['member_count']}</p>
          <p><strong>Renderers:</strong> {', '.join(summary['renderers_present'])}</p>
        </div>
        <div>
          <h3>Font summary</h3>
          <ul>{font_bits or '<li>none</li>'}</ul>
        </div>
        <div>
          <h3>Clipping summary</h3>
          <ul>{clipping_bits or '<li>none</li>'}</ul>
        </div>
      </div>
    </section>
    <section class="panel">
      <h2>Slot Order</h2>
      <table>
        <thead><tr><th>Order</th><th>Slot</th><th>Figure</th><th>Role</th></tr></thead>
        <tbody>{slot_rows}</tbody>
      </table>
    </section>
    <section class="grid">
      {''.join(member_cards)}
    </section>
  </main>
</body>
</html>
"""
    outputs["review_page"].write_text(html_text, encoding="utf-8")
    _write_json(outputs["summary_json"], summary)
    return outputs["review_page"]


def validate_bundle(bundle_id: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    bundle = load_bundle_manifest(bundle_id, repo_root)
    spec_map = figure_spec_map()
    review_path = repo_root / str(bundle["bundle_outputs"]["review_page"])
    if not review_path.exists():
        raise ValueError(f"{bundle_id} bundle review page is missing")
    review_html = review_path.read_text(encoding="utf-8")
    fragment_items = _display_items_from_fragment(bundle, repo_root)
    _writing_refs_from_fragment(bundle, repo_root)
    _results_fragment_text(bundle, repo_root)
    visualization_plan = _load_json(repo_root / "figures" / "plans" / "visualization_plan.json")
    plan_items = {
        str(item.get("figure_id")): item
        for item in visualization_plan.get("figures", [])
        if isinstance(item, dict) and item.get("figure_id")
    }

    seen_display_ids: set[str] = set()
    for item in fragment_items:
        figure_id = str(item["display_item_id"])
        if figure_id in seen_display_ids:
            raise ValueError(f"{bundle_id} display_item_map.fragment.json has duplicate {figure_id}")
        seen_display_ids.add(figure_id)
        spec = spec_map[figure_id]
        if item.get("claim_ids") != spec["claim_ids"]:
            raise ValueError(f"{bundle_id} fragment claim drift detected for {figure_id}")
        if item.get("spec_path") != spec["_spec_path"]:
            raise ValueError(f"{bundle_id} fragment spec_path drift detected for {figure_id}")
        if item.get("fact_sheet") != spec["fact_sheet"]:
            raise ValueError(f"{bundle_id} fragment fact_sheet drift detected for {figure_id}")
        if item.get("legend_path") != spec["legend_path"]:
            raise ValueError(f"{bundle_id} fragment legend drift detected for {figure_id}")
        plan_item = plan_items.get(figure_id)
        if plan_item is None:
            raise ValueError(f"{bundle_id} visualization plan is missing {figure_id}")
        if plan_item.get("bundle_id") != bundle_id:
            raise ValueError(f"{bundle_id} visualization plan bundle_id drift detected for {figure_id}")
        if plan_item.get("manuscript_section") != "results":
            raise ValueError(f"{bundle_id} visualization plan manuscript_section drift detected for {figure_id}")

    last_position = -1
    for figure_id in bundle_figure_ids(bundle):
        position = review_html.find(figure_id)
        if position == -1:
            raise ValueError(f"{bundle_id} review page is missing {figure_id}")
        if position < last_position:
            raise ValueError(f"{bundle_id} review page does not preserve bundle order")
        last_position = position

    summary_path = repo_root / str(bundle["bundle_outputs"]["summary_json"])
    if not summary_path.exists():
        raise ValueError(f"{bundle_id} bundle summary is missing")
    if bundle_wiring_status(bundle, repo_root) == "applied":
        display_map = _load_json(repo_root / "manuscript" / "plans" / "display_item_map.json")
        current_ids = [
            str(item.get("display_item_id"))
            for item in display_map.get("items", [])
            if isinstance(item, dict)
        ]
        expected_ids = bundle_figure_ids(bundle)
        indices = [current_ids.index(figure_id) for figure_id in expected_ids]
        if indices != list(range(min(indices), max(indices) + 1)):
            raise ValueError(f"{bundle_id} mapped display items are not contiguous in display_item_map.json")
        writing_plan = _load_json(repo_root / "manuscript" / "plans" / "writing_plan.json")
        if writing_plan.get("display_item_refs") != current_ids:
            raise ValueError(f"{bundle_id} writing_plan.json drift detected after apply")
    return _load_json(summary_path)


def scaffold_bundle_manifest(
    bundle_id: str,
    recipe_id: str,
    prefix: str,
    figure_items: list[dict[str, Any]],
) -> dict[str, Any]:
    recipes = load_figure_recipes()
    recipe = recipes[recipe_id]
    return {
        "bundle_id": bundle_id,
        "recipe_id": recipe_id,
        "family": recipe["family"],
        "expertise_track": recipe["expertise_track"],
        "acceptance_tier": "draft",
        "target_manuscript_section": "results",
        "wiring_mode": "additive_drafts",
        "figure_order": [item["figure_id"] for item in figure_items],
        "figures": figure_items,
        "bundle_outputs": {
            "review_page": f"figures/output/review/bundles/{bundle_id}/index.html",
            "summary_json": f"figures/output/bundles/{bundle_id}/summary.json",
        },
        "manuscript_fragments": {
            "display_item_map": f"figures/bundles/{bundle_id}/manuscript/display_item_map.fragment.json",
            "writing_plan": f"figures/bundles/{bundle_id}/manuscript/writing_plan.fragment.json",
            "results_fragment": f"figures/bundles/{bundle_id}/manuscript/results_fragment.md",
            "managed_include": f"manuscript/display_items/_bundles/{bundle_id}.md.txt",
        },
        "shared_claim_ids": [],
        "bundle_prefix": prefix,
    }


def scaffold_bundle_readme(bundle: dict[str, Any]) -> str:
    return (
        f"# {bundle['bundle_id']}\n\n"
        f"- recipe: `{bundle['recipe_id']}`\n"
        f"- family: `{bundle['family']}`\n"
        f"- expertise: `{bundle['expertise_track']}`\n"
        f"- wiring: `{bundle['wiring_mode']}`\n"
        f"- figure count: `{len(bundle['figures'])}`\n\n"
        "This bundle is a tracked figure-set manifest plus manuscript fragments.\n"
    )


def scaffold_bundle_display_fragment(bundle: dict[str, Any]) -> dict[str, Any]:
    items = []
    for figure in bundle["figures"]:
        spec = figure_spec_map()[figure["figure_id"]]
        items.append(
            {
                "display_item_id": figure["figure_id"],
                "type": "figure",
                "manuscript_section": bundle["target_manuscript_section"],
                "claim_ids": figure["claim_ids"],
                "preview_asset": f"manuscript/assets/generated/{figure['figure_id']}.png",
                "spec_path": figure["spec_path"],
                "fact_sheet": figure["fact_sheet"],
                "legend_path": figure["legend_path"],
                "source_data": figure["source_data"],
            }
        )
    return {"items": items}


def scaffold_bundle_writing_fragment(bundle: dict[str, Any]) -> dict[str, Any]:
    return {"display_item_refs": bundle["figure_order"]}


def scaffold_bundle_results_fragment(bundle: dict[str, Any]) -> str:
    lines: list[str] = []
    for figure in bundle["figures"]:
        title = figure_spec_map()[figure["figure_id"]]["title"]
        lines.extend(
            [
                f"### Bundle claim {figure['display_order']}. {title}",
                "",
                f"Use `{figure['figure_id']}` to draft the final Results prose for this bundle slot.",
                "",
                f"```{{include}} ../{figure['figure_id']}.md.txt",
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
