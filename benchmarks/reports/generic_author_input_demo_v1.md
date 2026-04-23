# Agent Evaluation Benchmark

- suite_id: `generic_author_input_demo_v1`
- definition_type: `bundle`
- adapter_type: `generic_author_input_bundle`
- benchmark_family: `generic_author_input_bundle`
- reference_benchmark: `internal_generic_author_input`
- readiness: `ready`
- overall_score: `100.0`
- case_count: `2`
- passed_case_count: `2`
- failed_case_count: `0`

Example generic author-input benchmark package that carries direct author guidance plus optional source notes into the multi-agent manuscript system without depending on PaperWritingBench-specific field names.

## Notes

- This package exercises a simpler external package shape built around direct author inputs.
- The generic author-input adapter requires author_inputs.topic instead of deriving the topic from idea-summary materials.

## Cases

### generic_author_input_authoring

- kind: `author_input_propagation`
- adapter_type: `generic_author_input_bundle`
- dimension: `structured_authoring`
- status: `pass`
- score: `100.0`
- checks: `7/7`

A generic author-input package should be able to drive the manuscript system directly from author_inputs while still carrying supporting context in source materials.

#### Source Materials

- `brief`: This package uses direct author inputs instead of benchmark-specific pre-writing fields.

#### Checks

- `topic`: `pass` | expected `Direct author input benchmark for therapeutic response` | actual `Direct author input benchmark for therapeutic response`
- `claim_coverage_status`: `pass` | expected `ready` | actual `ready`
- `section_briefs_status`: `pass` | expected `ready` | actual `ready`
- `section_drafts_status`: `pass` | expected `ready` | actual `ready`
- `results_section_note_contains`: `pass` | expected_contains `Lead the Results` | actual `Lead the Results with the strongest treatment-response separation.`
- `claim_response_kinetics_claim_packet_note_contains`: `pass` | expected_contains `response-divergence claim` | actual `Open the first results subsection with this response-divergence claim.`
- `claim_response_kinetics_draft_subsection_note_contains`: `pass` | expected_contains `response-divergence claim` | actual `Open the first results subsection with this response-divergence claim.`

### generic_author_input_unknown_claim

- kind: `author_input_error`
- adapter_type: `generic_author_input_bundle`
- dimension: `guardrails`
- status: `pass`
- score: `100.0`
- checks: `1/1`

The generic adapter should preserve the same unknown-claim guardrail behavior when direct author inputs point to a non-existent claim id.

#### Source Materials

- `brief`: This negative case checks that direct author inputs still honor the tracked claim-id guardrail.

#### Checks

- `expected_error_contains`: `pass` | expected_contains `unknown claim_ids` | actual `author_content_inputs.json contains unknown claim_ids: claim_not_in_repo. Decide whether to add or replace the underlying fact-sheet/display-item claim before generating drafts.`

## Package Paths

- `benchmarks/bundles/generic_author_input_demo_v1.json`
- `scripts/check_harness_benchmark.py`
- `scripts/harness_benchmark.py`
- `tests/manuscript/test_harness_benchmark.py`
