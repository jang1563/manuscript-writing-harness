from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from scripts.figures_common import resolve_specs


pytest.importorskip("pytest_mpl")


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_DIR = Path(__file__).with_name("baseline")


def _load_create_figure(figure_id: str):
    spec = resolve_specs([figure_id])[0]
    module_path = REPO_ROOT / f"figures/src/python/classes/{spec['class_id']}.py"
    module_spec = importlib.util.spec_from_file_location(f"test_{spec['class_id']}", module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Unable to load module for {figure_id}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return spec, module.create_figure


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_01_example_python.png",
)
def test_figure_01_example_python():
    spec, create_figure = _load_create_figure("figure_01_example")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_02_volcano_pathway_python.png",
)
def test_figure_02_volcano_pathway_python():
    spec, create_figure = _load_create_figure("figure_02_volcano_pathway")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_03_ma_plot_python.png",
)
def test_figure_03_ma_plot_python():
    spec, create_figure = _load_create_figure("figure_03_ma_plot")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_04_sample_pca_python.png",
)
def test_figure_04_sample_pca_python():
    spec, create_figure = _load_create_figure("figure_04_sample_pca")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_05_pathway_enrichment_dot_python.png",
)
def test_figure_05_pathway_enrichment_dot_python():
    spec, create_figure = _load_create_figure("figure_05_pathway_enrichment_dot")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_06_roc_pr_compound_python.png",
)
def test_figure_06_roc_pr_compound_python():
    spec, create_figure = _load_create_figure("figure_06_roc_pr_compound")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_07_calibration_reliability_python.png",
)
def test_figure_07_calibration_reliability_python():
    spec, create_figure = _load_create_figure("figure_07_calibration_reliability")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_08_training_dynamics_python.png",
)
def test_figure_08_training_dynamics_python():
    spec, create_figure = _load_create_figure("figure_08_training_dynamics")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_09_confusion_matrix_normalized_python.png",
)
def test_figure_09_confusion_matrix_normalized_python():
    spec, create_figure = _load_create_figure("figure_09_confusion_matrix_normalized")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_10_feature_importance_summary_python.png",
)
def test_figure_10_feature_importance_summary_python():
    spec, create_figure = _load_create_figure("figure_10_feature_importance_summary")
    return create_figure(REPO_ROOT / spec["_spec_path"])


@pytest.mark.mpl_image_compare(
    baseline_dir=str(BASELINE_DIR),
    filename="test_figure_11_ablation_summary_python.png",
)
def test_figure_11_ablation_summary_python():
    spec, create_figure = _load_create_figure("figure_11_ablation_summary")
    return create_figure(REPO_ROOT / spec["_spec_path"])
