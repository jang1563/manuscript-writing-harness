from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import anonymized_release
import project_handoff
import project_release
import release_policy
import repo_maturity
import scaffold_msigdb_profile


def test_build_repo_maturity_demo_is_ready_for_current_repo() -> None:
    report = repo_maturity.build_repo_maturity_report("demo", repo_root=REPO_ROOT)
    assert report["readiness"] == "ready"
    assert report["profile"] == "demo"
    assert report["evidence"]["external_validation"]["steps"]["python_suite"]["status"] == "not_run"


def test_build_repo_maturity_submission_framework_is_ready_for_current_repo() -> None:
    report = repo_maturity.build_repo_maturity_report("submission-framework", repo_root=REPO_ROOT)
    assert report["readiness"] == "ready"
    gates = {item["gate"] for item in report["deferred_submission_blockers"]}
    assert gates == {
        "manuscript_scope_gate",
        "bibliography_scope_gate",
        "submission_gate",
    }
    assert any("project release `rnaseq_real_project_template` remains provisional" in warning for warning in report["warnings"])
    assert any("project handoff `rnaseq_real_project_template` remains provisional" in warning for warning in report["warnings"])


def test_build_repo_maturity_submission_ready_is_blocked_for_current_repo() -> None:
    report = repo_maturity.build_repo_maturity_report(
        "submission-ready",
        repo_root=REPO_ROOT,
        selected_venues=["neurips"],
    )
    assert report["readiness"] == "blocked"
    assert report["deferred_submission_blockers"] == []
    assert any("manuscript scope must be `real`" in issue for issue in report["blocking_issues"])
    assert any("bibliography manuscript scope must be `confirmed`" in issue for issue in report["blocking_issues"])
    assert any("venue verification must be `current`" in issue for issue in report["blocking_issues"])


def test_blocked_project_release_promotes_repo_maturity_to_blocked() -> None:
    with patch.object(
        repo_maturity,
        "build_pre_submission_audit",
        return_value={
            "audit_id": "pre_submission_audit_v1",
            "readiness": "ready",
            "venue_scope": {"venue_ids": ["neurips"]},
            "manuscript_scope_gate": {
                "status": "blocked",
                "required_scope_status": "real",
                "current_scope_status": "exemplar",
                "issues": [],
            },
            "bibliography_scope_gate": {
                "status": "blocked",
                "required_manuscript_scope_status": "confirmed",
                "current_manuscript_scope_status": "unconfirmed",
                "note": None,
            },
            "submission_gate": {
                "status": "blocked",
                "required_verification_status": "current",
                "failed_count": 1,
                "failed_venues": [{"venue": "neurips", "display_name": "NeurIPS"}],
            },
            "package_paths": [],
        },
    ), patch.object(
        repo_maturity,
        "build_release_bundle",
        return_value={"profile_id": "integrated_demo_release", "readiness": "ready", "package_paths": []},
    ), patch.object(
        repo_maturity,
        "build_project_release",
        return_value={"project_id": "demo_project", "readiness": "blocked", "package_paths": []},
    ), patch.object(
        repo_maturity,
        "build_project_handoff",
        return_value={"project_id": "demo_project", "readiness": "ready", "package_paths": []},
    ), patch.object(
        repo_maturity,
        "build_harness_benchmark_matrix_report",
        return_value={"matrix_id": "harness_benchmark_matrix", "readiness": "ready", "overall_score": 100.0, "package_paths": []},
    ), patch.object(
        repo_maturity,
        "build_reference_report",
        return_value={"readiness": "ready", "bibliography_scope_gate": {"status": "blocked"}, "package_paths": []},
    ), patch.object(
        repo_maturity,
        "build_manuscript_scope_status",
        return_value={
            "status": "provisional",
            "scope_status": "exemplar",
            "confirmed_on": None,
            "note": "demo",
            "issues": [],
            "warnings": [],
            "manifest_path": "manuscript/plans/manuscript_scope.json",
        },
    ):
        report = repo_maturity.build_repo_maturity_report("submission-framework", repo_root=REPO_ROOT)
    assert report["readiness"] == "blocked"
    assert "project release `demo_project` is blocked" in report["blocking_issues"]


