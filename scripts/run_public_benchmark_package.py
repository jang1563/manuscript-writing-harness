#!/usr/bin/env python3
"""Evaluate a local public benchmark package into a self-contained run directory."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from harness_benchmark import (
    PUBLIC_RUNS_DIR,
    REPO_ROOT,
    build_harness_benchmark_report_from_package,
    build_harness_benchmark_report_from_package_archive,
    package_archive_effective_sha256,
    package_effective_sha256,
    write_harness_benchmark_report_outputs_to_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, help="Benchmark package directory to evaluate.")
    parser.add_argument("--package-archive", type=Path, help="Benchmark package .zip archive to evaluate.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PUBLIC_RUNS_DIR,
        help="Parent directory to write the public benchmark run into.",
    )
    parser.add_argument("--run-id", help="Optional run identifier. Defaults to a source-based timestamped id.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing run directory with the same id.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every benchmark case passes.")
    return parser.parse_args()


def _emit_error_json(message: str) -> None:
    print(json.dumps({"error": message}, indent=2))


def _default_run_id(source_path: Path) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", source_path.stem.lower()).strip("_") or "benchmark_package"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%SZ").lower()
    return f"{slug}_{timestamp}"


def _validate_run_id(run_id: str) -> str:
    normalized = run_id.strip()
    if not normalized:
        raise ValueError("Run id must not be empty.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", normalized):
        raise ValueError(
            "Run id must contain only letters, numbers, dots, underscores, and hyphens."
        )
    return normalized


def _prepare_run_dir(output_dir: Path, run_id: str, *, force: bool) -> Path:
    output_dir = output_dir.resolve()
    run_dir = (output_dir / run_id).resolve()
    try:
        run_dir.relative_to(output_dir)
    except ValueError as exc:
        raise ValueError(f"Run id escapes the output directory: {run_id}") from exc
    if run_dir.exists():
        has_contents = any(run_dir.iterdir()) if run_dir.is_dir() else True
        if has_contents and not force:
            raise ValueError(
                f"Refusing to overwrite existing public benchmark run: {run_dir}. "
                "Use --force to replace it."
            )
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _git_output(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def _collect_environment_metadata(repo_root: Path) -> dict[str, object]:
    git_commit = _git_output(repo_root, "rev-parse", "HEAD")
    git_branch = _git_output(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    git_status = _git_output(repo_root, "status", "--porcelain")
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "repo_root": str(repo_root.resolve()),
        "invocation": " ".join(shlex.quote(arg) for arg in sys.argv),
        "git_commit": git_commit,
        "git_branch": git_branch,
        "git_dirty": bool(git_status) if git_commit else None,
    }


def main() -> int:
    args = parse_args()
    if bool(args.package_dir) == bool(args.package_archive):
        message = "Specify exactly one of --package-dir or --package-archive."
        if args.json:
            _emit_error_json(message)
        else:
            print(f"Error: {message}", file=sys.stderr)
        return 2

    source_path = (args.package_archive or args.package_dir).resolve()

    try:
        run_id = _validate_run_id(args.run_id or _default_run_id(source_path))
        run_dir = _prepare_run_dir(args.output_dir, run_id, force=args.force)
        repo_root = REPO_ROOT.resolve()
        generation_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%S%fZ").lower()
            + f"_{uuid4().hex[:8]}"
        )
        if args.package_archive:
            report = build_harness_benchmark_report_from_package_archive(args.package_archive, repo_root=repo_root)
            source_type = "package_archive"
            source_sha256 = package_archive_effective_sha256(args.package_archive)
        else:
            report = build_harness_benchmark_report_from_package(args.package_dir, repo_root=repo_root)
            source_type = "package_dir"
            source_sha256 = package_effective_sha256(args.package_dir)

        metadata = {
            "run_id": run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "generation_id": generation_id,
            "source_type": source_type,
            "source_path": str(source_path),
            "source_sha256": source_sha256,
            "suite_id": report["suite_id"],
            "readiness": report["readiness"],
            "overall_score": report["overall_score"],
            "case_count": report["case_count"],
            "environment": _collect_environment_metadata(repo_root),
        }
        writes = write_harness_benchmark_report_outputs_to_dir(report, run_dir, metadata=metadata)
    except ValueError as exc:
        if args.json:
            _emit_error_json(str(exc))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"report": report, "run_metadata": metadata, "writes": writes}, indent=2))
    else:
        print("# Public Benchmark Run")
        print()
        print(f"- run_id: `{run_id}`")
        print(f"- source_type: `{source_type}`")
        print(f"- source_path: `{source_path}`")
        if source_sha256:
            print(f"- source_sha256: `{source_sha256}`")
        print(f"- readiness: `{report['readiness']}`")
        print(f"- overall_score: `{report['overall_score']}`")
        print(f"- case_count: `{report['case_count']}`")
        print("Generated outputs:")
        print(f"- `{writes['report_json']}`")
        print(f"- `{writes['report_md']}`")
        print(f"- `{writes['manifest']}`")
        print(f"- `{writes['run_metadata']}`")

    if args.strict:
        return 0 if report["readiness"] == "ready" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
