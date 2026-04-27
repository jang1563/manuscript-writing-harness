from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from real_manuscript_preflight import (  # noqa: E402
    build_real_manuscript_preflight,
    render_real_manuscript_preflight_markdown,
    write_real_manuscript_preflight_outputs,
)


def test_real_manuscript_preflight_blocks_current_exemplar_repo() -> None:
    report = build_real_manuscript_preflight()
    checks = {check["check_id"]: check for check in report["checks"]}

    assert report["readiness"] == "blocked"
    assert checks["manuscript_scope_metadata_valid"]["status"] == "ready"
    assert checks["bibliography_scope_confirmed"]["status"] == "blocked"
    assert checks["venue_verification_current"]["status"] == "blocked"
    assert checks["project_release_ready"]["status"] == "blocked"
    assert checks["project_handoff_ready"]["status"] == "blocked"
    assert checks["active_project_study_source"]["status"] == "blocked"
    assert checks["release_metadata_placeholders_absent"]["status"] == "blocked"


def test_real_manuscript_preflight_markdown_mentions_remediation() -> None:
    markdown = render_real_manuscript_preflight_markdown(build_real_manuscript_preflight())
    assert "# Real Manuscript Preflight" in markdown
    assert "bibliography_scope_confirmed" in markdown
    assert "confirm_bibliography_scope.py" in markdown
    assert "confirm_venue_verification.py" in markdown


def test_write_real_manuscript_preflight_outputs_creates_artifacts() -> None:
    outputs = write_real_manuscript_preflight_outputs()
    assert (REPO_ROOT / outputs["report_json"]).exists()
    assert (REPO_ROOT / outputs["report_md"]).exists()
    assert (REPO_ROOT / outputs["manifest"]).exists()


def test_cli_real_manuscript_preflight_strict_blocks_current_repo() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_real_manuscript_preflight.py",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "blocked"
