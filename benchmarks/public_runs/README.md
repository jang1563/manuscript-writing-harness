# Public Benchmark Runs

This directory is for local run outputs produced by:

```bash
python3 scripts/run_public_benchmark_package.py \
  --package-archive /path/to/benchmark_package.zip \
  --run-id my_public_package_run \
  --json --strict
```

Each run is written into its own subdirectory and contains:

- `report.json`
- `report.md`
- `manifest.json`
- `run_metadata.json`

`run_metadata.json` includes reproducibility context such as:

- Python version and implementation
- platform and machine
- exact command invocation
- git commit, branch, and dirty state when available
- a stable `source_sha256` fingerprint for either the package archive or the evaluated contents of the unpacked package directory

For unpacked directories, `source_sha256` is based on the normalized imported benchmark bundle,
not every incidental file in the folder, so junk files like `.DS_Store` do not change the
recorded benchmark source fingerprint.

These runs are intentionally separate from the tracked benchmark `reports/` and `manifests/`
so local public-package evaluations do not overwrite the curated repo benchmark artifacts.

To summarize multiple local runs together, use:

```bash
python3 scripts/check_public_benchmark_run.py --run-dir benchmarks/public_runs/<run_id> --json --strict
python3 scripts/check_public_benchmark_runs.py --runs-dir benchmarks/public_runs --json --strict
```

`check_public_benchmark_run.py` validates one run directory directly, including
`report.json`, `report.md`, `manifest.json`, `run_metadata.json`, and the consistency between
them. `check_public_benchmark_runs.py` then gives you the cross-run view.
The cross-run summary now reuses that stricter run-level validation, so a corrupted or internally
inconsistent run is surfaced as `invalid` in the aggregate report instead of looking healthy just
because its lightweight summary fields still parse.

When `--write` is used, the emitted stdout report and the written summary artifacts now come
from the same in-memory snapshot so the CLI does not mix different generations of run state.

The summary highlights:

- the latest discovered run
- the best-scoring valid run
- duplicate-source groups, so repeated reruns of the same package are easy to spot
