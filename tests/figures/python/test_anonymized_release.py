from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import anonymized_release


def test_build_anonymized_release_for_template_is_provisional() -> None:
    report = anonymized_release.build_anonymized_release("rnaseq_real_project_template", REPO_ROOT)
    assert report["readiness"] == "provisional"
    assert report["anonymization_required"] is True
    assert any("msigdb_license_confirmed" in warning for warning in report["warnings"])


def test_write_anonymized_release_outputs_redacts_frontmatter() -> None:
    writes = anonymized_release.write_anonymized_release_outputs("rnaseq_real_project_template", REPO_ROOT)
    index_path = REPO_ROOT / writes["anonymized_index"]
    text = index_path.read_text(encoding="utf-8")
    _, remainder = text.split("---\n", 1)
    frontmatter, _, _ = remainder.partition("\n---\n")
    payload = yaml.safe_load(frontmatter)
    assert payload["authors"][0]["name"] == "Anonymous Authors"
    assert payload["affiliations"][0]["institution"] == "Withheld for blind review"


def test_redacted_metadata_contains_anonymous_creators() -> None:
    writes = anonymized_release.write_anonymized_release_outputs("rnaseq_real_project_template", REPO_ROOT)
    redacted_metadata = REPO_ROOT / writes["redacted_metadata"]
    payload = json.loads(redacted_metadata.read_text(encoding="utf-8"))
    assert payload["redacted_creators"] == ["Anonymous Authors"]


def test_cli_check_anonymized_release_json() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_anonymized_release.py",
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
