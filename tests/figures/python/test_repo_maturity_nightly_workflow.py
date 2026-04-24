from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repo_maturity_nightly_workflow_targets_nightly_runner() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "repo-maturity-nightly.yml"
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")

    workflow_on = payload.get("on", payload.get(True))
    assert "schedule" in workflow_on
    assert "workflow_dispatch" in workflow_on
    assert "actions/setup-node@v4" in workflow_text
    assert "scripts/build_phase2.py" in workflow_text
    assert "myst build --html" in workflow_text
    assert "scripts/run_repo_maturity_nightly.py" in workflow_text
    assert "scripts/check_repo_maturity_nightly.py" in workflow_text
    assert "--profile submission-framework" in workflow_text
    assert "repo-maturity-nightly-artifacts" in workflow_text
