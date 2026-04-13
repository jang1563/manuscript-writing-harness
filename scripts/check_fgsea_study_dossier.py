#!/usr/bin/env python3
"""Check fgsea study dossier readiness and optionally write tracked outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fgsea_study_dossier import build_fgsea_study_dossier, render_fgsea_study_markdown, write_fgsea_study_dossier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--no-active-mirror", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_fgsea_study_dossier(Path(args.config))
    writes = {}
    if args.write:
        writes = write_fgsea_study_dossier(Path(args.config), write_active_mirror=not args.no_active_mirror)
    if args.json:
        print(json.dumps({"report": report, "writes": writes}, indent=2))
    else:
        print(render_fgsea_study_markdown(report), end="")
    if args.strict:
        return 0 if report["readiness"] == "ready" else 1
    return 0 if report["readiness"] != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
