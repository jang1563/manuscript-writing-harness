#!/usr/bin/env python3
"""Run a class-based Python renderer for a specific figure spec."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def load_module(class_id: str):
    module_path = REPO_ROOT / f"figures/src/python/classes/{class_id}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Unknown Python class renderer: {class_id}")
    spec = importlib.util.spec_from_file_location(f"figure_class_{class_id}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load renderer module for {class_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--class", dest="class_id", required=True)
    parser.add_argument("--spec", dest="spec_path", required=True)
    args = parser.parse_args()

    module = load_module(args.class_id)
    spec_path = (REPO_ROOT / args.spec_path).resolve()
    module.build_figure(spec_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
