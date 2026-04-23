# Release

Use this directory for release manifests and submission-bundle metadata.

Current contents now include:

- release profiles under `workflows/release/profiles/`
- venue readiness reports under `workflows/release/reports/`
- venue submission-package manifests under `workflows/release/manifests/`
- integrated release-bundle reports and manifests generated from the profile layer
- conference anonymization stubs under `workflows/release/`
- project onboarding scaffolds under `workflows/release/projects/`
- project anonymization and data-sharing policies under `workflows/release/policies/`

For repo-level submission gating before a real venue submission, use:

```bash
python3 scripts/check_venue_readiness.py --venue neurips --json --strict --require-current-verification
python3 scripts/check_venue_readiness.py --all --json --strict --require-current-verification
python3 scripts/check_pre_submission_audit.py --venue neurips --json --strict --require-current-venue-verification
python3 scripts/check_pre_submission_audit.py --json --strict --require-current-venue-verification
python3 scripts/check_pre_submission_audit.py --json --strict --require-confirmed-manuscript-bibliography
python3 scripts/check_reference_integrity.py --json --require-confirmed-manuscript-bibliography
python3 scripts/confirm_manuscript_scope.py --note "Confirmed against the finalized manuscript submission package." --dry-run --json
python3 scripts/confirm_bibliography_scope.py --note "Confirmed against the accepted manuscript Zotero Better BibTeX export." --dry-run --json
python3 scripts/confirm_venue_verification.py --venue neurips --source-summary "Confirmed against the NeurIPS 2026 CFP" --dry-run --json
```

For the canonical repo-maturity view across demo, framework, and real-submission states, use:

```bash
python3 scripts/check_repo_maturity.py --profile demo --json --strict
python3 scripts/check_repo_maturity.py --profile submission-framework --json
python3 scripts/check_repo_maturity.py --profile submission-ready --venue neurips --json
python3 scripts/run_repo_maturity_acceptance.py --profile submission-framework --strict
python3 scripts/check_repo_maturity_acceptance.py --profile submission-framework --json
python3 scripts/run_repo_maturity_nightly.py --profile submission-framework --write-step-summary
python3 scripts/check_repo_maturity_nightly.py --profile submission-framework --json
```

`submission-framework` is the intended top-level CI signal for the deterministic harness substrate that underpins the multi-agent manuscript system.
`submission-ready` stays intentionally blocked until manuscript scope is `real`, the
bibliography export is confirmed for the real manuscript, and the target venue has been
human-confirmed as current. The acceptance runner now also writes
`workflows/release/reports/repo_maturity_<profile>_acceptance/summary.md`, which gives
one markdown summary of runtime, scaffold, Python, R, and repo-maturity evidence. The
matching acceptance manifest now also records controller environment metadata,
per-step durations for reproducibility, and the canonical repo-maturity report
JSON/markdown/manifest paths so the acceptance checker can validate that whole set
as one consistent output surface.

For ongoing monitoring beyond PR/push acceptance, `.github/workflows/repo-maturity-nightly.yml`
runs `scripts/run_repo_maturity_nightly.py` on a schedule and on manual dispatch. That runner
reuses the canonical `submission-framework` acceptance path, then adds the benchmark matrix
and a sample public benchmark package run plus a dedicated single-run validation step so the
manuscript system has one longer-horizon health report.
The workflow now also runs `scripts/check_repo_maturity_nightly.py` afterward so the nightly
artifact itself is validated, not just generated. The nightly path now keeps its acceptance
manifest, summary, and repo-maturity report inside the nightly output directory rather than
reusing the tracked `workflows/release/` output paths. Its benchmark-matrix report and
manifest now stay in that same nightly output tree too, so the monitoring run no longer
needs to rewrite the tracked benchmark-report artifacts. Each nightly run also records a
unique `session_id` and writes its sample public benchmark artifacts into
`public_runs/nightly_session_<session_id>/`, which prevents stale sibling runs from earlier
nightly passes from contaminating the current summary.

For a manual GitHub Actions gate on one target venue, run `.github/workflows/submission-gate.yml` and choose the target from the tracked `venue` dropdown. The workflow now delegates the end-to-end gate execution to `scripts/run_submission_gate.py`, so the same artifact flow can be exercised locally.

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

For real-project onboarding on top of the demo multi-agent manuscript system:

```bash
python3 scripts/scaffold_project_release.py --project-id my_project --title "My Project Release" --species human --collection H --json
python3 scripts/check_project_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json
python3 scripts/check_anonymized_release.py --project rnaseq_real_project_template --write --json
python3 scripts/check_project_handoff.py --project rnaseq_real_project_template --write --json
```
