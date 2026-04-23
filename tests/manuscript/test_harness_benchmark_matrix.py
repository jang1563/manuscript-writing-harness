from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_benchmark


def test_list_benchmark_definition_refs_includes_tracked_suites_and_bundles() -> None:
    refs = harness_benchmark.list_benchmark_definition_refs()
    assert refs == [
        {"definition_type": "suite", "definition_id": "paper_writing_bench_like_internal_v1"},
        {"definition_type": "bundle", "definition_id": "generic_author_input_demo_v1"},
        {"definition_type": "bundle", "definition_id": "paperwritingbench_style_demo_v1"},
        {"definition_type": "bundle", "definition_id": "paperwritingbench_style_heldout_v1"},
    ]


def test_build_harness_benchmark_matrix_report_is_ready() -> None:
    report = harness_benchmark.build_harness_benchmark_matrix_report()
    assert report["matrix_id"] == harness_benchmark.MATRIX_REPORT_STEM
    assert report["readiness"] == "ready"
    assert report["benchmark_count"] == 4
    assert report["ready_benchmark_count"] == 4
    assert report["blocked_benchmark_count"] == 0
    assert report["total_case_count"] == 9
    assert report["total_passed_case_count"] == 9
    assert report["total_failed_case_count"] == 0
    assert report["overall_score"] == 100.0
    assert [definition["definition_id"] for definition in report["definitions"]] == [
        "paper_writing_bench_like_internal_v1",
        "generic_author_input_demo_v1",
        "paperwritingbench_style_demo_v1",
        "paperwritingbench_style_heldout_v1",
    ]


def test_write_harness_benchmark_matrix_outputs_can_be_redirected(tmp_path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(harness_benchmark, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(harness_benchmark, "MANIFESTS_DIR", manifests_dir)

    writes = harness_benchmark.write_harness_benchmark_matrix_outputs()
    report_json = reports_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.json"
    report_md = reports_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.md"
    manifest = manifests_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.json"

    assert Path(writes["report_json"]) == report_json
    assert Path(writes["report_md"]) == report_md
    assert Path(writes["manifest"]) == manifest
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["matrix_id"] == harness_benchmark.MATRIX_REPORT_STEM
    assert payload["benchmark_count"] == 4
    assert payload["overall_score"] == 100.0


def test_render_harness_benchmark_matrix_markdown_uses_agent_evaluation_title() -> None:
    report = harness_benchmark.build_harness_benchmark_matrix_report()
    markdown = harness_benchmark.render_harness_benchmark_matrix_markdown(report)
    assert markdown.startswith("# Agent Evaluation Benchmark Matrix")


def test_cli_check_harness_benchmark_matrix_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark_matrix.py",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["matrix_id"] == harness_benchmark.MATRIX_REPORT_STEM
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["benchmark_count"] == 4
    assert payload["report"]["overall_score"] == 100.0


def test_cli_check_harness_benchmark_matrix_bundles_only_json_strict() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark_matrix.py",
            "--bundles-only",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["benchmark_count"] == 3
    assert payload["report"]["include_suites"] is False
    assert payload["report"]["include_bundles"] is True


def test_cli_check_harness_benchmark_matrix_write_can_redirect_outputs(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark_matrix.py",
            "--write",
            "--json",
            "--strict",
            "--reports-dir",
            str(reports_dir),
            "--manifests-dir",
            str(manifests_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert Path(payload["writes"]["report_json"]) == reports_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.json"
    assert Path(payload["writes"]["report_md"]) == reports_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.md"
    assert Path(payload["writes"]["manifest"]) == manifests_dir / f"{harness_benchmark.MATRIX_REPORT_STEM}.json"


def test_cli_check_harness_benchmark_matrix_rejects_conflicting_scope_flags() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_harness_benchmark_matrix.py",
            "--suites-only",
            "--bundles-only",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "at most one" in payload["error"]
