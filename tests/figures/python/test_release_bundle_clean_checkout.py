from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import release_bundle  # noqa: E402


def test_bundle_component_builds_missing_bundle_outputs(tmp_path, monkeypatch) -> None:
    summary_path = tmp_path / "figures/output/bundles/bundle_demo/summary.json"
    review_path = tmp_path / "figures/output/review/bundles/bundle_demo/index.html"
    bundle = {
        "bundle_id": "bundle_demo",
        "recipe_id": "demo_recipe",
        "acceptance_tier": "acceptance",
        "_bundle_path": "figures/bundles/bundle_demo/bundle.yml",
        "figures": [{"figure_id": "figure_demo"}],
        "bundle_outputs": {
            "summary_json": "figures/output/bundles/bundle_demo/summary.json",
            "review_page": "figures/output/review/bundles/bundle_demo/index.html",
        },
    }

    def fake_load_bundle_manifest(bundle_id: str, repo_root: Path) -> dict:
        assert bundle_id == "bundle_demo"
        assert repo_root == tmp_path
        return bundle

    def fake_build_bundle_review_page(bundle_id: str, repo_root: Path) -> Path:
        assert bundle_id == "bundle_demo"
        assert repo_root == tmp_path
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(
                {
                    "member_count": 1,
                    "figure_ids": ["figure_demo"],
                    "renderers_present": ["python", "r"],
                    "manuscript_wiring_status": "applied",
                    "clipping_risk_counts": {"low": 2},
                    "font_status_counts": {"preferred": 2},
                }
            ),
            encoding="utf-8",
        )
        review_path.write_text("<html>bundle review</html>", encoding="utf-8")
        return review_path

    monkeypatch.setattr(release_bundle, "load_bundle_manifest", fake_load_bundle_manifest)
    monkeypatch.setattr(release_bundle, "build_bundle_review_page", fake_build_bundle_review_page)

    component = release_bundle._bundle_component("bundle_demo", tmp_path)

    assert component["bundle_id"] == "bundle_demo"
    assert component["blocking_issues"] == []
    assert component["summary_json"] == "figures/output/bundles/bundle_demo/summary.json"
