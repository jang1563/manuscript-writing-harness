from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_handoff


def test_build_project_handoff_for_template_is_provisional() -> None:
    report = project_handoff.build_project_handoff("rnaseq_real_project_template", REPO_ROOT)
    assert report["readiness"] == "provisional"
    assert report["project_readiness"]["status"] == "provisional"
    assert report["policy_readiness"]["status"] == "provisional"
    assert report["anonymized_preview"]["status"] == "provisional"


def test_write_project_handoff_outputs_can_be_regenerated() -> None:
    writes = project_handoff.write_project_handoff_outputs("rnaseq_real_project_template", REPO_ROOT)
    report_json = REPO_ROOT / writes["report_json"]
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["project_id"] == "rnaseq_real_project_template"


def test_cli_check_project_handoff_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_project_handoff.py",
            "--project",
            "rnaseq_real_project_template",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["project_id"] == "rnaseq_real_project_template"


def test_blocked_subreport_promotes_handoff_to_blocked() -> None:
    with patch.object(
        project_handoff,
        "build_project_release",
        return_value={"readiness": "ready", "warnings": [], "package_paths": []},
    ), patch.object(
        project_handoff,
        "build_release_policy",
        return_value={
            "readiness": "blocked",
            "blocking_issues": ["policy missing required approval"],
            "warnings": [],
            "package_paths": [],
        },
    ), patch.object(
        project_handoff,
        "build_anonymized_release",
        return_value={"readiness": "ready", "warnings": [], "package_paths": []},
    ), patch.object(
        project_handoff,
        "_load_project",
        return_value={
            "project_id": "demo_project",
            "title": "Demo Project",
            "release_profile_id": "demo_release",
            "_project_path": "workflows/release/projects/demo_project/project.yml",
        },
    ):
        report = project_handoff.build_project_handoff("demo_project", REPO_ROOT)
    assert report["readiness"] == "blocked"
    assert report["blocking_issues"] == ["policy missing required approval"]
