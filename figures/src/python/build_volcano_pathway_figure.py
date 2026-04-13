#!/usr/bin/env python3
"""Compatibility wrapper for the volcano/pathway figure."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "figures/src/python/run_class_renderer.py"),
            "--class",
            "volcano_pathway_compound",
            "--spec",
            "figures/specs/figure_02_volcano_pathway.yml",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
