# Artifact-Driven Multi-Agent System Positioning

## Objective

Reframe this repository externally as an artifact-driven multi-agent manuscript system without pretending that the current repo is an unrestricted autonomous writing runtime.

The public positioning is:

> an artifact-driven multi-agent manuscript system built on a deterministic harness substrate

That relationship is the key design constraint for this phase:

- the system-level story is `multi-agent manuscript system`
- the implementation substrate remains the deterministic `harness`
- tracked artifacts and validators remain authoritative over free-form agent behavior

## Why Reframe At All

`Harness` correctly describes the repo's deterministic substrate, but it undersells the higher-level role structure that is already present in the workflow graph. The current repository already has distinct planning, figure, literature, review, venue, release, handoff, and evaluation surfaces. Reframing the repo makes that specialization legible to agent-oriented readers without changing the compatibility layer that existing scripts and file paths rely on.

## What Counts As An Agent Here

In this repository, an agent is a specialized worker that is bounded by tracked artifacts, explicit validators, and handoff contracts.

An agent in this repo is therefore not:

- a single prompt-only autonomous writer
- unrestricted code execution with hidden state
- a replacement for tracked figures, references, or venue rules

An agent in this repo is:

- a role with well-defined inputs and outputs
- a participant in an artifact-and-validator DAG
- a public framing for work that is still grounded in deterministic scripts and tracked files

## Deterministic Substrate Rule

The harness remains the substrate for the system.

That means:

- figures are still specified in tracked classes, bundles, and fact sheets
- reference integrity is still governed by bibliography exports, citation graphs, and audits
- venue compliance is still governed by tracked overlays and explicit human confirmation
- submission readiness is still governed by deterministic audits, maturity checks, and acceptance evidence
- release and deposit outputs are still generated from tracked profile metadata and packaged artifacts

The repo should not claim that agents replace those contracts. Agents operate through those contracts.

## Current Orchestration Model

The current orchestration model is a documented artifact-and-validator DAG.

In practice:

- source artifacts live under manuscript, figures, references, review, pathways, benchmarks, and workflows
- build scripts transform those artifacts into machine-readable intermediate outputs
- validators and acceptance checks decide whether those outputs are usable downstream
- packaging and handoff surfaces ship the validated state

This phase does not introduce a new autonomous orchestrator runtime. It adds an explicit architecture layer that interprets the existing repo as an artifact-driven agent system.

## Initial Agent Set

The initial registry names these roles:

1. `planning_agent`
2. `figure_agent`
3. `literature_grounding_agent`
4. `review_evidence_agent`
5. `section_writing_agent`
6. `venue_compliance_agent`
7. `submission_readiness_agent`
8. `release_packaging_agent`
9. `project_handoff_agent`
10. `evaluation_agent`

These are registry-level roles, not promises of equal autonomy. Some roles are already fully implemented as deterministic pipelines. Others are only partial as agent-shaped workflow layers.

## Overclaiming Guardrails

To keep the framing honest:

- `implementation_status` distinguishes `implemented`, `partial`, and `planned`
- `runtime_mode` distinguishes `deterministic`, `hybrid`, and `planned`
- validators are modeled as validators, not as agents
- authoritative truth stays in tracked artifacts and machine-readable gates

The repo should therefore describe current section writing as artifact-bounded drafting assistance, not as an autonomous end-to-end author.

## Public Naming Policy

External positioning should lead with `multi-agent manuscript system`.

Internal compatibility should keep:

- repo slug and historical identifiers such as `manuscript-writing-harness`
- benchmark and report filenames such as `harness_benchmark_matrix`
- existing script and module names

Historical research notes should remain historical. Notes such as the figure-agent review and the PaperOrchestra review stay in place and now point forward to this document for the current architecture stance.

## Machine-Readable Contract

The machine-readable source of truth for this layer is [workflows/agents/agent_registry.json](../workflows/agents/agent_registry.json).

That registry is meant to answer:

- which role owns which tracked artifacts
- which scripts act as entrypoints and validators
- which artifacts downstream consumers should treat as authoritative
- which upstream and downstream handoffs define the current DAG

## Non-Goals

This phase does not:

- rename the repository
- rename existing CLI entrypoints
- replace deterministic validators with opaque LLM behavior
- claim official equivalence to external benchmark packages
- collapse the repo into a single general-purpose writer agent

## Practical Reading

The most accurate short description of the repository after this change is:

> An artifact-driven multi-agent manuscript system built on a deterministic harness substrate, where specialized agents operate through tracked artifacts and explicit validators.
