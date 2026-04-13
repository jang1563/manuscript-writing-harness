from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from figures_bundle import apply_bundles_to_repo, load_bundle_manifest, load_bundle_manifests


def test_bundle_registry_contains_exemplar_bundles() -> None:
    manifests = load_bundle_manifests(REPO_ROOT)
    assert {
        "bundle_bulk_omics_deg_exemplar",
        "bundle_ai_ml_evaluation_exemplar",
    }.issubset(manifests)


def test_bulk_bundle_manifest_wraps_existing_bulk_omics_figures() -> None:
    bundle = load_bundle_manifest("bundle_bulk_omics_deg_exemplar", REPO_ROOT)
    assert bundle["recipe_id"] == "bulk_omics_deg_story"
    assert bundle["acceptance_tier"] == "exemplar"
    assert bundle["figure_order"] == [
        "figure_04_sample_pca",
        "figure_03_ma_plot",
        "figure_02_volcano_pathway",
        "figure_05_pathway_enrichment_dot",
    ]


def test_apply_bundles_preview_keeps_standalone_assets_outside_managed_block() -> None:
    preview = apply_bundles_to_repo(
        [
            "bundle_bulk_omics_deg_exemplar",
            "bundle_ai_ml_evaluation_exemplar",
        ],
        repo_root=REPO_ROOT,
        write=False,
    )
    refs = preview["writing_plan"]["display_item_refs"]
    assert refs[0] == "figure_01_example"
    assert refs[-1] == "table_01_main"
    assert refs[1:5] == [
        "figure_04_sample_pca",
        "figure_03_ma_plot",
        "figure_02_volcano_pathway",
        "figure_05_pathway_enrichment_dot",
    ]
    assert refs[5:11] == [
        "figure_06_roc_pr_compound",
        "figure_07_calibration_reliability",
        "figure_08_training_dynamics",
        "figure_09_confusion_matrix_normalized",
        "figure_10_feature_importance_summary",
        "figure_11_ablation_summary",
    ]
    assert "../display_items/_bundles/bundle_bulk_omics_deg_exemplar.md.txt" in preview["results_text"]
    assert "../display_items/_bundles/bundle_ai_ml_evaluation_exemplar.md.txt" in preview["results_text"]


def test_cli_lists_bundles() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "list-bundles"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "bundle_bulk_omics_deg_exemplar" in completed.stdout
    assert "bundle_ai_ml_evaluation_exemplar" in completed.stdout


def test_cli_shows_bundle_detail() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/figures_cli.py",
            "show-bundle",
            "--bundle",
            "bundle_ai_ml_evaluation_exemplar",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "discrimination -> figure_06_roc_pr_compound" in completed.stdout
    assert "design_justification -> figure_11_ablation_summary" in completed.stdout


def test_scaffold_bundle_dry_run_reports_bundle_targets_without_writing() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/figures_cli.py",
            "scaffold-bundle",
            "--recipe",
            "bulk_omics_deg_story",
            "--bundle-id",
            "bundle_preview_test",
            "--prefix",
            "preview_bundle",
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["bundle_id"] == "bundle_preview_test"
    assert payload["figure_count"] == 4
    assert "figures/bundles/bundle_preview_test/bundle.yml" in payload["create"]
    assert "figures/bundles/bundles.yml" in payload["create"]
    assert not (REPO_ROOT / "figures/bundles/bundle_preview_test").exists()
