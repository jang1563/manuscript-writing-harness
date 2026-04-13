#!/usr/bin/env python3
"""Copy generated display assets into the manuscript project for stable preview rendering."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from figures_common import (
    REPO_ROOT,
    figure_output_paths,
    figure_spec_map,
    manuscript_figure_items,
    preview_renderer,
)


def sync_generated_assets(figure_ids: list[str] | None = None) -> list[Path]:
    synced: list[Path] = []
    spec_map = figure_spec_map()
    selected = set(figure_ids or [])
    for figure_id, item in sorted(manuscript_figure_items().items()):
        if selected and figure_id not in selected:
            continue
        spec = spec_map[figure_id]
        renderer = preview_renderer(spec)
        source_rel = figure_output_paths(spec, renderer)["png"]
        source = REPO_ROOT / source_rel
        if not source.exists():
            raise FileNotFoundError(f"Missing preview-renderer output for {figure_id}: {source_rel}")
        targets = [
            REPO_ROOT / str(item["preview_asset"]),
            REPO_ROOT / "manuscript/sections/assets/generated" / f"{figure_id}.png",
        ]
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"Synced manuscript asset: {target.relative_to(REPO_ROOT)}")
            synced.append(target)
    return synced


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--figure",
        action="append",
        dest="figure_ids",
        help="Sync only the specified manuscript figure id. Repeatable.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Sync all mapped manuscript figure preview assets.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sync_generated_assets(args.figure_ids)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
