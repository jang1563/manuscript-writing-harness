#!/usr/bin/env python3
"""Tests for deprecated compatibility aliases around renamed reference helpers."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def test_references_common_alias_points_to_bibliography_common() -> None:
    import bibliography_common
    import references_common

    assert references_common is bibliography_common
    assert references_common.parse_bibtex is bibliography_common.parse_bibtex


def test_reference_common_alias_points_to_reference_graph_common() -> None:
    import reference_common
    import reference_graph_common

    assert reference_common is reference_graph_common
    assert reference_common.sync_citation_graph is reference_graph_common.sync_citation_graph


def test_aliases_preserve_module_level_mutation() -> None:
    import bibliography_common
    import reference_graph_common
    import references_common
    import reference_common

    original_manuscript_dir = bibliography_common.MANUSCRIPT_DIR
    original_citation_graph = reference_graph_common.CITATION_GRAPH_PATH

    sentinel_dir = Path("/tmp/legacy-bibliography-common")
    sentinel_graph = Path("/tmp/legacy-reference-graph.json")

    references_common.MANUSCRIPT_DIR = sentinel_dir
    reference_common.CITATION_GRAPH_PATH = sentinel_graph

    try:
        assert bibliography_common.MANUSCRIPT_DIR == sentinel_dir
        assert reference_graph_common.CITATION_GRAPH_PATH == sentinel_graph
    finally:
        bibliography_common.MANUSCRIPT_DIR = original_manuscript_dir
        reference_graph_common.CITATION_GRAPH_PATH = original_citation_graph
