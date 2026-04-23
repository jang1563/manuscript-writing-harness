# Benchmarks

This directory holds tracked benchmark suites and generated scorecards for the multi-agent manuscript system.

Current scope:

- `suites/`: benchmark definitions
- `bundles/`: adapter-ready benchmark bundles that carry pre-writing materials
- `packages/`: source-style benchmark packages that can be imported into tracked bundles
- `public_runs/`: self-contained local run outputs for public package evaluations
- `reports/`: rendered benchmark reports
- `manifests/`: compact machine-readable benchmark summaries

The aggregate benchmark matrix is written to `reports/harness_benchmark_matrix.md` and
`manifests/harness_benchmark_matrix.json`, giving one readiness and score view across all
tracked suites and bundles.

The initial suite is intentionally conservative: it is a `PaperWritingBench`-inspired
internal benchmark for the repo's own artifact-driven drafting pipeline, not a claim of
official comparability to the external benchmark.

The bundle layer is the next step outward: it lets us keep pre-writing materials such as
idea summaries, experimental logs, venue templates, and guideline notes in a tracked
benchmark package and map them into this repo's author-input surface through a stable
adapter.

The package layer is one step earlier again: it keeps those pre-writing materials as
separate files and lets us import them into the tracked bundle format with a local CLI.

Tracked package examples now cover:

- a `PaperWritingBench`-style pre-writing package
- a held-out `PaperWritingBench`-style pre-writing package with a different Results emphasis
- a simpler `generic_author_input` package that uses direct author inputs plus optional source notes
