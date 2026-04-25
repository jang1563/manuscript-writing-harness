# Agent Evaluation Benchmark

- suite_id: `paper_writing_bench_like_internal_v1`
- definition_type: `suite`
- adapter_type: `none`
- benchmark_family: `paper_writing_bench_like_internal`
- reference_benchmark: `PaperWritingBench`
- readiness: `ready`
- overall_score: `100.0`
- case_count: `3`
- passed_case_count: `3`
- failed_case_count: `0`

Internal structured-input benchmark for the artifact-driven multi-agent manuscript system. It scores the current repo against stable drafting, evidence, and guardrail expectations without claiming official external benchmark equivalence.

## Notes

- This suite is inspired by PaperWritingBench's pre-writing-material framing, but it runs entirely on repo-local artifacts.
- The score reflects manuscript-system integrity and harness-substrate guardrails, not human-judged prose quality.

## Cases

### tracked_demo_readiness

- kind: `repo_readiness`
- adapter_type: `none`
- dimension: `integrated_readiness`
- status: `pass`
- score: `100.0`
- checks: `10/10`

The tracked demo manuscript should remain structurally ready across claim coverage, section scaffolding, references, review evidence, and the cross-cutting audit while still distinguishing real-submission gates from general repo health.

#### Checks

- `claim_count`: `pass` | expected `24` | actual `24`
- `claim_coverage_status`: `pass` | expected `ready` | actual `ready`
- `section_briefs_status`: `pass` | expected `ready` | actual `ready`
- `section_drafts_status`: `pass` | expected `ready` | actual `ready`
- `reference_integrity_status`: `pass` | expected `ready` | actual `ready`
- `review_evidence_status`: `pass` | expected `ready` | actual `ready`
- `review_validation_status`: `pass` | expected `ready` | actual `ready`
- `pre_submission_audit_status`: `pass` | expected `ready` | actual `ready`
- `submission_gate_status`: `pass` | expected `blocked` | actual `blocked`
- `bibliography_scope_gate_status`: `pass` | expected `blocked` | actual `blocked`

### author_input_propagation

- kind: `author_input_propagation`
- adapter_type: `none`
- dimension: `results_first_authoring`
- status: `pass`
- score: `100.0`
- checks: `7/7`

Author-supplied topic, section framing, and claim-specific notes should propagate cleanly from the author-input file through claim packets, section briefs, and draft scaffolds without breaking readiness.

#### Checks

- `topic`: `pass` | expected `Therapy response trajectories in a multimodal benchmark` | actual `Therapy response trajectories in a multimodal benchmark`
- `claim_coverage_status`: `pass` | expected `ready` | actual `ready`
- `section_briefs_status`: `pass` | expected `ready` | actual `ready`
- `section_drafts_status`: `pass` | expected `ready` | actual `ready`
- `results_section_note_contains`: `pass` | expected_contains `Start the Results` | actual `Start the Results with the strongest treatment-response separation.`
- `claim_response_kinetics_claim_packet_note_contains`: `pass` | expected_contains `opening sentence` | actual `Use this as the opening sentence for the first results subsection.`
- `claim_response_kinetics_draft_subsection_note_contains`: `pass` | expected_contains `opening sentence` | actual `Use this as the opening sentence for the first results subsection.`

### unknown_claim_guardrail

- kind: `author_input_error`
- adapter_type: `none`
- dimension: `guardrails`
- status: `pass`
- score: `100.0`
- checks: `1/1`

The pipeline should fail early and clearly when an author note targets a claim id that is not present in the tracked evidence layer.

#### Checks

- `expected_error_contains`: `pass` | expected_contains `unknown claim_ids` | actual `author_content_inputs.json contains unknown claim_ids: claim_not_in_repo. Decide whether to add or replace the underlying fact-sheet/display-item claim before generating drafts.`

## Package Paths

- `benchmarks/suites/paper_writing_bench_like_internal_v1.json`
- `scripts/check_harness_benchmark.py`
- `scripts/harness_benchmark.py`
- `tests/manuscript/test_harness_benchmark.py`
