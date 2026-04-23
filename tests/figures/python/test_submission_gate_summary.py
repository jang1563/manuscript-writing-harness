from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import submission_gate_summary


def test_render_markdown_includes_gate_details() -> None:
    rendered = submission_gate_summary.render_markdown(
        venue_input="neurips",
        venue_status="1",
        audit_status="1",
        venue_payload={
            "submission_gate": {
                "status": "blocked",
                "failed_count": 1,
                "failed_venues": [
                    {
                        "display_name": "NeurIPS",
                        "venue": "neurips",
                        "verification_status": "needs_submission_confirmation",
                    }
                ],
            }
        },
        audit_payload={
            "report": {
                "audit_id": "pre_submission_audit_neurips_v1",
                "readiness": "ready",
                "bibliography_scope_gate": {
                    "status": "blocked",
                    "current_manuscript_scope_status": "unconfirmed",
                },
                "submission_gate": {
                    "status": "blocked",
                    "failed_count": 1,
                    "failed_venues": [
                        {
                            "display_name": "NeurIPS",
                            "venue": "neurips",
                            "verification_status": "needs_submission_confirmation",
                        }
                    ],
                },
            }
        },
    )

    assert "# Submission Gate Summary" in rendered
    assert "- venue_input: `neurips`" in rendered
    assert "- status: `blocked`" in rendered
    assert "- bibliography_scope_gate: `blocked`" in rendered
    assert "- `NeurIPS` (`neurips`): `needs_submission_confirmation`" in rendered
    assert "- audit_id: `pre_submission_audit_neurips_v1`" in rendered


def test_render_markdown_includes_payload_errors_and_stderr() -> None:
    rendered = submission_gate_summary.render_markdown(
        venue_input="not_a_real_venue",
        venue_status="2",
        audit_status="2",
        venue_payload=None,
        audit_payload={"error": "Unknown venue ids for pre-submission audit: not_a_real_venue"},
        venue_payload_error="submission-gate-venue.json was empty",
        audit_payload_error=None,
        venue_stderr="traceback one",
        audit_stderr="traceback two",
    )

    assert "- payload_error: `submission-gate-venue.json was empty`" in rendered
    assert "- error: `Unknown venue ids for pre-submission audit: not_a_real_venue`" in rendered
    assert "- stderr: `traceback one`" in rendered
    assert "- stderr: `traceback two`" in rendered


def test_load_json_payload_reports_invalid_json(tmp_path: Path) -> None:
    payload_path = tmp_path / "broken.json"
    payload_path.write_text("{not valid json", encoding="utf-8")

    payload, error = submission_gate_summary.load_json_payload(payload_path)

    assert payload is None
    assert error is not None
    assert "contained invalid JSON" in error


def test_cli_writes_summary_file(tmp_path: Path) -> None:
    venue_json = tmp_path / "submission-gate-venue.json"
    audit_json = tmp_path / "submission-gate-audit.json"
    venue_exit = tmp_path / "submission-gate-venue.exit"
    audit_exit = tmp_path / "submission-gate-audit.exit"
    output = tmp_path / "submission-gate-summary.md"
    step_summary = tmp_path / "github-step-summary.md"

    venue_json.write_text(
        json.dumps({"submission_gate": {"status": "ready", "failed_count": 0, "failed_venues": []}}),
        encoding="utf-8",
    )
    audit_json.write_text(
        json.dumps(
            {
                "report": {
                    "audit_id": "pre_submission_audit_neurips_v1",
                    "readiness": "ready",
                    "submission_gate": {"status": "ready", "failed_count": 0, "failed_venues": []},
                }
            }
        ),
        encoding="utf-8",
    )
    venue_exit.write_text("0\n", encoding="utf-8")
    audit_exit.write_text("0\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/submission_gate_summary.py",
            "--venue",
            "neurips",
            "--venue-json",
            str(venue_json),
            "--audit-json",
            str(audit_json),
            "--venue-exit",
            str(venue_exit),
            "--audit-exit",
            str(audit_exit),
            "--output",
            str(output),
            "--github-step-summary",
            str(step_summary),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "# Submission Gate Summary" in completed.stdout
    assert output.exists()
    assert step_summary.exists()
    assert "- venue_input: `neurips`" in output.read_text(encoding="utf-8")
