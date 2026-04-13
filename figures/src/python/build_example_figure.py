#!/usr/bin/env python3
"""Compatibility wrapper for the example timecourse figure."""

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
            "timecourse_endpoint",
            "--spec",
            "figures/specs/figure_01_example.yml",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