def test_write_repo_maturity_outputs_use_provided_report(tmp_path: Path, monkeypatch) -> None:
    reports_dir = tmp_path / "reports"
    manifests_dir = tmp_path / "manifests"
    monkeypatch.setattr(repo_maturity, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(repo_maturity, "MANIFESTS_DIR", manifests_dir)

    report = repo_maturity.build_repo_maturity_report("demo", repo_root=REPO_ROOT)
    writes = repo_maturity.write_repo_maturity_outputs("demo", repo_root=REPO_ROOT, report=report)
    payload = json.loads((reports_dir / "repo_maturity_demo.json").read_text(encoding="utf-8"))

    assert Path(writes["report_json"]) == reports_dir / "repo_maturity_demo.json"
    assert payload == report


def test_cli_check_repo_maturity_reports_not_run_without_acceptance_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity.py",
            "--profile",
            "submission-framework",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["report"]["readiness"] == "ready"
    assert payload["report"]["evidence"]["external_validation"]["steps"]["runtime_support"]["status"] == "not_run"


def test_cli_check_repo_maturity_strict_requires_acceptance_artifact() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity.py",
            "--profile",
            "submission-framework",
            "--json",
            "--strict",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert any("external validation step `runtime_support` is `not_run`" in issue for issue in payload["report"]["strict_requirement_issues"])


def test_cli_check_repo_maturity_rejects_invalid_acceptance_json(tmp_path: Path) -> None:
    acceptance_path = tmp_path / "bad_acceptance.json"
    acceptance_path.write_text("{not valid json", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity.py",
            "--profile",
            "submission-framework",
            "--acceptance-json",
            str(acceptance_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Acceptance artifact is not valid JSON" in payload["error"]


def test_cli_check_repo_maturity_rejects_acceptance_venue_mismatch(tmp_path: Path) -> None:
    acceptance_path = tmp_path / "acceptance.json"
    acceptance_path.write_text(
        json.dumps(
            {
                "acceptance_id": "demo",
                "profile": "submission-framework",
                "venue": "nature",
                "generated_at_utc": "2026-04-21T00:00:00+00:00",
                "steps": {
                    step_id: {
                        "status": "ready",
                        "command": ["python3", "fake.py"],
                        "exit_code": 0,
                        "stdout_path": "stdout",
                        "stderr_path": "stderr",
                    }
                    for step_id in repo_maturity.ACCEPTANCE_STEP_IDS
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_repo_maturity.py",
            "--profile",
            "submission-framework",
            "--venue",
            "neurips",
            "--acceptance-json",
            str(acceptance_path),
            "--json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert "Acceptance artifact venue does not match" in payload["error"]


def _copy_seed_file(relative_path: str, destination_root: Path) -> None:
    source = REPO_ROOT / relative_path
    destination = destination_root / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def test_temp_workspace_scaffolded_project_stays_provisional(tmp_path: Path, monkeypatch) -> None:
    for relative_path in (
        "workflows/release/profiles/profiles.yml",
        "pathways/msigdb/catalog.yml",
        "workflows/release/anonymization_check.md",
        "manuscript/myst.yml",
        "manuscript/index.md",
        "manuscript/sections/01_summary.md",
        "manuscript/sections/02_introduction.md",
        "manuscript/sections/03_results.md",
        "manuscript/sections/04_discussion.md",
        "manuscript/sections/05_methods.md",
        "manuscript/sections/06_acknowledgements.md",
        "manuscript/sections/07_funding_and_statements.md",
    ):
        _copy_seed_file(relative_path, tmp_path)

    monkeypatch.setattr(scaffold_msigdb_profile, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(scaffold_msigdb_profile, "STUDIES_ROOT", tmp_path / "pathways" / "studies")
    monkeypatch.setattr(scaffold_msigdb_profile, "MSIGDB_CATALOG_PATH", tmp_path / "pathways" / "msigdb" / "catalog.yml")
    monkeypatch.setattr(project_release, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(project_release, "RELEASE_ROOT", tmp_path / "workflows" / "release")
    monkeypatch.setattr(project_release, "PROJECTS_DIR", tmp_path / "workflows" / "release" / "projects")
    monkeypatch.setattr(project_release, "PROFILE_PATH", tmp_path / "workflows" / "release" / "profiles" / "profiles.yml")
    monkeypatch.setattr(project_release, "POLICY_DIR", tmp_path / "workflows" / "release" / "policies")
    monkeypatch.setattr(anonymized_release, "MANUSCRIPT_ROOT", tmp_path / "manuscript")
    monkeypatch.setattr(anonymized_release, "ANONYMIZATION_STUB", tmp_path / "workflows" / "release" / "anonymization_check.md")

    with patch.object(
        project_release,
        "build_fgsea_study_dossier",
        return_value={
            "readiness": "provisional",
            "warnings": ["rank preparation is ready; add the licensed MSigDB GMT to move this profile to ready"],
            "blocking_issues": [],
            "active_profile": {"is_active_source": False, "figure_05_sync": {"status": "inactive"}},
            "fgsea": {"result_count": 0, "figure_export_count": 0},
            "config": "pathways/studies/temp_project/configs/fgsea.yml",
        },
    ), patch.object(
        project_release,
        "load_release_profile",
        return_value={
            "profile_id": "temp_project_release",
            "release_metadata": {
                "title": "Temp Project",
                "description": "Placeholder release description",
                "date_released": "2026-04-21",
                "creators": [{"name": "Add Lead Author", "affiliation": "Add Institution"}],
            },
        },
    ):
        scaffold = project_release.scaffold_project_release(
            "temp_project",
            title="Temp Project",
            species="human",
            collection="H",
            overwrite=False,
        )
        assert scaffold["project_id"] == "temp_project"

        project_release.write_project_release_outputs("temp_project", repo_root=tmp_path)
        release_policy.write_release_policy_outputs("temp_project", repo_root=tmp_path)
        anonymized_release.write_anonymized_release_outputs("temp_project", repo_root=tmp_path)
        project_handoff.write_project_handoff_outputs("temp_project", repo_root=tmp_path)

        project_report = json.loads(
            (tmp_path / "workflows" / "release" / "projects" / "temp_project" / "project_readiness.json").read_text(
                encoding="utf-8"
            )
        )
        handoff_report = json.loads(
            (tmp_path / "workflows" / "release" / "projects" / "temp_project" / "handoff.json").read_text(
                encoding="utf-8"
            )
        )

    assert project_report["readiness"] == "provisional"
    assert handoff_report["readiness"] == "provisional"
    assert handoff_report["project_readiness"]["status"] == "provisional"
    assert handoff_report["policy_readiness"]["status"] == "provisional"
    assert handoff_report["anonymized_preview"]["status"] == "provisional"
