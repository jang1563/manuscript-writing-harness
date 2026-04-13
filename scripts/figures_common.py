#!/usr/bin/env python3
"""Shared helpers for the class-based figure library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURE_REGISTRY_PATH = REPO_ROOT / "figures/registry/classes.yml"
FIGURE_RECIPE_PATH = REPO_ROOT / "figures/registry/recipes.yml"
STYLE_PROFILE_PATH = REPO_ROOT / "figures/config/style_profiles.yml"
FIGURE_SPECS_DIR = REPO_ROOT / "figures/specs"
DISPLAY_ITEM_MAP_PATH = REPO_ROOT / "manuscript/plans/display_item_map.json"

CLASS_REQUIRED_FIELDS = {
    "class_id",
    "class_version",
    "intent",
    "required_inputs",
    "supported_renderers",
    "default_size_mm",
    "qa_profile",
    "review_preset",
    "scaffold_templates",
    "authoritative_output_formats",
}

SPEC_REQUIRED_FIELDS = {
    "figure_id",
    "class_id",
    "class_version",
    "title",
    "style_profile",
    "target_profile",
    "claim_ids",
    "fact_sheet",
    "legend_path",
    "visualization_plan",
    "qa_profile",
    "review_preset",
    "parity_status",
    "source_data_outputs",
    "data_inputs",
    "renderers",
    "size",
}

RECIPE_REQUIRED_FIELDS = {
    "recipe_id",
    "family",
    "expertise_track",
    "intent",
    "recommended_sequence",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, dict) else {}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_class_registry() -> dict[str, dict[str, Any]]:
    registry = load_yaml(FIGURE_REGISTRY_PATH)
    classes = registry.get("classes", {})
    if not isinstance(classes, dict):
        raise ValueError("figures/registry/classes.yml must define a classes object")
    normalized: dict[str, dict[str, Any]] = {}
    for class_id, metadata in classes.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"class registry entry {class_id!r} must be an object")
        missing = sorted(CLASS_REQUIRED_FIELDS - metadata.keys())
        if missing:
            raise ValueError(f"class registry entry {class_id!r} is missing {missing}")
        if metadata.get("class_id") != class_id:
            raise ValueError(f"class registry entry {class_id!r} has a mismatched class_id")
        normalized[class_id] = metadata
    return normalized


def load_style_profiles() -> dict[str, dict[str, Any]]:
    payload = load_yaml(STYLE_PROFILE_PATH)
    profiles = payload.get("profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("figures/config/style_profiles.yml must define a non-empty profiles object")
    normalized: dict[str, dict[str, Any]] = {}
    for profile_id, metadata in profiles.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"style profile {profile_id!r} must be an object")
        normalized[profile_id] = metadata
    return normalized


def load_figure_recipes() -> dict[str, dict[str, Any]]:
    payload = load_yaml(FIGURE_RECIPE_PATH)
    recipes = payload.get("recipes", {})
    if not isinstance(recipes, dict):
        raise ValueError("figures/registry/recipes.yml must define a recipes object")
    registry = load_class_registry()
    normalized: dict[str, dict[str, Any]] = {}
    for recipe_id, metadata in recipes.items():
        if not isinstance(metadata, dict):
            raise ValueError(f"recipe {recipe_id!r} must be an object")
        missing = sorted(RECIPE_REQUIRED_FIELDS - metadata.keys())
        if missing:
            raise ValueError(f"recipe {recipe_id!r} is missing {missing}")
        if metadata.get("recipe_id") != recipe_id:
            raise ValueError(f"recipe {recipe_id!r} has a mismatched recipe_id")
        sequence = metadata.get("recommended_sequence", [])
        if not isinstance(sequence, list) or not sequence:
            raise ValueError(f"recipe {recipe_id!r} must define a non-empty recommended_sequence")
        for item in sequence:
            if not isinstance(item, dict):
                raise ValueError(f"recipe {recipe_id!r} recommended_sequence items must be objects")
            class_id = item.get("class_id")
            slot_id = item.get("slot_id")
            if not class_id or not slot_id:
                raise ValueError(
                    f"recipe {recipe_id!r} items must define class_id and slot_id"
                )
            if class_id not in registry:
                raise ValueError(f"recipe {recipe_id!r} references unknown class_id {class_id!r}")
        normalized[recipe_id] = metadata
    return normalized


def source_data_mapping(spec: dict[str, Any]) -> dict[str, str]:
    source_data = spec.get("source_data_outputs") or spec.get("source_data") or {}
    if not isinstance(source_data, dict):
        raise ValueError(f"{spec.get('figure_id', '<unknown>')} source data mapping must be an object")
    return {str(key): str(value) for key, value in source_data.items()}


def normalize_spec(spec: dict[str, Any], spec_path: Path | None = None) -> dict[str, Any]:
    normalized = dict(spec)
    normalized["source_data_outputs"] = source_data_mapping(normalized)
    if "authority_renderer" not in normalized:
        normalized["authority_renderer"] = None
    if spec_path is not None:
        normalized["_spec_path"] = str(spec_path.relative_to(REPO_ROOT))
    return normalized


def validate_spec_against_registry(
    spec: dict[str, Any], registry: dict[str, dict[str, Any]]
) -> None:
    class_id = str(spec["class_id"])
    class_entry = registry[class_id]
    if int(spec["class_version"]) != int(class_entry["class_version"]):
        raise ValueError(f"{spec['figure_id']} class_version does not match the class registry")
    if spec["qa_profile"] != class_entry["qa_profile"]:
        raise ValueError(f"{spec['figure_id']} qa_profile does not match its class registry entry")
    if spec["review_preset"] != class_entry["review_preset"]:
        raise ValueError(f"{spec['figure_id']} review_preset does not match its class registry entry")
    if spec["style_profile"] != class_entry.get("default_style_profile"):
        raise ValueError(f"{spec['figure_id']} style_profile does not match its class registry entry")

    data_inputs = spec.get("data_inputs", [])
    if not isinstance(data_inputs, list) or not data_inputs:
        raise ValueError(f"{spec['figure_id']} data_inputs must be a non-empty list")
    required_inputs = class_entry.get("required_inputs", [])
    if len(data_inputs) != len(required_inputs):
        raise ValueError(
            f"{spec['figure_id']} data_inputs do not match the class registry input contract"
        )

    source_outputs = source_data_mapping(spec)
    panel_ids = [str(panel.get("id")) for panel in spec.get("panels", []) if isinstance(panel, dict)]
    if panel_ids and set(source_outputs.keys()) != set(panel_ids):
        raise ValueError(
            f"{spec['figure_id']} source_data_outputs must match its declared panel ids"
        )

    renderers = spec.get("renderers", {})
    if not isinstance(renderers, dict):
        raise ValueError(f"{spec['figure_id']} renderers must be an object")
    supported = set(class_entry.get("supported_renderers", []))
    unsupported = sorted(set(renderers.keys()) - supported)
    if unsupported:
        raise ValueError(f"{spec['figure_id']} includes unsupported renderers {unsupported}")
    enabled_renderers(spec)


def load_figure_specs() -> list[dict[str, Any]]:
    registry = load_class_registry()
    style_profiles = load_style_profiles()
    specs: list[dict[str, Any]] = []
    for spec_path in sorted(FIGURE_SPECS_DIR.glob("*.yml")):
        raw_spec = load_yaml(spec_path)
        if "style_profile" not in raw_spec and raw_spec.get("class_id") in registry:
            raw_spec["style_profile"] = registry[raw_spec["class_id"]].get("default_style_profile")
        spec = normalize_spec(raw_spec, spec_path)
        missing = sorted(SPEC_REQUIRED_FIELDS - spec.keys())
        if missing:
            raise ValueError(f"{spec_path.relative_to(REPO_ROOT)} is missing canonical fields {missing}")
        if spec.get("parity_status") not in {"dual", "authority_only"}:
            raise ValueError(f"{spec['figure_id']} has invalid parity_status {spec.get('parity_status')!r}")
        if spec["class_id"] not in registry:
            raise ValueError(f"{spec['figure_id']} references unknown class_id {spec['class_id']!r}")
        if spec["style_profile"] not in style_profiles:
            raise ValueError(f"{spec['figure_id']} references unknown style_profile {spec['style_profile']!r}")
        if spec["parity_status"] == "authority_only" and not spec.get("authority_renderer"):
            raise ValueError(f"{spec['figure_id']} must define authority_renderer for authority_only parity")
        validate_spec_against_registry(spec, registry)
        specs.append(spec)
    return specs


def figure_spec_map() -> dict[str, dict[str, Any]]:
    return {spec["figure_id"]: spec for spec in load_figure_specs()}


def figure_instances_by_class() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for spec in load_figure_specs():
        grouped.setdefault(str(spec["class_id"]), []).append(spec)
    for class_id in grouped:
        grouped[class_id] = sorted(grouped[class_id], key=lambda item: str(item["figure_id"]))
    return grouped


def resolve_specs(
    figure_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    specs = load_figure_specs()
    if not figure_ids:
        return specs
    spec_map = {spec["figure_id"]: spec for spec in specs}
    missing = [figure_id for figure_id in figure_ids if figure_id not in spec_map]
    if missing:
        raise ValueError(f"Unknown figure ids: {missing}")
    return [spec_map[figure_id] for figure_id in figure_ids]


def enabled_renderers(spec: dict[str, Any]) -> list[str]:
    renderers = spec.get("renderers", {})
    if not isinstance(renderers, dict):
        raise ValueError(f"{spec['figure_id']} renderers must be an object")
    allowed = {"python", "r"}
    for renderer in renderers:
        if renderer not in allowed:
            raise ValueError(f"{spec['figure_id']} has unsupported renderer {renderer!r}")
    if spec["parity_status"] == "dual":
        required = ["python", "r"]
    else:
        required = [str(spec["authority_renderer"])]
    enabled: list[str] = []
    for renderer in required:
        settings = renderers.get(renderer)
        if not isinstance(settings, dict) or not settings.get("enabled", False):
            raise ValueError(f"{spec['figure_id']} must enable renderer {renderer!r}")
        enabled.append(renderer)
    return enabled


def preview_renderer(spec: dict[str, Any]) -> str:
    if spec["parity_status"] == "authority_only":
        return str(spec["authority_renderer"])
    return "python"


def figure_output_paths(spec: dict[str, Any], renderer: str) -> dict[str, str]:
    output_dir = str(spec["renderers"][renderer]["output_dir"])
    stem = str(spec["figure_id"])
    return {
        "png": f"{output_dir}/{stem}.png",
        "pdf": f"{output_dir}/{stem}.pdf",
        "svg": f"{output_dir}/{stem}.svg",
        "manifest": f"{output_dir}/{stem}.manifest.json",
    }


def load_display_item_map() -> dict[str, Any]:
    if not DISPLAY_ITEM_MAP_PATH.exists():
        return {"items": []}
    return load_json(DISPLAY_ITEM_MAP_PATH)


def manuscript_figure_items() -> dict[str, dict[str, Any]]:
    items = load_display_item_map().get("items", [])
    mapped: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and item.get("type") == "figure":
            mapped[str(item["display_item_id"])] = item
    return mapped


def class_module_path(renderer: str, class_id: str) -> Path:
    if renderer == "python":
        return REPO_ROOT / f"figures/src/python/classes/{class_id}.py"
    if renderer == "r":
        return REPO_ROOT / f"figures/src/r/classes/{class_id}.R"
    raise ValueError(f"Unsupported renderer {renderer!r}")


def figure_ids_for_class(class_id: str) -> list[str]:
    return [spec["figure_id"] for spec in load_figure_specs() if spec["class_id"] == class_id]


def load_figure_roadmap() -> dict[str, Any]:
    roadmap_path = REPO_ROOT / "figures/registry/roadmap.yml"
    roadmap = load_yaml(roadmap_path)
    families = roadmap.get("families", {})
    if not isinstance(families, dict):
        raise ValueError("figures/registry/roadmap.yml must define a families object")
    return roadmap
