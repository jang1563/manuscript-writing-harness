from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import project_release


def test_build_project_release_for_tracked_template_is_provisional() -> None:
    report = project_release.build_project_release("rnaseq_real_project_template", REPO_ROOT)
    assert report["readiness"] == "provisional"
    assert report["release_profile_id"] == "rnaseq_real_project_template_release"
    assert report["study_id"] == "msigdb_hallmark_demo"
    assert any("licensed MSigDB GMT" in warning for warning in report["warnings"])
    assert any("placeholder" in warning for warning in report["warnings"])


def test_render_project_release_markdown_mentions_next_steps() -> None:
    report = project_release.build_project_release("rnaseq_real_project_template", REPO_ROOT)
    markdown = project_release.render_project_release_markdown(report)
    assert "# Project Release Readiness: rnaseq_real_project_template" in markdown
    assert "## Study Status" in markdown
    assert "run_msigdb_profile.py" in markdown


def test_write_project_release_outputs_can_be_regenerated() -> None:
    writes = project_release.write_project_release_outputs("rnaseq_real_project_template", REPO_ROOT)
    report_json = REPO_ROOT / writes["report_json"]
    report_md = REPO_ROOT / writes["report_md"]
    assert report_json.exists()
    assert report_md.exists()
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["project_id"] == "rnaseq_real_project_template"


def test_cli_check_project_release_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_project_release.py",
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
