from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from scripts.figures_common import load_class_registry, load_figure_recipes, load_figure_specs


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_class_registry_contains_wave1_classes() -> None:
    registry = load_class_registry()
    assert {
        "timecourse_endpoint",
        "volcano_pathway_compound",
        "ma_plot",
        "sample_pca",
        "pathway_enrichment_dot",
        "roc_pr_compound",
        "calibration_reliability",
        "training_dynamics",
        "confusion_matrix_normalized",
        "feature_importance_summary",
        "ablation_summary",
    }.issubset(registry)


def test_specs_align_with_registry() -> None:
    specs = load_figure_specs()
    figure_ids = {spec["figure_id"] for spec in specs}
    assert {
        "figure_01_example",
        "figure_02_volcano_pathway",
        "figure_03_ma_plot",
        "figure_04_sample_pca",
        "figure_05_pathway_enrichment_dot",
        "figure_06_roc_pr_compound",
        "figure_07_calibration_reliability",
        "figure_08_training_dynamics",
        "figure_09_confusion_matrix_normalized",
        "figure_10_feature_importance_summary",
        "figure_11_ablation_summary",
    }.issubset(figure_ids)


def test_recipe_registry_contains_core_bundles() -> None:
    recipes = load_figure_recipes()
    assert {"bulk_omics_deg_story", "ai_ml_evaluation_story"}.issubset(recipes)


def test_cli_lists_classes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "list-classes"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "timecourse_endpoint" in completed.stdout
    assert "pathway_enrichment_dot" in completed.stdout
    assert "roc_pr_compound" in completed.stdout
    assert "confusion_matrix_normalized" in completed.stdout
    assert "feature_importance_summary" in completed.stdout
    assert "ablation_summary" in completed.stdout
    assert "instances:" in completed.stdout


def test_cli_lists_instances() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "list-instances"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "figure_01_example" in completed.stdout
    assert "figure_11_ablation_summary" in completed.stdout
    assert "manuscript: mapped" in completed.stdout


def test_cli_lists_roadmap() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "list-roadmap"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "ai_ml_professional" in completed.stdout
    assert "roc_pr_compound" in completed.stdout
    assert "confusion_matrix_normalized" in completed.stdout
    assert "feature_importance_summary" in completed.stdout
    assert "ablation_summary" in completed.stdout


def test_cli_lists_recipes() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "list-recipes"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "bulk_omics_deg_story" in completed.stdout
    assert "ai_ml_evaluation_story" in completed.stdout


def test_cli_shows_recipe_detail() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/figures_cli.py",
            "show-recipe",
            "--recipe",
            "ai_ml_evaluation_story",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "recommended_sequence:" in completed.stdout
    assert "discrimination: roc_pr_compound" in completed.stdout


def test_cli_renders_catalog() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "catalog"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "# Figure Library Catalog" in completed.stdout
    assert "## roc_pr_compound" in completed.stdout
    assert "`figure_06_roc_pr_compound`" in completed.stdout


def test_cli_can_write_catalog(tmp_path: Path) -> None:
    relative_target = "figures/guides/tmp_catalog_test.md"
    target = REPO_ROOT / relative_target
    try:
        completed = subprocess.run(
            [sys.executable, "scripts/figures_cli.py", "catalog", "--write", relative_target],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert f"Wrote {relative_target}" in completed.stdout
        assert target.exists()
        assert "# Figure Library Catalog" in target.read_text(encoding="utf-8")
    finally:
        if target.exists():
            target.unlink()


def test_cli_can_render_cookbook() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "cookbook"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "# Figure Recipe Cookbook" in completed.stdout
    assert "## ai_ml_evaluation_story" in completed.stdout


def test_recipe_scaffold_dry_run_reports_bundle_targets_without_writing() -> None:
    prefix = "recipe_preview_bundle"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/figures_cli.py",
            "scaffold-recipe",
            "--recipe",
            "bulk_omics_deg_story",
            "--prefix",
            prefix,
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["recipe_id"] == "bulk_omics_deg_story"
    assert payload["figure_count"] == 4
    first_figure = payload["figures"][0]
    assert first_figure["figure_id"].startswith(f"{prefix}_")
    assert any(path.endswith(".yml") for path in first_figure["create"])
    assert not (REPO_ROOT / f"figures/specs/{prefix}_sample_structure.yml").exists()


def test_scaffold_dry_run_reports_targets_without_writing() -> None:
    figure_id = "figure_99_test_scaffold_preview"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/figures_cli.py",
            "scaffold",
            "--class",
            "ma_plot",
            "--figure-id",
            figure_id,
            "--dry-run",
            "--json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["figure_id"] == figure_id
    assert payload["create_count"] >= 5
    assert f"figures/specs/{figure_id}.yml" in payload["create"]
    assert not (REPO_ROOT / f"figures/specs/{figure_id}.yml").exists()


def test_validate_cli_syncs_manuscript_preview_assets() -> None:
    figure_id = "figure_11_ablation_summary"
    preview_assets = [
        REPO_ROOT / "manuscript/assets/generated" / f"{figure_id}.png",
        REPO_ROOT / "manuscript/sections/assets/generated" / f"{figure_id}.png",
    ]

    subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "build", "--figure", figure_id],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for path in preview_assets:
        if path.exists():
            path.unlink()

    subprocess.run(
        [sys.executable, "scripts/figures_cli.py", "validate", "--figure", figure_id],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    for path in preview_assets:
        assert path.exists()


def test_dual_renderer_manifests_share_semantic_source_data_hashes() -> None:
    for spec in load_figure_specs():
        if spec["parity_status"] != "dual":
            continue
        python_manifest = json.loads(
            (REPO_ROOT / spec["renderers"]["python"]["output_dir"] / f"{spec['figure_id']}.manifest.json").read_text(
                encoding="utf-8"
            )
        )
        r_manifest = json.loads(
            (REPO_ROOT / spec["renderers"]["r"]["output_dir"] / f"{spec['figure_id']}.manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            python_manifest["checksums_semantic"]["source_data"]
            == r_manifest["checksums_semantic"]["source_data"]
        )
