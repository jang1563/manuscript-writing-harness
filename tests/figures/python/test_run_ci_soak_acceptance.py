from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_ci_soak_acceptance import parse_args


def test_parse_args_uses_ci_short_soak_defaults() -> None:
    args = parse_args([])

    assert args.max_hours == 0.1
    assert args.light_interval_min == 1
    assert args.full_interval_min == 2
    assert args.myst_interval_min == 3
    assert args.workspace_root == Path("/tmp/manuscript_overnight_ci")
    assert args.no_keep_workspace is False
    assert args.write_step_summary is False
