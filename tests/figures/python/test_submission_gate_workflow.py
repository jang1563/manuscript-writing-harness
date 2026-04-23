from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_submission_gate_workflow_venue_choices_match_tracked_configs() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "submission-gate.yml"
    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    workflow_text = workflow_path.read_text(encoding="utf-8")

    workflow_on = payload.get("on", payload.get(True))
    dispatch_input = workflow_on["workflow_dispatch"]["inputs"]["venue"]
    assert dispatch_input["type"] == "choice"

    expected = sorted(path.stem for path in (REPO_ROOT / "workflows" / "venue_configs").glob("*.yml"))
    actual = list(dispatch_input["options"])

    assert actual == expected
    assert "scripts/run_submission_gate.py" in workflow_text
