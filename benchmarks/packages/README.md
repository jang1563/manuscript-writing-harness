# Benchmark Packages

This directory holds source-style benchmark packages that can be imported into the tracked
bundle format with:

```bash
python3 scripts/import_benchmark_bundle.py \
  --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 \
  --dry-run --json

python3 scripts/import_benchmark_bundle.py \
  --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 \
  --dry-run --json

python3 scripts/import_benchmark_bundle.py \
  --package-dir benchmarks/packages/generic_author_input_source_demo_v1 \
  --dry-run --json

python3 scripts/import_benchmark_bundle.py \
  --package-archive /path/to/benchmark_package.zip \
  --dry-run --json
```

By default the importer refuses to overwrite an existing tracked bundle. Use `--force`
only when you intentionally want to replace the current bundle file.
Archive imports must use a local `.zip` file and are extracted with the same path-safety
checks as unpacked directory imports.
The benchmark checker can also score either package form directly with
`python3 scripts/check_harness_benchmark.py --package-dir ... --json --strict` or
`--package-archive ... --json --strict`.

Current package families:

- `paperwritingbench_style_source_demo_v1`: pre-writing-material package modeled after PaperWritingBench-style inputs
- `paperwritingbench_style_source_heldout_v1`: held-out PaperWritingBench-style sample package with a different Results-story emphasis
- `generic_author_input_source_demo_v1`: direct author-input package with optional supporting notes

Package layout:

- `package_manifest.json`: top-level benchmark metadata plus case definitions
- case-local files referenced from the manifest, such as:
  - `idea_summary.json`
  - `experimental_log.md`
  - `guidelines.md`
  - `mapping.json`
  - `expect.json`
