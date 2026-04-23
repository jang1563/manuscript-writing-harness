#!/usr/bin/env python3
"""Benchmark the multi-agent manuscript system against tracked structured-input suites."""

from __future__ import annotations

import json
from contextlib import contextmanager
import hashlib
from pathlib import Path, PurePosixPath
import shutil
from tempfile import TemporaryDirectory
import time
from typing import Any, Iterator
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

try:  # pragma: no cover - import path differs between script and package use.
    from . import manuscript_claims, manuscript_section_briefs, manuscript_section_drafts
    from .figures_common import REPO_ROOT, write_text
    from .manuscript_claims import build_claim_coverage, build_claim_packets
    from .manuscript_section_briefs import build_section_briefs
    from .manuscript_section_drafts import build_section_drafts
    from .pre_submission_audit import build_pre_submission_audit
    from .reference_integrity import build_reference_report
    from .review_common import validate_review_artifacts
    from .review_evidence import build_evidence_report
except ImportError:  # pragma: no cover
    import manuscript_claims
    import manuscript_section_briefs
    import manuscript_section_drafts
    from figures_common import REPO_ROOT, write_text
    from manuscript_claims import build_claim_coverage, build_claim_packets
    from manuscript_section_briefs import build_section_briefs
    from manuscript_section_drafts import build_section_drafts
    from pre_submission_audit import build_pre_submission_audit
    from reference_integrity import build_reference_report
    from review_common import validate_review_artifacts
    from review_evidence import build_evidence_report


