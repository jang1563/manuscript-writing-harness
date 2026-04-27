#!/usr/bin/env python3
"""Check whether external gates are ready before promoting the manuscript to real."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from real_manuscript_preflight import (
    PREFLIGHT_CONFIG_PATH,
    build_real_manuscript_preflight,
    render_real_manuscript_preflight_markdown,
    write_real_manuscript_preflight_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PREFLIGHT_CONFIG_PATH)
    parser.add_argument("--write", action="store_true", help="Write preflight report and manifest.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless preflight readiness is ready.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_real_manuscript_preflight(config_path=args.config)
    payload: dict[str, object] = {"report": report}
    if args.write:
        payload["writes"] = write_real_manuscript_preflight_outputs(config_path=args.config)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render_real_manuscript_preflight_markdown(report))
    if args.strict and report["readiness"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
