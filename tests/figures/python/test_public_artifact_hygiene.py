from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_scaffold  # noqa: E402


def test_figures_readme_uses_repo_safe_links() -> None:
    readme = (REPO_ROOT / "figures" / "README.md").read_text(encoding="utf-8")

    assert "/Users/" not in readme
    assert "Dropbox/Bioinformatics/Claude" not in readme
    assert "[guides/class_catalog.md](guides/class_catalog.md)" in readme
    assert "[guides/cookbook.md](guides/cookbook.md)" in readme


def test_figure_manifests_do_not_embed_absolute_font_paths() -> None:
    manifest_paths = sorted((REPO_ROOT / "figures" / "output").glob("*/*.manifest.json"))
    assert manifest_paths

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
