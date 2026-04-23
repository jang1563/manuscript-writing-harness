# Contributing

Thanks for your interest in contributing. This project is an artifact-driven multi-agent manuscript system built on a deterministic harness substrate, and contributions are welcome.

Participation in this project is governed by the [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Before you start

1. **Read the [LICENSE](LICENSE) and [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).** This project is dual-licensed (PolyForm Noncommercial + commercial). By submitting a contribution, you agree that your contribution is licensed to the project under the same terms.

2. **Open an issue first for non-trivial changes.** A short discussion before you write code saves everyone time. Bug fixes can go straight to a PR.

## Setting up locally

```bash
# Python (3.10-3.12)
# If your system python3 is older, point this at a specific supported interpreter.
python3.11 -m venv .venv
source .venv/bin/activate
python --version
python scripts/check_runtime_support.py
python -m pip install -r env/requirements-myst.txt
python -m pip install -r env/requirements-phase2.txt

# R figures (optional)
Rscript env/install_r_figure_deps.R

# Node 20 for MyST CLI
# (use nvm or your preferred Node manager)
```

Run the validation entrypoints to confirm setup:

```bash
python3 scripts/check_scaffold.py
./.venv/bin/python -m pytest tests/
```

## Pull request checklist

- [ ] All existing tests still pass: `./.venv/bin/python -m pytest tests/`
- [ ] New behavior has tests (unit, integration, or visual regression as appropriate)
- [ ] CLI changes update the relevant module README and the top-level README quick-start
- [ ] Schema changes update the affected YAML schema in `*/schemas/` and the corresponding `*_common.py` field constants
- [ ] No hardcoded absolute paths (`/Users/...`, `/home/...`)
- [ ] No secrets, API keys, personal email addresses, or proprietary data

## Coding conventions

- **Python**: target 3.10+, type hints on public functions, no external deps for parsing tasks where the standard library suffices
- **R**: ggplot2 + patchwork for figures; testthat + vdiffr for visual regression
- **YAML schemas** drive code; never hardcode field lists when a schema exists
- **CSV** for record-level data, **YAML** for configuration and computed outputs
- **Comments**: only when WHY is non-obvious; well-named identifiers explain WHAT
- **No emojis** in code or commits unless explicitly requested by users in their own content

## Commit messages

- One concise sentence describing the change, followed by a blank line and a short paragraph if needed
- Imperative mood: "Add NBIB parser" not "Added" or "Adds"
- Reference issues with `#NN` where applicable
- Do not add co-authorship lines for AI assistants

## Reporting bugs

Open a GitHub issue with:

1. What you tried (the exact command)
2. What you expected to happen
3. What actually happened (with the relevant terminal output)
4. Your environment: OS, Python version, R version, Node version

## Reporting security issues

Do not open a public issue for security vulnerabilities.

Follow [SECURITY.md](SECURITY.md) for the private reporting process. The current supported intake path is email to **silveray1563@gmail.com**.

## Questions about commercial use

See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md). Open an issue with the `licensing` label if you'd like written confirmation that your use case is covered under the noncommercial license.
