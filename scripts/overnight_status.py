#!/usr/bin/env python3
"""Inspect the latest overnight soak-validation run without opening logs manually."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_ROOT = REPO_ROOT / "reports" / "overnight"
EVENT_HEADER_RE = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\] phase=(?P<phase>\S+) label=(?P<label>\S+)$"
)
KEY_VALUE_RE = re.compile(r"^(?P<key>[a-z_]+)=(?P<value>.+)$")


@dataclass
class EventRecord:
    timestamp: str
    phase: str
    label: str
    cwd: str | None = None
    command: str | None = None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--run-id", help="Explicit overnight run directory name")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of plain text",
    )
    return parser.parse_args()


def latest_run_dir(report_root: Path) -> Path:
    candidates = sorted(
        [path for path in report_root.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No overnight runs found in {report_root}")
    return candidates[0]


def choose_run_dir(report_root: Path, run_id: str | None) -> Path:
    if run_id is None:
        return latest_run_dir(report_root)
    target = report_root / run_id
    if not target.is_dir():
        raise FileNotFoundError(f"Overnight run not found: {target}")
    return target


def parse_run_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_events(path: Path) -> list[EventRecord]:
    if not path.is_file():
        return []
    events: list[EventRecord] = []
    current: EventRecord | None = None
    stream: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        header = EVENT_HEADER_RE.match(raw_line)
        if header:
            if current is not None:
                events.append(current)
            current = EventRecord(
                timestamp=header.group("timestamp"),
                phase=header.group("phase"),
                label=header.group("label"),
            )
            stream = None
            continue
        if current is None:
            continue
        if raw_line == "--- stdout ---":
            stream = "stdout"
            continue
        if raw_line == "--- stderr ---":
            stream = "stderr"
            continue
        if raw_line == "--- end ---":
            stream = None
            continue
        pair = KEY_VALUE_RE.match(raw_line)
        if stream is not None:
            if stream == "stdout":
                current.stdout += raw_line + "\n"
            else:
                current.stderr += raw_line + "\n"
            continue
        if not pair:
            continue
        key = pair.group("key")
        value = pair.group("value")
        if key == "cwd":
            current.cwd = value
        elif key == "command":
            current.command = value
        elif key == "returncode":
            try:
                current.returncode = int(value)
            except ValueError:
                current.returncode = None
    if current is not None:
        events.append(current)
    return events


def event_status(event: EventRecord) -> str:
    if event.returncode in (None, 0):
        return "ok"
    if (
        event.label == "myst-build"
        and "listen EPERM: operation not permitted" in event.stderr
    ):
        return "expected-local-bind-warning"
    return "failed"


def parse_summary_status(path: Path) -> dict[str, str]:
    status: dict[str, str] = {}
    if not path.is_file():
        return status
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- "):
            continue
        if ": `" not in line:
            continue
        key, value = line[2:].split(": `", 1)
        status[key.strip()] = value.rstrip("`")
    return status


def progress_snapshot(run_dir: Path) -> dict[str, Any]:
    run_config = parse_run_config(run_dir / "run_config.json")
    events = parse_events(run_dir / "events.log")
    summary = parse_summary_status(run_dir / "summary.md")
    latest_event = events[-1] if events else None

    phase_counts: dict[str, int] = {}
    for event in events:
        phase_counts[event.phase] = phase_counts.get(event.phase, 0) + 1

    snapshot = {
        "run_dir": str(run_dir),
        "started_at": run_config.get("invoked_at"),
        "summary_exists": (run_dir / "summary.md").is_file(),
        "preflight_exists": (run_dir / "preflight.txt").is_file(),
        "event_count": len(events),
        "phase_counts": phase_counts,
        "latest_event": (
            {
                "timestamp": latest_event.timestamp,
                "phase": latest_event.phase,
                "label": latest_event.label,
                "returncode": latest_event.returncode,
                "status": event_status(latest_event),
            }
            if latest_event is not None
            else None
        ),
        "summary_status": summary,
    }
    return snapshot


def render_text(snapshot: dict[str, Any]) -> str:
    lines = [
        "Overnight Run Status",
        "",
        f"Run: {snapshot['run_dir']}",
        f"Started: {snapshot.get('started_at') or 'unknown'}",
        f"Preflight file: {'present' if snapshot['preflight_exists'] else 'missing'}",
        f"Summary file: {'present' if snapshot['summary_exists'] else 'not yet written'}",
        f"Recorded events: {snapshot['event_count']}",
    ]

    phase_counts = snapshot.get("phase_counts") or {}
    if phase_counts:
        lines.append("Phase counts:")
        for phase, count in sorted(phase_counts.items()):
            lines.append(f"  {phase}: {count}")

    latest_event = snapshot.get("latest_event")
    if latest_event:
        lines.extend(
            [
                "Latest event:",
                f"  time: {latest_event['timestamp']}",
                f"  phase: {latest_event['phase']}",
                f"  label: {latest_event['label']}",
                f"  returncode: {latest_event['returncode']}",
                f"  status: {latest_event['status']}",
            ]
        )

    summary_status = snapshot.get("summary_status") or {}
    if summary_status:
        lines.append("Summary snapshot:")
        for key in (
            "baseline",
            "MyST artifact mode",
            "light runs",
            "full runs",
            "manuscript runs",
        ):
            if key in summary_status:
                lines.append(f"  {key}: {summary_status[key]}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        run_dir = choose_run_dir(args.report_root, args.run_id)
        snapshot = progress_snapshot(run_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(snapshot, indent=2))
    else:
        print(render_text(snapshot), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
