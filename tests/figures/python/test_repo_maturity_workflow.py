from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repo_maturity_workflow_targets_submission_framework() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "repo-maturity-acceptance.yml"
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")

    workflow_on = payload.get("on", payload.get(True))
    assert "push" in workflow_on
    assert "pull_request" in workflow_on
    assert "scripts/run_repo_maturity_acceptance.py" in workflow_text
    assert "scripts/check_repo_maturity_acceptance.py" in workflow_text
    assert "--profile submission-framework" in workflow_text
