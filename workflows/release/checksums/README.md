# Release Checksums

Frozen archive inventories live here.

Generate them with:

```bash
python3 scripts/build_archive_export.py --profile integrated_demo_release --write
python3 scripts/check_archive_export.py --profile integrated_demo_release --write --strict
```

Each inventory is a plain `sha256  relative/path` listing so downstream deposits can be verified without custom tooling.
