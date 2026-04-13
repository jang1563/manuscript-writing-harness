#!/usr/bin/env python3
"""Repo-local CLI for the class-based figure library."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import yaml

from build_figure_review import build_review_page
from check_generated_artifacts import validate_generated_artifacts
from figures_bundle import (
    apply_bundles_to_repo,
    build_bundle_review_page,
    build_bundle_summary,
    load_bundle_manifest,
    load_bundle_manifests,
    load_bundle_registry,
    scaffold_bundle_manifest,
    scaffold_bundle_readme,
    validate_bundle,
)
from figures_common import (
    REPO_ROOT,
    enabled_renderers,
    figure_instances_by_class,
    load_class_registry,
    load_figure_recipes,
    load_figure_roadmap,
    load_yaml,
    manuscript_figure_items,
    resolve_specs,
    write_text,
)
from sync_manuscript_display_assets import sync_generated_assets


def _runtime_env() -> dict[str, str]:
    cache_root = REPO_ROOT / ".cache"
    matplotlib_cache = cache_root / "matplotlib"
    cache_root.mkdir(parents=True, exist_ok=True)
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("XDG_CACHE_HOME", str(cache_root))
    env.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    return env


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=_runtime_env())


def _spec_target_profile(class_entry: dict[str, Any]) -> str:
    width_mm = float(class_entry["default_size_mm"]["width_mm"])
    if width_mm <= 89:
        return "nature_main_single_column"
    return "nature_main_double_column"


def _default_panels(class_id: str) -> list[dict[str, str]]:
    if class_id == "timecourse_endpoint":
        return [
            {"id": "a", "title": "Time-course panel", "chart_type": "line_with_error_band"},
            {"id": "b", "title": "Endpoint panel", "chart_type": "summary_with_replicates"},
        ]
    if class_id == "volcano_pathway_compound":
        return [
            {"id": "a", "title": "Volcano panel", "chart_type": "volcano_plot"},
            {"id": "b", "title": "Pathway panel", "chart_type": "signed_pathway_summary"},
        ]
    if class_id == "roc_pr_compound":
        return [
            {"id": "a", "title": "ROC discrimination", "chart_type": "roc_curve"},
            {"id": "b", "title": "Precision-recall under imbalance", "chart_type": "precision_recall_curve"},
        ]
    return [{"id": "a", "title": "Primary panel", "chart_type": class_id}]


def _scaffold_spec(class_entry: dict[str, Any], figure_id: str) -> dict[str, Any]:
    data_inputs = []
    for item in class_entry["required_inputs"]:
        data_inputs.append(f"figures/data/{figure_id}_{item['name']}.csv")
    panels = _default_panels(class_entry["class_id"])
    source_outputs = {
        panel["id"]: f"figures/source_data/{figure_id}_{panel['id']}.csv" for panel in panels
    }
    return {
        "figure_id": figure_id,
        "class_id": class_entry["class_id"],
        "class_version": class_entry["class_version"],
        "title": f"Scaffolded {figure_id.replace('_', ' ')}",
        "theme_id": "manuscript_default",
        "font_policy_id": "publication_sans",
        "style_profile": class_entry["default_style_profile"],
        "target_profile": _spec_target_profile(class_entry),
        "qa_profile": class_entry["qa_profile"],
        "review_preset": class_entry["review_preset"],
        "parity_status": "dual",
        "claim_ids": [f"claim_{figure_id}_primary"],
        "fact_sheet": f"figures/fact_sheets/{figure_id}.json",
        "visualization_plan": "figures/plans/visualization_plan.json",
        "legend_path": f"manuscript/legends/{figure_id}.md",
        "size": class_entry["default_size_mm"],
        "data_inputs": data_inputs,
        "source_data_outputs": source_outputs,
        "panels": panels,
        "renderers": {
            "python": {"enabled": True, "output_dir": "figures/output/python"},
            "r": {"enabled": True, "output_dir": "figures/output/r"},
        },
        "caption_stub": (
            "Replace this scaffold caption with a claim-backed description of the figure, "
            "its panel structure, and the evidence path."
        ),
    }


def _scaffold_fact_sheet(spec: dict[str, Any]) -> dict[str, Any]:
    first_panel = spec["panels"][0]["id"]
    first_source = spec["source_data_outputs"][first_panel]
    return {
        "figure_id": spec["figure_id"],
        "claim_ids": spec["claim_ids"],
        "facts": [
            {
                "fact_id": spec["claim_ids"][0],
                "statement": "Replace this placeholder statement with the concrete claim the figure will support.",
                "panel_id": first_panel,
                "source_data": first_source,
                "evidence_type": "replace_with_specific_evidence_type",
            }
        ],
        "design_notes": [
            "Replace this placeholder note with class-specific design constraints before production use.",
            "Keep source-data exports panel-specific and preserve editable vector text.",
        ],
    }


def _scaffold_legend(spec: dict[str, Any]) -> str:
    return (
        f"### {spec['figure_id']}\n\n"
        "Replace this placeholder legend with a concise panel-by-panel description that is consistent "
        "with the fact sheet and manuscript claims.\n"
    )


def _scaffold_display_item(spec: dict[str, Any]) -> str:
    return (
        f"### {spec['figure_id']}\n\n"
        f"```{{figure}} assets/generated/{spec['figure_id']}.png\n"
        f":alt: Replace with an accurate accessibility description for {spec['figure_id']}.\n"
        ":width: 100%\n\n"
        "Replace this placeholder caption with manuscript-ready figure prose.\n"
        "```\n\n"
        "Audit artifacts:\n\n"
        f"- `{spec['fact_sheet']}`\n"
        f"- `{spec['legend_path']}`\n"
        f"- `{spec['visualization_plan']}`\n"
    )


def _scaffold_csv(columns: list[str]) -> str:
    return ",".join(columns) + "\n"


def scaffold_figure(class_id: str, figure_id: str) -> None:
    created = scaffold_targets(class_id, figure_id)
    existing = [path for path in created if path.exists()]
    if existing:
        relative = [str(path.relative_to(REPO_ROOT)) for path in existing]
        raise FileExistsError(f"Scaffold target already exists: {relative}")

    for path, content in created.items():
        write_text(path, content)
        print(f"Created {path.relative_to(REPO_ROOT)}")


def scaffold_targets(class_id: str, figure_id: str) -> dict[Path, str]:
    registry = load_class_registry()
    if class_id not in registry:
        raise ValueError(f"Unknown class_id {class_id!r}")
    class_entry = registry[class_id]
    spec = _scaffold_spec(class_entry, figure_id)

    targets = {
        REPO_ROOT / f"figures/specs/{figure_id}.yml": yaml.safe_dump(
            spec, sort_keys=False, allow_unicode=False
        ),
        REPO_ROOT / f"figures/fact_sheets/{figure_id}.json": json.dumps(
            _scaffold_fact_sheet(spec), indent=2
        )
        + "\n",
        REPO_ROOT / f"manuscript/legends/{figure_id}.md": _scaffold_legend(spec),
        REPO_ROOT / f"manuscript/display_items/{figure_id}.md.txt": _scaffold_display_item(spec),
    }
    for required_input, data_path in zip(class_entry["required_inputs"], spec["data_inputs"]):
        targets[REPO_ROOT / data_path] = _scaffold_csv(list(required_input["columns"]))
    return targets


def preview_scaffold(class_id: str, figure_id: str, as_json: bool = False) -> None:
    targets = scaffold_targets(class_id, figure_id)
    existing = [str(path.relative_to(REPO_ROOT)) for path in targets if path.exists()]
    payload = {
        "class_id": class_id,
        "figure_id": figure_id,
        "create_count": len(targets),
        "create": [str(path.relative_to(REPO_ROOT)) for path in targets],
        "already_exists": existing,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Scaffold preview for {figure_id} ({class_id})")
    print(f"  create_count: {payload['create_count']}")
    if payload["already_exists"]:
        print("  already_exists:")
        for relative in payload["already_exists"]:
            print(f"    - {relative}")
    print("  create:")
    for relative in payload["create"]:
        print(f"    - {relative}")


def recipe_targets(recipe_id: str, prefix: str) -> dict[str, dict[Path, str]]:
    recipes = load_figure_recipes()
    if recipe_id not in recipes:
        raise ValueError(f"Unknown recipe_id {recipe_id!r}")
    targets: dict[str, dict[Path, str]] = {}
    for item in recipes[recipe_id]["recommended_sequence"]:
        figure_id = f"{prefix}_{item['slot_id']}"
        targets[figure_id] = scaffold_targets(str(item["class_id"]), figure_id)
    return targets


def preview_recipe(recipe_id: str, prefix: str, as_json: bool = False) -> None:
    recipes = load_figure_recipes()
    recipe = recipes[recipe_id]
    all_targets = recipe_targets(recipe_id, prefix)
    payload = {
        "recipe_id": recipe_id,
        "prefix": prefix,
        "figure_count": len(all_targets),
        "figures": [],
    }
    for item in recipe["recommended_sequence"]:
        figure_id = f"{prefix}_{item['slot_id']}"
        targets = all_targets[figure_id]
        payload["figures"].append(
            {
                "figure_id": figure_id,
                "class_id": item["class_id"],
                "role": item.get("role", ""),
                "create": [str(path.relative_to(REPO_ROOT)) for path in targets],
                "already_exists": [
                    str(path.relative_to(REPO_ROOT)) for path in targets if path.exists()
                ],
            }
        )
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Recipe preview for {recipe_id} with prefix {prefix}")
    for figure in payload["figures"]:
        print(f"  {figure['figure_id']} ({figure['class_id']})")
        if figure["already_exists"]:
            print("    already_exists:")
            for relative in figure["already_exists"]:
                print(f"      - {relative}")
        print("    create:")
        for relative in figure["create"]:
            print(f"      - {relative}")


def _sorted_bundle_registry_payload(
    existing: dict[str, Any],
    bundle_id: str,
    recipe_id: str,
    acceptance_tier: str = "draft",
) -> dict[str, Any]:
    bundles = dict(existing.get("bundles", {}))
    bundles[bundle_id] = {
        "bundle_id": bundle_id,
        "path": f"figures/bundles/{bundle_id}/bundle.yml",
        "recipe_id": recipe_id,
        "acceptance_tier": acceptance_tier,
    }
    return {"bundles": {key: bundles[key] for key in sorted(bundles)}}


def _bundle_fragment_display_map(
    figure_specs: dict[str, dict[str, Any]],
    figure_items: list[dict[str, Any]],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for figure in figure_items:
        spec = figure_specs[str(figure["figure_id"])]
        items.append(
            {
                "display_item_id": spec["figure_id"],
                "type": "figure",
                "manuscript_section": "results",
                "claim_ids": spec["claim_ids"],
                "preview_asset": f"manuscript/assets/generated/{spec['figure_id']}.png",
                "spec_path": f"figures/specs/{spec['figure_id']}.yml",
                "fact_sheet": spec["fact_sheet"],
                "legend_path": spec["legend_path"],
                "source_data": list(spec["source_data_outputs"].values()),
            }
        )
    return {"items": items}


def _bundle_fragment_results(
    figure_specs: dict[str, dict[str, Any]],
    figure_items: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    for figure in figure_items:
        spec = figure_specs[str(figure["figure_id"])]
        lines.extend(
            [
                f"### Bundle claim {figure['display_order']}. {spec['title']}",
                "",
                f"Use `{spec['figure_id']}` to draft the final Results prose for this bundle slot.",
                "",
                f"```{{include}} ../{spec['figure_id']}.md.txt",
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def bundle_targets(recipe_id: str, bundle_id: str, prefix: str) -> dict[Path, str]:
    recipes = load_figure_recipes()
    if recipe_id not in recipes:
        raise ValueError(f"Unknown recipe_id {recipe_id!r}")
    registry_path = REPO_ROOT / "figures/bundles/bundles.yml"
    registry_payload = load_yaml(registry_path)
    bundles = registry_payload.get("bundles", {})
    if bundle_id in bundles:
        raise FileExistsError(f"Bundle scaffold target already exists: figures/bundles/{bundle_id}")

    class_registry = load_class_registry()
    recipe = recipes[recipe_id]
    figure_targets = recipe_targets(recipe_id, prefix)
    figure_specs: dict[str, dict[str, Any]] = {}
    figure_items: list[dict[str, Any]] = []
    for order, item in enumerate(recipe["recommended_sequence"], start=1):
        class_id = str(item["class_id"])
        figure_id = f"{prefix}_{item['slot_id']}"
        spec = _scaffold_spec(class_registry[class_id], figure_id)
        figure_specs[figure_id] = spec
        figure_items.append(
            {
                "slot_id": str(item["slot_id"]),
                "class_id": class_id,
                "figure_id": figure_id,
                "role": str(item.get("role", "")),
                "display_order": order,
                "claim_ids": spec["claim_ids"],
                "spec_path": f"figures/specs/{figure_id}.yml",
                "fact_sheet": spec["fact_sheet"],
                "legend_path": spec["legend_path"],
                "source_data": list(spec["source_data_outputs"].values()),
            }
        )

    bundle_manifest = scaffold_bundle_manifest(bundle_id, recipe_id, prefix, figure_items)
    bundle_root = REPO_ROOT / "figures" / "bundles" / bundle_id
    bundle_display_fragment = _bundle_fragment_display_map(figure_specs, figure_items)
    bundle_writing_fragment = {"display_item_refs": [item["figure_id"] for item in figure_items]}
    bundle_results_fragment = _bundle_fragment_results(figure_specs, figure_items)

    targets: dict[Path, str] = {
        registry_path: yaml.safe_dump(
            _sorted_bundle_registry_payload(registry_payload, bundle_id, recipe_id),
            sort_keys=False,
            allow_unicode=False,
        ),
        bundle_root / "bundle.yml": yaml.safe_dump(
            bundle_manifest,
            sort_keys=False,
            allow_unicode=False,
        ),
        bundle_root / "README.md": scaffold_bundle_readme(bundle_manifest),
        bundle_root / "manuscript/display_item_map.fragment.json": json.dumps(
            bundle_display_fragment,
            indent=2,
        )
        + "\n",
        bundle_root / "manuscript/writing_plan.fragment.json": json.dumps(
            bundle_writing_fragment,
            indent=2,
        )
        + "\n",
        bundle_root / "manuscript/results_fragment.md": bundle_results_fragment,
    }
    for figure_target_map in figure_targets.values():
        targets.update(figure_target_map)
    return targets


def preview_bundle(recipe_id: str, bundle_id: str, prefix: str, as_json: bool = False) -> None:
    targets = bundle_targets(recipe_id, bundle_id, prefix)
    bundle_root = REPO_ROOT / "figures" / "bundles" / bundle_id
    payload = {
        "recipe_id": recipe_id,
        "bundle_id": bundle_id,
        "prefix": prefix,
        "create_count": len(targets),
        "bundle_paths": [
            str(path.relative_to(REPO_ROOT))
            for path in sorted(targets)
            if bundle_root in path.parents or path == bundle_root
        ],
        "figure_count": len(load_figure_recipes()[recipe_id]["recommended_sequence"]),
        "create": [str(path.relative_to(REPO_ROOT)) for path in sorted(targets)],
        "already_exists": [
            str(path.relative_to(REPO_ROOT)) for path in sorted(targets) if path.exists()
        ],
    }
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Bundle scaffold preview for {bundle_id} from {recipe_id}")
    print(f"  figure_count: {payload['figure_count']}")
    print(f"  create_count: {payload['create_count']}")
    if payload["already_exists"]:
        print("  already_exists:")
        for relative in payload["already_exists"]:
            print(f"    - {relative}")
    print("  create:")
    for relative in payload["create"]:
        print(f"    - {relative}")


def scaffold_bundle(recipe_id: str, bundle_id: str, prefix: str) -> None:
    targets = bundle_targets(recipe_id, bundle_id, prefix)
    registry_path = REPO_ROOT / "figures/bundles/bundles.yml"
    existing = [path for path in targets if path.exists() and path != registry_path]
    if existing:
        relative = [str(path.relative_to(REPO_ROOT)) for path in existing]
        raise FileExistsError(f"Bundle scaffold target already exists: {relative}")
    for path, content in targets.items():
        write_text(path, content)
        print(f"Created {path.relative_to(REPO_ROOT)}")


def scaffold_recipe(recipe_id: str, prefix: str) -> None:
    all_targets = recipe_targets(recipe_id, prefix)
    existing = [
        str(path.relative_to(REPO_ROOT))
        for targets in all_targets.values()
        for path in targets
        if path.exists()
    ]
    if existing:
        raise FileExistsError(f"Recipe scaffold target already exists: {existing}")
    for figure_id, targets in all_targets.items():
        for path, content in targets.items():
            write_text(path, content)
            print(f"Created {path.relative_to(REPO_ROOT)} for {figure_id}")


def list_bundles() -> None:
    manifests = load_bundle_manifests()
    for bundle_id, bundle in sorted(manifests.items()):
        print(
            f"{bundle_id}\n"
            f"  recipe: {bundle['recipe_id']}\n"
            f"  family: {bundle['family']}\n"
            f"  expertise: {bundle['expertise_track']}\n"
            f"  acceptance: {bundle['acceptance_tier']}\n"
            f"  figures: {len(bundle['figures'])}\n"
            f"  wiring: {bundle['wiring_mode']}"
        )


def show_bundle(bundle_id: str) -> None:
    bundle = load_bundle_manifest(bundle_id)
    print(
        f"{bundle_id}\n"
        f"  recipe: {bundle['recipe_id']}\n"
        f"  family: {bundle['family']}\n"
        f"  expertise: {bundle['expertise_track']}\n"
        f"  acceptance: {bundle['acceptance_tier']}\n"
        f"  target_manuscript_section: {bundle['target_manuscript_section']}\n"
        f"  wiring: {bundle['wiring_mode']}"
    )
    print("  figures:")
    for item in bundle["figures"]:
        print(
            f"    - {item['display_order']}. {item['slot_id']} -> {item['figure_id']} "
            f"({item['class_id']}; {item['role']})"
        )
    print("  fragments:")
    for key, value in bundle["manuscript_fragments"].items():
        print(f"    - {key}: {value}")


def list_classes() -> None:
    registry = load_class_registry()
    instances = figure_instances_by_class()
    for class_id, entry in sorted(registry.items()):
        renderers = ", ".join(entry["supported_renderers"])
        print(
            f"{class_id}\n"
            f"  family: {entry.get('family', 'unknown')}\n"
            f"  expertise: {entry.get('expertise_track', 'unknown')}\n"
            f"  status: {entry.get('status', 'unknown')}\n"
            f"  style_profile: {entry.get('default_style_profile', 'unknown')}\n"
            f"  renderers: {renderers}\n"
            f"  instances: {len(instances.get(class_id, []))}\n"
            f"  intent: {entry['intent']}"
        )


def list_instances() -> None:
    mapped_ids = set(manuscript_figure_items())
    for spec in resolve_specs():
        renderers = ", ".join(enabled_renderers(spec))
        manuscript_status = "mapped" if spec["figure_id"] in mapped_ids else "unmapped"
        print(
            f"{spec['figure_id']}\n"
            f"  class: {spec['class_id']}\n"
            f"  style_profile: {spec['style_profile']}\n"
            f"  parity: {spec['parity_status']}\n"
            f"  renderers: {renderers}\n"
            f"  manuscript: {manuscript_status}\n"
            f"  title: {spec['title']}"
        )


def list_roadmap() -> None:
    roadmap = load_figure_roadmap()
    for family_id, family in sorted(roadmap.get("families", {}).items()):
        print(
            f"{family_id}\n"
            f"  status: {family.get('status', 'unknown')}\n"
            f"  expertise: {family.get('expertise_track', 'unknown')}\n"
            f"  style_profile: {family.get('default_style_profile', 'n/a')}"
        )
        for key in ("implemented_classes", "planned_classes"):
            entries = family.get(key, [])
            if not entries:
                continue
            print(f"  {key}:")
            for entry in entries:
                if isinstance(entry, dict):
                    print(f"    - {entry.get('class_id')}: {entry.get('intent', '')}")
                else:
                    print(f"    - {entry}")


def list_recipes() -> None:
    recipes = load_figure_recipes()
    for recipe_id, recipe in sorted(recipes.items()):
        print(
            f"{recipe_id}\n"
            f"  family: {recipe.get('family', 'unknown')}\n"
            f"  expertise: {recipe.get('expertise_track', 'unknown')}\n"
            f"  figures: {len(recipe.get('recommended_sequence', []))}\n"
            f"  intent: {recipe['intent']}"
        )


def show_recipe(recipe_id: str) -> None:
    recipes = load_figure_recipes()
    if recipe_id not in recipes:
        raise ValueError(f"Unknown recipe_id {recipe_id!r}")
    recipe = recipes[recipe_id]
    print(
        f"{recipe_id}\n"
        f"  family: {recipe.get('family', 'unknown')}\n"
        f"  expertise: {recipe.get('expertise_track', 'unknown')}\n"
        f"  intent: {recipe['intent']}"
    )
    print("  recommended_sequence:")
    for item in recipe.get("recommended_sequence", []):
        print(
            f"    - {item['slot_id']}: {item['class_id']} "
            f"({item.get('role', '').strip()})"
        )
    for note in recipe.get("notes", []):
        print(f"  note: {note}")


def render_cookbook_markdown() -> str:
    recipes = load_figure_recipes()
    lines = [
        "# Figure Recipe Cookbook",
        "",
        f"- recipes: `{len(recipes)}`",
        "",
    ]
    for recipe_id, recipe in sorted(recipes.items()):
        lines.extend(
            [
                f"## {recipe_id}",
                "",
                f"- family: `{recipe.get('family', 'unknown')}`",
                f"- expertise: `{recipe.get('expertise_track', 'unknown')}`",
                f"- figure count: `{len(recipe.get('recommended_sequence', []))}`",
                f"- intent: {recipe['intent']}",
                "",
                "Recommended sequence:",
            ]
        )
        for item in recipe.get("recommended_sequence", []):
            lines.append(
                f"- `{item['slot_id']}` -> `{item['class_id']}`: {item.get('role', '').strip()}"
            )
        notes = recipe.get("notes", [])
        if notes:
            lines.extend(["", "Notes:"])
            for note in notes:
                lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def print_cookbook(output_path: str | None = None) -> None:
    rendered = render_cookbook_markdown()
    if output_path:
        target = REPO_ROOT / output_path
        write_text(target, rendered)
        print(f"Wrote {target.relative_to(REPO_ROOT)}")
        return
    print(rendered, end="")


def render_catalog_markdown() -> str:
    registry = load_class_registry()
    instances = figure_instances_by_class()
    lines = [
        "# Figure Library Catalog",
        "",
        f"- implemented classes: `{len(registry)}`",
        f"- figure instances: `{sum(len(items) for items in instances.values())}`",
        "",
    ]
    for class_id, entry in sorted(registry.items()):
        class_instances = instances.get(class_id, [])
        lines.extend(
            [
                f"## {class_id}",
                "",
                f"- family: `{entry.get('family', 'unknown')}`",
                f"- expertise: `{entry.get('expertise_track', 'unknown')}`",
                f"- status: `{entry.get('status', 'unknown')}`",
                f"- style profile: `{entry.get('default_style_profile', 'unknown')}`",
                f"- renderers: `{', '.join(entry.get('supported_renderers', []))}`",
                f"- instance count: `{len(class_instances)}`",
                f"- intent: {entry['intent']}",
                "",
                "Required inputs:",
            ]
        )
        for item in entry.get("required_inputs", []):
            columns = ", ".join(item.get("columns", []))
            lines.append(f"- `{item['name']}` ({item['format']}): {columns}")
        lines.extend(["", "Instances:"])
        if class_instances:
            for spec in class_instances:
                lines.append(
                    f"- `{spec['figure_id']}`: {spec['title']} "
                    f"(style `{spec['style_profile']}`, parity `{spec['parity_status']}`)"
                )
        else:
            lines.append("- `none yet`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def print_catalog(output_path: str | None = None) -> None:
    rendered = render_catalog_markdown()
    if output_path:
        target = REPO_ROOT / output_path
        write_text(target, rendered)
        print(f"Wrote {target.relative_to(REPO_ROOT)}")
        return
    print(rendered, end="")


def build_figures(figure_ids: list[str] | None = None) -> None:
    specs = resolve_specs(figure_ids)
    rscript = shutil.which("Rscript")
    if any("r" in enabled_renderers(spec) for spec in specs) and not rscript:
        raise RuntimeError("Rscript is required for the dual-language figure pipeline")
    for spec in specs:
        for renderer in enabled_renderers(spec):
            if renderer == "python":
                command = [
                    sys.executable,
                    str(REPO_ROOT / "figures/src/python/run_class_renderer.py"),
                    "--class",
                    str(spec["class_id"]),
                    "--spec",
                    str(spec["_spec_path"]),
                ]
            else:
                command = [
                    str(rscript),
                    str(REPO_ROOT / "figures/src/r/run_class_renderer.R"),
                    "--class",
                    str(spec["class_id"]),
                    "--spec",
                    str(spec["_spec_path"]),
                ]
            print(f"[figures] build {spec['figure_id']} ({renderer})")
            _run(command)


def build_bundle(bundle_id: str) -> None:
    bundle = load_bundle_manifest(bundle_id)
    build_figures(bundle["figure_order"])


def review_bundle(bundle_id: str) -> None:
    bundle = load_bundle_manifest(bundle_id)
    build_figures(bundle["figure_order"])
    review_path = build_bundle_review_page(bundle_id)
    mapped_ids = set(manuscript_figure_items())
    manuscript_ids = [figure_id for figure_id in bundle["figure_order"] if figure_id in mapped_ids]
    if manuscript_ids:
        sync_generated_assets(manuscript_ids)
    print(f"Wrote {review_path.relative_to(REPO_ROOT)}")


def validate_bundle_cli(bundle_id: str) -> None:
    bundle = load_bundle_manifest(bundle_id)
    build_figures(bundle["figure_order"])
    build_review_page(bundle["figure_order"])
    build_bundle_review_page(bundle_id)
    mapped_ids = set(manuscript_figure_items())
    manuscript_ids = [figure_id for figure_id in bundle["figure_order"] if figure_id in mapped_ids]
    if manuscript_ids:
        sync_generated_assets(manuscript_ids)
    validate_generated_artifacts(figure_ids=bundle["figure_order"], include_table=False)
    summary = validate_bundle(bundle_id)
    print(json.dumps(summary, indent=2))


def apply_bundle(bundle_id: str) -> None:
    bundle_ids = list(load_bundle_registry().keys())
    if bundle_id not in bundle_ids:
        raise ValueError(f"Unknown bundle_id {bundle_id!r}")
    result = apply_bundles_to_repo(bundle_ids)
    print(
        json.dumps(
            {
                "bundle_ids": bundle_ids,
                "requested_bundle_id": bundle_id,
                "display_item_refs": result["writing_plan"]["display_item_refs"],
                "managed_include_paths": result["managed_include_paths"],
            },
            indent=2,
        )
    )


def apply_all_bundles() -> None:
    bundle_ids = list(load_bundle_registry().keys())
    result = apply_bundles_to_repo(bundle_ids)
    print(
        json.dumps(
            {
                "bundle_ids": bundle_ids,
                "display_item_refs": result["writing_plan"]["display_item_refs"],
                "managed_include_paths": result["managed_include_paths"],
            },
            indent=2,
        )
    )


def build_review(figure_ids: list[str] | None = None) -> None:
    build_review_page(figure_ids)
    if figure_ids is None:
        sync_generated_assets(None)
        return
    mapped_ids = set(manuscript_figure_items())
    manuscript_ids = [figure_id for figure_id in figure_ids if figure_id in mapped_ids]
    if manuscript_ids:
        sync_generated_assets(manuscript_ids)


def validate_figures(figure_ids: list[str] | None = None, include_table: bool = False) -> None:
    build_review_page(figure_ids)
    if figure_ids is None:
        sync_generated_assets(None)
    else:
        mapped_ids = set(manuscript_figure_items())
        manuscript_ids = [figure_id for figure_id in figure_ids if figure_id in mapped_ids]
        if manuscript_ids:
            sync_generated_assets(manuscript_ids)
    validate_generated_artifacts(figure_ids=figure_ids, include_table=include_table)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-classes", help="List available figure classes.")
    subparsers.add_parser("list-instances", help="List implemented figure instances.")
    subparsers.add_parser("list-roadmap", help="List implemented and planned figure families.")
    subparsers.add_parser("list-recipes", help="List reusable figure-bundle recipes.")
    subparsers.add_parser("list-bundles", help="List tracked manuscript-facing figure bundles.")
    catalog = subparsers.add_parser("catalog", help="Render the figure-library catalog as markdown.")
    catalog.add_argument("--write", dest="output_path", help="Write the catalog markdown to a repo-relative path.")
    cookbook = subparsers.add_parser("cookbook", help="Render the figure recipe cookbook as markdown.")
    cookbook.add_argument("--write", dest="output_path", help="Write the cookbook markdown to a repo-relative path.")
    show_recipe_parser = subparsers.add_parser("show-recipe", help="Show one recipe in detail.")
    show_recipe_parser.add_argument("--recipe", required=True)
    show_bundle_parser = subparsers.add_parser("show-bundle", help="Show one tracked bundle in detail.")
    show_bundle_parser.add_argument("--bundle", required=True)

    scaffold = subparsers.add_parser("scaffold", help="Scaffold a new figure instance.")
    scaffold.add_argument("--class", dest="class_id", required=True)
    scaffold.add_argument("--figure-id", required=True)
    scaffold.add_argument("--dry-run", action="store_true", help="Preview scaffold targets without writing files.")
    scaffold.add_argument("--json", action="store_true", help="Emit scaffold preview as JSON. Requires --dry-run.")

    scaffold_recipe_parser = subparsers.add_parser(
        "scaffold-recipe",
        help="Scaffold a recipe-aligned bundle of figure instances.",
    )
    scaffold_recipe_parser.add_argument("--recipe", required=True)
    scaffold_recipe_parser.add_argument("--prefix", required=True)
    scaffold_recipe_parser.add_argument("--dry-run", action="store_true", help="Preview recipe scaffold targets without writing files.")
    scaffold_recipe_parser.add_argument("--json", action="store_true", help="Emit recipe scaffold preview as JSON. Requires --dry-run.")

    scaffold_bundle_parser = subparsers.add_parser(
        "scaffold-bundle",
        help="Scaffold a tracked bundle plus recipe-aligned figure instance stubs.",
    )
    scaffold_bundle_parser.add_argument("--recipe", required=True)
    scaffold_bundle_parser.add_argument("--bundle-id", required=True)
    scaffold_bundle_parser.add_argument("--prefix", required=True)
    scaffold_bundle_parser.add_argument("--dry-run", action="store_true", help="Preview bundle scaffold targets without writing files.")
    scaffold_bundle_parser.add_argument("--json", action="store_true", help="Emit bundle scaffold preview as JSON. Requires --dry-run.")

    for command_name, help_text in (
        ("build", "Build one figure or all figures."),
        ("review", "Generate the figure-review page."),
        ("validate", "Validate generated figure artifacts."),
    ):
        command = subparsers.add_parser(command_name, help=help_text)
        group = command.add_mutually_exclusive_group()
        group.add_argument("--figure", action="append", dest="figure_ids")
        group.add_argument("--all", action="store_true")

    for command_name, help_text in (
        ("build-bundle", "Build one tracked bundle."),
        ("review-bundle", "Build the review page for one tracked bundle."),
        ("validate-bundle", "Validate one tracked bundle plus its member figures."),
        ("apply-bundle", "Apply one tracked bundle into the canonical manuscript planning files."),
    ):
        command = subparsers.add_parser(command_name, help=help_text)
        command.add_argument("--bundle", required=True)

    apply_all = subparsers.add_parser(
        "apply-bundles",
        help="Apply all tracked bundles into the canonical manuscript planning files.",
    )
    apply_all.add_argument("--all", action="store_true", required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "list-classes":
            list_classes()
        elif args.command == "list-instances":
            list_instances()
        elif args.command == "list-roadmap":
            list_roadmap()
        elif args.command == "list-recipes":
            list_recipes()
        elif args.command == "list-bundles":
            list_bundles()
        elif args.command == "catalog":
            print_catalog(args.output_path)
        elif args.command == "cookbook":
            print_cookbook(args.output_path)
        elif args.command == "show-recipe":
            show_recipe(args.recipe)
        elif args.command == "show-bundle":
            show_bundle(args.bundle)
        elif args.command == "scaffold":
            if args.json and not args.dry_run:
                raise ValueError("--json is only supported together with --dry-run")
            if args.dry_run:
                preview_scaffold(args.class_id, args.figure_id, as_json=bool(args.json))
            else:
                scaffold_figure(args.class_id, args.figure_id)
        elif args.command == "scaffold-recipe":
            if args.json and not args.dry_run:
                raise ValueError("--json is only supported together with --dry-run")
            if args.dry_run:
                preview_recipe(args.recipe, args.prefix, as_json=bool(args.json))
            else:
                scaffold_recipe(args.recipe, args.prefix)
        elif args.command == "scaffold-bundle":
            if args.json and not args.dry_run:
                raise ValueError("--json is only supported together with --dry-run")
            if args.dry_run:
                preview_bundle(args.recipe, args.bundle_id, args.prefix, as_json=bool(args.json))
            else:
                scaffold_bundle(args.recipe, args.bundle_id, args.prefix)
        elif args.command == "build":
            build_figures(args.figure_ids)
        elif args.command == "review":
            build_review(args.figure_ids)
        elif args.command == "validate":
            validate_figures(
                figure_ids=args.figure_ids,
                include_table=bool(args.all or not args.figure_ids),
            )
        elif args.command == "build-bundle":
            build_bundle(args.bundle)
        elif args.command == "review-bundle":
            review_bundle(args.bundle)
        elif args.command == "validate-bundle":
            validate_bundle_cli(args.bundle)
        elif args.command == "apply-bundle":
            apply_bundle(args.bundle)
        elif args.command == "apply-bundles":
            if not args.all:
                raise ValueError("apply-bundles currently requires --all")
            apply_all_bundles()
        else:
            raise ValueError(f"Unsupported command {args.command!r}")
    except (FileExistsError, FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"figures_cli failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
