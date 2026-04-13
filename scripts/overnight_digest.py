#!/usr/bin/env python3
"""Generate a high-signal morning digest for an overnight soak-validation run."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

from build_figure_review import analyze_font_resolution, analyze_png
from figures_common import load_yaml
from overnight_status import choose_run_dir, parse_events, progress_snapshot, REPORT_ROOT


FONT_POLICY_PATH = Path(__file__).resolve().parent.parent / "figures/config/font_policy.yml"
WORKSPACE_CWD_RE = re.compile(r"(?P<workspace>/tmp/.+/workspace)(?:/manuscript)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--run-id", help="Explicit overnight run directory name")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of markdown",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the digest to morning_digest.md inside the run directory",
    )
    return parser.parse_args()


def parse_summary_sections(summary_path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "frontmatter"
    if not summary_path.is_file():
        return sections
    for raw_line in summary_path.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("## "):
            current = raw_line[3:].strip()
            sections[current] = []
            continue
        sections.setdefault(current, []).append(raw_line)
    return sections


def parse_bullet_counter(lines: list[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for line in lines:
        text = line.strip()
        if not text.startswith("- `") and not text.startswith("- phase="):
            continue
        if "` " in text and "x` " in text:
            parts = text.split("`", 2)
            if len(parts) >= 3 and parts[1].endswith("x"):
                try:
                    count = int(parts[1][:-1])
                except ValueError:
                    count = 1
                counter[parts[2].strip()] += count
        else:
            counter[text.removeprefix("- ").strip()] += 1
    return counter


def subsection_lines(lines: list[str], heading: str) -> list[str]:
    active = False
    selected: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped == f"- {heading}":
            active = True
            continue
        if active and stripped.startswith("- ") and not raw_line.startswith("  - "):
            break
        if active and raw_line.startswith("  - "):
            selected.append(raw_line)
    return selected


def summary_field(lines: list[str], prefix: str) -> str | None:
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith(f"- {prefix}:"):
            return stripped
    return None


def extract_workspace_path(run_dir: Path, snapshot: dict[str, Any], events: list[Any]) -> Path | None:
    run_config_path = run_dir / "run_config.json"
    if run_config_path.is_file():
        run_config = json.loads(run_config_path.read_text(encoding="utf-8"))
        workspace = run_config.get("workspace")
        if workspace:
            path = Path(str(workspace))
            if path.exists():
                return path
    summary = snapshot.get("summary_status") or {}
    workspace = summary.get("workspace")
    if workspace:
        path = Path(str(workspace))
        if path.exists():
            return path
    for event in events:
        if not getattr(event, "cwd", None):
            continue
        match = WORKSPACE_CWD_RE.match(str(event.cwd))
        if match:
            path = Path(match.group("workspace"))
            if path.exists():
                return path
    return None


def collect_figure_qa_summary(workspace: Path | None) -> dict[str, Any] | None:
    if workspace is None:
        return None
    manifest_paths = sorted((workspace / "figures/output").glob("*/*.manifest.json"))
    manifest_paths = [path for path in manifest_paths if path.parent.name in {"python", "r"}]
    if not manifest_paths:
        return None

    font_policy = load_yaml(FONT_POLICY_PATH)
    font_status_counts: Counter[str] = Counter()
    clipping_risk_counts: Counter[str] = Counter()
    fallback_renderers: list[str] = []
    clipping_targets: list[str] = []
    parity_targets: list[str] = []
    by_figure: dict[str, dict[str, dict[str, Any]]] = {}

    for manifest_path in manifest_paths:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        renderer = str(manifest["renderer"])
        figure_id = str(manifest["figure_id"])
        outputs = manifest.get("outputs", {})
        png_path = workspace / str(outputs["png"])
        if not png_path.is_file():
            continue
        font_analysis = analyze_font_resolution(manifest, font_policy)
        png_analysis = analyze_png(png_path)
        font_status_counts[font_analysis["status"]] += 1
        clipping_risk_counts[png_analysis["clipping_risk"]] += 1
        if font_analysis["status"] != "preferred":
            fallback_renderers.append(f"{figure_id}/{renderer}:{font_analysis['resolved_name']}")
        if png_analysis["clipping_risk"] in {"moderate", "high"}:
            clipping_targets.append(
                f"{figure_id}/{renderer}:{png_analysis['clipping_risk']}:{png_analysis['hotspot_edge']}"
            )
        by_figure.setdefault(figure_id, {})[renderer] = {
            "font": font_analysis,
            "png": png_analysis,
        }

    for figure_id, renderers in sorted(by_figure.items()):
        if "python" not in renderers or "r" not in renderers:
            continue
        python_font = renderers["python"]["font"]["status"]
        r_font = renderers["r"]["font"]["status"]
        python_clip = renderers["python"]["png"]["clipping_risk"]
        r_clip = renderers["r"]["png"]["clipping_risk"]
        if python_font != r_font or python_clip != r_clip:
            parity_targets.append(
                f"{figure_id}:font={python_font}/{r_font},clipping={python_clip}/{r_clip}"
            )

    return {
        "workspace": str(workspace),
        "manifest_count": len(manifest_paths),
        "figure_count": len(by_figure),
        "font_status_counts": dict(font_status_counts),
        "clipping_risk_counts": dict(clipping_risk_counts),
        "fallback_renderers": fallback_renderers[:8],
        "clipping_targets": clipping_targets[:8],
        "parity_targets": parity_targets[:8],
    }


def summary_snapshot(run_dir: Path) -> dict[str, Any]:
    snapshot = progress_snapshot(run_dir)
    events = parse_events(run_dir / "events.log")
    summary_path = run_dir / "summary.md"
    sections = parse_summary_sections(summary_path)
    warning_lines = sections.get("Warnings", [])
    drift_lines = sections.get("Artifact Drift", [])
    failure_lines = sections.get("Failures", [])
    morning_lines = sections.get("Morning Check Paths", [])
    note_lines = sections.get("Notes", [])

    expected_counter = parse_bullet_counter(subsection_lines(warning_lines, "expected warnings:"))
    unexpected_warnings = [line.strip() for line in subsection_lines(warning_lines, "unexpected warnings:")]
    drift_items = [line.strip() for line in drift_lines if line.strip().startswith("- ")]
    failure_items = [line.strip() for line in failure_lines if line.strip().startswith("- ")]
    morning_paths = [line.strip() for line in morning_lines if line.strip().startswith("- ")]
    notes = [line.strip() for line in note_lines if line.strip()]

    completed = snapshot["summary_exists"]
    health = "healthy"
    reasons: list[str] = []
    if completed:
        unexpected_field = summary_field(warning_lines, "unexpected warnings")
        first_failure_field = summary_field(failure_lines, "first failure")
        latest_failure_field = summary_field(failure_lines, "latest failure")
        if unexpected_field is not None and unexpected_field != "- unexpected warnings: `none`":
            health = "attention"
            reasons.append("unexpected warnings present")
        if any(line != "- `none`" for line in drift_items):
            health = "attention"
            reasons.append("artifact drift detected")
        if (
            first_failure_field is not None
            and first_failure_field != "- first failure: `none`"
        ) or (
            latest_failure_field is not None
            and latest_failure_field != "- latest failure: `none`"
        ):
            health = "attention"
            reasons.append("failures recorded")
    else:
        health = "running"
        reasons.append("run still in progress")

    recent_events = [
        {
            "timestamp": event.timestamp,
            "phase": event.phase,
            "label": event.label,
            "returncode": event.returncode,
        }
        for event in events[-5:]
    ]
    workspace = extract_workspace_path(run_dir, snapshot, events)
    figure_qa = collect_figure_qa_summary(workspace)

    return {
        "run_dir": str(run_dir),
        "workspace": str(workspace) if workspace is not None else None,
        "completed": completed,
        "health": health,
        "reasons": reasons,
        "status_snapshot": snapshot,
        "expected_warning_counts": dict(expected_counter),
        "unexpected_warning_lines": unexpected_warnings,
        "drift_items": drift_items,
        "failure_items": failure_items,
        "morning_paths": morning_paths,
        "notes": notes,
        "recent_events": recent_events,
        "figure_qa": figure_qa,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    snapshot = payload["status_snapshot"]
    lines = [
        "# Overnight Morning Digest",
        "",
        f"- run: `{payload['run_dir']}`",
        f"- status: `{payload['health']}`",
        f"- completed: `{payload['completed']}`",
    ]
    if payload["reasons"]:
        lines.append(f"- rationale: `{'; '.join(payload['reasons'])}`")
    latest_event = snapshot.get("latest_event")
    if latest_event is not None:
        lines.append(
            f"- latest event: `{latest_event['phase']} / {latest_event['label']} / rc={latest_event['returncode']} / {latest_event['status']}`"
        )

    lines.extend(["", "## What To Check First"])
    if payload["health"] == "healthy":
        lines.append("- Open the review page and spot-check figure quality.")
        lines.append("- Skim the summary once, then move on to new figure or manuscript work.")
    elif payload["health"] == "running":
        lines.append("- The run is still active. Re-check later with `python3 scripts/overnight_status.py`.")
        lines.append("- If you need interim confidence, inspect the latest review page path from the sandbox.")
    else:
        lines.append("- Start with `summary.md`, then inspect `events.log` around the first failure.")
        lines.append("- Check unexpected warnings and artifact drift before trusting rendered outputs.")

    lines.extend(["", "## High-Signal Summary"])
    lines.append(f"- event count: `{snapshot['event_count']}`")
    for phase, count in sorted((snapshot.get("phase_counts") or {}).items()):
        lines.append(f"- phase `{phase}`: `{count}`")

    lines.extend(["", "## Warnings"])
    if payload["expected_warning_counts"]:
        for signature, count in sorted(payload["expected_warning_counts"].items()):
            lines.append(f"- expected `{signature}`: `{count}`")
    else:
        lines.append("- expected warnings: `none captured`")
    if payload["unexpected_warning_lines"]:
        for line in payload["unexpected_warning_lines"]:
            lines.append(f"- unexpected: {line}")
    else:
        lines.append("- unexpected warnings: `none`")

    lines.extend(["", "## Failures And Drift"])
    if payload["failure_items"]:
        for line in payload["failure_items"]:
            lines.append(line)
    else:
        lines.append("- failures: `none`")
    if payload["drift_items"]:
        for line in payload["drift_items"]:
            lines.append(line)
    else:
        lines.append("- artifact drift: `none`")

    lines.extend(["", "## Morning Paths"])
    if payload["morning_paths"]:
        lines.extend(payload["morning_paths"])
    else:
        lines.append("- summary not finished yet, so no final morning paths are available")

    figure_qa = payload.get("figure_qa")
    lines.extend(["", "## Figure QA"])
    if figure_qa is None:
        lines.append("- figure QA summary unavailable for this run")
    else:
        lines.append(f"- workspace: `{figure_qa['workspace']}`")
        lines.append(f"- manifests inspected: `{figure_qa['manifest_count']}`")
        lines.append(f"- figures covered: `{figure_qa['figure_count']}`")
        for status, count in sorted(figure_qa["font_status_counts"].items()):
            lines.append(f"- font `{status}`: `{count}`")
        for status, count in sorted(figure_qa["clipping_risk_counts"].items()):
            lines.append(f"- clipping `{status}`: `{count}`")
        if figure_qa["fallback_renderers"]:
            lines.append("- renderer font follow-up:")
            for item in figure_qa["fallback_renderers"]:
                lines.append(f"  - `{item}`")
        if figure_qa["clipping_targets"]:
            lines.append("- clipping follow-up:")
            for item in figure_qa["clipping_targets"]:
                lines.append(f"  - `{item}`")
        if figure_qa["parity_targets"]:
            lines.append("- renderer parity follow-up:")
            for item in figure_qa["parity_targets"]:
                lines.append(f"  - `{item}`")

    lines.extend(["", "## Recent Events"])
    if payload["recent_events"]:
        for event in payload["recent_events"]:
            lines.append(
                f"- `{event['timestamp']}` `{event['phase']}` `{event['label']}` rc=`{event['returncode']}`"
            )
    else:
        lines.append("- no recorded events")

    if payload["notes"]:
        lines.extend(["", "## Notes"])
        for line in payload["notes"]:
            lines.append(f"- {line.lstrip('- ').strip()}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        run_dir = choose_run_dir(args.report_root, args.run_id)
        payload = summary_snapshot(run_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = render_markdown(payload)

    if args.write:
        output_path = run_dir / "morning_digest.md"
        output_path.write_text(rendered, encoding="utf-8")

    print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
