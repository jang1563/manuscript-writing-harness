# Release Policies

This directory tracks anonymization and data-sharing policy files for real projects.

Use these files to record:

- review model and anonymization requirements
- whether manuscript, supplement, and metadata have been scrubbed
- human-subject / controlled-access expectations
- raw-data and code-release posture
- MSigDB license confirmation when pathway analysis depends on licensed gene sets

Validate a tracked policy with:

```bash
python3 scripts/check_release_policy.py --project rnaseq_real_project_template --write --json
```
