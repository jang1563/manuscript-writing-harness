#!/usr/bin/env python3
"""Repo-local CLI for the systematic review pipeline."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from review_common import (
    BIAS_DIR,
    BIAS_REQUIRED_COLUMNS,
    EXTRACTION_DIR,
    EXTRACTION_REQUIRED_COLUMNS,
    PROTOCOL_DIR,
    PROTOCOL_REQUIRED_FIELDS,
    QUERIES_DIR,
    QUERY_REQUIRED_FIELDS,
    REVIEW_ROOT,
    SCREENING_DIR,
    SCREENING_REQUIRED_COLUMNS,
    load_bias_assessments,
    load_extraction_table,
    load_protocol,
    load_queries,
    load_screening_log,
    validate_csv_columns,
    validate_yaml_fields,
)


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new review project from the protocol template."""
    template = PROTOCOL_DIR / "protocol_template.yml"
    target = PROTOCOL_DIR / "protocol.yml"
    if target.exists() and not args.force:
        print(f"Protocol already exists: {target}")
        print("Use --force to overwrite.")
        return 1
    shutil.copy2(template, target)
    print(f"Created protocol: {target}")
    print("Edit this file to define your review question and criteria.")
    return 0


def cmd_add_query(args: argparse.Namespace) -> int:
    """Add a new query file from the template."""
    template = QUERIES_DIR / "query_template.yml"
    existing = sorted(QUERIES_DIR.glob("query_*.yml"))
    # Exclude template from count
    existing = [p for p in existing if "template" not in p.name]
    n = len(existing) + 1
    db = args.database.lower().replace(" ", "_") if args.database else "database"
    target = QUERIES_DIR / f"query_{n:02d}_{db}.yml"
    shutil.copy2(template, target)
    print(f"Created query file: {target}")
    print("Edit this file to record your search strategy.")
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    """Normalize raw exports and deduplicate."""
    from review_retrieve import run_retrieval

    queries = load_queries()
    if not queries:
        print("No query files found. Run 'add-query' first.")
        return 1

    raw_exports = []
    for q in queries:
        export_file = q.get("export_file", "")
        if not export_file:
            print(f"Query {q.get('query_id', '?')}: no export_file specified, skipping.")
            continue
        raw_path = REVIEW_ROOT / export_file
        if not raw_path.exists():
            print(f"Export file not found: {raw_path}")
            return 1
        raw_exports.append((raw_path, q.get("database", "unknown")))

    if not raw_exports:
        print("No export files to process.")
        return 1

    counts = run_retrieval(
        raw_exports,
        strategy=getattr(args, "strategy", "exact"),
        similarity_threshold=getattr(args, "similarity_threshold", 0.92),
    )
    print(f"Retrieval complete (strategy: {getattr(args, 'strategy', 'exact')}):")
    print(f"  Total raw records: {counts['total_raw']}")
    print(f"  Duplicates removed: {counts['duplicates_removed']}")
    print(f"  Unique records: {counts['unique_records']}")
    return 0


def cmd_init_screening(args: argparse.Namespace) -> int:
    """Create screening log from deduplicated records."""
    from review_screen import init_screening_log

    path = init_screening_log()
    print(f"Screening log initialized: {path}")
    return 0


def cmd_apply_decisions(args: argparse.Namespace) -> int:
    """Merge a batch of screening decisions."""
    from review_screen import apply_decisions

    dec_path = Path(args.decisions) if args.decisions else None
    counts = apply_decisions(decisions_path=dec_path)
    print(f"Applied {counts['applied']} of {counts['total_decisions']} decisions.")
    return 0


def cmd_promote_fulltext(args: argparse.Namespace) -> int:
    """Promote included records to full-text screening stage."""
    from review_screen import promote_to_fulltext

    counts = promote_to_fulltext()
    print(f"Promoted {counts['promoted']} records to full-text screening.")
    return 0


