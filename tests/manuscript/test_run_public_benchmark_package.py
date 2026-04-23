from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_benchmark


SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_demo_v1"
HELDOUT_SOURCE_PACKAGE_DIR = REPO_ROOT / "benchmarks" / "packages" / "paperwritingbench_style_source_heldout_v1"


def _write_package_archive(source_dir: Path, archive_path: Path, *, root_prefix: str | None = None) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w") as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            relative_path = path.relative_to(source_dir)
            arcname = (Path(root_prefix) / relative_path) if root_prefix else relative_path
            archive.write(path, arcname.as_posix())


def test_run_public_benchmark_package_writes_package_dir_outputs(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    run_dir = tmp_path / "heldout_dir_run"
    assert payload["report"]["suite_id"] == "paperwritingbench_style_heldout_v1"
    assert payload["run_metadata"]["source_type"] == "package_dir"
    assert payload["run_metadata"]["source_sha256"]
    assert payload["run_metadata"]["generation_id"]
    environment = payload["run_metadata"]["environment"]
    assert environment["python_version"]
    assert environment["python_implementation"]
    assert environment["python_executable"]
    assert environment["platform"]
    assert environment["repo_root"] == str(REPO_ROOT.resolve())
    assert environment["invocation"]
    assert payload["report"]["repo_root"] == "."
    assert (run_dir / "report.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "run_metadata.json").exists()


def test_run_public_benchmark_package_writes_archive_outputs(tmp_path) -> None:
    archive_path = tmp_path / "paperwritingbench_style_source_demo_v1.zip"
    _write_package_archive(
        SOURCE_PACKAGE_DIR,
        archive_path,
        root_prefix=SOURCE_PACKAGE_DIR.name,
    )
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-archive",
            str(archive_path),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "archive_run",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    run_dir = tmp_path / "archive_run"
    assert payload["report"]["suite_id"] == "paperwritingbench_style_demo_v1"
    assert payload["run_metadata"]["source_type"] == "package_archive"
    assert payload["run_metadata"]["source_sha256"]
    assert payload["run_metadata"]["generation_id"]
    assert payload["run_metadata"]["environment"]["python_version"]
    assert payload["report"]["suite_path"].endswith(".zip")
    assert (run_dir / "run_metadata.json").exists()


def test_run_public_benchmark_package_uses_repo_root_when_invoked_outside_repo(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_public_benchmark_package.py"),
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "outside_repo_cwd_run",
            "--json",
            "--strict",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["run_metadata"]["environment"]["repo_root"] == str(REPO_ROOT.resolve())
    assert payload["report"]["repo_root"] == "."


def test_run_public_benchmark_package_package_dir_fingerprint_ignores_unreferenced_files(tmp_path) -> None:
    clean_package_dir = tmp_path / "clean_package"
    noisy_package_dir = tmp_path / "noisy_package"
    shutil.copytree(HELDOUT_SOURCE_PACKAGE_DIR, clean_package_dir)
    shutil.copytree(HELDOUT_SOURCE_PACKAGE_DIR, noisy_package_dir)
    (noisy_package_dir / ".DS_Store").write_text("finder noise", encoding="utf-8")

    clean_completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(clean_package_dir),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "clean_run",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    noisy_completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(noisy_package_dir),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "noisy_run",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    clean_payload = json.loads(clean_completed.stdout)
    noisy_payload = json.loads(noisy_completed.stdout)
    assert clean_payload["report"]["overall_score"] == noisy_payload["report"]["overall_score"] == 100.0
    assert clean_payload["run_metadata"]["source_sha256"] == noisy_payload["run_metadata"]["source_sha256"]
    assert (
        harness_benchmark.directory_sha256(clean_package_dir)
        != harness_benchmark.directory_sha256(noisy_package_dir)
    )


def test_run_public_benchmark_package_refuses_overwrite_without_force(tmp_path) -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "heldout_dir_run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Refusing to overwrite existing public benchmark run" in payload["error"]


def test_run_public_benchmark_package_rejects_escaping_run_id(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--output-dir",
            str(tmp_path),
            "--run-id",
            "../escaped_run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Run id must contain only letters" in payload["error"]


def test_run_public_benchmark_package_rejects_multiple_source_flags(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_public_benchmark_package.py",
            "--package-dir",
            str(HELDOUT_SOURCE_PACKAGE_DIR),
            "--package-archive",
            str(tmp_path / "fake.zip"),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "exactly one" in payload["error"]
