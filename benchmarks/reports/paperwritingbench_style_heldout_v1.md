# Agent Evaluation Benchmark

- suite_id: `paperwritingbench_style_heldout_v1`
- definition_type: `bundle`
- adapter_type: `paperwritingbench_style_bundle`
- benchmark_family: `paperwritingbench_style_bundle`
- reference_benchmark: `PaperWritingBench`
- readiness: `ready`
- overall_score: `100.0`
- case_count: `2`
- passed_case_count: `2`
- failed_case_count: `0`

Held-out PaperWritingBench-style sample package for the multi-agent manuscript system that shifts emphasis from opening-response claims to model calibration and ranking evidence later in Results.

## Notes

- This is a tracked held-out sample package, not an official PaperWritingBench release.
- The held-out case exercises a different real claim id so the benchmark matrix covers more than the opening response-kinetics path.

## Cases

### heldout_bundle_calibration_authoring

- kind: `author_input_propagation`
- adapter_type: `paperwritingbench_style_bundle`
- dimension: `structured_authoring`
- status: `pass`
- score: `100.0`
- checks: `7/7`

A held-out PaperWritingBench-style case should propagate a calibration-focused story into the Results section without relying on the original response-kinetics demo fixture.

#### Source Materials

- `venue_template`: icml
- `idea_summary`: title=Calibration-aware foundation model ranking for imbalanced disease states, objective=Use the model-comparison subsection to foreground probability quality before the broader ranking synthesis.
- `experimental_log`: The held-out benchmark case emphasizes comparative model behavior under class imbalance.
Keep the Results narrative focused on calibration quality before summarizing global ranking.
- `guidelines`: Prioritize the calibration-focused evidence before broader synthesis claims.
Avoid rewriting the opening response-kinetics framing from the original demo bundle.

#### Checks

- `topic`: `pass` | expected `Calibration-aware foundation model ranking for imbalanced disease states` | actual `Calibration-aware foundation model ranking for imbalanced disease states`
- `claim_coverage_status`: `pass` | expected `ready` | actual `ready`
- `section_briefs_status`: `pass` | expected `ready` | actual `ready`
- `section_drafts_status`: `pass` | expected `ready` | actual `ready`
- `results_section_note_contains`: `pass` | expected_contains `calibration-quality comparison` | actual `Lead the mid-results narrative with the calibration-quality comparison.`
- `claim_calibration_loss_mainly_affects_probability_quality_claim_packet_note_contains`: `pass` | expected_contains `probability-quality subsection` | actual `Use this to anchor the probability-quality subsection before the broader ranking synthesis.`
- `claim_calibration_loss_mainly_affects_probability_quality_draft_subsection_note_contains`: `pass` | expected_contains `probability-quality subsection` | actual `Use this to anchor the probability-quality subsection before the broader ranking synthesis.`

### heldout_bundle_unknown_claim_guardrail

- kind: `author_input_error`
- adapter_type: `paperwritingbench_style_bundle`
- dimension: `guardrails`
- status: `pass`
- score: `100.0`
- checks: `1/1`

The held-out PaperWritingBench-style path should preserve the same guardrail behavior when its mapping points to a claim id that does not exist in the repo.

#### Source Materials

- `venue_template`: icml
- `idea_summary`: title=Held-out calibration guardrail case, objective=Preserve the unknown-claim stop condition even when the package otherwise looks valid.
- `experimental_log`: This negative case mirrors a real pre-writing package shape but points to an invalid claim id.
- `guidelines`: The importer and benchmark adapter should accept the package shape but the manuscript system must still block generation on the invalid claim reference.

#### Checks

- `expected_error_contains`: `pass` | expected_contains `unknown claim_ids` | actual `author_content_inputs.json contains unknown claim_ids: claim_not_in_repo_calibration. Decide whether to add or replace the underlying fact-sheet/display-item claim before generating drafts.`

## Package Paths

- `benchmarks/bundles/paperwritingbench_style_heldout_v1.json`
- `scripts/check_harness_benchmark.py`
- `scripts/harness_benchmark.py`
- `tests/manuscript/test_harness_benchmark.py`
