#!/usr/bin/env python3
"""Risk-of-bias assessment management for the systematic review pipeline."""

from __future__ import annotations

from pathlib import Path

from review_common import (
    BIAS_DIR,
    BIAS_REQUIRED_COLUMNS,
    EXTRACTION_DIR,
    ROB2_DOMAINS,
    ROBINS_I_DOMAINS,
    load_csv,
    validate_csv_columns,
    write_csv,
)


def _domain_columns(tool: str) -> list[str]:
    """Return the domain column names for the given bias tool."""
    if tool == "rob2":
        return list(ROB2_DOMAINS)
    if tool == "robins_i":
        return list(ROBINS_I_DOMAINS)
    return []


def init_bias_table(
    extraction_table_path: Path | None = None,
    output_path: Path | None = None,
    tool: str = "rob2",
) -> Path:
    """Create a bias assessment table from the extraction table.

    One row per included study with domain columns pre-populated
    for the selected tool and all judgments blank.
    """
    ext_file = extraction_table_path or (EXTRACTION_DIR / "extraction_table.csv")
    out_file = output_path or (BIAS_DIR / "bias_assessments.csv")

    ext_rows = load_csv(ext_file)
    domains = _domain_columns(tool)

    rows = []
    for rec in ext_rows:
        row: dict[str, str] = {
            "record_id": rec["record_id"],
            "tool": tool,
            "overall_judgment": "",
            "assessor": "",
            "ai_assisted": "false",
            "timestamp": "",
        }
        for d in domains:
            row[d] = ""
        rows.append(row)

    fieldnames = BIAS_REQUIRED_COLUMNS + domains
    write_csv(out_file, rows, fieldnames)
    return out_file


# Allowed values for enumerated bias fields.
ALLOWED_TOOLS = {"rob2", "robins_i", "newcastle_ottawa", "custom"}
ALLOWED_OVERALL_JUDGMENTS = {"low", "some_concerns", "high", "no_information"}
ALLOWED_DOMAIN_JUDGMENTS = {
    "low",
    "some_concerns",
    "moderate",
    "serious",
    "high",
    "critical",
    "no_information",
}
ALLOWED_BOOL_VALUES = {"true", "false"}


def validate_bias(
    table_path: Path | None = None, semantic: bool = True
) -> list[str]:
    """Validate the bias assessment table.

    Args:
        table_path: Path to bias_assessments.csv (defaults to repo path).
        semantic: When True, also check enumerated values (tool, judgments)
                  in addition to presence checks.

    Returns:
        List of error messages (empty if valid).
    """
    tbl_file = table_path or (BIAS_DIR / "bias_assessments.csv")
    rows = load_csv(tbl_file)

    errors = validate_csv_columns(rows, BIAS_REQUIRED_COLUMNS, "bias_assessments")
    if errors:
        return errors

    for i, row in enumerate(rows, 1):
        rid = row.get("record_id", f"row_{i}")
        tool = row.get("tool", "")
        domains = _domain_columns(tool)

        # Presence
        for col in BIAS_REQUIRED_COLUMNS:
            if not row.get(col, "").strip():
                errors.append(f"Record {rid}: missing value for '{col}'")

        for d in domains:
            if not row.get(d, "").strip():
                errors.append(f"Record {rid}: missing domain judgment for '{d}'")

        if not semantic:
            continue

        # Enum checks
        if tool and tool not in ALLOWED_TOOLS:
            errors.append(
                f"Record {rid}: unknown tool '{tool}' (allowed: {sorted(ALLOWED_TOOLS)})"
            )

        oj = row.get("overall_judgment", "").strip()
        if oj and oj not in ALLOWED_OVERALL_JUDGMENTS:
            errors.append(
                f"Record {rid}: unknown overall_judgment '{oj}' "
                f"(allowed: {sorted(ALLOWED_OVERALL_JUDGMENTS)})"
            )

        ai = row.get("ai_assisted", "").strip().lower()
        if ai and ai not in ALLOWED_BOOL_VALUES:
            errors.append(
                f"Record {rid}: ai_assisted must be 'true' or 'false' (got '{ai}')"
            )

        for d in domains:
            v = row.get(d, "").strip()
            if v and v not in ALLOWED_DOMAIN_JUDGMENTS:
                errors.append(
                    f"Record {rid}: invalid judgment for '{d}': '{v}' "
                    f"(allowed: {sorted(ALLOWED_DOMAIN_JUDGMENTS)})"
                )

    return errors


def export_robvis_data(
    table_path: Path | None = None, output_path: Path | None = None
) -> Path:
    """Export bias assessments in robvis-compatible CSV format.

    robvis (https://github.com/mcguinlu/robvis) expects a wide-format CSV
    with columns: Study, D1, D2, ... Dn, Overall. Judgments use single-letter
    codes (Low='L', Some concerns='S', High='H', No information='X').

    The output is consumable directly by ``robvis::rob_summary()`` and
    ``robvis::rob_traffic_light()`` in R.
    """
    tbl_file = table_path or (BIAS_DIR / "bias_assessments.csv")
    out_file = output_path or (BIAS_DIR / "robvis_input.csv")

    rows = load_csv(tbl_file)
    if not rows:
        write_csv(out_file, [], ["Study"])
        return out_file

    # All rows should use the same tool (robvis expects one tool per file)
    tool = rows[0].get("tool", "")
    domains = _domain_columns(tool)

    # robvis uses D1, D2, ... Dn (1-indexed). Map our domain columns.
    domain_short = [f"D{i + 1}" for i in range(len(domains))]

    judgment_map = {
        "low": "Low",
        "some_concerns": "Some concerns",
        "moderate": "Moderate",
        "serious": "Serious",
        "high": "High",
        "critical": "Critical",
        "no_information": "No information",
    }

    output_rows = []
    for row in rows:
        out_row = {"Study": row.get("record_id", "")}
        for short, full in zip(domain_short, domains):
            raw = row.get(full, "").strip().lower()
            out_row[short] = judgment_map.get(raw, "No information")
        oj = row.get("overall_judgment", "").strip().lower()
        out_row["Overall"] = judgment_map.get(oj, "No information")
        out_row["Weight"] = "1"
        output_rows.append(out_row)

    fieldnames = ["Study"] + domain_short + ["Overall", "Weight"]
    write_csv(out_file, output_rows, fieldnames)
    return out_file


def bias_summary(table_path: Path | None = None) -> dict[str, dict[str, int]]:
    """Return distribution of overall judgments and per-domain judgments."""
    tbl_file = table_path or (BIAS_DIR / "bias_assessments.csv")
    rows = load_csv(tbl_file)

    overall: dict[str, int] = {}
    domain_counts: dict[str, dict[str, int]] = {}

    for row in rows:
        oj = row.get("overall_judgment", "").strip() or "unassessed"
        overall[oj] = overall.get(oj, 0) + 1

        tool = row.get("tool", "").strip()
        for d in _domain_columns(tool):
            if d not in domain_counts:
                domain_counts[d] = {}
            val = row.get(d, "").strip() or "unassessed"
            domain_counts[d][val] = domain_counts[d].get(val, 0) + 1

    return {"overall": overall, "domains": domain_counts}
