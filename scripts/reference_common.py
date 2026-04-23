#!/usr/bin/env python3
"""Deprecated compatibility alias for reference_graph_common."""

from __future__ import annotations

import sys

import reference_graph_common as _reference_graph_common


sys.modules[__name__] = _reference_graph_common
