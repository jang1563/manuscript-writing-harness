# Release Profiles

Release profiles define which validated subsystems are assembled into a top-level handoff package.

Use them with:

```bash
python3 scripts/build_release_bundle.py --profile integrated_demo_release --write
python3 scripts/check_release_bundle.py --profile integrated_demo_release --write --strict
```

Profiles live in `profiles.yml` so the release layer can grow without hard-coding venue or bundle choices in the scripts.

Profiles may also define `release_metadata` overrides for deposit-facing outputs such as:

- release title and description
- release date
- keyword lists
- creators and affiliations used by `CITATION.cff`, `codemeta.json`, Zenodo, and OSF metadata

For real-project onboarding, pair a release profile with a project scaffold under `workflows/release/projects/` and validate it with:

```bash
python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json
```
