# Security Policy

## Supported Code

This repository is still pre-1.0 and moves quickly. Security fixes are applied to:

- the latest state of the default branch
- the most recent tagged or packaged release, if one exists

Older snapshots, stale generated artifacts, and long-lived forks may need to be rebased before a fix can be applied cleanly.

## Reporting A Vulnerability

Do not open a public GitHub issue, discussion, or pull request for an undisclosed security vulnerability.

Report vulnerabilities privately by email to **silveray1563@gmail.com** with the subject line `Security report: manuscript-writing-harness`.

Please include:

- the affected commit, branch, release, script, or workflow
- reproduction steps or a proof of concept
- the expected impact and any data-exposure risk
- whether credentials, API keys, or private data may be involved
- any suggested mitigation or patch if you already have one

## What To Expect

- acknowledgment within 5 business days
- a follow-up status update within 10 business days when triage is in progress
- coordinated disclosure after a fix or mitigation is available

## Scope Notes

- Accidental secret disclosure should be reported immediately, and any exposed credential should also be rotated.
- Licensing questions, feature requests, and ordinary correctness bugs should use the normal public issue flow unless they create a real security risk.
- GitHub private advisories are not the primary intake channel for this repository yet; email is the supported private route.
