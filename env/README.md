# Environment Notes

This harness will likely need:

- `Python` for manuscript utilities, figure scripts, metadata tooling, and validation
- `Node.js` for `mystmd`
- `R` for the dual-language figure pipeline
- optional `LaTeX` or `Typst` toolchains for PDF exports

## Current Local Requirement

For the current scaffold, the only required local dependency is:

- `mystmd`
- Phase 2 figure and table dependencies

Install with:

```bash
python3 -m pip install -r env/requirements-myst.txt
python3 -m pip install -r env/requirements-phase2.txt
Rscript env/install_r_figure_deps.R
myst -v
```

`mystmd` requires `node` v20+.

Per the current official MyST installation guide, if `node` is not already installed, the PyPI-installed `mystmd` CLI can prompt to install a compatible local Node.js runtime the first time `myst` is executed.

For reproducibility, local development and CI should always install the same pinned version from:

- `env/requirements-myst.txt`
- `env/requirements-phase2.txt`
- `env/install_r_figure_deps.R`
- `env/runtime_support.yml`

## Runtime Support Matrix

The harness now tracks supported interpreter versions explicitly in `env/runtime_support.yml`.

Current support policy:

- primary full-build Python: `3.12`
- supported Python range in CI: `3.10`, `3.11`, `3.12`
- primary full-build R: `release`
- supported R range in CI: `oldrel-1`, `release`
- primary Node runtime for `mystmd`: `20`

The primary manuscript build stays on one reference pair for reproducibility, while a separate
compatibility workflow checks the Python and R version matrix.

For local multi-version work, the expected workflow is:

- `pyenv` or `mise` for switching Python versions
- `rig` or system package managers for switching R versions
- run `python3 scripts/check_runtime_support.py` before changing CI or support policy

Validate that the runtime metadata and workflows stay aligned with:

```bash
python3 scripts/check_runtime_support.py
```

## Planned Environment Expansion

Later phases should likely add:

- a locked Python environment for the manuscript and metadata toolchain
- `renv` for the R stack when review/meta-analysis and publication-grade statistical tables are added
- optional `conda-lock` or `pixi` once the repo mixes Python, R, and PDF toolchains heavily

## Current Phase 2b Figure Stack

- `matplotlib` for the example multi-panel figure pipeline
- `PyYAML` for reading shared theme and table schema files
- `ggplot2` and `patchwork` for the R renderer
- `svglite`, `ragg`, and `systemfonts` for R export and font control
- `fgsea` via Bioconductor for preranked pathway enrichment when pathway figures need a full enrichment-analysis backend

## Optional fgsea Pathway Stack

The harness now includes an optional `fgsea` preranked enrichment pipeline under `pathways/`.

Install support with the same R dependency bootstrap:

```bash
Rscript env/install_r_figure_deps.R
```

Then validate or run the demo pipeline with:

```bash
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_active.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/configs/fgsea_active.yml --allow-missing-package --json
python3 scripts/fgsea_pipeline.py validate --config pathways/configs/fgsea_demo.yml --json
python3 scripts/fgsea_pipeline.py run --config pathways/configs/fgsea_demo.yml --allow-missing-package --json
```

If `fgsea` is installed, the run writes a figure-compatible export for the pathway dot plot.
If `fgsea` is not installed, the run exits cleanly in `--allow-missing-package` mode and records a
transparent `skipped_missing_package` status instead of pretending the enrichment analysis ran.
