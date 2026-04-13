# Release Exports

Physical export bundles live here.

Use them when you want a deterministic tar/zip package built from the frozen archive inventory:

```bash
python3 scripts/build_export_bundle.py --profile integrated_demo_release --write
python3 scripts/check_export_bundle.py --profile integrated_demo_release --write --strict
```

The export layer writes:

- `*_export.json` and `*_export.md`
- `*_export_checksums.txt`
- deterministic `tar.gz` and `zip` bundles
- `*_export_manifest.json`