BENCHMARK_ROOT = REPO_ROOT / "benchmarks"
SUITES_DIR = BENCHMARK_ROOT / "suites"
BUNDLES_DIR = BENCHMARK_ROOT / "bundles"
PACKAGES_DIR = BENCHMARK_ROOT / "packages"
REPORTS_DIR = BENCHMARK_ROOT / "reports"
MANIFESTS_DIR = BENCHMARK_ROOT / "manifests"
PUBLIC_RUNS_DIR = BENCHMARK_ROOT / "public_runs"
DEFAULT_SUITE_ID = "paper_writing_bench_like_internal_v1"
DEFAULT_BUNDLE_ID = "paperwritingbench_style_demo_v1"
PACKAGE_MANIFEST_NAME = "package_manifest.json"
MATRIX_REPORT_STEM = "harness_benchmark_matrix"
PUBLIC_RUN_ENVIRONMENT_KEYS = (
    "python_version",
    "python_implementation",
    "python_executable",
    "platform",
    "machine",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp-{uuid4().hex}"
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_sha256(path: Path) -> str:
    path = path.resolve()
    if not path.exists():
        raise ValueError(f"Directory not found for hashing: {_relative(path)}")
    if not path.is_dir():
        raise ValueError(f"Expected directory for hashing: {_relative(path)}")

    digest = hashlib.sha256()
    file_paths = sorted(child for child in path.rglob("*") if child.is_file())
    for file_path in file_paths:
        relative_path = file_path.relative_to(path).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bundle_fingerprint_payload(bundle_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(bundle_payload)
    payload.pop("import_source", None)
    return payload


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _provenance_relative(path: Path, *, package_root: Path | None = None) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        if package_root is not None:
            try:
                relative_to_package = path.relative_to(package_root)
                if str(relative_to_package) == ".":
                    return str(Path("external") / package_root.name)
                return str(Path("external") / package_root.name / relative_to_package)
            except ValueError:
                pass
        return path.name


def list_benchmark_suites() -> list[str]:
    return sorted(path.stem for path in SUITES_DIR.glob("*.json") if path.name != "README.md")


def load_benchmark_suite(suite_id: str = DEFAULT_SUITE_ID) -> dict[str, Any]:
    path = SUITES_DIR / f"{suite_id}.json"
    if not path.exists():
        available = ", ".join(list_benchmark_suites()) or "none"
        raise ValueError(f"Unknown benchmark suite '{suite_id}'. Available suites: {available}")
    payload = load_json(path)
    payload.setdefault("suite_id", suite_id)
    payload["_suite_path"] = _relative(path)
    return payload


def list_benchmark_bundles() -> list[str]:
    return sorted(path.stem for path in BUNDLES_DIR.glob("*.json") if path.name != "README.md")


def load_benchmark_bundle(bundle_id: str = DEFAULT_BUNDLE_ID) -> dict[str, Any]:
    path = BUNDLES_DIR / f"{bundle_id}.json"
    if not path.exists():
        available = ", ".join(list_benchmark_bundles()) or "none"
        raise ValueError(f"Unknown benchmark bundle '{bundle_id}'. Available bundles: {available}")
    payload = load_json(path)
    payload.setdefault("bundle_id", bundle_id)
    payload["_bundle_path"] = _relative(path)
    return payload


def _load_package_value(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return load_json(path)
    return path.read_text(encoding="utf-8").strip()


def _load_package_object(
    package_root: Path,
    relative_path: str,
    *,
    label: str,
    required_type: type | tuple[type, ...] | None = None,
) -> Any:
    candidate_path = (package_root / relative_path).resolve()
    try:
        candidate_path.relative_to(package_root)
    except ValueError as exc:
        raise ValueError(
            f"{label} must stay within package root: {relative_path}"
        ) from exc
    if not candidate_path.exists():
        raise ValueError(f"{label} file not found: {relative_path}")
    if candidate_path.is_dir():
        raise ValueError(f"{label} must resolve to a file: {relative_path}")
    value = _load_package_value(candidate_path)
    if required_type is not None and not isinstance(value, required_type):
        expected_name = (
            ", ".join(type_.__name__ for type_ in required_type)
            if isinstance(required_type, tuple)
            else required_type.__name__
        )
        raise ValueError(f"{label} must resolve to {expected_name}: {relative_path}")
    return value


def _resolve_package_case(package_root: Path, raw_case: dict[str, Any]) -> dict[str, Any]:
    case = dict(raw_case)
    case_id = str(case.get("case_id", ""))
    if not case_id:
        raise ValueError("package case is missing case_id")

    source_materials = case.get("source_materials", {})
    if source_materials is None:
        source_materials = {}
    if not isinstance(source_materials, dict):
        raise ValueError(f"{case_id}: source_materials must be an object")
    resolved_source_materials = dict(source_materials)
    for key, relative_path in _string_dict(
        case.get("source_material_files", {}),
        f"{case_id}.source_material_files",
    ).items():
        resolved_source_materials[key] = _load_package_object(
            package_root,
            relative_path,
            label=f"{case_id}.source_material_files.{key}",
        )

    mapping = case.get("mapping", {})
    if mapping is None:
        mapping = {}
    if not isinstance(mapping, dict):
        raise ValueError(f"{case_id}: mapping must be an object")
    mapping_file = str(case.get("mapping_file", "")).strip()
    if mapping_file:
        loaded_mapping = _load_package_object(
            package_root,
            mapping_file,
            label=f"{case_id}.mapping_file",
            required_type=dict,
        )
        mapping = {**mapping, **loaded_mapping}

    author_inputs = case.get("author_inputs", {})
    if author_inputs is None:
        author_inputs = {}
    if not isinstance(author_inputs, dict):
        raise ValueError(f"{case_id}: author_inputs must be an object")
    author_inputs_file = str(case.get("author_inputs_file", "")).strip()
    if author_inputs_file:
        loaded_author_inputs = _load_package_object(
            package_root,
            author_inputs_file,
            label=f"{case_id}.author_inputs_file",
            required_type=dict,
        )
        author_inputs = {**author_inputs, **loaded_author_inputs}

    expect = case.get("expect")
    expect_file = str(case.get("expect_file", "")).strip()
    if expect_file:
        loaded_expect = _load_package_object(
            package_root,
            expect_file,
            label=f"{case_id}.expect_file",
            required_type=dict,
        )
        expect = loaded_expect if expect is None else {**expect, **loaded_expect}

    resolved = dict(case)
    resolved["source_materials"] = resolved_source_materials
    resolved["mapping"] = mapping
    resolved["author_inputs"] = author_inputs
    if expect is not None:
        resolved["expect"] = expect

    for transient_key in (
        "source_material_files",
        "mapping_file",
        "author_inputs_file",
        "expect_file",
    ):
        resolved.pop(transient_key, None)
    return resolved


def _package_import_provenance(
    package_dir: Path,
    manifest_path: Path,
    *,
    source_provenance: dict[str, str] | None = None,
) -> dict[str, str]:
    if source_provenance is not None:
        return dict(source_provenance)
    return {
        "package_dir": _provenance_relative(package_dir, package_root=package_dir),
        "manifest_path": _provenance_relative(manifest_path, package_root=package_dir),
    }


def _validate_zip_member_path(member_name: str) -> PurePosixPath:
    candidate = PurePosixPath(member_name)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ValueError(f"Benchmark package archive contains an unsafe member path: {member_name}")
    return candidate


def _extract_benchmark_package_archive(archive_path: Path, extract_root: Path) -> tuple[Path, dict[str, str]]:
    if archive_path.suffix.lower() != ".zip":
        raise ValueError(
            f"Benchmark package archive must be a .zip file: {_relative(archive_path)}"
        )

    extract_root.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(archive_path) as archive:
            for info in archive.infolist():
                if info.filename.startswith("__MACOSX/"):
                    continue
                member_path = _validate_zip_member_path(info.filename)
                if info.is_dir():
                    (extract_root / Path(member_path)).mkdir(parents=True, exist_ok=True)
                    continue
                destination = extract_root / Path(member_path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    except BadZipFile as exc:
        raise ValueError(f"Invalid benchmark package archive: {_relative(archive_path)}") from exc

    manifest_paths = [
        path for path in extract_root.rglob(PACKAGE_MANIFEST_NAME)
        if "__MACOSX" not in path.parts
    ]
    if not manifest_paths:
        raise ValueError(
            f"Benchmark package archive does not contain {PACKAGE_MANIFEST_NAME}: {_relative(archive_path)}"
        )
    if len(manifest_paths) > 1:
        raise ValueError(
            f"Benchmark package archive contains multiple {PACKAGE_MANIFEST_NAME} files: {_relative(archive_path)}"
        )

    manifest_path = manifest_paths[0]
    package_root = manifest_path.parent
    try:
        package_root_rel = package_root.relative_to(extract_root)
    except ValueError:
        package_root_rel = Path(package_root.name)
    package_root_label = (
        Path(archive_path.stem)
        if str(package_root_rel) == "."
        else Path("archive_contents") / package_root_rel
    )

    return package_root, {
        "archive_path": _provenance_relative(archive_path),
        "package_dir": str(package_root_label),
        "manifest_path": str(package_root_label / PACKAGE_MANIFEST_NAME),
    }


def import_benchmark_package(
    package_dir: Path,
    *,
    bundle_id: str | None = None,
    output_dir: Path = BUNDLES_DIR,
    dry_run: bool = False,
    force: bool = False,
    source_provenance: dict[str, str] | None = None,
) -> dict[str, Any]:
    package_dir = package_dir.resolve()
    manifest_path = package_dir / PACKAGE_MANIFEST_NAME
    if not manifest_path.exists():
        raise ValueError(
            f"Benchmark package manifest not found at {manifest_path}. Expected {PACKAGE_MANIFEST_NAME}."
        )
    manifest = load_json(manifest_path)
    resolved_bundle_id = bundle_id or str(manifest.get("bundle_id", "")).strip()
    if not resolved_bundle_id:
        raise ValueError(
            "Benchmark package is missing bundle_id and no --bundle-id override was provided."
        )

    cases = manifest.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("Benchmark package manifest field 'cases' must be a list.")
    resolved_cases = [_resolve_package_case(package_dir, case) for case in cases]

    bundle_payload = {
        "bundle_id": resolved_bundle_id,
        "adapter_type": str(manifest.get("adapter_type", "paperwritingbench_style_bundle")),
        "benchmark_family": str(manifest.get("benchmark_family", "")),
        "reference_benchmark": str(manifest.get("reference_benchmark", "")),
        "description": str(manifest.get("description", "")),
        "notes": list(manifest.get("notes", [])),
        "import_source": _package_import_provenance(
            package_dir,
            manifest_path,
            source_provenance=source_provenance,
        ),
        "cases": resolved_cases,
    }

    output_path = output_dir / f"{resolved_bundle_id}.json"
    _adapt_benchmark_bundle_payload(
        bundle_payload,
        bundle_id=resolved_bundle_id,
        suite_path=_relative(output_path),
    )
    if output_path.exists() and not dry_run and not force:
        raise ValueError(
            f"Refusing to overwrite existing benchmark bundle: {_relative(output_path)}. "
            "Use force=True or pass --force to replace it."
        )
    if not dry_run:
        write_json(output_path, bundle_payload)

    import_source = dict(bundle_payload["import_source"])
    return {
        "bundle": bundle_payload,
        "bundle_id": resolved_bundle_id,
        "dry_run": dry_run,
        "package_manifest": import_source.get("manifest_path", _relative(manifest_path)),
        "package_archive": import_source.get("archive_path", ""),
        "output_path": _relative(output_path),
        "case_count": len(resolved_cases),
    }


def import_benchmark_package_archive(
    package_archive: Path,
    *,
    bundle_id: str | None = None,
    output_dir: Path = BUNDLES_DIR,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    package_archive = package_archive.resolve()
    if not package_archive.exists():
        raise ValueError(f"Benchmark package archive not found: {_relative(package_archive)}")
    if package_archive.is_dir():
        raise ValueError(f"Benchmark package archive must be a file, not a directory: {_relative(package_archive)}")

    with TemporaryDirectory() as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        package_root, provenance = _extract_benchmark_package_archive(
            package_archive,
            tmp_dir / "archive_contents",
        )
        return import_benchmark_package(
            package_root,
            bundle_id=bundle_id,
            output_dir=output_dir,
            dry_run=dry_run,
            force=force,
            source_provenance=provenance,
        )


def package_effective_sha256(
    package_dir: Path,
    *,
    bundle_id: str | None = None,
) -> str:
    result = import_benchmark_package(
        package_dir,
        bundle_id=bundle_id,
        dry_run=True,
    )
    return _canonical_sha256(_bundle_fingerprint_payload(result["bundle"]))


def package_archive_effective_sha256(
    package_archive: Path,
    *,
    bundle_id: str | None = None,
) -> str:
    result = import_benchmark_package_archive(
        package_archive,
        bundle_id=bundle_id,
        dry_run=True,
    )
    return _canonical_sha256(_bundle_fingerprint_payload(result["bundle"]))


def _make_check(label: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "label": label,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _make_contains_check(label: str, actual: str, expected_fragment: str) -> dict[str, Any]:
    return {
        "label": label,
        "passed": expected_fragment in actual,
        "actual": actual,
        "expected_contains": expected_fragment,
    }


def _summarize_case(case: dict[str, Any], checks: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    passed_check_count = sum(1 for check in checks if check["passed"])
    check_count = len(checks)
    score = 100.0 if check_count == 0 else round((passed_check_count / check_count) * 100.0, 2)
    summary = {
        "case_id": str(case.get("case_id", "")),
        "kind": str(case.get("kind", "")),
        "description": str(case.get("description", "")),
        "dimension": str(case.get("dimension", "")),
        "weight": float(case.get("weight", 1.0)),
        "status": "pass" if passed_check_count == check_count else "fail",
        "score": score,
        "check_count": check_count,
        "passed_check_count": passed_check_count,
        "checks": checks,
        "metrics": metrics,
    }
    if "source_materials" in case:
        summary["source_materials"] = case["source_materials"]
    if "adapter_type" in case:
        summary["adapter_type"] = case["adapter_type"]
    return summary


def _string_dict(values: Any, label: str) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError(f"{label} must be an object")
    normalized: dict[str, str] = {}
    for key, value in values.items():
        if not isinstance(value, str):
            raise ValueError(f"{label}.{key} must be a string")
        normalized[str(key)] = value
    return normalized


def _derive_topic_from_source_materials(source_materials: dict[str, Any]) -> str:
    idea_summary = source_materials.get("idea_summary", {})
    if isinstance(idea_summary, str):
        return idea_summary.strip()
    if isinstance(idea_summary, dict):
        for key in ("title", "topic", "objective"):
            value = idea_summary.get(key, "")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _adapt_author_inputs(bundle_case: dict[str, Any]) -> dict[str, Any]:
    source_materials = bundle_case.get("source_materials", {})
    if source_materials is None:
        source_materials = {}
    if not isinstance(source_materials, dict):
        raise ValueError(f"{bundle_case.get('case_id', 'case')}: source_materials must be an object")

    explicit_author_inputs = bundle_case.get("author_inputs", {})
    if explicit_author_inputs is None:
        explicit_author_inputs = {}
    if not isinstance(explicit_author_inputs, dict):
        raise ValueError(f"{bundle_case.get('case_id', 'case')}: author_inputs must be an object")

    mapping = bundle_case.get("mapping", {})
    if mapping is None:
        mapping = {}
    if not isinstance(mapping, dict):
        raise ValueError(f"{bundle_case.get('case_id', 'case')}: mapping must be an object")

    topic = ""
    explicit_topic = explicit_author_inputs.get("topic", "")
    if isinstance(explicit_topic, str) and explicit_topic.strip():
        topic = explicit_topic.strip()
    else:
        topic = _derive_topic_from_source_materials(source_materials)
    if not topic:
        raise ValueError(
            f"{bundle_case.get('case_id', 'case')}: no topic could be derived from author_inputs.topic or source_materials.idea_summary"
        )

    section_notes = _string_dict(explicit_author_inputs.get("section_notes", {}), "author_inputs.section_notes")
    section_notes.update(_string_dict(mapping.get("section_notes", {}), "mapping.section_notes"))

    claim_notes = _string_dict(explicit_author_inputs.get("claim_notes", {}), "author_inputs.claim_notes")
    claim_notes.update(_string_dict(mapping.get("claim_notes", {}), "mapping.claim_notes"))

    return {
        "topic": topic,
        "section_notes": section_notes,
        "claim_notes": claim_notes,
    }


def _normalize_direct_author_inputs(bundle_case: dict[str, Any]) -> dict[str, Any]:
    explicit_author_inputs = bundle_case.get("author_inputs", {})
    if explicit_author_inputs is None:
        explicit_author_inputs = {}
    if not isinstance(explicit_author_inputs, dict):
        raise ValueError(f"{bundle_case.get('case_id', 'case')}: author_inputs must be an object")

    topic = str(explicit_author_inputs.get("topic", "")).strip()
    if not topic:
        raise ValueError(
            f"{bundle_case.get('case_id', 'case')}: author_inputs.topic is required for generic_author_input_bundle"
        )

    return {
        "topic": topic,
        "section_notes": _string_dict(
            explicit_author_inputs.get("section_notes", {}),
            "author_inputs.section_notes",
        ),
        "claim_notes": _string_dict(
            explicit_author_inputs.get("claim_notes", {}),
            "author_inputs.claim_notes",
        ),
    }


def _adapt_benchmark_bundle_payload(
    bundle: dict[str, Any],
    *,
    bundle_id: str,
    suite_path: str,
) -> dict[str, Any]:
    adapter_type = str(bundle.get("adapter_type", ""))
    if adapter_type not in {"paperwritingbench_style_bundle", "generic_author_input_bundle"}:
        raise ValueError(
            f"Unsupported benchmark bundle adapter_type '{adapter_type}' for bundle '{bundle_id}'"
        )

    adapted_cases: list[dict[str, Any]] = []
    for raw_case in bundle.get("cases", []):
        if not isinstance(raw_case, dict):
            raise ValueError(f"{bundle_id}: every case must be an object")
        case_id = str(raw_case.get("case_id", ""))
        if not case_id:
            raise ValueError(f"{bundle_id}: a case is missing case_id")
        raw_kind = str(raw_case.get("kind", ""))
        adapted_case = {
            "case_id": case_id,
            "description": str(raw_case.get("description", "")),
            "dimension": str(raw_case.get("dimension", "")),
            "weight": float(raw_case.get("weight", 1.0)),
            "source_materials": raw_case.get("source_materials", {}),
            "adapter_type": adapter_type,
        }

        if adapter_type == "paperwritingbench_style_bundle":
            if raw_kind == "paperwritingbench_style_authoring":
                adapted_case["kind"] = "author_input_propagation"
                adapted_case["author_inputs"] = _adapt_author_inputs(raw_case)
                adapted_case["expect"] = raw_case.get("expect", {})
            elif raw_kind == "paperwritingbench_style_error":
                adapted_case["kind"] = "author_input_error"
                adapted_case["author_inputs"] = _adapt_author_inputs(raw_case)
                adapted_case["expect_error_contains"] = str(raw_case.get("expect_error_contains", ""))
            elif raw_kind in {"repo_readiness", "author_input_propagation", "author_input_error"}:
                adapted_case.update(raw_case)
            else:
                raise ValueError(f"{bundle_id}:{case_id}: unsupported case kind '{raw_kind}'")
        elif adapter_type == "generic_author_input_bundle":
            if raw_kind == "generic_author_input_authoring":
                adapted_case["kind"] = "author_input_propagation"
                adapted_case["author_inputs"] = _normalize_direct_author_inputs(raw_case)
                adapted_case["expect"] = raw_case.get("expect", {})
            elif raw_kind == "generic_author_input_error":
                adapted_case["kind"] = "author_input_error"
                adapted_case["author_inputs"] = _normalize_direct_author_inputs(raw_case)
                adapted_case["expect_error_contains"] = str(raw_case.get("expect_error_contains", ""))
            elif raw_kind in {"repo_readiness", "author_input_propagation", "author_input_error"}:
                adapted_case.update(raw_case)
            else:
                raise ValueError(f"{bundle_id}:{case_id}: unsupported case kind '{raw_kind}'")
        else:
            adapted_case.update(raw_case)
        adapted_cases.append(adapted_case)

    return {
        "suite_id": str(bundle.get("bundle_id", bundle_id)),
        "benchmark_family": str(bundle.get("benchmark_family", "")),
        "reference_benchmark": str(bundle.get("reference_benchmark", "")),
        "description": str(bundle.get("description", "")),
        "notes": list(bundle.get("notes", [])),
        "adapter_type": adapter_type,
        "_suite_path": suite_path,
        "_definition_type": "bundle",
        "cases": adapted_cases,
    }


def adapt_benchmark_bundle(bundle_id: str = DEFAULT_BUNDLE_ID) -> dict[str, Any]:
    bundle = load_benchmark_bundle(bundle_id)
    return _adapt_benchmark_bundle_payload(
        bundle,
        bundle_id=bundle_id,
        suite_path=bundle["_bundle_path"],
    )


def load_benchmark_definition(
    suite_id: str | None = DEFAULT_SUITE_ID,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    if bundle_id:
        return adapt_benchmark_bundle(bundle_id)
    return load_benchmark_suite(suite_id or DEFAULT_SUITE_ID)


def _build_harness_benchmark_report_from_definition(
    suite: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    cases = [_run_case(case) for case in suite.get("cases", [])]
    total_weight = sum(case.get("weight", 1.0) for case in cases) or 1.0
    overall_score = round(
        sum(case["score"] * float(case.get("weight", 1.0)) for case in cases) / total_weight,
        2,
    )
    failed_cases = [case["case_id"] for case in cases if case["status"] != "pass"]
    package_paths = sorted(
        dict.fromkeys(
            [
                suite["_suite_path"],
                "scripts/harness_benchmark.py",
                "scripts/check_harness_benchmark.py",
                "tests/manuscript/test_harness_benchmark.py",
            ]
        )
    )
    return {
        "suite_id": suite["suite_id"],
        "definition_type": str(suite.get("_definition_type", "suite")),
        "adapter_type": str(suite.get("adapter_type", "")),
        "benchmark_family": str(suite.get("benchmark_family", "")),
        "reference_benchmark": str(suite.get("reference_benchmark", "")),
        "description": str(suite.get("description", "")),
        "notes": list(suite.get("notes", [])),
        "suite_path": suite["_suite_path"],
        "case_count": len(cases),
        "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
        "failed_case_count": len(failed_cases),
        "overall_score": overall_score,
        "readiness": "ready" if not failed_cases else "blocked",
        "failed_case_ids": failed_cases,
        "cases": cases,
        "package_paths": package_paths,
        "repo_root": _relative(repo_root),
    }


def _build_harness_benchmark_report_from_import_result(
    result: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    suite = _adapt_benchmark_bundle_payload(
        result["bundle"],
        bundle_id=result["bundle_id"],
        suite_path=result.get("package_archive") or result.get("package_manifest") or result["output_path"],
    )
    return _build_harness_benchmark_report_from_definition(suite, repo_root=repo_root)


def build_harness_benchmark_report_from_package(
    package_dir: Path,
    *,
    bundle_id: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    result = import_benchmark_package(
        package_dir,
        bundle_id=bundle_id,
        dry_run=True,
    )
    return _build_harness_benchmark_report_from_import_result(result, repo_root=repo_root)


def build_harness_benchmark_report_from_package_archive(
    package_archive: Path,
    *,
    bundle_id: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    result = import_benchmark_package_archive(
        package_archive,
        bundle_id=bundle_id,
        dry_run=True,
    )
    return _build_harness_benchmark_report_from_import_result(result, repo_root=repo_root)


def write_harness_benchmark_report_outputs_to_dir(
    report: dict[str, Any],
    output_dir: Path,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_json_path = output_dir / "report.json"
    report_md_path = output_dir / "report.md"
    manifest_path = output_dir / "manifest.json"
    generation_id = ""
    if metadata is not None:
        generation_id = str(metadata.get("generation_id", "")).strip()

    report_payload = dict(report)
    if generation_id:
        report_payload["run_generation_id"] = generation_id
    manifest_payload = build_harness_benchmark_manifest(report_payload)

    _atomic_write_json(report_json_path, report_payload)
    _atomic_write_text(report_md_path, render_harness_benchmark_markdown(report_payload))
    _atomic_write_json(manifest_path, manifest_payload)

    writes = {
        "report_json": _relative(report_json_path),
        "report_md": _relative(report_md_path),
        "manifest": _relative(manifest_path),
    }
    if metadata is not None:
        metadata_path = output_dir / "run_metadata.json"
        _atomic_write_json(metadata_path, dict(metadata))
        writes["run_metadata"] = _relative(metadata_path)
    return writes


def _invalid_public_benchmark_run_summary(
    run_dir: Path,
    *,
    errors: list[str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = metadata or {}
    environment = metadata.get("environment", {}) if isinstance(metadata.get("environment", {}), dict) else {}
    return {
        "run_id": str(metadata.get("run_id") or run_dir.name),
        "created_at_utc": str(metadata.get("created_at_utc", "")),
        "source_type": str(metadata.get("source_type", "")),
        "source_path": str(metadata.get("source_path", "")),
        "source_sha256": str(metadata.get("source_sha256", "")),
        "suite_id": str(metadata.get("suite_id", "")),
        "python_version": str(environment.get("python_version", "")),
        "python_implementation": str(environment.get("python_implementation", "")),
        "git_commit": str(environment.get("git_commit", "")),
        "git_branch": str(environment.get("git_branch", "")),
        "git_dirty": environment.get("git_dirty"),
        "readiness": "invalid",
        "overall_score": 0.0,
        "case_count": 0,
        "passed_case_count": 0,
        "failed_case_count": 0,
        "run_dir": _relative(run_dir),
        "errors": errors,
    }


def _public_run_generation_ids(
    metadata: dict[str, Any],
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> dict[str, str]:
    return {
        "metadata": str(metadata.get("generation_id", "")).strip(),
        "report": str(report.get("run_generation_id", "")).strip(),
        "manifest": str(manifest.get("run_generation_id", "")).strip(),
    }


def _public_run_generation_error(
    metadata: dict[str, Any],
    report: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    generation_ids = _public_run_generation_ids(metadata, report, manifest)
    present_generation_ids = {key: value for key, value in generation_ids.items() if value}
    if not present_generation_ids:
        return ""
    if len(present_generation_ids) != len(generation_ids):
        details = ", ".join(
            f"{key}={value or 'missing'}" for key, value in generation_ids.items()
        )
        return f"incomplete run generation markers ({details})"
    if len(set(present_generation_ids.values())) != 1:
        details = ", ".join(f"{key}={value}" for key, value in generation_ids.items())
        return f"inconsistent run generation markers ({details})"
    return ""


def _compare_run_scalar(
    issues: list[str],
    *,
    label: str,
    left: Any,
    right: Any,
) -> None:
    if left == right:
        return
    try:
        if float(left) == float(right):
            return
    except (TypeError, ValueError):
        pass
    issues.append(f"`{label}` mismatch: expected `{left}` but found `{right}`")


def validate_public_benchmark_run(
    run_dir: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    if not run_dir.exists():
        raise ValueError(f"Public benchmark run directory not found: {_relative(run_dir, repo_root)}")
    if not run_dir.is_dir():
        raise ValueError(f"Public benchmark run path must be a directory: {_relative(run_dir, repo_root)}")

    issues: list[str] = []
    warnings: list[str] = []
    artifacts = {
        "report_json": run_dir / "report.json",
        "report_md": run_dir / "report.md",
        "manifest_json": run_dir / "manifest.json",
        "run_metadata_json": run_dir / "run_metadata.json",
    }
    for key, artifact_path in artifacts.items():
        if not artifact_path.exists():
            issues.append(f"missing `{key}` at {_relative(artifact_path, repo_root)}")

    summary = summarize_public_benchmark_run(run_dir)
    run_id = str(summary.get("run_id") or run_dir.name)
    readiness = str(summary.get("readiness", "invalid"))
    for error in summary.get("errors", []):
        issues.append(f"summary: {error}")

    metadata: dict[str, Any] | None = None
    report: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    report_markdown: str | None = None

    if artifacts["run_metadata_json"].exists():
        try:
            metadata = load_json(artifacts["run_metadata_json"])
        except Exception as exc:
            issues.append(f"invalid run_metadata.json: {exc}")
    if artifacts["report_json"].exists():
        try:
            report = load_json(artifacts["report_json"])
        except Exception as exc:
            issues.append(f"invalid report.json: {exc}")
    if artifacts["manifest_json"].exists():
        try:
            manifest = load_json(artifacts["manifest_json"])
        except Exception as exc:
            issues.append(f"invalid manifest.json: {exc}")
    if artifacts["report_md"].exists():
        report_markdown = artifacts["report_md"].read_text(encoding="utf-8")

    if metadata is not None:
        metadata_run_id = str(metadata.get("run_id", "")).strip()
        if not metadata_run_id:
            issues.append("`run_metadata.run_id` is required")
        elif metadata_run_id != run_dir.name:
            issues.append("`run_metadata.run_id` must match the run directory name")
        source_type = str(metadata.get("source_type", "")).strip()
        if source_type not in {"package_dir", "package_archive"}:
            issues.append("`run_metadata.source_type` must be `package_dir` or `package_archive`")
        if not str(metadata.get("source_path", "")).strip():
            issues.append("`run_metadata.source_path` is required")
        if not str(metadata.get("source_sha256", "")).strip():
            issues.append("`run_metadata.source_sha256` is required")
        environment = metadata.get("environment", {})
        if not isinstance(environment, dict):
            issues.append("`run_metadata.environment` must be an object")
            environment = {}
        for key in PUBLIC_RUN_ENVIRONMENT_KEYS:
            if not str(environment.get(key, "")).strip():
                issues.append(f"`run_metadata.environment.{key}` is required")

    if metadata is not None and report is not None:
        _compare_run_scalar(
            issues,
            label="run_metadata.suite_id",
            left=report.get("suite_id", ""),
            right=metadata.get("suite_id", ""),
        )
        _compare_run_scalar(
            issues,
            label="run_metadata.readiness",
            left=report.get("readiness", ""),
            right=metadata.get("readiness", ""),
        )
        _compare_run_scalar(
            issues,
            label="run_metadata.overall_score",
            left=report.get("overall_score", 0.0),
            right=metadata.get("overall_score", 0.0),
        )
        _compare_run_scalar(
            issues,
            label="run_metadata.case_count",
            left=report.get("case_count", 0),
            right=metadata.get("case_count", 0),
        )

    if report is not None and manifest is not None:
        try:
            expected_manifest = build_harness_benchmark_manifest(report)
        except KeyError as exc:
            issues.append(f"`report.json` is missing required key `{exc.args[0]}`")
        else:
            for key, expected_value in expected_manifest.items():
                if manifest.get(key) != expected_value:
                    issues.append(f"`manifest.{key}` does not match `report.{key}`")
            for key in manifest:
                if key not in expected_manifest:
                    warnings.append(f"`manifest.{key}` is not part of the canonical run manifest surface")

    if report is not None and report_markdown is not None:
        expected_snippets = [
            "# Agent Evaluation Benchmark",
            f"- suite_id: `{report.get('suite_id', '')}`",
            f"- readiness: `{report.get('readiness', '')}`",
            f"- overall_score: `{report.get('overall_score', '')}`",
            f"- case_count: `{report.get('case_count', '')}`",
        ]
        for snippet in expected_snippets:
            if snippet not in report_markdown:
                issues.append(f"`report.md` is missing expected content: {snippet}")

    return {
        "run_dir": _relative(run_dir, repo_root),
        "run_id": run_id,
        "readiness": readiness,
        "suite_id": str(summary.get("suite_id", "")),
        "overall_score": float(summary.get("overall_score", 0.0) or 0.0),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "artifacts": {key: _relative(path, repo_root) for key, path in artifacts.items()},
    }


def summarize_public_benchmark_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    metadata_path = run_dir / "run_metadata.json"
    report_path = run_dir / "report.json"
    manifest_path = run_dir / "manifest.json"
    last_errors: list[str] = []
    last_metadata: dict[str, Any] | None = None

    for attempt in range(3):
        errors: list[str] = []
        metadata: dict[str, Any] | None = None
        report: dict[str, Any] | None = None
        manifest: dict[str, Any] | None = None

        if not metadata_path.exists():
            errors.append("missing run_metadata.json")
        else:
            try:
                metadata = load_json(metadata_path)
            except Exception as exc:
                errors.append(f"invalid run_metadata.json: {exc}")

        if not report_path.exists():
            errors.append("missing report.json")
        else:
            try:
                report = load_json(report_path)
            except Exception as exc:
                errors.append(f"invalid report.json: {exc}")

        if not manifest_path.exists():
            errors.append("missing manifest.json")
        else:
            try:
                manifest = load_json(manifest_path)
            except Exception as exc:
                errors.append(f"invalid manifest.json: {exc}")

        if not errors and metadata is not None and report is not None and manifest is not None:
            generation_error = _public_run_generation_error(metadata, report, manifest)
            if generation_error:
                errors.append(generation_error)

        if not errors and metadata is not None and report is not None:
            environment = (
                metadata.get("environment", {})
                if isinstance(metadata.get("environment", {}), dict)
                else {}
            )
            return {
                "run_id": str(metadata.get("run_id") or run_dir.name),
                "created_at_utc": str(metadata.get("created_at_utc", "")),
                "source_type": str(metadata.get("source_type", "")),
                "source_path": str(metadata.get("source_path", "")),
                "source_sha256": str(metadata.get("source_sha256", "")),
                "suite_id": str(report.get("suite_id", metadata.get("suite_id", ""))),
                "python_version": str(environment.get("python_version", "")),
                "python_implementation": str(environment.get("python_implementation", "")),
                "git_commit": str(environment.get("git_commit", "")),
                "git_branch": str(environment.get("git_branch", "")),
                "git_dirty": environment.get("git_dirty"),
                "readiness": str(report.get("readiness", metadata.get("readiness", "invalid"))),
                "overall_score": float(report.get("overall_score", metadata.get("overall_score", 0.0)) or 0.0),
                "case_count": int(report.get("case_count", metadata.get("case_count", 0)) or 0),
                "passed_case_count": int(report.get("passed_case_count", 0) or 0),
                "failed_case_count": int(report.get("failed_case_count", 0) or 0),
                "run_dir": _relative(run_dir),
                "errors": [],
            }

        last_errors = errors
        last_metadata = metadata
        if attempt < 2:
            time.sleep(0.01)

    return _invalid_public_benchmark_run_summary(run_dir, errors=last_errors, metadata=last_metadata)


def build_public_benchmark_run_record(
    run_dir: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    summary = summarize_public_benchmark_run(run_dir)
    validation = validate_public_benchmark_run(run_dir, repo_root=repo_root)
    readiness = str(summary.get("readiness", "invalid"))
    if not validation.get("passed", False):
        readiness = "invalid"
    return {
        "run_id": str(summary.get("run_id", validation.get("run_id", run_dir.name))),
        "created_at_utc": str(summary.get("created_at_utc", "")),
        "source_type": str(summary.get("source_type", "")),
        "source_path": str(summary.get("source_path", "")),
        "source_sha256": str(summary.get("source_sha256", "")),
        "suite_id": str(summary.get("suite_id", validation.get("suite_id", ""))),
        "python_version": str(summary.get("python_version", "")),
        "python_implementation": str(summary.get("python_implementation", "")),
        "git_commit": str(summary.get("git_commit", "")),
        "git_branch": str(summary.get("git_branch", "")),
        "git_dirty": summary.get("git_dirty"),
        "readiness": readiness,
        "overall_score": float(summary.get("overall_score", 0.0) or 0.0),
        "case_count": int(summary.get("case_count", 0) or 0),
        "passed_case_count": int(summary.get("passed_case_count", 0) or 0),
        "failed_case_count": int(summary.get("failed_case_count", 0) or 0),
        "run_dir": str(validation.get("run_dir", _relative(run_dir, repo_root))),
        "passed": bool(validation.get("passed", False)),
        "errors": list(validation.get("issues", [])),
        "warnings": list(validation.get("warnings", [])),
        "artifacts": dict(validation.get("artifacts", {})),
    }


def build_public_benchmark_runs_report(
    runs_dir: Path = PUBLIC_RUNS_DIR,
) -> dict[str, Any]:
    runs_dir = runs_dir.resolve()
    if not runs_dir.exists():
        raise ValueError(f"Public benchmark runs directory not found: {_relative(runs_dir)}")
    if not runs_dir.is_dir():
        raise ValueError(f"Public benchmark runs path must be a directory: {_relative(runs_dir)}")

    run_dirs = sorted(path for path in runs_dir.iterdir() if path.is_dir())
    if not run_dirs:
        raise ValueError(f"No public benchmark runs found in {_relative(runs_dir)}")

    runs = [build_public_benchmark_run_record(run_dir) for run_dir in run_dirs]
    runs.sort(key=lambda run: (run.get("created_at_utc", ""), run.get("run_id", "")), reverse=True)

    ready_runs = [run for run in runs if run["readiness"] == "ready"]
    blocked_runs = [run for run in runs if run["readiness"] == "blocked"]
    invalid_runs = [run for run in runs if run["readiness"] == "invalid"]
    valid_runs = [run for run in runs if run["readiness"] != "invalid"]
    total_case_count = sum(run["case_count"] for run in valid_runs)
    weighting_denominator = total_case_count or len(valid_runs) or 1
    overall_score = round(
        sum(run["overall_score"] * max(run["case_count"], 1) for run in valid_runs) / weighting_denominator,
        2,
    )
    best_run = max(
        valid_runs,
        key=lambda run: (run["overall_score"], run["case_count"], run.get("created_at_utc", ""), run["run_id"]),
        default=None,
    )
    latest_run = runs[0] if runs else None
    latest_ready_run = next((run for run in runs if run["readiness"] == "ready"), None)

    source_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for run in runs:
        source_type = str(run.get("source_type", "")).strip()
        source_fingerprint = str(run.get("source_sha256") or run.get("source_path") or "").strip()
        if not source_type or not source_fingerprint:
            continue
        source_groups.setdefault((source_type, source_fingerprint), []).append(run)
    duplicate_sources = [
        {
            "source_type": source_type,
            "source_fingerprint": source_fingerprint,
            "run_ids": [group_run["run_id"] for group_run in group_runs],
            "run_count": len(group_runs),
        }
        for (source_type, source_fingerprint), group_runs in source_groups.items()
        if len(group_runs) > 1
    ]
    duplicate_sources.sort(key=lambda item: (item["source_type"], item["source_fingerprint"]))

    return {
        "runs_dir": _relative(runs_dir),
        "readiness": "ready" if len(ready_runs) == len(runs) else "blocked",
        "run_count": len(runs),
        "ready_run_count": len(ready_runs),
        "blocked_run_count": len(blocked_runs),
        "invalid_run_count": len(invalid_runs),
        "total_case_count": total_case_count,
        "overall_score": overall_score,
        "latest_run_id": str(latest_run["run_id"]) if latest_run else "",
        "latest_ready_run_id": str(latest_ready_run["run_id"]) if latest_ready_run else "",
        "best_run_id": str(best_run["run_id"]) if best_run else "",
        "duplicate_source_count": len(duplicate_sources),
        "duplicate_sources": duplicate_sources,
        "runs": runs,
    }


def build_public_benchmark_runs_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "runs_dir": report["runs_dir"],
        "readiness": report["readiness"],
        "run_count": report["run_count"],
        "ready_run_count": report["ready_run_count"],
        "blocked_run_count": report["blocked_run_count"],
        "invalid_run_count": report["invalid_run_count"],
        "total_case_count": report["total_case_count"],
        "overall_score": report["overall_score"],
        "latest_run_id": report["latest_run_id"],
        "latest_ready_run_id": report["latest_ready_run_id"],
        "best_run_id": report["best_run_id"],
        "duplicate_source_count": report["duplicate_source_count"],
        "duplicate_sources": report["duplicate_sources"],
        "runs": report["runs"],
    }


def render_public_benchmark_runs_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Public Benchmark Runs",
        "",
        f"- runs_dir: `{report['runs_dir']}`",
        f"- readiness: `{report['readiness']}`",
        f"- run_count: `{report['run_count']}`",
        f"- ready_run_count: `{report['ready_run_count']}`",
        f"- blocked_run_count: `{report['blocked_run_count']}`",
        f"- invalid_run_count: `{report['invalid_run_count']}`",
        f"- total_case_count: `{report['total_case_count']}`",
        f"- overall_score: `{report['overall_score']}`",
        f"- latest_run_id: `{report['latest_run_id'] or 'none'}`",
        f"- latest_ready_run_id: `{report['latest_ready_run_id'] or 'none'}`",
        f"- best_run_id: `{report['best_run_id'] or 'none'}`",
        f"- duplicate_source_count: `{report['duplicate_source_count']}`",
        "",
    ]
    if report.get("duplicate_sources"):
        lines.extend(["## Duplicate Sources", ""])
        for duplicate_source in report["duplicate_sources"]:
            lines.extend(
                [
                    f"### {duplicate_source['source_type']}",
                    "",
                    f"- source_fingerprint: `{duplicate_source['source_fingerprint']}`",
                    f"- run_count: `{duplicate_source['run_count']}`",
                    "",
                    "Runs:",
                ]
            )
            for run_id in duplicate_source["run_ids"]:
                lines.append(f"- `{run_id}`")
            lines.append("")
    lines.extend([
        "## Runs",
        "",
    ])
    for run in report.get("runs", []):
        lines.extend(
            [
                f"### {run['run_id']}",
                "",
                f"- readiness: `{run['readiness']}`",
                f"- suite_id: `{run['suite_id'] or 'unknown'}`",
                f"- overall_score: `{run['overall_score']}`",
                f"- case_count: `{run['case_count']}`",
                f"- source_type: `{run['source_type'] or 'unknown'}`",
                f"- source_path: `{run['source_path'] or 'unknown'}`",
                f"- created_at_utc: `{run['created_at_utc'] or 'unknown'}`",
                f"- python_version: `{run['python_version'] or 'unknown'}`",
                f"- python_implementation: `{run['python_implementation'] or 'unknown'}`",
                f"- git_commit: `{run['git_commit'] or 'unknown'}`",
                f"- git_branch: `{run['git_branch'] or 'unknown'}`",
                f"- git_dirty: `{run['git_dirty']}`",
                f"- run_dir: `{run['run_dir']}`",
                "",
            ]
        )
        if run.get("errors"):
            lines.append("Errors:")
            for error in run["errors"]:
                lines.append(f"- {error}")
            lines.append("")
        if run.get("warnings"):
            lines.append("Warnings:")
            for warning in run["warnings"]:
                lines.append(f"- {warning}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_public_benchmark_runs_outputs(
    runs_dir: Path = PUBLIC_RUNS_DIR,
    *,
    report: dict[str, Any] | None = None,
) -> dict[str, str]:
    report = report or build_public_benchmark_runs_report(runs_dir)
    report_json_path = runs_dir / "public_benchmark_runs_summary.json"
    report_md_path = runs_dir / "public_benchmark_runs_summary.md"
    manifest_path = runs_dir / "public_benchmark_runs_summary_manifest.json"

    _atomic_write_json(report_json_path, report)
    _atomic_write_text(report_md_path, render_public_benchmark_runs_markdown(report))
    _atomic_write_json(manifest_path, build_public_benchmark_runs_manifest(report))

    return {
        "report_json": _relative(report_json_path),
        "report_md": _relative(report_md_path),
        "manifest": _relative(manifest_path),
    }


def list_benchmark_definition_refs(
    *,
    include_suites: bool = True,
    include_bundles: bool = True,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if include_suites:
        refs.extend({"definition_type": "suite", "definition_id": suite_id} for suite_id in list_benchmark_suites())
    if include_bundles:
        refs.extend(
            {"definition_type": "bundle", "definition_id": bundle_id}
            for bundle_id in list_benchmark_bundles()
        )
    return refs


def _baseline_metrics(selected_venues: list[str] | None = None) -> dict[str, Any]:
    packets = build_claim_packets()
    coverage = build_claim_coverage(packets)
    briefs = build_section_briefs()
    drafts = build_section_drafts()
    reference_report = build_reference_report()
    review_evidence = build_evidence_report()
    review_validation = validate_review_artifacts()
    pre_submission = build_pre_submission_audit(REPO_ROOT, selected_venues=selected_venues)
    return {
        "claim_count": packets["claim_count"],
        "claim_coverage_status": coverage["overall_status"],
        "section_briefs_status": briefs["overall_status"],
        "section_drafts_status": drafts["overall_status"],
        "reference_integrity_status": reference_report["readiness"],
        "review_evidence_status": review_evidence["readiness"],
        "review_validation_status": review_validation["overall_status"],
        "pre_submission_audit_status": pre_submission["readiness"],
        "submission_gate_status": pre_submission["submission_gate"]["status"],
        "bibliography_scope_gate_status": pre_submission["bibliography_scope_gate"]["status"],
    }


def _run_repo_readiness_case(case: dict[str, Any]) -> dict[str, Any]:
    metrics = _baseline_metrics(case.get("selected_venues"))
    expected = case.get("expect", {})
    checks: list[dict[str, Any]] = []
    for key, expected_value in expected.items():
        checks.append(_make_check(key, metrics.get(key), expected_value))
    return _summarize_case(case, checks, metrics)


@contextmanager
def _override_author_inputs(author_inputs: dict[str, Any]) -> Iterator[None]:
    with TemporaryDirectory() as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        author_inputs_path = tmp_dir / "author_content_inputs.json"
        write_json(author_inputs_path, author_inputs)

        claim_packets_path = tmp_dir / "claim_packets.json"
        section_briefs_path = tmp_dir / "section_briefs.json"

        original_values = [
            (manuscript_claims, "AUTHOR_CONTENT_INPUTS_PATH", manuscript_claims.AUTHOR_CONTENT_INPUTS_PATH),
            (manuscript_section_briefs, "AUTHOR_CONTENT_INPUTS_PATH", manuscript_section_briefs.AUTHOR_CONTENT_INPUTS_PATH),
            (manuscript_section_briefs, "CLAIM_PACKETS_PATH", manuscript_section_briefs.CLAIM_PACKETS_PATH),
            (manuscript_section_drafts, "CLAIM_PACKETS_PATH", manuscript_section_drafts.CLAIM_PACKETS_PATH),
            (manuscript_section_drafts, "SECTION_BRIEFS_JSON_PATH", manuscript_section_drafts.SECTION_BRIEFS_JSON_PATH),
        ]

        manuscript_claims.AUTHOR_CONTENT_INPUTS_PATH = author_inputs_path
        manuscript_section_briefs.AUTHOR_CONTENT_INPUTS_PATH = author_inputs_path
        manuscript_section_briefs.CLAIM_PACKETS_PATH = claim_packets_path
        manuscript_section_drafts.CLAIM_PACKETS_PATH = claim_packets_path
        manuscript_section_drafts.SECTION_BRIEFS_JSON_PATH = section_briefs_path
        try:
            yield
        finally:
            for module, attribute, value in original_values:
                setattr(module, attribute, value)


def _find_section(sections: list[dict[str, Any]], section_id: str) -> dict[str, Any]:
    return next(section for section in sections if str(section.get("section_id")) == section_id)


def _find_results_subsection(section: dict[str, Any], claim_id: str) -> dict[str, Any]:
    return next(item for item in section.get("subsection_plan", []) if str(item.get("claim_id")) == claim_id)


def _run_author_input_propagation_case(case: dict[str, Any]) -> dict[str, Any]:
    author_inputs = case.get("author_inputs", {})
    expected = case.get("expect", {})
    results_section_id = str(expected.get("section_note_section", "results"))
    claim_note_claim_id = str(expected.get("claim_note_claim_id", ""))

    with _override_author_inputs(author_inputs):
        packets = build_claim_packets()
        coverage = build_claim_coverage(packets)
        briefs = build_section_briefs()
        drafts = build_section_drafts()

    packet_lookup = {str(packet.get("claim_id")): packet for packet in packets.get("claims", [])}
    results_brief = _find_section(briefs.get("sections", []), results_section_id)
    results_draft = _find_section(drafts.get("sections", []), results_section_id)
    subsection = _find_results_subsection(results_draft, claim_note_claim_id)

    metrics = {
        "topic": str(packets.get("author_inputs", {}).get("topic", "")),
        "claim_coverage_status": coverage["overall_status"],
        "section_briefs_status": briefs["overall_status"],
        "section_drafts_status": drafts["overall_status"],
        "section_note": str(results_brief.get("author_input", {}).get("section_note", "")),
        "claim_packet_note": str(packet_lookup.get(claim_note_claim_id, {}).get("author_input", {}).get("claim_note", "")),
        "draft_subsection_note": str(subsection.get("author_note", "")),
    }

    checks = [
        _make_check("topic", metrics["topic"], str(expected.get("topic", ""))),
        _make_check("claim_coverage_status", metrics["claim_coverage_status"], str(expected.get("claim_coverage_status", ""))),
        _make_check("section_briefs_status", metrics["section_briefs_status"], str(expected.get("section_briefs_status", ""))),
        _make_check("section_drafts_status", metrics["section_drafts_status"], str(expected.get("section_drafts_status", ""))),
        _make_contains_check(
            f"{results_section_id}_section_note_contains",
            metrics["section_note"],
            str(expected.get("section_note_contains", "")),
        ),
        _make_contains_check(
            f"{claim_note_claim_id}_claim_packet_note_contains",
            metrics["claim_packet_note"],
            str(expected.get("claim_note_contains", "")),
        ),
        _make_contains_check(
            f"{claim_note_claim_id}_draft_subsection_note_contains",
            metrics["draft_subsection_note"],
            str(expected.get("claim_note_contains", "")),
        ),
    ]
    return _summarize_case(case, checks, metrics)


def _run_author_input_error_case(case: dict[str, Any]) -> dict[str, Any]:
    author_inputs = case.get("author_inputs", {})
    expected_fragment = str(case.get("expect_error_contains", ""))
    error_message = ""
    passed = False

    try:
        with _override_author_inputs(author_inputs):
            build_claim_packets()
    except ValueError as exc:
        error_message = str(exc)
        passed = expected_fragment in error_message
    else:
        error_message = "no error raised"

    checks = [
        {
            "label": "expected_error_contains",
            "passed": passed,
            "actual": error_message,
            "expected_contains": expected_fragment,
        }
    ]
    metrics = {"error_message": error_message}
    return _summarize_case(case, checks, metrics)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = str(case.get("kind", ""))
    try:
        if kind == "repo_readiness":
            return _run_repo_readiness_case(case)
        if kind == "author_input_propagation":
            return _run_author_input_propagation_case(case)
        if kind == "author_input_error":
            return _run_author_input_error_case(case)
        raise ValueError(f"Unsupported benchmark case kind: {kind}")
    except Exception as exc:
        checks = [
            {
                "label": "runtime_error",
                "passed": False,
                "actual": str(exc),
                "expected": "case completed without exception",
            }
        ]
        metrics = {"runtime_error": str(exc)}
        return _summarize_case(case, checks, metrics)


def build_harness_benchmark_report(
    suite_id: str = DEFAULT_SUITE_ID,
    bundle_id: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    suite = load_benchmark_definition(suite_id=suite_id, bundle_id=bundle_id)
    return _build_harness_benchmark_report_from_definition(suite, repo_root=repo_root)


def _summarize_benchmark_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "definition_id": report["suite_id"],
        "definition_type": report["definition_type"],
        "adapter_type": report["adapter_type"],
        "benchmark_family": report["benchmark_family"],
        "reference_benchmark": report["reference_benchmark"],
        "readiness": report["readiness"],
        "overall_score": report["overall_score"],
        "case_count": report["case_count"],
        "passed_case_count": report["passed_case_count"],
        "failed_case_count": report["failed_case_count"],
        "failed_case_ids": report["failed_case_ids"],
        "suite_path": report["suite_path"],
    }


def build_harness_benchmark_matrix_report(
    *,
    include_suites: bool = True,
    include_bundles: bool = True,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    definition_refs = list_benchmark_definition_refs(
        include_suites=include_suites,
        include_bundles=include_bundles,
    )
    if not definition_refs:
        raise ValueError("No benchmark definitions selected for the matrix report.")

    reports: list[dict[str, Any]] = []
    for definition_ref in definition_refs:
        if definition_ref["definition_type"] == "bundle":
            reports.append(
                build_harness_benchmark_report(
                    bundle_id=definition_ref["definition_id"],
                    repo_root=repo_root,
                )
            )
        else:
            reports.append(
                build_harness_benchmark_report(
                    suite_id=definition_ref["definition_id"],
                    repo_root=repo_root,
                )
            )

    ready_definitions = [report for report in reports if report["readiness"] == "ready"]
    total_case_count = sum(report["case_count"] for report in reports)
    total_passed_case_count = sum(report["passed_case_count"] for report in reports)
    total_failed_case_count = sum(report["failed_case_count"] for report in reports)
    weighting_denominator = total_case_count or len(reports) or 1
    overall_score = round(
        sum(report["overall_score"] * max(report["case_count"], 1) for report in reports) / weighting_denominator,
        2,
    )
    package_paths = sorted(
        dict.fromkeys(
            path
            for report in reports
            for path in report.get("package_paths", [])
        )
    )
    package_paths.extend(
        path
        for path in (
            "scripts/check_harness_benchmark_matrix.py",
            "tests/manuscript/test_harness_benchmark_matrix.py",
        )
        if path not in package_paths
    )

    return {
        "matrix_id": MATRIX_REPORT_STEM,
        "readiness": "ready" if len(ready_definitions) == len(reports) else "blocked",
        "benchmark_count": len(reports),
        "ready_benchmark_count": len(ready_definitions),
        "blocked_benchmark_count": len(reports) - len(ready_definitions),
        "total_case_count": total_case_count,
        "total_passed_case_count": total_passed_case_count,
        "total_failed_case_count": total_failed_case_count,
        "overall_score": overall_score,
        "include_suites": include_suites,
        "include_bundles": include_bundles,
        "definitions": [_summarize_benchmark_report(report) for report in reports],
        "package_paths": package_paths,
        "repo_root": _relative(repo_root),
    }


def build_harness_benchmark_manifest(report: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "suite_id": report["suite_id"],
        "definition_type": report["definition_type"],
        "adapter_type": report["adapter_type"],
        "benchmark_family": report["benchmark_family"],
        "reference_benchmark": report["reference_benchmark"],
        "readiness": report["readiness"],
        "overall_score": report["overall_score"],
        "case_count": report["case_count"],
        "passed_case_count": report["passed_case_count"],
        "failed_case_count": report["failed_case_count"],
        "failed_case_ids": report["failed_case_ids"],
        "package_paths": report["package_paths"],
    }
    generation_id = str(report.get("run_generation_id", "")).strip()
    if generation_id:
        manifest["run_generation_id"] = generation_id
    return manifest


def build_harness_benchmark_matrix_manifest(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "matrix_id": report["matrix_id"],
        "readiness": report["readiness"],
        "benchmark_count": report["benchmark_count"],
        "ready_benchmark_count": report["ready_benchmark_count"],
        "blocked_benchmark_count": report["blocked_benchmark_count"],
        "total_case_count": report["total_case_count"],
        "total_passed_case_count": report["total_passed_case_count"],
        "total_failed_case_count": report["total_failed_case_count"],
        "overall_score": report["overall_score"],
        "include_suites": report["include_suites"],
        "include_bundles": report["include_bundles"],
        "definitions": report["definitions"],
        "package_paths": report["package_paths"],
    }


def render_harness_benchmark_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Evaluation Benchmark",
        "",
        f"- suite_id: `{report['suite_id']}`",
        f"- definition_type: `{report['definition_type']}`",
        f"- adapter_type: `{report['adapter_type'] or 'none'}`",
        f"- benchmark_family: `{report['benchmark_family']}`",
        f"- reference_benchmark: `{report['reference_benchmark']}`",
        f"- readiness: `{report['readiness']}`",
        f"- overall_score: `{report['overall_score']}`",
        f"- case_count: `{report['case_count']}`",
        f"- passed_case_count: `{report['passed_case_count']}`",
        f"- failed_case_count: `{report['failed_case_count']}`",
        "",
    ]
    if report.get("description"):
        lines.extend([report["description"], ""])
    if report.get("notes"):
        lines.extend(["## Notes", ""])
        for note in report["notes"]:
            lines.append(f"- {note}")
        lines.append("")
    lines.extend(["## Cases", ""])
    for case in report.get("cases", []):
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- kind: `{case['kind']}`",
                f"- adapter_type: `{case.get('adapter_type', 'none')}`",
                f"- dimension: `{case['dimension']}`",
                f"- status: `{case['status']}`",
                f"- score: `{case['score']}`",
                f"- checks: `{case['passed_check_count']}/{case['check_count']}`",
                "",
            ]
        )
        if case.get("description"):
            lines.append(f"{case['description']}")
            lines.append("")
        if case.get("source_materials"):
            lines.append("#### Source Materials")
            lines.append("")
            source_materials = case["source_materials"]
            if isinstance(source_materials, dict):
                for key, value in source_materials.items():
                    if isinstance(value, dict):
                        rendered = ", ".join(f"{nested_key}={nested_value}" for nested_key, nested_value in value.items())
                        lines.append(f"- `{key}`: {rendered}")
                    else:
                        lines.append(f"- `{key}`: {value}")
            lines.append("")
        lines.append("#### Checks")
        lines.append("")
        for check in case.get("checks", []):
            label = check.get("label", "check")
            state = "pass" if check.get("passed") else "fail"
            if "expected_contains" in check:
                lines.append(
                    f"- `{label}`: `{state}` | expected_contains `{check['expected_contains']}` | actual `{check.get('actual')}`"
                )
            else:
                lines.append(
                    f"- `{label}`: `{state}` | expected `{check.get('expected')}` | actual `{check.get('actual')}`"
                )
        lines.append("")
    lines.extend(["## Package Paths", ""])
    for path in report.get("package_paths", []):
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def render_harness_benchmark_matrix_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Evaluation Benchmark Matrix",
        "",
        f"- matrix_id: `{report['matrix_id']}`",
        f"- readiness: `{report['readiness']}`",
        f"- overall_score: `{report['overall_score']}`",
        f"- benchmark_count: `{report['benchmark_count']}`",
        f"- ready_benchmark_count: `{report['ready_benchmark_count']}`",
        f"- blocked_benchmark_count: `{report['blocked_benchmark_count']}`",
        f"- total_case_count: `{report['total_case_count']}`",
        f"- total_passed_case_count: `{report['total_passed_case_count']}`",
        f"- total_failed_case_count: `{report['total_failed_case_count']}`",
        f"- include_suites: `{report['include_suites']}`",
        f"- include_bundles: `{report['include_bundles']}`",
        "",
        "## Definitions",
        "",
    ]
    for definition in report.get("definitions", []):
        lines.extend(
            [
                f"### {definition['definition_id']}",
                "",
                f"- definition_type: `{definition['definition_type']}`",
                f"- adapter_type: `{definition['adapter_type'] or 'none'}`",
                f"- benchmark_family: `{definition['benchmark_family']}`",
                f"- reference_benchmark: `{definition['reference_benchmark']}`",
                f"- readiness: `{definition['readiness']}`",
                f"- overall_score: `{definition['overall_score']}`",
                f"- case_count: `{definition['case_count']}`",
                f"- passed_case_count: `{definition['passed_case_count']}`",
                f"- failed_case_count: `{definition['failed_case_count']}`",
                f"- suite_path: `{definition['suite_path']}`",
                "",
            ]
        )
        if definition.get("failed_case_ids"):
            lines.append("Failed cases:")
            for case_id in definition["failed_case_ids"]:
                lines.append(f"- `{case_id}`")
            lines.append("")
    lines.extend(["## Package Paths", ""])
    for path in report.get("package_paths", []):
        lines.append(f"- `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_harness_benchmark_outputs(
    suite_id: str = DEFAULT_SUITE_ID,
    bundle_id: str | None = None,
) -> dict[str, str]:
    report = build_harness_benchmark_report(suite_id=suite_id, bundle_id=bundle_id)
    report_stem = str(bundle_id or suite_id)
    report_json_path = REPORTS_DIR / f"{report_stem}.json"
    report_md_path = REPORTS_DIR / f"{report_stem}.md"
    manifest_path = MANIFESTS_DIR / f"{report_stem}.json"

    write_json(report_json_path, report)
    write_text(report_md_path, render_harness_benchmark_markdown(report))
    write_json(manifest_path, build_harness_benchmark_manifest(report))

    return {
        "report_json": _relative(report_json_path),
        "report_md": _relative(report_md_path),
        "manifest": _relative(manifest_path),
    }


def write_harness_benchmark_matrix_outputs(
    *,
    include_suites: bool = True,
    include_bundles: bool = True,
    reports_dir: Path | None = None,
    manifests_dir: Path | None = None,
) -> dict[str, str]:
    reports_dir = reports_dir or REPORTS_DIR
    manifests_dir = manifests_dir or MANIFESTS_DIR
    report = build_harness_benchmark_matrix_report(
        include_suites=include_suites,
        include_bundles=include_bundles,
    )
    report_json_path = reports_dir / f"{MATRIX_REPORT_STEM}.json"
    report_md_path = reports_dir / f"{MATRIX_REPORT_STEM}.md"
    manifest_path = manifests_dir / f"{MATRIX_REPORT_STEM}.json"

    write_json(report_json_path, report)
    write_text(report_md_path, render_harness_benchmark_matrix_markdown(report))
    write_json(manifest_path, build_harness_benchmark_matrix_manifest(report))

    return {
        "report_json": _relative(report_json_path),
        "report_md": _relative(report_md_path),
        "manifest": _relative(manifest_path),
    }