def cmd_init_extraction(args: argparse.Namespace) -> int:
    """Create extraction table from included studies."""
    from review_extract import init_extraction_table

    path = init_extraction_table()
    print(f"Extraction table initialized: {path}")
    return 0


def cmd_init_bias(args: argparse.Namespace) -> int:
    """Create bias assessment table."""
    from review_bias import init_bias_table

    tool = args.tool if args.tool else "rob2"
    path = init_bias_table(tool=tool)
    print(f"Bias assessment table initialized: {path} (tool: {tool})")
    return 0


def cmd_prisma(args: argparse.Namespace) -> int:
    """Generate all PRISMA outputs."""
    from review_prisma import generate_all

    paths = generate_all()
    print("PRISMA outputs generated:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """Generate an evidence summary and package manifest for the review."""
    from review_evidence import write_evidence_outputs

    paths = write_evidence_outputs()
    print("Evidence outputs generated:")
    print(f"  report_md: {paths['report_md']}")
    print(f"  report_json: {paths['report_json']}")
    print(f"  manifest: {paths['manifest']}")
    return 0


def cmd_export_robvis(args: argparse.Namespace) -> int:
    """Export bias assessments as a robvis-compatible CSV."""
    from review_bias import export_robvis_data

    path = export_robvis_data()
    print(f"robvis input written: {path}")
    print("Use in R: robvis::rob_summary(read.csv('...'), tool = 'ROB2')")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show current state of the review pipeline."""
    print("=== Systematic Review Status ===\n")

    # Protocol
    try:
        protocol = load_protocol()
        print(f"Protocol: {protocol.get('title', '(untitled)')}")
        print(f"  Status: {protocol.get('status', 'unknown')}")
        print(f"  Version: {protocol.get('version', '?')}")
    except FileNotFoundError:
        print("Protocol: not initialized (run 'init')")

    # Queries
    queries = load_queries()
    print(f"\nQueries: {len(queries)} file(s)")
    for q in queries:
        print(f"  {q.get('query_id', '?')}: {q.get('database', '?')} ({q.get('hit_count', 0)} hits)")

    # Screening
    try:
        from review_screen import screening_summary
        summary = screening_summary()
        print(f"\nScreening:")
        for stage, counts in summary.items():
            parts = [f"{k}={v}" for k, v in sorted(counts.items())]
            print(f"  {stage}: {', '.join(parts)}")
    except FileNotFoundError:
        print("\nScreening: not started")

    # Extraction
    try:
        ext = load_extraction_table()
        filled = sum(1 for r in ext if r.get("study_design", "").strip())
        print(f"\nExtraction: {len(ext)} studies ({filled} with data)")
    except FileNotFoundError:
        print("\nExtraction: not started")

    # Bias
    try:
        bias = load_bias_assessments()
        assessed = sum(1 for r in bias if r.get("overall_judgment", "").strip())
        print(f"\nBias: {len(bias)} studies ({assessed} assessed)")
    except FileNotFoundError:
        print("\nBias: not started")

    # PRISMA
    prisma_counts = REVIEW_ROOT / "prisma" / "prisma_counts.yml"
    if prisma_counts.exists():
        print(f"\nPRISMA: counts generated ({prisma_counts})")
    else:
        print("\nPRISMA: not generated (run 'prisma')")

    evidence_summary = REVIEW_ROOT / "reports" / "evidence_summary.md"
    if evidence_summary.exists():
        print(f"\nEvidence summary: generated ({evidence_summary})")
    else:
        print("\nEvidence summary: not generated (run 'evidence')")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate all review artifacts against schemas."""
    all_errors: list[str] = []

    # Protocol
    try:
        protocol = load_protocol()
        all_errors.extend(validate_yaml_fields(protocol, PROTOCOL_REQUIRED_FIELDS, "protocol"))
    except FileNotFoundError:
        all_errors.append("protocol: file not found")

    # Queries
    queries = load_queries()
    for q in queries:
        all_errors.extend(
            validate_yaml_fields(q, QUERY_REQUIRED_FIELDS, f"query:{q.get('query_id', '?')}")
        )

    # Screening
    try:
        screening = load_screening_log()
        all_errors.extend(validate_csv_columns(screening, SCREENING_REQUIRED_COLUMNS, "screening_log"))
    except FileNotFoundError:
        pass  # Not an error if screening hasn't started

    # Extraction
    try:
        extraction = load_extraction_table()
        all_errors.extend(
            validate_csv_columns(extraction, EXTRACTION_REQUIRED_COLUMNS, "extraction_table")
        )
        # Field-level validation (only if columns are present)
        from review_extract import validate_extraction
        all_errors.extend(validate_extraction())
    except FileNotFoundError:
        pass

    # Bias
    try:
        bias = load_bias_assessments()
        all_errors.extend(validate_csv_columns(bias, BIAS_REQUIRED_COLUMNS, "bias_assessments"))
        # Field-level validation (only if columns are present)
        from review_bias import validate_bias
        all_errors.extend(validate_bias())
    except FileNotFoundError:
        pass

    if all_errors:
        print(f"Validation found {len(all_errors)} issue(s):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("All artifacts valid.")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """Run the full pipeline with synthetic data."""
    # Import here to avoid circular dependency and keep demo isolated
    sys.path.insert(0, str(REVIEW_ROOT / "demo"))
    from generate_demo import run_demo

    run_demo()
    print("\nDemo complete. Run 'status' to see the results.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="review_cli",
        description="Systematic review pipeline CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new review from protocol template")
    p_init.add_argument("--force", action="store_true", help="Overwrite existing protocol")

    # add-query
    p_query = sub.add_parser("add-query", help="Add a new query file from template")
    p_query.add_argument("--database", "-d", help="Database name for the filename")

    # retrieve
    p_retrieve = sub.add_parser("retrieve", help="Normalize raw exports and deduplicate")
    p_retrieve.add_argument(
        "--strategy", choices=["exact", "fuzzy"], default="exact",
        help="Deduplication strategy (default: exact)",
    )
    p_retrieve.add_argument(
        "--similarity-threshold", type=float, default=0.92,
        help="Title similarity threshold for fuzzy mode (0.0-1.0, default: 0.92)",
    )

    # init-screening
    sub.add_parser("init-screening", help="Create screening log from deduplicated records")

    # apply-decisions
    p_dec = sub.add_parser("apply-decisions", help="Merge a batch of screening decisions")
    p_dec.add_argument("--decisions", help="Path to decisions CSV")

    # promote-fulltext
    sub.add_parser("promote-fulltext", help="Promote included records to full-text stage")

    # init-extraction
    sub.add_parser("init-extraction", help="Create extraction table from included studies")

    # init-bias
    p_bias = sub.add_parser("init-bias", help="Create bias assessment table")
    p_bias.add_argument("--tool", choices=["rob2", "robins_i"], default="rob2", help="Bias tool")

    # prisma
    sub.add_parser("prisma", help="Generate all PRISMA outputs")

    # evidence
    sub.add_parser("evidence", help="Generate evidence summary and package manifest")

    # export-robvis
    sub.add_parser("export-robvis", help="Export bias assessments as a robvis-compatible CSV")

    # status
    sub.add_parser("status", help="Show current state of the review pipeline")

    # validate
    sub.add_parser("validate", help="Validate all review artifacts against schemas")

    # demo
    sub.add_parser("demo", help="Run full pipeline with synthetic data")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "init": cmd_init,
        "add-query": cmd_add_query,
        "retrieve": cmd_retrieve,
        "init-screening": cmd_init_screening,
        "apply-decisions": cmd_apply_decisions,
        "promote-fulltext": cmd_promote_fulltext,
        "init-extraction": cmd_init_extraction,
        "init-bias": cmd_init_bias,
        "prisma": cmd_prisma,
        "evidence": cmd_evidence,
        "export-robvis": cmd_export_robvis,
        "status": cmd_status,
        "validate": cmd_validate,
        "demo": cmd_demo,
    }

    try:
        return handlers[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
