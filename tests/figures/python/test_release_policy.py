from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import release_policy


def test_build_release_policy_for_template_is_provisional() -> None:
    report = release_policy.build_release_policy("rnaseq_real_project_template", REPO_ROOT)
    assert report["readiness"] == "provisional"
    assert report["anonymization_required"] is True
    assert any("msigdb_license_confirmed" in warning for warning in report["warnings"])
    assert any("deposit_contact" in warning for warning in report["warnings"])


def test_render_release_policy_markdown_mentions_review_model() -> None:
    report = release_policy.build_release_policy("rnaseq_real_project_template", REPO_ROOT)
    markdown = release_policy.render_release_policy_markdown(report)
    assert "# Release Policy Readiness: rnaseq_real_project_template" in markdown
    assert "review_model" in markdown


def test_write_release_policy_outputs_can_be_regenerated() -> None:
    writes = release_policy.write_release_policy_outputs("rnaseq_real_project_template", REPO_ROOT)
    report_json = REPO_ROOT / writes["report_json"]
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["project_id"] == "rnaseq_real_project_template"


def test_cli_check_release_policy_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_release_policy.py",
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
    assert payload["report"]["readiness"] == "provisional"
