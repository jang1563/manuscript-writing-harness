from __future__ import annotations

from pathlib import Path

from scripts.run_overnight_validation import (
    canonical_bytes_for_path,
    CommandResult,
    CORE_HASH_GLOBS,
    RunState,
    assess_runtime_support,
    detect_myst_hash_mode,
    diff_hashes,
    expected_warning_signature,
    morning_check_paths,
    myst_build_usable_despite_bind_error,
    normalize_warning_signature,
    MYST_HTML_HASH_GLOBS,
    MYST_SITE_FALLBACK_HASH_GLOBS,
    RSYNC_EXCLUDES,
    selected_myst_hash_globs,
    stable_artifact_files,
    summarize,
)


def test_sandbox_excludes_only_root_reports_directory() -> None:
    assert "/reports/" in RSYNC_EXCLUDES
    assert "reports/" not in RSYNC_EXCLUDES


def test_warning_normalization_and_expected_classification() -> None:
    assert normalize_warning_signature("Setting LC_CTYPE failed, using \"C\"") == "r-locale-setting-failed"
    assert normalize_warning_signature("System font `DejaVu Sans` not found. Closest match: `Helvetica`") == "r-font-fallback-helvetica"
    assert normalize_warning_signature("System font `Manuscript DejaVu Sans` not found. Closest match: `DejaVu Sans`") == "r-font-alias-mapped-to-dejavu"
    assert normalize_warning_signature("listen EPERM: operation not permitted 0.0.0.0:3100") == "myst-bind-eperm-after-build"
    assert normalize_warning_signature("package 'jsonlite' was built under R version 4.1.2") == "r-package-built-under-different-version"
    assert expected_warning_signature("r-locale-setting-failed") is True
    assert expected_warning_signature("myst-bind-eperm-after-build") is True
    assert expected_warning_signature("r-package-built-under-different-version") is True
    assert expected_warning_signature("r-font-alias-mapped-to-dejavu") is True


def test_runtime_support_assessment_uses_concrete_python_node_and_advisory_r() -> None:
    checks = assess_runtime_support(
        {
            "system-python": "Python 3.8.8",
            "venv-python": "Python 3.8.8",
            "node": "v20.0.0",
            "rscript": "R scripting front-end version 4.1.1 (2021-08-10)",
        },
        require_supported_runtime=False,
    )
    by_name = {item.name: item for item in checks}
    assert by_name["system-python"].status == "unsupported"
    assert by_name["venv-python"].status == "unsupported"
    assert by_name["node"].status == "supported"
    assert by_name["rscript"].status == "advisory"


def test_stable_artifact_files_exclude_manifest_and_gate_myst_outputs(tmp_path: Path) -> None:
    files_to_create = [
        "figures/output/python/example.png",
        "figures/output/python/example.svg",
        "figures/output/python/example.pdf",
        "figures/output/python/example.manifest.json",
        "figures/source_data/example.csv",
        "tables/output/table_01_main.json",
        "figures/output/review/index.html",
        "manuscript/assets/generated/example.png",
        "manuscript/sections/assets/generated/example.png",
        "manuscript/_build/site/config.json",
        "manuscript/_build/site/content/index.json",
        "manuscript/_build/site/content/results.json",
        "manuscript/_build/site/myst.xref.json",
        "manuscript/_build/site/myst.search.json",
    ]
    for relative in files_to_create:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    core = {str(path.relative_to(tmp_path)) for path in stable_artifact_files(tmp_path, include_myst=False)}
    myst = {str(path.relative_to(tmp_path)) for path in stable_artifact_files(tmp_path, include_myst=True)}

    assert "figures/output/python/example.manifest.json" not in core
    assert "manuscript/_build/site/content/index.json" not in core
    assert "manuscript/_build/site/content/index.json" in myst
    assert "manuscript/_build/site/content/results.json" in myst
    assert CORE_HASH_GLOBS
    assert MYST_HTML_HASH_GLOBS
    assert MYST_SITE_FALLBACK_HASH_GLOBS


def test_diff_hashes_reports_new_missing_and_changed() -> None:
    drift = diff_hashes(
        {
            "a.txt": "old",
            "b.txt": "same",
            "c.txt": "gone",
        },
        {
            "a.txt": "new",
            "b.txt": "same",
            "d.txt": "added",
        },
    )
    assert {"path": "a.txt", "status": "changed"} in drift
    assert {"path": "c.txt", "status": "missing"} in drift
    assert {"path": "d.txt", "status": "new"} in drift


def test_canonical_bytes_for_svg_strip_date_and_generated_ids(tmp_path: Path) -> None:
    svg_a = tmp_path / "a.svg"
    svg_b = tmp_path / "b.svg"
    svg_a.write_text(
        """<svg><metadata><dc:date>2026-01-01T01:02:03</dc:date></metadata><defs><clipPath id="pabc"><path id="C0_0_abc"/></clipPath></defs><use xlink:href="#C0_0_abc" clip-path="url(#pabc)"/></svg>""",
        encoding="utf-8",
    )
    svg_b.write_text(
        """<svg><metadata><dc:date>2026-09-09T09:09:09</dc:date></metadata><defs><clipPath id="pzzz"><path id="C0_0_zzz"/></clipPath></defs><use xlink:href="#C0_0_zzz" clip-path="url(#pzzz)"/></svg>""",
        encoding="utf-8",
    )

    assert canonical_bytes_for_path(svg_a) == canonical_bytes_for_path(svg_b)


