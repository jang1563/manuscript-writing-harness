#!/usr/bin/env python3
"""Build Phase 2 figure and table artifacts without requiring make."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parent.parent


def run_step(label: str, command: list[str]) -> None:
    cache_root = REPO_ROOT / ".cache"
    matplotlib_cache = cache_root / "matplotlib"
    cache_root.mkdir(parents=True, exist_ok=True)
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("XDG_CACHE_HOME", str(cache_root))
    env.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    print(f"[phase2] {label}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=env)


def main() -> int:
    python = sys.executable
    run_step("scaffold check", [python, "scripts/check_scaffold.py"])
    run_step(
        "refresh active fgsea profile",
        [
            python,
            "scripts/fgsea_pipeline.py",
            "run",
            "--config",
            "pathways/configs/fgsea_active.yml",
            "--allow-missing-package",
            "--json",
        ],
    )
    run_step("build all figures", [python, "scripts/figures_cli.py", "build", "--all"])
    run_step("build example table", [python, "tables/src/build_main_table.py"])
    run_step("build figure review page", [python, "scripts/figures_cli.py", "review", "--all"])
    run_step("generated artifact check", [python, "scripts/figures_cli.py", "validate", "--all"])
    print("[phase2] complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
