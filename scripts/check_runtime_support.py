#!/usr/bin/env python3
"""Validate runtime-support metadata against CI workflows."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_SUPPORT_PATH = REPO_ROOT / "env/runtime_support.yml"
BUILD_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/build-manuscript.yml"
COMPAT_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/runtime-compatibility.yml"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a YAML object")
    return payload


def validate_runtime_support() -> None:
    runtime = load_yaml(RUNTIME_SUPPORT_PATH)
    build = load_yaml(BUILD_WORKFLOW_PATH)
    compat = load_yaml(COMPAT_WORKFLOW_PATH)

    build_job = build["jobs"]["build"]
    setup_python_step = next(
        step for step in build_job["steps"] if step.get("uses") == "actions/setup-python@v5"
    )
    setup_node_step = next(
        step for step in build_job["steps"] if step.get("uses") == "actions/setup-node@v4"
    )
    setup_r_step = next(
        step for step in build_job["steps"] if step.get("uses") == "r-lib/actions/setup-r@v2"
    )

    if str(setup_python_step["with"]["python-version"]) != str(runtime["python"]["primary"]):
        raise ValueError("build-manuscript.yml does not use the primary Python version")
    if str(setup_node_step["with"]["node-version"]) != str(runtime["node"]["primary"]):
        raise ValueError("build-manuscript.yml does not use the primary Node version")
    if str(setup_r_step["with"]["r-version"]) != str(runtime["r"]["primary"]):
        raise ValueError("build-manuscript.yml does not use the primary R version")

    python_matrix = compat["jobs"]["python-compat"]["strategy"]["matrix"]["python-version"]
    if list(python_matrix) != list(runtime["python"]["ci_tested"]):
        raise ValueError("runtime-compatibility.yml Python matrix does not match runtime_support.yml")

    r_matrix = compat["jobs"]["r-compat"]["strategy"]["matrix"]["r-version"]
    if list(r_matrix) != list(runtime["r"]["ci_tested"]):
        raise ValueError("runtime-compatibility.yml R matrix does not match runtime_support.yml")


def main() -> int:
    try:
        validate_runtime_support()
    except (KeyError, OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Runtime support check failed: {exc}")
        return 1
    print("Runtime support check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
