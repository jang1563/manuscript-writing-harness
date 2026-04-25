from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_scaffold  # noqa: E402
import check_generated_artifacts  # noqa: E402
import public_artifact_safety  # noqa: E402


PUBLIC_DOC_PATHS = (
    REPO_ROOT / "SECURITY.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CODE_OF_CONDUCT.md",
    REPO_ROOT / "COMMERCIAL-LICENSE.md",
)

LOCAL_ONLY_PATTERNS = (
    "/Users/",
    "Dropbox/Bioinformatics/Claude",
    "/private/var/folders",
    "/var/folders",
    "/home/runner/work",
    "/opt/hostedtoolcache",
    "pytest-of-",
)


def test_figures_readme_uses_repo_safe_links() -> None:
    readme = (REPO_ROOT / "figures" / "README.md").read_text(encoding="utf-8")

    assert "/Users/" not in readme
    assert "Dropbox/Bioinformatics/Claude" not in readme
    assert "[guides/class_catalog.md](guides/class_catalog.md)" in readme
    assert "[guides/cookbook.md](guides/cookbook.md)" in readme


def test_public_security_docs_do_not_expose_personal_contact_details() -> None:
    email_pattern = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")

    for path in PUBLIC_DOC_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "silveray1563@gmail.com" not in text
        assert email_pattern.search(text) is None


def test_repo_maturity_public_artifacts_do_not_embed_local_paths() -> None:
    artifact_roots = (
        REPO_ROOT / "workflows" / "release" / "reports",
        REPO_ROOT / "workflows" / "release" / "manifests",
    )
    artifact_paths = sorted(
        path
        for root in artifact_roots
        if root.exists()
        for path in root.rglob("*")
        if path.is_file() and "repo_maturity_submission-framework" in str(path.relative_to(REPO_ROOT))
    )
    if not artifact_paths:
        pytest.skip("requires generated repo-maturity artifacts")

    for path in artifact_paths:
        text = path.read_text(encoding="utf-8")
        for pattern in LOCAL_ONLY_PATTERNS:
            assert pattern not in text, f"{path.relative_to(REPO_ROOT)} contains {pattern}"


def test_public_artifact_safety_redacts_workspace_and_temp_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    text = (
        f"{repo_root}/scripts/check_repo_maturity.py "
        "/Users/example/work/project "
        "/private/var/folders/aa/bb/T/pytest-of-user/case "
        "/home/runner/work/project/project "
        "/home/runner/work/_temp/setup"
    )

    sanitized = public_artifact_safety.sanitize_public_text(text, repo_root=repo_root)

    assert str(repo_root) not in sanitized
    assert "/Users/" not in sanitized
    assert "/private/var/folders" not in sanitized
    assert "/home/runner/work" not in sanitized
    assert "<local-temp>" in sanitized
    assert "<github-workspace>" in sanitized
    assert "<github-temp>" in sanitized


def test_public_artifact_safety_handles_github_runner_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        public_artifact_safety.Path,
        "home",
        classmethod(lambda cls: Path("/home/runner")),
    )

    sanitized = public_artifact_safety.sanitize_public_text(
        "/home/runner/work/project/project /home/runner/work/_temp/setup",
        repo_root=tmp_path,
    )

    assert "/home/runner/work" not in sanitized
    assert "<github-workspace>" in sanitized
    assert "<github-temp>" in sanitized


def test_figure_manifests_do_not_embed_absolute_font_paths() -> None:
    manifest_paths = sorted((REPO_ROOT / "figures" / "output").glob("*/*.manifest.json"))
    if not manifest_paths:
        pytest.skip("requires generated figure manifests from build_phase2.py")

    for manifest_path in manifest_paths:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        font_resolution = payload.get("font_resolution", {})
        public_path = str(font_resolution.get("path") or "")

        assert public_path
        assert Path(public_path).name == public_path
        assert not Path(public_path).is_absolute()
        assert "/" not in public_path
        assert "/Users/" not in public_path
        assert "\\" not in public_path


def test_scaffold_required_paths_are_tracked_sources() -> None:
    tracked_paths = set(
        subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
    )

    untracked_required_paths = sorted(
        path for path in check_scaffold.required_paths() if path not in tracked_paths
    )

    assert untracked_required_paths == []


def test_pathway_annotation_minimum_tracks_active_export(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = {"figure_id": "figure_05_pathway_enrichment_dot"}

    monkeypatch.setattr(
        check_generated_artifacts,
        "_expected_pathway_provenance",
        lambda _spec: {"status": "ready", "figure_export_count": 3},
    )

    assert check_generated_artifacts._minimum_annotation_count(
        spec,
        {"min_annotation_count": 4},
    ) == 3
