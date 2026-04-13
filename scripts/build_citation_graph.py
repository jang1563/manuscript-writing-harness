#!/usr/bin/env python3
"""Synchronize the citation graph claim nodes from manuscript display items."""

from __future__ import annotations

import json
import sys

from reference_common import CITATION_GRAPH_PATH, sync_citation_graph


def main() -> int:
    graph = sync_citation_graph(write=True)
    print(json.dumps(
        {
            "citation_graph": str(CITATION_GRAPH_PATH.relative_to(CITATION_GRAPH_PATH.parent.parent.parent)),
            "claim_count": len(graph.get("claim_nodes", [])),
            "reference_node_count": len(graph.get("reference_nodes", [])),
            "edge_count": len(graph.get("edges", [])),
        },
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
