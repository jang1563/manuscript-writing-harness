#!/usr/bin/env python3
"""Deprecated compatibility alias for bibliography_common."""

from __future__ import annotations

import sys

import bibliography_common as _bibliography_common


sys.modules[__name__] = _bibliography_common
