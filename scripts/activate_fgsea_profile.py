#!/usr/bin/env python3
"""Promote a validated fgsea config into the active figure-backed profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from fgsea_pipeline import REPO_ROOT, validate_config


ACTIVE_CONFIG_PATH = REPO_ROOT / "pathways" / "configs" / "fgsea_active.yml"
ACTIVE_OUTPUT_DIR = "pathways/results/active_fgsea"
ACTIVE_EXPORT = "pathways/results/active_fgsea/fgsea_pathway_dot_export.csv"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def activate_fgsea_profile(config_path: Path) -> dict[str, object]:
    resolved = config_path.resolve()
    validation = validate_config(resolved)
    if validation["status"] != "valid":
        raise ValueError(f"Cannot activate invalid fgsea profile: {validation['errors']}")

    payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    payload["source_profile"] = _display_path(resolved)
    payload["run_id"] = "fgsea_active"
    payload["output_dir"] = ACTIVE_OUTPUT_DIR
    payload["figure_export_csv"] = ACTIVE_EXPORT

    ACTIVE_CONFIG_PATH.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return {
        "status": "activated",
        "active_config": str(ACTIVE_CONFIG_PATH.relative_to(REPO_ROOT)),
        "source_profile": _display_path(resolved),
        "active_output_dir": ACTIVE_OUTPUT_DIR,
        "active_figure_export_csv": ACTIVE_EXPORT,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Activate a validated fgsea profile")
    parser.add_argument("--config", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = activate_fgsea_profile(Path(args.config))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Activated fgsea profile from {payload['source_profile']}")
        print(f"Active config: {payload['active_config']}")
        print(f"Figure export: {payload['active_figure_export_csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
