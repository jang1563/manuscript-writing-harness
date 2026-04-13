#!/usr/bin/env python3
"""Build a schema-backed example main table in multiple output formats."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "tables/schemas/main_table_schema.yml"


def load_schema() -> dict[str, object]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def parse_row(row: dict[str, str], columns: list[dict[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for column in columns:
        name = str(column["name"])
        column_type = str(column["type"])
        raw_value = row[name]
        if column_type == "integer":
            parsed[name] = int(raw_value)
        elif column_type == "float":
            parsed[name] = float(raw_value)
        else:
            parsed[name] = raw_value
    return parsed


def format_value(value: object, column: dict[str, object], default_decimals: int) -> str:
    column_type = str(column["type"])
    if column_type == "integer":
        return str(int(value))
    if column_type == "float":
        decimals = int(column.get("decimals", default_decimals))
        return f"{float(value):.{decimals}f}"
    return str(value)


def alignment_token(align: str) -> str:
    if align == "right":
        return "---:"
    if align == "center":
        return ":---:"
    return ":---"


def main() -> int:
    schema = load_schema()
    columns: list[dict[str, object]] = list(schema["columns"])
    input_path = REPO_ROOT / str(schema["input_path"])
    output_dir = REPO_ROOT / "tables/output"
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        observed_columns = reader.fieldnames or []
        expected_columns = [str(column["name"]) for column in columns]
        if observed_columns != expected_columns:
            raise ValueError(
                f"Input columns {observed_columns!r} do not match schema columns {expected_columns!r}"
            )
        rows = [parse_row(row, columns) for row in reader]

    sort_config = schema["sort"]
    sort_by = str(sort_config["by"])
    reverse = str(sort_config["order"]).lower() == "descending"
    rows.sort(key=lambda row: row[sort_by], reverse=reverse)

    default_decimals = int(schema.get("default_decimals", 3))
    display_rows: list[dict[str, str]] = []
    for row in rows:
        display_rows.append(
            {
                str(column["label"]): format_value(row[str(column["name"])], column, default_decimals)
                for column in columns
            }
        )

    output_basename = str(schema["output_basename"])
    markdown_path = output_dir / f"{output_basename}.md"
    csv_path = output_dir / f"{output_basename}.csv"
    json_path = output_dir / f"{output_basename}.json"
    manifest_path = output_dir / f"{output_basename}.manifest.json"

    labels = [str(column["label"]) for column in columns]
    alignments = [alignment_token(str(column.get("align", "left"))) for column in columns]
    markdown_lines = [
        f"**{schema['title']}.** {schema['caption']}",
        "",
        "| " + " | ".join(labels) + " |",
        "| " + " | ".join(alignments) + " |",
    ]
    for row in display_rows:
        markdown_lines.append("| " + " | ".join(row[label] for label in labels) + " |")
    markdown_path.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=labels)
        writer.writeheader()
        writer.writerows(display_rows)

    json_payload = {
        "table_id": schema["table_id"],
        "title": schema["title"],
        "caption": schema["caption"],
        "claim_ids": list(schema.get("claim_ids", [])),
        "fact_sheet": str(schema.get("fact_sheet", "")),
        "rows": rows,
    }
    json_path.write_text(json.dumps(json_payload, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "table_id": schema["table_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path.relative_to(REPO_ROOT)),
        "claim_ids": list(schema.get("claim_ids", [])),
        "fact_sheet": str(schema.get("fact_sheet", "")),
        "outputs": [
            str(markdown_path.relative_to(REPO_ROOT)),
            str(csv_path.relative_to(REPO_ROOT)),
            str(json_path.relative_to(REPO_ROOT)),
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print("Built example table pipeline.")
    print(f"  - markdown: {markdown_path.relative_to(REPO_ROOT)}")
    print(f"  - csv: {csv_path.relative_to(REPO_ROOT)}")
    print(f"  - json: {json_path.relative_to(REPO_ROOT)}")
    print(f"  - manifest: {manifest_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
