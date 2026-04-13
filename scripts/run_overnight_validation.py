#!/usr/bin/env python3
"""Run an isolated local overnight soak-validation loop for the manuscript harness."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKSPACE_ROOT = Path("/tmp/manuscript_overnight")
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports" / "overnight"
RUNTIME_SUPPORT_PATH = REPO_ROOT / "env" / "runtime_support.yml"
RSYNC_EXCLUDES = [
    ".venv/",
    ".nodeenv/",
    ".cache/",
    "manuscript/_build/",
    "figures/output/",
    "tables/output/",
    "review/retrieval/raw/",
    "review/screening/exports/",
    "reports/",
    "*.log",
]
PYTHON_IMPORTS = [
    "yaml",
    "matplotlib",
    "pytest",
    "pytest_mpl",
    "adjustText",
]
R_PACKAGES = [
    "ggplot2",
    "patchwork",
    "svglite",
    "ragg",
    "yaml",
    "jsonlite",
    "systemfonts",
    "ggrepel",
    "testthat",
]
CORE_HASH_GLOBS = [
    "figures/source_data/**/*.csv",
    "figures/output/python/*.png",
    "figures/output/python/*.svg",
    "figures/output/python/*.pdf",
    "figures/output/r/*.png",
    "figures/output/r/*.svg",
    "figures/output/r/*.pdf",
    "tables/output/table_01_main.csv",
    "tables/output/table_01_main.md",
    "tables/output/table_01_main.json",
    "figures/output/review/index.html",
    "manuscript/assets/generated/*.png",
    "manuscript/sections/assets/generated/*.png",
]
MYST_HTML_HASH_GLOBS = [
    "manuscript/_build/html/index.html",
    "manuscript/_build/html/results/index.html",
]
MYST_SITE_FALLBACK_HASH_GLOBS = [
    "manuscript/_build/site/config.json",
    "manuscript/_build/site/content/index.json",
    "manuscript/_build/site/content/results.json",
    "manuscript/_build/site/myst.xref.json",
    "manuscript/_build/site/myst.search.json",
]
EXPECTED_WARNING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"^(cell|nature|science|conference)\.yml depends on planned (section|special asset) .+$"
        ),
        "planned-venue-dependency",
    ),
    (re.compile(r"^Setting LC_[A-Z_]+ failed, using .+$"), "r-locale-setting-failed"),
    (
        re.compile(r"^OS reports request to set locale to .+ cannot be honored$"),
        "r-locale-request-not-honored",
    ),
    (
        re.compile(r"^System font `DejaVu Sans` not found\. Closest match: `Helvetica`$"),
        "r-font-fallback-helvetica",
    ),
    (
        re.compile(
            r"^System font `Manuscript DejaVu Sans` not found\. Closest match: `DejaVu Sans`$"
        ),
        "r-font-alias-mapped-to-dejavu",
    ),
    (re.compile(r"^Reason: vdiffr cannot be loaded$"), "r-vdiffr-unavailable"),
    (
        re.compile(r"^listen EPERM: operation not permitted .+$"),
        "myst-bind-eperm-after-build",
    ),
    (
        re.compile(r"^(?:\d+:\s*)?package '.+' was built under R version .+$"),
        "r-package-built-under-different-version",
    ),
]
NORMALIZED_WARNING_PATTERNS: list[tuple[re.Pattern[str], str]] = EXPECTED_WARNING_PATTERNS


@dataclass
class CommandResult:
    label: str
    phase: str
    command: list[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str
    started_at: str
    ended_at: str
    duration_seconds: float


@dataclass
class RuntimeCheck:
    name: str
    version: str
    status: str
    detail: str
    comparable: bool


@dataclass
class RunState:
    sandbox_root: Path
    workspace: Path
    report_dir: Path
    baseline_passed: bool = False
    baseline_core_hashes: dict[str, str] | None = None
    baseline_myst_hashes: dict[str, str] | None = None
    myst_hash_mode: str | None = None
    light_runs: int = 0
    full_runs: int = 0
    myst_runs: int = 0
    expected_warnings: Counter[str] | None = None
    unexpected_warnings: Counter[str] | None = None
    failure_signatures: Counter[str] | None = None
    first_failure: dict[str, str] | None = None
    latest_failure: dict[str, str] | None = None
    drift_events: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.expected_warnings is None:
            self.expected_warnings = Counter()
        if self.unexpected_warnings is None:
            self.unexpected_warnings = Counter()
        if self.failure_signatures is None:
            self.failure_signatures = Counter()
        if self.drift_events is None:
            self.drift_events = []


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message)
        if not message.endswith("\n"):
            handle.write("\n")


def _normalize_svg_ids(text: str) -> str:
    id_matches = re.findall(r'id="([^"]+)"', text)
    replacements: dict[str, str] = {}
    for index, original in enumerate(id_matches, start=1):
        replacements.setdefault(original, f"id{index:04d}")
    for original, replacement in replacements.items():
        text = text.replace(f'id="{original}"', f'id="{replacement}"')
        text = text.replace(f'url(#{original})', f'url(#{replacement})')
        text = text.replace(f'xlink:href="#{original}"', f'xlink:href="#{replacement}"')
        text = text.replace(f'href="#{original}"', f'href="#{replacement}"')
    return text


_CSV_NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def _normalize_csv_cell(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    if re.fullmatch(r"[+-]?\d+", text):
        return str(int(text))
    if _CSV_NUMERIC_PATTERN.fullmatch(text):
        number = float(text)
        if abs(number - round(number)) < 1e-9:
            return str(int(round(number)))
        return f"{number:.6f}".rstrip("0").rstrip(".")
    return text


def _serialize_csv_row(cells: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="")
    writer.writerow(cells)
    return buffer.getvalue()


_SITE_HASH_SUFFIX_PATTERN = re.compile(r"-[0-9a-f]{16,64}(?=\.[A-Za-z0-9]+)")


def _normalize_site_json_string(value: str) -> str:
    return _SITE_HASH_SUFFIX_PATTERN.sub("-HASH", value)


def _normalize_site_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            if key in {"key", "sha256"}:
                continue
            normalized[key] = _normalize_site_json_value(value[key])
        return normalized
    if isinstance(value, list):
        return [_normalize_site_json_value(item) for item in value]
    if isinstance(value, str):
        return _normalize_site_json_string(value)
    return value


def canonical_bytes_for_path(path: Path) -> bytes:
    if path.suffix == ".csv" and "figures/source_data" in path.as_posix():
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            return b""
        header = [str(cell).strip() for cell in rows[0]]
        normalized_body = sorted(
            [
                [_normalize_csv_cell(cell) for cell in row[: len(header)]]
                + [""] * max(0, len(header) - len(row))
                for row in rows[1:]
            ]
        )
        serialized = [_serialize_csv_row(header)]
        serialized.extend(_serialize_csv_row(row) for row in normalized_body)
        return ("\n".join(serialized) + "\n").encode("utf-8")
    if path.suffix == ".svg":
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"<metadata>.*?</metadata>", "", text, flags=re.DOTALL)
        text = re.sub(r"<dc:date>.*?</dc:date>", "<dc:date>normalized</dc:date>", text)
        text = _normalize_svg_ids(text)
        text = re.sub(r"\s+\n", "\n", text)
        return text.encode("utf-8")
    if path.suffix == ".pdf":
        blob = path.read_bytes()
        blob = re.sub(
            rb"/CreationDate \(D:\d{14}(?:[+-]\d{2}'\d{2}')?\)",
            b"/CreationDate (D:normalized)",
            blob,
        )
        return blob
    if path.suffix == ".json" and "manuscript/_build/site/" in path.as_posix():
        payload = json.loads(path.read_text(encoding="utf-8"))
        normalized = _normalize_site_json_value(payload)
        return json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return path.read_bytes()


def sha256_for_path(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(canonical_bytes_for_path(path))
    return digest.hexdigest()


def stable_artifact_files(workspace: Path, include_myst: bool) -> list[Path]:
    files: set[Path] = set()
    patterns = CORE_HASH_GLOBS[:]
    if include_myst:
        patterns.extend(selected_myst_hash_globs(workspace))
    for pattern in patterns:
        files.update(path for path in workspace.glob(pattern) if path.is_file())
    return sorted(files)


def hash_artifacts(workspace: Path, include_myst: bool) -> dict[str, str]:
    return {
        str(path.relative_to(workspace)): sha256_for_path(path)
        for path in stable_artifact_files(workspace, include_myst=include_myst)
    }


def diff_hashes(baseline: dict[str, str], current: dict[str, str]) -> list[dict[str, str]]:
    drift: list[dict[str, str]] = []
    for relative in sorted(set(baseline) | set(current)):
        if relative not in baseline:
            drift.append({"path": relative, "status": "new"})
        elif relative not in current:
            drift.append({"path": relative, "status": "missing"})
        elif baseline[relative] != current[relative]:
            drift.append({"path": relative, "status": "changed"})
    return drift


def hash_specific_relative_paths(
    workspace: Path, relative_paths: list[str]
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative in relative_paths:
        path = workspace / relative
        if path.is_file():
            hashes[relative] = sha256_for_path(path)
    return hashes


def write_hash_snapshot(report_dir: Path, snapshot_name: str, hashes: dict[str, str]) -> None:
    write_json(
        report_dir / "hashes" / f"{snapshot_name}.json",
        {
            "snapshot": snapshot_name,
            "path_count": len(hashes),
            "hashes": hashes,
        },
    )


def normalize_warning_signature(line: str) -> str | None:
    text = line.strip()
    if not text:
        return None
    if text in {
        "Warning message:",
        "Warning messages:",
        "During startup - Warning messages:",
        "Warnings:",
    }:
        return None
    if text.startswith("Warning ('test-renderers.R:"):
        return None
    for pattern, signature in NORMALIZED_WARNING_PATTERNS:
        if pattern.search(text):
            return signature
    if text.startswith("Warning"):
        return text
    return None


def expected_warning_signature(signature: str) -> bool:
    return signature in {item[1] for item in EXPECTED_WARNING_PATTERNS}


def failure_signature(result: CommandResult) -> str:
    combined = [line.strip() for line in (result.stdout + "\n" + result.stderr).splitlines()]
    candidates = [
        line
        for line in combined
        if line
        and (
            "failed" in line.lower()
            or line.startswith("Error")
            or line.startswith("Traceback")
            or line.startswith("fatal:")
            or line.startswith("FAIL")
        )
    ]
    detail = candidates[-1] if candidates else f"exit_{result.returncode}"
    return f"{result.label}: {detail}"


def myst_build_artifacts_exist(workspace: Path) -> bool:
    return detect_myst_hash_mode(workspace) != "missing"


def detect_myst_hash_mode(workspace: Path) -> str:
    if all((workspace / relative).is_file() for relative in MYST_HTML_HASH_GLOBS):
        return "html"
    if all((workspace / relative).is_file() for relative in MYST_SITE_FALLBACK_HASH_GLOBS):
        return "site"
    return "missing"


def selected_myst_hash_globs(workspace: Path) -> list[str]:
    mode = detect_myst_hash_mode(workspace)
    if mode == "html":
        return MYST_HTML_HASH_GLOBS
    if mode == "site":
        return MYST_SITE_FALLBACK_HASH_GLOBS
    return []


def selected_myst_relative_paths(workspace: Path) -> list[str]:
    mode = detect_myst_hash_mode(workspace)
    if mode == "html":
        return MYST_HTML_HASH_GLOBS[:]
    if mode == "site":
        return MYST_SITE_FALLBACK_HASH_GLOBS[:]
    return []


def morning_check_paths(workspace: Path) -> dict[str, str]:
    review_page = workspace / "figures/output/review/index.html"
    mode = detect_myst_hash_mode(workspace)
    if mode == "html":
        return {
            "mode": "html",
            "review": str(review_page),
            "index": str(workspace / "manuscript/_build/html/index.html"),
            "results": str(workspace / "manuscript/_build/html/results/index.html"),
        }
    return {
        "mode": "site",
        "review": str(review_page),
        "index": str(workspace / "manuscript/_build/site/content/index.json"),
        "results": str(workspace / "manuscript/_build/site/content/results.json"),
    }


def myst_build_usable_despite_bind_error(result: CommandResult, workspace: Path) -> bool:
    if result.label != "myst-build" or result.returncode == 0:
        return False
    if "listen EPERM: operation not permitted" not in result.stderr:
        return False
    return myst_build_artifacts_exist(workspace)


def runtime_env(workspace: Path, include_node: bool = False) -> dict[str, str]:
    cache_root = workspace / ".cache"
    matplotlib_cache = cache_root / "matplotlib"
    cache_root.mkdir(parents=True, exist_ok=True)
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(cache_root)
    env["MPLCONFIGDIR"] = str(matplotlib_cache)
    if include_node:
        node_bin = workspace / ".nodeenv" / "bin"
        env["PATH"] = f"{node_bin}{os.pathsep}{env.get('PATH', '')}"
    return env


def run_command(
    *,
    label: str,
    phase: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None,
    events_log: Path,
) -> CommandResult:
    started = datetime.now(timezone.utc)
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    ended = datetime.now(timezone.utc)
    result = CommandResult(
        label=label,
        phase=phase,
        command=command,
        cwd=cwd,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_seconds=(ended - started).total_seconds(),
    )
    append_log(
        events_log,
        (
            f"[{result.started_at}] phase={phase} label={label}\n"
            f"cwd={cwd}\n"
            f"command={' '.join(command)}\n"
            f"returncode={result.returncode}\n"
            "--- stdout ---\n"
            f"{result.stdout}"
            "--- stderr ---\n"
            f"{result.stderr}"
            "--- end ---\n"
        ),
    )
    return result


def classify_warnings(state: RunState, result: CommandResult) -> None:
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        signature = normalize_warning_signature(line)
        if signature is None:
            continue
        if expected_warning_signature(signature):
            state.expected_warnings[signature] += 1
        else:
            state.unexpected_warnings[signature] += 1


def record_failure(state: RunState, result: CommandResult) -> None:
    signature = failure_signature(result)
    state.failure_signatures[signature] += 1
    payload = {
        "phase": result.phase,
        "label": result.label,
        "signature": signature,
        "ended_at": result.ended_at,
    }
    if state.first_failure is None:
        state.first_failure = payload
    state.latest_failure = payload


def create_sandbox(source_repo: Path, workspace_root: Path, token: str) -> tuple[Path, Path]:
    sandbox_root = workspace_root / token
    workspace = sandbox_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    rsync = shutil.which("rsync")
    if rsync is None:
        raise RuntimeError("rsync is required for sandbox creation")
    command = [rsync, "-a"]
    for pattern in RSYNC_EXCLUDES:
        command.extend(["--exclude", pattern])
    command.extend([f"{source_repo}/", str(workspace)])
    subprocess.run(command, check=True, cwd=source_repo)

    for name in (".venv", ".nodeenv"):
        target = workspace / name
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.symlink_to(source_repo / name, target_is_directory=True)

    tracked_report_readme = source_repo / "reports" / "overnight" / "README.md"
    if tracked_report_readme.exists():
        sandbox_report_readme = workspace / "reports" / "overnight" / "README.md"
        sandbox_report_readme.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tracked_report_readme, sandbox_report_readme)
    template_cache = source_repo / "manuscript" / "_build" / "templates"
    if template_cache.exists():
        sandbox_template_cache = workspace / "manuscript" / "_build" / "templates"
        sandbox_template_cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(template_cache, sandbox_template_cache, dirs_exist_ok=True)
    return sandbox_root, workspace


def runtime_snapshot(workspace: Path, events_log: Path) -> tuple[dict[str, str], list[CommandResult]]:
    commands = [
        ("system-python", ["python3", "--version"], REPO_ROOT, None),
        ("venv-python", [str(workspace / ".venv" / "bin" / "python"), "--version"], workspace, None),
        ("rscript", ["Rscript", "--version"], workspace, None),
        ("node", [str(workspace / ".nodeenv" / "bin" / "node"), "--version"], workspace, None),
    ]
    versions: dict[str, str] = {}
    results: list[CommandResult] = []
    for label, command, cwd, env in commands:
        result = run_command(
            label=label,
            phase="preflight",
            command=command,
            cwd=cwd,
            env=env,
            events_log=events_log,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Preflight command failed: {label}")
        output = (result.stdout or result.stderr).strip().splitlines()
        versions[label] = output[-1] if output else ""
        results.append(result)
    return versions, results


def assess_runtime_support(versions: dict[str, str], require_supported_runtime: bool) -> list[RuntimeCheck]:
    runtime_support = load_yaml(RUNTIME_SUPPORT_PATH)
    checks: list[RuntimeCheck] = []

    system_python_match = re.search(r"Python (\d+\.\d+)", versions.get("system-python", ""))
    venv_python_match = re.search(r"Python (\d+\.\d+)", versions.get("venv-python", ""))
    node_match = re.search(r"v(\d+)", versions.get("node", ""))
    r_match = re.search(r"version (\d+\.\d+\.\d+)", versions.get("rscript", ""))

    supported_python = {str(item) for item in runtime_support["python"]["supported"]}
    if system_python_match:
        version = system_python_match.group(1)
        status = "supported" if version in supported_python else "unsupported"
        checks.append(
            RuntimeCheck(
                name="system-python",
                version=version,
                status=status,
                detail=f"supported={sorted(supported_python)}",
                comparable=True,
            )
        )
    if venv_python_match:
        version = venv_python_match.group(1)
        status = "supported" if version in supported_python else "unsupported"
        checks.append(
            RuntimeCheck(
                name="venv-python",
                version=version,
                status=status,
                detail=f"supported={sorted(supported_python)}",
                comparable=True,
            )
        )
    if node_match:
        version = node_match.group(1)
        supported_node = {str(item) for item in runtime_support["node"]["supported"]}
        status = "supported" if version in supported_node else "unsupported"
        checks.append(
            RuntimeCheck(
                name="node",
                version=version,
                status=status,
                detail=f"supported_major={sorted(supported_node)}",
                comparable=True,
            )
        )
    if r_match:
        checks.append(
            RuntimeCheck(
                name="rscript",
                version=r_match.group(1),
                status="advisory",
                detail=(
                    "runtime_support.yml uses CI aliases for R "
                    f"({runtime_support['r']['supported']}); exact local version mapping is advisory only"
                ),
                comparable=False,
            )
        )

    if require_supported_runtime:
        failures = [check for check in checks if check.comparable and check.status != "supported"]
        if failures:
            formatted = ", ".join(f"{item.name}={item.version}" for item in failures)
            raise RuntimeError(f"Unsupported concrete local runtimes: {formatted}")
    return checks


def dependency_checks(workspace: Path, events_log: Path) -> list[CommandResult]:
    python_command = [
        str(workspace / ".venv" / "bin" / "python"),
        "-c",
        "; ".join(f"import {name}" for name in PYTHON_IMPORTS),
    ]
    r_command = [
        "Rscript",
        "-e",
        (
            "pkgs <- c("
            + ", ".join(f'"{name}"' for name in R_PACKAGES)
            + "); missing <- pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]; "
            "if (length(missing) > 0) { stop(paste('Missing R packages:', paste(missing, collapse=', '))) }"
        ),
    ]
    return [
        run_command(
            label="python-deps",
            phase="preflight",
            command=python_command,
            cwd=workspace,
            env=runtime_env(workspace),
            events_log=events_log,
        ),
        run_command(
            label="r-deps",
            phase="preflight",
            command=r_command,
            cwd=workspace,
            env=runtime_env(workspace),
            events_log=events_log,
        ),
    ]


def preflight(
    workspace: Path, require_supported_runtime: bool, events_log: Path
) -> tuple[str, list[RuntimeCheck], list[CommandResult]]:
    results: list[CommandResult] = []
    versions, version_results = runtime_snapshot(workspace, events_log)
    results.extend(version_results)
    checks = assess_runtime_support(versions, require_supported_runtime)
    for label, command in (
        ("check-scaffold", [str(workspace / ".venv" / "bin" / "python"), "scripts/check_scaffold.py"]),
        (
            "check-runtime-support",
            [str(workspace / ".venv" / "bin" / "python"), "scripts/check_runtime_support.py"],
        ),
    ):
        results.append(
            run_command(
                label=label,
                phase="preflight",
                command=command,
                cwd=workspace,
                env=runtime_env(workspace),
                events_log=events_log,
            )
        )
    results.extend(dependency_checks(workspace, events_log))
    failures = [result for result in results if result.returncode != 0]
    report = [
        "# Preflight",
        "",
        "## Runtime Snapshot",
    ]
    for name, value in versions.items():
        report.append(f"- `{name}`: `{value}`")
    report.append("")
    report.append("## Runtime Support Assessment")
    for check in checks:
        report.append(
            f"- `{check.name}`: `{check.version}` -> `{check.status}` ({check.detail})"
        )
    report.append("")
    report.append("## Command Results")
    for result in results:
        report.append(
            f"- `{result.label}`: returncode={result.returncode}, duration={result.duration_seconds:.1f}s"
        )
    if failures:
        report.append("")
        report.append("## Failures")
        for result in failures:
            report.append(f"- `{result.label}` failed with returncode {result.returncode}")
    return "\n".join(report) + "\n", checks, results


def baseline_commands(workspace: Path) -> list[tuple[str, Path, list[str], dict[str, str]]]:
    return [
        (
            "build-phase2",
            workspace,
            [str(workspace / ".venv" / "bin" / "python"), "scripts/build_phase2.py"],
            runtime_env(workspace),
        ),
        (
            "python-tests",
            workspace,
            [str(workspace / ".venv" / "bin" / "python"), "-m", "pytest", "tests/figures/python"],
            runtime_env(workspace),
        ),
        (
            "r-tests",
            workspace,
            ["Rscript", "tests/figures/r/testthat.R"],
            runtime_env(workspace),
        ),
        (
            "myst-build",
            workspace / "manuscript",
            [str(workspace / ".venv" / "bin" / "myst"), "build", "--html"],
            runtime_env(workspace, include_node=True),
        ),
    ]


def restore_hash_targets(workspace: Path, state: RunState) -> None:
    result = run_command(
        label="restore-review-assets",
        phase="normalization",
        command=[str(workspace / ".venv" / "bin" / "python"), "scripts/figures_cli.py", "review", "--all"],
        cwd=workspace,
        env=runtime_env(workspace),
        events_log=state.report_dir / "events.log",
    )
    classify_warnings(state, result)
    if result.returncode != 0:
        raise RuntimeError("Failed to restore canonical review/manuscript preview assets before hashing")


def execute_phase(
    *,
    state: RunState,
    phase: str,
    commands: list[tuple[str, Path, list[str], dict[str, str]]],
    stop_on_failure: bool,
    include_myst_hashes: bool,
    snapshot_name: str | None = None,
) -> bool:
    phase_failed = False
    for label, cwd, command, env in commands:
        result = run_command(
            label=label,
            phase=phase,
            command=command,
            cwd=cwd,
            env=env,
            events_log=state.report_dir / "events.log",
        )
        classify_warnings(state, result)
        if result.returncode != 0 and not myst_build_usable_despite_bind_error(result, state.workspace):
            phase_failed = True
            record_failure(state, result)
            if stop_on_failure:
                return False
    if state.baseline_core_hashes is not None or snapshot_name is not None:
        restore_hash_targets(state.workspace, state)
    if include_myst_hashes and state.baseline_myst_hashes is not None:
        current = {
            **hash_artifacts(state.workspace, include_myst=False),
            **hash_specific_relative_paths(
                state.workspace, sorted(state.baseline_myst_hashes.keys())
            ),
        }
        if snapshot_name is not None:
            write_hash_snapshot(state.report_dir, snapshot_name, current)
        drift = diff_hashes(
            {**state.baseline_core_hashes, **state.baseline_myst_hashes}, current
        )
        if snapshot_name is not None and drift:
            write_json(
                state.report_dir / "hashes" / f"{snapshot_name}_drift.json",
                {"phase": phase, "drift": drift},
            )
        for event in drift:
            state.drift_events.append({"phase": phase, **event})
    elif state.baseline_core_hashes is not None:
        current = hash_artifacts(state.workspace, include_myst=False)
        if snapshot_name is not None:
            write_hash_snapshot(state.report_dir, snapshot_name, current)
        drift = diff_hashes(state.baseline_core_hashes, current)
        if snapshot_name is not None and drift:
            write_json(
                state.report_dir / "hashes" / f"{snapshot_name}_drift.json",
                {"phase": phase, "drift": drift},
            )
        for event in drift:
            state.drift_events.append({"phase": phase, **event})
    return not phase_failed


def summarize(state: RunState, started_at: str, ended_at: str, runtime_checks: list[RuntimeCheck]) -> str:
    checks = morning_check_paths(state.workspace)
    lines = [
        "# Overnight Soak Validation Summary",
        "",
        f"- start: `{started_at}`",
        f"- end: `{ended_at}`",
        f"- sandbox root: `{state.sandbox_root}`",
        f"- workspace: `{state.workspace}`",
        f"- baseline: `{'passed' if state.baseline_passed else 'failed'}`",
        f"- MyST artifact mode: `{state.myst_hash_mode or detect_myst_hash_mode(state.workspace)}`",
        f"- light runs: `{state.light_runs}`",
        f"- full runs: `{state.full_runs}`",
        f"- manuscript runs: `{state.myst_runs}`",
        "",
        "## Runtime Snapshot",
    ]
    for check in runtime_checks:
        lines.append(f"- `{check.name}`: `{check.version}` -> `{check.status}` ({check.detail})")
    lines.extend(
        [
            "",
            "## Failures",
            f"- first failure: `{state.first_failure if state.first_failure is not None else 'none'}`",
            f"- latest failure: `{state.latest_failure if state.latest_failure is not None else 'none'}`",
        ]
    )
    if state.failure_signatures:
        lines.append("- repeated failure signatures:")
        for signature, count in state.failure_signatures.most_common():
            lines.append(f"  - `{count}x` {signature}")
    else:
        lines.append("- repeated failure signatures: `none`")

    lines.extend(["", "## Warnings"])
    if state.expected_warnings:
        lines.append("- expected warnings:")
        for signature, count in state.expected_warnings.most_common():
            lines.append(f"  - `{count}x` {signature}")
    else:
        lines.append("- expected warnings: `none`")
    if state.unexpected_warnings:
        lines.append("- unexpected warnings:")
        for signature, count in state.unexpected_warnings.most_common():
            lines.append(f"  - `{count}x` {signature}")
    else:
        lines.append("- unexpected warnings: `none`")

    lines.extend(["", "## Artifact Drift"])
    if state.drift_events:
        for event in state.drift_events:
            lines.append(
                f"- phase=`{event['phase']}` path=`{event['path']}` status=`{event['status']}`"
            )
    else:
        lines.append("- `none`")

    lines.extend(
        [
            "",
            "## Morning Check Paths",
            f"- review page: `{checks['review']}`",
            f"- manuscript index artifact: `{checks['index']}`",
            f"- manuscript results artifact: `{checks['results']}`",
            f"- hash snapshots: `{state.report_dir / 'hashes'}`",
        ]
    )
    if checks["mode"] == "site":
        lines.extend(
            [
                "",
                "## Notes",
                "- Local MyST static HTML export fell back to stable site artifacts because this runtime hits the known application-port bind limitation during `myst build --html`.",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-hours", type=float, default=8.0)
    parser.add_argument("--light-interval-min", type=float, default=15.0)
    parser.add_argument("--full-interval-min", type=float, default=60.0)
    parser.add_argument("--myst-interval-min", type=float, default=120.0)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    parser.add_argument("--keep-workspace", dest="keep_workspace", action="store_true")
    parser.add_argument("--no-keep-workspace", dest="keep_workspace", action="store_false")
    parser.set_defaults(keep_workspace=True)
    parser.add_argument(
        "--require-supported-runtime",
        dest="require_supported_runtime",
        action="store_true",
    )
    parser.add_argument(
        "--no-require-supported-runtime",
        dest="require_supported_runtime",
        action="store_false",
    )
    parser.set_defaults(require_supported_runtime=False)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = datetime.now(timezone.utc)
    token = timestamp_slug()
    report_dir = args.report_root / token
    report_dir.mkdir(parents=True, exist_ok=True)
    events_log = report_dir / "events.log"
    runtime_checks: list[RuntimeCheck] = []
    state: RunState | None = None
    exit_code = 0

    write_json(
        report_dir / "run_config.json",
        {
            "invoked_at": started.isoformat(),
            "repo_root": str(REPO_ROOT),
            "workspace_root": str(args.workspace_root),
            "report_root": str(args.report_root),
            "max_hours": args.max_hours,
            "light_interval_min": args.light_interval_min,
            "full_interval_min": args.full_interval_min,
            "myst_interval_min": args.myst_interval_min,
            "keep_workspace": args.keep_workspace,
            "require_supported_runtime": args.require_supported_runtime,
        },
    )

    try:
        sandbox_root, workspace = create_sandbox(REPO_ROOT, args.workspace_root, token)
        write_json(
            report_dir / "run_config.json",
            {
                "invoked_at": started.isoformat(),
                "repo_root": str(REPO_ROOT),
                "workspace_root": str(args.workspace_root),
                "report_root": str(args.report_root),
                "sandbox_root": str(sandbox_root),
                "workspace": str(workspace),
                "max_hours": args.max_hours,
                "light_interval_min": args.light_interval_min,
                "full_interval_min": args.full_interval_min,
                "myst_interval_min": args.myst_interval_min,
                "keep_workspace": args.keep_workspace,
                "require_supported_runtime": args.require_supported_runtime,
            },
        )
        state = RunState(
            sandbox_root=sandbox_root,
            workspace=workspace,
            report_dir=report_dir,
        )

        preflight_text, runtime_checks, preflight_results = preflight(
            workspace,
            require_supported_runtime=bool(args.require_supported_runtime),
            events_log=events_log,
        )
        write_text(report_dir / "preflight.txt", preflight_text)
        for result in preflight_results:
            classify_warnings(state, result)
        if any(result.returncode != 0 for result in preflight_results):
            raise RuntimeError("Preflight failed")

        baseline_ok = execute_phase(
            state=state,
            phase="baseline",
            commands=baseline_commands(workspace),
            stop_on_failure=True,
            include_myst_hashes=False,
            snapshot_name="baseline_phase_outputs",
        )
        if not baseline_ok:
            exit_code = 1
        else:
            state.baseline_passed = True
            state.myst_hash_mode = detect_myst_hash_mode(workspace)
            if state.myst_hash_mode == "missing":
                raise RuntimeError("Baseline completed without usable MyST artifacts")
            restore_hash_targets(workspace, state)
            all_hashes = hash_artifacts(workspace, include_myst=False)
            myst_hashes = hash_specific_relative_paths(
                workspace, selected_myst_relative_paths(workspace)
            )
            state.baseline_core_hashes = {
                key: value for key, value in all_hashes.items()
            }
            state.baseline_myst_hashes = myst_hashes
            write_hash_snapshot(report_dir, "baseline_core", state.baseline_core_hashes)
            write_hash_snapshot(report_dir, "baseline_myst", state.baseline_myst_hashes)

            deadline = time.monotonic() + max(0.0, float(args.max_hours) * 3600.0)
            now = time.monotonic()
            next_light = now + float(args.light_interval_min) * 60.0
            next_full = now + float(args.full_interval_min) * 60.0
            next_myst = now + float(args.myst_interval_min) * 60.0

            while time.monotonic() < deadline:
                now = time.monotonic()
                ran = False

                if now >= next_full:
                    execute_phase(
                        state=state,
                        phase="full",
                        commands=[
                            (
                                "build-phase2",
                                workspace,
                                [str(workspace / ".venv" / "bin" / "python"), "scripts/build_phase2.py"],
                                runtime_env(workspace),
                            )
                        ],
                        stop_on_failure=False,
                        include_myst_hashes=False,
                        snapshot_name=f"full_{state.full_runs + 1:03d}",
                    )
                    state.full_runs += 1
                    next_full = time.monotonic() + float(args.full_interval_min) * 60.0
                    ran = True

                if now >= next_light:
                    execute_phase(
                        state=state,
                        phase="light",
                        commands=[
                            (
                                "python-tests",
                                workspace,
                                [
                                    str(workspace / ".venv" / "bin" / "python"),
                                    "-m",
                                    "pytest",
                                    "tests/figures/python",
                                ],
                                runtime_env(workspace),
                            ),
                            (
                                "r-tests",
                                workspace,
                                ["Rscript", "tests/figures/r/testthat.R"],
                                runtime_env(workspace),
                            ),
                        ],
                        stop_on_failure=False,
                        include_myst_hashes=False,
                    )
                    state.light_runs += 1
                    next_light = time.monotonic() + float(args.light_interval_min) * 60.0
                    ran = True

                if now >= next_myst:
                    execute_phase(
                        state=state,
                        phase="manuscript",
                        commands=[
                            (
                                "myst-build",
                                workspace / "manuscript",
                                [str(workspace / ".venv" / "bin" / "myst"), "build", "--html"],
                                runtime_env(workspace, include_node=True),
                            )
                        ],
                        stop_on_failure=False,
                        include_myst_hashes=True,
                        snapshot_name=f"manuscript_{state.myst_runs + 1:03d}",
                    )
                    state.myst_runs += 1
                    next_myst = time.monotonic() + float(args.myst_interval_min) * 60.0
                    ran = True

                if not ran:
                    next_due = min(next_light, next_full, next_myst, deadline)
                    sleep_seconds = max(1.0, min(30.0, next_due - time.monotonic()))
                    time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        exit_code = 130
        append_log(events_log, "[interrupt] overnight validation interrupted by user")
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError, yaml.YAMLError) as exc:
        exit_code = 1
        append_log(events_log, f"[fatal] {exc}")
    finally:
        ended = datetime.now(timezone.utc)
        if state is not None:
            summary = summarize(
                state,
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                runtime_checks=runtime_checks,
            )
            write_text(report_dir / "summary.md", summary)
            digest_script = REPO_ROOT / "scripts" / "overnight_digest.py"
            if digest_script.exists():
                subprocess.run(
                    [sys.executable, str(digest_script), "--run-id", token, "--write"],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                )
            if not args.keep_workspace:
                shutil.rmtree(state.sandbox_root, ignore_errors=True)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