def test_canonical_bytes_for_pdf_strip_creation_date(tmp_path: Path) -> None:
    pdf_a = tmp_path / "a.pdf"
    pdf_b = tmp_path / "b.pdf"
    pdf_a.write_bytes(
        b"<< /Creator (Matplotlib) /Producer (Matplotlib pdf backend) /CreationDate (D:20260410094524-04'00') >>"
    )
    pdf_b.write_bytes(
        b"<< /Creator (Matplotlib) /Producer (Matplotlib pdf backend) /CreationDate (D:20260410101524-04'00') >>"
    )

    assert canonical_bytes_for_path(pdf_a) == canonical_bytes_for_path(pdf_b)


def test_canonical_bytes_for_source_csv_ignore_row_order(tmp_path: Path) -> None:
    csv_a = tmp_path / "figures" / "source_data" / "panel.csv"
    csv_b = tmp_path / "figures" / "source_data" / "panel_reordered.csv"
    csv_a.parent.mkdir(parents=True, exist_ok=True)
    csv_a.write_text("gene,value\nB,2\nA,1\n", encoding="utf-8")
    csv_b.write_text("gene,value\nA,1\nB,2\n", encoding="utf-8")

    assert canonical_bytes_for_path(csv_a) == canonical_bytes_for_path(csv_b)


def test_canonical_bytes_for_source_csv_normalize_numeric_formatting(tmp_path: Path) -> None:
    csv_a = tmp_path / "figures" / "source_data" / "panel_numeric_a.csv"
    csv_b = tmp_path / "figures" / "source_data" / "panel_numeric_b.csv"
    csv_a.parent.mkdir(parents=True, exist_ok=True)
    csv_a.write_text("gene,value,padj\nA,1,1e-03\nB,2.000000,0.050000\n", encoding="utf-8")
    csv_b.write_text('gene,value,padj\n"A",1.0,0.001000\nB,2,5.0e-2\n', encoding="utf-8")

    assert canonical_bytes_for_path(csv_a) == canonical_bytes_for_path(csv_b)


def test_canonical_bytes_for_myst_site_json_ignore_mdast_keys_and_hashed_suffixes(
    tmp_path: Path,
) -> None:
    json_a = tmp_path / "manuscript" / "_build" / "site" / "content" / "index.json"
    json_b = tmp_path / "manuscript" / "_build" / "site" / "content" / "results.json"
    json_a.parent.mkdir(parents=True, exist_ok=True)
    json_a.write_text(
        (
            '{"version":3,"sha256":"abc","mdast":{"type":"root","key":"AAA","children":[{"type":"text","key":"BBB","value":"ok"}]},'
            '"frontmatter":{"thumbnail":"/figure_01_example-1d725fb961239a1bb3ac38a5a32c0ac8.png",'
            '"exports":[{"url":"/index-381b5567d908bd0d6d7493da637c1dcd.md"}]}}'
        ),
        encoding="utf-8",
    )
    json_b.write_text(
        (
            '{"version":3,"sha256":"xyz","mdast":{"type":"root","key":"CCC","children":[{"type":"text","key":"DDD","value":"ok"}]},'
            '"frontmatter":{"thumbnail":"/figure_01_example-d9735c6827d55b51feecf843184387e6.png",'
            '"exports":[{"url":"/index-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md"}]}}'
        ),
        encoding="utf-8",
    )

    assert canonical_bytes_for_path(json_a) == canonical_bytes_for_path(json_b)


def test_myst_build_can_be_treated_as_usable_when_html_exists(tmp_path: Path) -> None:
    for relative in MYST_SITE_FALLBACK_HASH_GLOBS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    result = CommandResult(
        label="myst-build",
        phase="baseline",
        command=["myst", "build", "--html"],
        cwd=tmp_path,
        returncode=1,
        stdout="built pages",
        stderr="listen EPERM: operation not permitted 0.0.0.0:3100",
        started_at="start",
        ended_at="end",
        duration_seconds=1.0,
    )

    assert myst_build_usable_despite_bind_error(result, tmp_path) is True


def test_detect_myst_hash_mode_and_morning_check_paths_fall_back_to_site_content(
    tmp_path: Path,
) -> None:
    for relative in MYST_SITE_FALLBACK_HASH_GLOBS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")
    review = tmp_path / "figures/output/review/index.html"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("review", encoding="utf-8")

    assert detect_myst_hash_mode(tmp_path) == "site"
    assert selected_myst_hash_globs(tmp_path) == MYST_SITE_FALLBACK_HASH_GLOBS

    checks = morning_check_paths(tmp_path)
    assert checks["mode"] == "site"
    assert checks["index"].endswith("manuscript/_build/site/content/index.json")
    assert checks["results"].endswith("manuscript/_build/site/content/results.json")


def test_detect_myst_hash_mode_prefers_stable_site_content_when_html_exists(
    tmp_path: Path,
) -> None:
    for relative in MYST_SITE_FALLBACK_HASH_GLOBS + MYST_HTML_HASH_GLOBS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    assert detect_myst_hash_mode(tmp_path) == "site"
    assert selected_myst_hash_globs(tmp_path) == MYST_SITE_FALLBACK_HASH_GLOBS


def test_summary_includes_morning_paths_even_when_drift_exists(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    review = workspace / "figures/output/review/index.html"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text("review", encoding="utf-8")
    for relative in MYST_SITE_FALLBACK_HASH_GLOBS:
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok", encoding="utf-8")

    state = RunState(
        sandbox_root=tmp_path / "sandbox",
        workspace=workspace,
        report_dir=tmp_path / "report",
        baseline_passed=True,
        drift_events=[{"phase": "full", "path": "figures/output/review/index.html", "status": "changed"}],
    )

    rendered = summarize(
        state,
        started_at="2026-04-10T00:00:00+00:00",
        ended_at="2026-04-10T01:00:00+00:00",
        runtime_checks=[],
    )

    assert "## Morning Check Paths" in rendered
    assert "review page:" in rendered
