from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from overnight_digest import collect_figure_qa_summary, summary_snapshot


def write_run_files(run_dir: Path, summary_text: str | None, events_text: str) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_config.json").write_text(
        json.dumps({"invoked_at": "2026-04-10T05:00:00+00:00"}),
        encoding="utf-8",
    )
    (run_dir / "events.log").write_text(events_text, encoding="utf-8")
    (run_dir / "preflight.txt").write_text("ok\n", encoding="utf-8")
    if summary_text is not None:
        (run_dir / "summary.md").write_text(summary_text, encoding="utf-8")


def test_summary_snapshot_marks_clean_completed_run_healthy(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260410-healthy"
    write_run_files(
        run_dir,
        """# Overnight Soak Validation Summary

- baseline: `passed`

## Failures
- first failure: `none`
- latest failure: `none`
- repeated failure signatures: `none`

## Warnings
- expected warnings:
  - `2x` r-font-fallback-helvetica
- unexpected warnings: `none`

## Artifact Drift
- `none`

## Morning Check Paths
- review page: `/tmp/review/index.html`
""",
        """[2026-04-10T05:10:00+00:00] phase=baseline label=python-tests
cwd=/tmp/workspace
command=pytest tests
returncode=0
--- stdout ---
ok
--- stderr ---
--- end ---
""",
    )

    payload = summary_snapshot(run_dir)

    assert payload["completed"] is True
    assert payload["health"] == "healthy"
    assert payload["unexpected_warning_lines"] == []
    assert payload["expected_warning_counts"]["r-font-fallback-helvetica"] == 2


def test_summary_snapshot_marks_in_progress_run_running(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260410-running"
    write_run_files(
        run_dir,
        None,
        """[2026-04-10T05:10:00+00:00] phase=light label=r-tests
cwd=/tmp/workspace
command=Rscript tests/figures/r/testthat.R
returncode=0
--- stdout ---
ok
--- stderr ---
--- end ---
""",
    )

    payload = summary_snapshot(run_dir)

    assert payload["completed"] is False
    assert payload["health"] == "running"
    assert "run still in progress" in payload["reasons"]


def test_collect_figure_qa_summary_reports_fallback_and_clipping(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    manifest_dir = workspace / "figures/output/python"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    png_path = workspace / "figures/output/python/figure_test.png"
    png_path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGBA", (120, 80), (255, 255, 255, 255))
    for y_pos in range(10, 70):
        for x_pos in range(0, 15):
            image.putpixel((x_pos, y_pos), (0, 0, 0, 255))
    image.save(png_path)

    manifest = {
        "figure_id": "figure_test",
        "renderer": "python",
        "font_resolution": {
            "family": "DejaVu Sans",
            "path": "/System/Library/Fonts/Helvetica.ttc",
        },
        "outputs": {
            "png": "figures/output/python/figure_test.png",
        },
    }
    (manifest_dir / "figure_test.manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    qa = collect_figure_qa_summary(workspace)

    assert qa is not None
    assert qa["manifest_count"] == 1
    assert qa["font_status_counts"]["fallback"] == 1
    assert qa["clipping_risk_counts"]["high"] >= 1 or qa["clipping_risk_counts"]["moderate"] >= 1
