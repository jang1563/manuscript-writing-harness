from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from render_ci_soak_summary import render_markdown


def test_render_markdown_includes_gate_and_paths() -> None:
    result = {
        "run_dir": "/tmp/reports/20260410-healthy",
        "passed": True,
        "health": "healthy",
        "baseline": "passed",
        "completed": True,
        "failures": [],
        "expected_paths": {
            "review": "/tmp/workspace/figures/output/review/index.html",
            "index": "/tmp/workspace/manuscript/_build/site/content/index.json",
            "results": "/tmp/workspace/manuscript/_build/site/content/results.json",
        },
    }
    payload = {
        "status_snapshot": {
            "phase_counts": {"baseline": 4, "full": 2},
            "summary_status": {"MyST artifact mode": "site"},
        },
        "unexpected_warning_lines": [],
        "drift_items": ["- `none`"],
        "figure_qa": {
            "figure_count": 11,
            "font_status_counts": {"preferred": 22},
            "clipping_risk_counts": {"low": 22},
        },
    }

    rendered = render_markdown(result, payload)

    assert "## Soak Acceptance" in rendered
    assert "- passed: `True`" in rendered
    assert "- artifact drift: `none`" in rendered
    assert "/tmp/workspace/figures/output/review/index.html" in rendered
    assert "- font `preferred`: `22`" in rendered
