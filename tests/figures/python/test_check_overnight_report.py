from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_overnight_report import evaluate_payload, parse_digest_status
from overnight_digest import summary_snapshot


def write_run_files(
    run_dir: Path,
    workspace: Path,
    summary_text: str,
    digest_text: str,
    events_text: str,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_config.json").write_text(
        json.dumps(
            {
                "invoked_at": "2026-04-10T05:00:00+00:00",
                "workspace": str(workspace),
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "events.log").write_text(events_text, encoding="utf-8")
    (run_dir / "preflight.txt").write_text("ok\n", encoding="utf-8")
    (run_dir / "summary.md").write_text(summary_text, encoding="utf-8")
    (run_dir / "morning_digest.md").write_text(digest_text, encoding="utf-8")


def create_workspace_outputs(workspace: Path) -> None:
    paths = [
        workspace / "figures/output/review/index.html",
        workspace / "manuscript/_build/site/content/index.json",
        workspace / "manuscript/_build/site/content/results.json",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")


def test_parse_digest_status_reads_health_line(tmp_path: Path) -> None:
    digest = tmp_path / "morning_digest.md"
    digest.write_text("# Overnight Morning Digest\n\n- status: `healthy`\n", encoding="utf-8")

    assert parse_digest_status(digest) == "healthy"


def test_evaluate_payload_accepts_clean_healthy_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260410-healthy"
    workspace = tmp_path / "workspace"
    create_workspace_outputs(workspace)
    write_run_files(
        run_dir,
        workspace,
        """# Overnight Soak Validation Summary

- workspace: `/tmp/workspace`
- baseline: `passed`
- MyST artifact mode: `site`

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
- review page: `/tmp/workspace/figures/output/review/index.html`
- manuscript index artifact: `/tmp/workspace/manuscript/_build/site/content/index.json`
- manuscript results artifact: `/tmp/workspace/manuscript/_build/site/content/results.json`
""",
        "# Overnight Morning Digest\n\n- status: `healthy`\n",
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
    result = evaluate_payload(run_dir, payload)

    assert result["passed"] is True
    assert result["failures"] == []
    assert result["digest_status"] == "healthy"


def test_evaluate_payload_rejects_drift_and_missing_digest(tmp_path: Path) -> None:
    run_dir = tmp_path / "20260410-attention"
    workspace = tmp_path / "workspace"
    create_workspace_outputs(workspace)
    write_run_files(
        run_dir,
        workspace,
        """# Overnight Soak Validation Summary

- workspace: `/tmp/workspace`
- baseline: `passed`
- MyST artifact mode: `site`

## Failures
- first failure: `none`
- latest failure: `none`
- repeated failure signatures: `none`

## Warnings
- expected warnings:
  - `1x` myst-bind-eperm-after-build
- unexpected warnings:
  - `1x` unexpected-warning

## Artifact Drift
- `1x` changed `figures/output/review/index.html`
""",
        "# Overnight Morning Digest\n\n- status: `attention`\n",
        """[2026-04-10T05:10:00+00:00] phase=full label=build-phase2
cwd=/tmp/workspace
command=python3 scripts/build_phase2.py
returncode=0
--- stdout ---
ok
--- stderr ---
--- end ---
""",
    )

    payload = summary_snapshot(run_dir)
    result = evaluate_payload(run_dir, payload)

    assert result["passed"] is False
    assert "unexpected warnings were recorded" in result["failures"]
    assert "artifact drift was recorded" in result["failures"]
