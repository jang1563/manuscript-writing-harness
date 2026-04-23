#!/usr/bin/env python3
"""Repo-local CLI for the references and citation pipeline."""

from __future__ import annotations

import argparse
import sys

from bibliography_common import (
    BIBLIOGRAPHY_SOURCE_MANIFEST,
    CSL_DIR,
    LIBRARY_BIB,
    MANUSCRIPT_DIR,
    REFERENCES_DIR,
    available_csl_styles,
    bibliography_source_status,
    cross_reference_check,
    extract_cite_keys_from_manuscript,
    lint_entries,
    load_library,
)


def cmd_status(args: argparse.Namespace) -> int:
    """Show bibliography and citation status."""
    print("=== References Status ===\n")

    # Library
    try:
        entries = load_library()
        print(f"Bibliography: {LIBRARY_BIB}")
        print(f"  Entries: {len(entries)}")

        # Count by type
        type_counts: dict[str, int] = {}
        for e in entries:
            t = e.get("entry_type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        for t, c in sorted(type_counts.items()):
            print(f"    {t}: {c}")

        # DOI coverage
        with_doi = sum(1 for e in entries if e.get("doi", "").strip())
        print(f"  With DOI: {with_doi}/{len(entries)}")

    except FileNotFoundError:
        print(f"Bibliography: not found ({LIBRARY_BIB})")
        entries = []

    # CSL styles
    styles = available_csl_styles()
    print(f"\nCSL styles: {len(styles)}")
    for s in styles:
        print(f"  {s}")

    source = bibliography_source_status()
    print("\nBibliography source:")
    print(f"  Readiness: {source['status']}")
    print(f"  Manifest: {BIBLIOGRAPHY_SOURCE_MANIFEST}")
    if source["source_type"]:
        print(f"  Source type: {source['source_type']}")
    if source["manifest_state"]:
        print(f"  Manifest state: {source['manifest_state']}")
    if source["translator"]:
        print(f"  Translator: {source['translator']}")
    if source["export_mode"]:
        print(f"  Export mode: {source['export_mode']}")
    print(f"  Output: {source['target_path']}")
    print(f"  Manuscript scope: {source['manuscript_scope_status']}")
    if source["manuscript_scope_confirmed_on"]:
        print(f"  Manuscript scope confirmed on: {source['manuscript_scope_confirmed_on']}")
    if source["manuscript_scope_note"]:
        print(f"  Manuscript scope note: {source['manuscript_scope_note']}")
    if source["issues"]:
        print("  Issues:")
        for issue in source["issues"]:
            print(f"    - {issue}")
    if source["warnings"]:
        print("  Warnings:")
        for warning in source["warnings"]:
            print(f"    - {warning}")
    if source["manuscript_scope_issues"]:
        print("  Manuscript scope issues:")
        for issue in source["manuscript_scope_issues"]:
            print(f"    - {issue}")
    if source["manuscript_scope_warnings"]:
        print("  Manuscript scope warnings:")
        for warning in source["manuscript_scope_warnings"]:
            print(f"    - {warning}")

    # Manuscript citations
    keys = extract_cite_keys_from_manuscript()
    print(f"\nManuscript citation keys: {len(keys)}")
    if keys:
        for k in sorted(keys):
            print(f"  {k}")

    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    """Lint the bibliography for quality issues."""
    entries = load_library()
    messages = lint_entries(entries)

    # Optionally include cross-reference check
    if not args.no_cross_ref:
        manuscript_keys = extract_cite_keys_from_manuscript()
        messages.extend(cross_reference_check(entries, manuscript_keys))

    if not messages:
        print("No issues found.")
        return 0

    errors = [m for m in messages if m.level == "error"]
    warnings = [m for m in messages if m.level == "warning"]
    infos = [m for m in messages if m.level == "info"]

    if errors:
        print(f"Errors ({len(errors)}):")
        for m in errors:
            print(f"  {m}")

    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for m in warnings:
            print(f"  {m}")

    if infos and args.verbose:
        print(f"Info ({len(infos)}):")
        for m in infos:
            print(f"  {m}")

    print(f"\nTotal: {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s)")

    # Return non-zero only for errors
    return 1 if errors else 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate bibliography structure and citation integrity."""
    all_ok = True

    # Check library exists and parses
    try:
        entries = load_library()
        print(f"Library: {len(entries)} entries parsed OK")
    except FileNotFoundError:
        print("Library: NOT FOUND")
        return 1
    except Exception as e:
        print(f"Library: PARSE ERROR - {e}")
        return 1

    # Check for errors (not warnings)
    messages = lint_entries(entries)
    errors = [m for m in messages if m.level == "error"]
    if errors:
        print(f"Lint errors: {len(errors)}")
        for m in errors:
            print(f"  {m}")
        all_ok = False
    else:
        print("Lint: no errors")

    # Check CSL styles
    styles = available_csl_styles()
    if styles:
        print(f"CSL styles: {len(styles)} available ({', '.join(styles)})")
    else:
        print("CSL styles: none found (expected at least one)")
        all_ok = False

    # Cross-reference check
    manuscript_keys = extract_cite_keys_from_manuscript()
    bib_keys = {e["cite_key"] for e in entries}
    unresolved = manuscript_keys - bib_keys
    if unresolved:
        print(f"Unresolved citations: {sorted(unresolved)}")
        all_ok = False
    else:
        print(f"Cross-reference: OK ({len(manuscript_keys)} keys resolved)")

    source = bibliography_source_status()
    if source["status"] == "ready":
        print(
            "Bibliography source: READY "
            f"({source['source_type']} -> {source['target_path']})"
        )
    else:
        print(f"Bibliography source: {source['status'].upper()}")
        print(f"  Manifest: {source['manifest_path']}")
        for issue in source["issues"]:
            print(f"  - {issue}")
        for warning in source["warnings"]:
            print(f"  - {warning}")
        all_ok = False

    if source["manuscript_scope_status"] == "confirmed":
        print("Bibliography manuscript scope: CONFIRMED")
    elif source["manuscript_scope_status"] == "invalid":
        print("Bibliography manuscript scope: INVALID")
        for issue in source["manuscript_scope_issues"]:
            print(f"  - {issue}")
        all_ok = False
    else:
        print("Bibliography manuscript scope: UNCONFIRMED")
        if source["manuscript_scope_note"]:
            print(f"  - {source['manuscript_scope_note']}")
        for warning in source["manuscript_scope_warnings"]:
            print(f"  - {warning}")

    if all_ok:
        print("\nAll checks passed.")
        return 0
    else:
        print("\nSome checks failed.")
        return 1


def cmd_list_styles(args: argparse.Namespace) -> int:
    """List available CSL styles."""
    styles = available_csl_styles()
    if not styles:
        print("No CSL styles found.")
        print(f"Add .csl files to: {CSL_DIR}")
        return 0

    print(f"Available CSL styles ({len(styles)}):")
    for s in styles:
        csl_path = CSL_DIR / f"{s}.csl"
        size = csl_path.stat().st_size
        print(f"  {s} ({size} bytes)")
    return 0


def cmd_keys(args: argparse.Namespace) -> int:
    """List all citation keys in the bibliography."""
    entries = load_library()
    for e in entries:
        key = e["cite_key"]
        etype = e.get("entry_type", "?")
        author = e.get("author", "?")
        year = e.get("year", "?")
        title = e.get("title", "?")
        if len(title) > 60:
            title = title[:57] + "..."
        print(f"  {key} [{etype}] {author} ({year}) {title}")
    print(f"\nTotal: {len(entries)} entries")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="references_cli",
        description="References and citation pipeline CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Show bibliography and citation status")

    # lint
    p_lint = sub.add_parser("lint", help="Lint the bibliography for quality issues")
    p_lint.add_argument("--verbose", "-v", action="store_true", help="Show info-level messages")
    p_lint.add_argument(
        "--no-cross-ref", action="store_true",
        help="Skip cross-reference check against manuscript",
    )

    # validate
    sub.add_parser("validate", help="Validate bibliography and citation integrity")

    # list-styles
    sub.add_parser("list-styles", help="List available CSL styles")

    # keys
    sub.add_parser("keys", help="List all citation keys in the bibliography")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 0

    handlers = {
        "status": cmd_status,
        "lint": cmd_lint,
        "validate": cmd_validate,
        "list-styles": cmd_list_styles,
        "keys": cmd_keys,
    }

    try:
        return handlers[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
