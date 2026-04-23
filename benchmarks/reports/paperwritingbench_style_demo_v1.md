# Agent Evaluation Benchmark

- suite_id: `paperwritingbench_style_demo_v1`
- definition_type: `bundle`
- adapter_type: `paperwritingbench_style_bundle`
- benchmark_family: `paperwritingbench_style_bundle`
- reference_benchmark: `PaperWritingBench`
- readiness: `ready`
- overall_score: `100.0`
- case_count: `2`
- passed_case_count: `2`
- failed_case_count: `0`

Example adapter-ready benchmark bundle that carries pre-writing materials and maps them into the multi-agent manuscript system author-input surface built on the deterministic harness substrate.

## Notes

- This is a tracked demo bundle for the adapter layer, not an official PaperWritingBench release.
- The adapter derives the manuscript topic from source_materials.idea_summary when author_inputs.topic is omitted.

## Cases

### bundle_authoring_from_prewriting_materials

- kind: `author_input_propagation`
- adapter_type: `paperwritingbench_style_bundle`
- dimension: `structured_authoring`
- status: `pass`
- score: `100.0`
- checks: `7/7`

A PaperWritingBench-style case should carry idea-summary and venue-guideline context, then map those materials into author inputs that propagate through the manuscript system's planning, briefing, and drafting artifacts.

#### Source Materials

- `venue_template`: neurips
- `idea_summary`: title=Therapy response trajectories in a multimodal benchmark, objective=Lead the manuscript with the strongest treatment-associated response divergence and keep the first Results subsection tightly display-backed.
- `experimental_log`: The display-backed response claim should anchor the first Results subsection before broader interpretation.
- `guidelines`: Start the Results with the clearest quantitative separation and avoid unsupported background expansion.

#### Checks

- `topic`: `pass` | expected `Therapy response trajectories in a multimodal benchmark` | actual `Therapy response trajectories in a multimodal benchmark`
- `claim_coverage_status`: `pass` | expected `ready` | actual `ready`
- `section_briefs_status`: `pass` | expected `ready` | actual `ready`
- `section_drafts_status`: `pass` | expected `ready` | actual `ready`
- `results_section_note_contains`: `pass` | expected_contains `Start the Results` | actual `Start the Results with the strongest treatment-response separation.`
- `claim_response_kinetics_claim_packet_note_contains`: `pass` | expected_contains `opening sentence` | actual `Use this as the opening sentence for the first results subsection.`
- `claim_response_kinetics_draft_subsection_note_contains`: `pass` | expected_contains `opening sentence` | actual `Use this as the opening sentence for the first results subsection.`

### bundle_unknown_claim_guardrail

- kind: `author_input_error`
- adapter_type: `paperwritingbench_style_bundle`
- dimension: `guardrails`
- status: `pass`
- score: `100.0`
- checks: `1/1`

The adapter path should preserve the same guardrail behavior as the repo-local suite when a pre-writing bundle points to an unknown claim id.

#### Source Materials

- `venue_template`: conference
- `idea_summary`: title=Example topic
- `experimental_log`: This case is intentionally malformed to verify the unknown-claim stop condition.
- `guidelines`: Do not invent unsupported claims.

#### Checks

- `expected_error_contains`: `pass` | expected_contains `unknown claim_ids` | actual `author_content_inputs.json contains unknown claim_ids: claim_not_in_repo. Decide whether to add or replace the underlying fact-sheet/display-item claim before generating drafts.`

## Package Paths

- `benchmarks/bundles/paperwritingbench_style_demo_v1.json`
- `scripts/check_harness_benchmark.py`
- `scripts/harness_benchmark.py`
- `tests/manuscript/test_harness_benchmark.py`
