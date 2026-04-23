# Agent Architecture

This directory defines the explicit agent layer for the repository.

The public framing is `multi-agent manuscript system`. The implementation reality is still a deterministic harness substrate with tracked artifacts and validators.

## Files

- `agent_registry.json`: machine-readable registry for the current agent graph

## Registry Semantics

Each agent entry uses the same contract:

- `agent_id`: stable machine-readable role id
- `display_name`: user-facing role name
- `purpose`: short description of what the role is responsible for
- `implementation_status`: one of `implemented`, `partial`, or `planned`
- `runtime_mode`: one of `deterministic`, `hybrid`, or `planned`
- `entrypoints`: tracked scripts or docs that expose the role
- `consumes`: tracked artifacts the role reads
- `produces`: tracked artifacts the role writes or maintains downstream
- `validators`: tracked scripts that gate or validate the role
- `upstream_agents`: agent ids that feed this role
- `downstream_agents`: agent ids that consume this role's outputs
- `authoritative_outputs`: tracked artifacts that downstream consumers should treat as the source of truth for this role
- `public_description`: short public-facing summary of the role

## Interpretation Rules

- Validators are not modeled as standalone agents.
- `authoritative_outputs` should prefer machine-readable tracked artifacts over markdown summaries.
- `authoritative_outputs` may point to maintained source artifacts when those artifacts are the real source of truth for a role.
- The registry describes the current artifact-and-validator DAG. It does not imply a new autonomous runtime.
