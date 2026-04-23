# integrated_demo_release_archive_v1 Deposit Notes

## Intended Targets

- `zenodo`
- `osf`

## Suggested Deposit Metadata

- title: `integrated_demo_release` archive export
- description: frozen archive of the multi-agent manuscript system release package
- artifact scope: manuscript, figures, references, review evidence, pathway provenance

## Required Files

- release report: `workflows/release/reports/integrated_demo_release_bundle.md`
- release manifest: `workflows/release/manifests/integrated_demo_release_bundle.json`
- checksum inventory: `workflows/release/checksums/integrated_demo_release_archive_sha256.txt`

## Notes

- Upload the exact files listed in the checksum inventory or a tarball generated from that list.
- Keep the checksum inventory alongside the deposited bundle so downstream users can verify file integrity.
- If the venue requires anonymized exports, reconcile this archive against `workflows/release/anonymization_check.md` before deposit.
