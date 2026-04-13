#!/usr/bin/env python3
"""Compatibility wrapper for the Python volcano/pathway figure builder."""

from __future__ import annotations

from pathlib import Path
import runpy


if __name__ == "__main__":
    target = Path(__file__).with_name("python") / "build_volcano_pathway_figure.py"
    runpy.run_path(str(target), run_name="__main__")
