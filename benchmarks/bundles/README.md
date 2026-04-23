# Benchmark Bundles

This directory holds adapter-ready benchmark bundles that mirror external benchmark framing
more closely than the repo-local suites do.

The current bundle format is:

- `adapter_type: "paperwritingbench_style_bundle"`
- per-case `source_materials` that capture pre-writing artifacts such as idea summaries,
  experimental logs, venue templates, and guidelines
- a lightweight `mapping` layer that projects those materials into this repo's
  `author_content_inputs.json` shape

Use:

```bash
python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_demo_v1 --json --strict
python3 scripts/check_harness_benchmark.py --bundle paperwritingbench_style_heldout_v1 --json --strict
python3 scripts/check_harness_benchmark.py --bundle generic_author_input_demo_v1 --json --strict
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_heldout_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/generic_author_input_source_demo_v1 --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-archive /path/to/benchmark_package.zip --dry-run --json
python3 scripts/import_benchmark_bundle.py --package-dir benchmarks/packages/paperwritingbench_style_source_demo_v1 --force --json
```
