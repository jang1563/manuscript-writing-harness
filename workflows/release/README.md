# Release

Use this directory for release manifests and submission-bundle metadata.

Current contents now include:

- release profiles under `workflows/release/profiles/`
- venue readiness reports under `workflows/release/reports/`
- venue submission-package manifests under `workflows/release/manifests/`
- integrated release-bundle reports and manifests generated from the profile layer
- conference anonymization stubs under `workflows/release/`

Generate the integrated release bundle with:

```bash
python3 scripts/build_release_bundle.py --profile integrated_demo_release --write
python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict
```

Freeze an archive/export package from that release bundle with:

```bash
python3 scripts/build_archive_export.py --profile integrated_demo_release --write
python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict
```

Create deterministic tar/zip deliverables from the frozen archive with:

```bash
python3 scripts/build_export_bundle.py --profile integrated_demo_release --write
python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict
```

Generate deposit-ready citation and repository metadata from that export with:

```bash
python3 scripts/build_deposit_metadata.py --profile integrated_demo_release --write
python3 scripts/check_deposit_metadata.py --profile integrated_demo_release --write --strict
```
