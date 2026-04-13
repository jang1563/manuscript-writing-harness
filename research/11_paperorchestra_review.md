# PaperOrchestra Review For This Harness

Reviewed: 2026-04-09

## Objective

Review `PaperOrchestra: A Multi-Agent Framework for Automated AI Research Paper Writing` carefully and translate the useful parts into concrete design guidance for this repository.

## Source Status

As of `2026-04-09`, the primary source I could verify is the `arXiv` preprint submitted on `2026-04-06`, plus the official project page.

Important clarification:

- I did **not** find a primary-source indication that this work has already been accepted to a peer-reviewed venue.
- So the safest description today is `recently released preprint`, not `already peer-reviewed publication`.

## Core Claim

PaperOrchestra argues that automated research writing works better when the problem is decomposed into specialized agents rather than pushed through a single monolithic writer.

Its claimed contributions are:

- a multi-agent framework for turning unconstrained pre-writing materials into submission-ready manuscripts
- generated visuals, including plots and conceptual diagrams
- API-grounded literature synthesis
- a benchmark called `PaperWritingBench`
- automated and human side-by-side evaluation

## Inputs They Standardize

One of the most important ideas in PaperOrchestra is that the system does **not** start from a blank page.

Instead, the official project page says the raw materials are:

- an `Idea Summary`
- an `Experimental Log`
- a venue-specific `LaTeX Template`
- conference `Guidelines`

This is a very strong design choice.

Why it matters:

- it separates `research completion` from `manuscript drafting`
- it makes the writer operate on explicit pre-writing artifacts
- it avoids coupling the manuscript system to one specific experiment runtime

This maps extremely well to our harness philosophy.

## Pipeline Design

From the official project page and framework overview, PaperOrchestra uses a five-step pipeline:

1. `Outline Agent`
2. `Plotting Agent`
3. `Literature Review Agent`
4. `Section Writing Agent`
5. `Content Refinement Agent`

The high-value architectural point is not just that there are five agents. It is that the writing workflow is explicitly decoupled into:

- planning
- visualization
- literature grounding
- drafting
- refinement

This separation is more important than the exact agent count.

## What Each Agent Seems To Do

### 1. Outline Agent

The framework overview says the Outline Agent converts the raw materials into:

- a `JSON Outline`
- a `Visualization Plan`
- a `Research Graph`
- a `Writing Plan`

This is one of the best ideas in the paper.

For our repository, this suggests we should not jump directly from notes to manuscript text. We should explicitly materialize:

- section plan
- display-item plan
- citation plan
- figure/table dependency graph

In other words, `planning artifacts` should be first-class files in the repo.

### 2. Plotting Agent

The project page says the Plotting Agent generates:

- `conceptual diagrams`
- `statistical plots`

and the overview figure labels its backbone as `PaperBanana`.

This matters, but only partially for us.

What is useful:

- plots and diagrams are treated as a distinct subsystem
- visualization is planned before section writing
- generated figures are integrated into the manuscript workflow rather than bolted on later

What is not directly portable:

- the paper is operating in `AI conference paper` space, not `journal-grade bioinformatics figure provenance`
- it does not appear, from the primary sources I reviewed, to focus on microscopy, gels, blots, source-data policies, or production-editable figure layers the way our harness must

So for us, the lesson is:

- keep a dedicated plotting subsystem
- but preserve our stricter deterministic figure contract

### 3. Literature Review Agent

This is probably the most directly relevant agent for our manuscript harness.

The project page states that the Literature Review Agent:

- performs targeted web searches
- identifies candidate papers
- verifies their existence and relevance via the `Semantic Scholar API`
- builds a robust citation graph

That is an unusually good design choice because it acknowledges two separate problems:

- retrieval
- citation validation

This aligns strongly with our current direction on reference management.

What we should borrow:

- candidate discovery should be separate from citation acceptance
- every accepted citation should be grounded in metadata validation
- literature review should produce a machine-readable citation graph, not only prose

### 4. Section Writing Agent

The Section Writing Agent writes the full manuscript draft in `LaTeX`.

For us, the important part is not the exact output format.

What matters:

- section writing is downstream of outline, figures, and literature gathering
- writing is constrained by explicit venue templates and guidelines

This is very compatible with our `MyST core + venue overlays` architecture.

We should keep our semantic source of truth, but borrow the discipline that:

- the writer should consume structured planning artifacts
- venue rules should be explicit inputs, not hidden post hoc formatting

### 5. Content Refinement Agent

The project page says the Content Refinement Agent iteratively improves the draft based on simulated peer-review feedback.

The framework figure also visually indicates a refinement loop with checks resembling:

- `Improve`
- `Neutral`
- `Degrade`

This is important even if the exact implementation details are not visible from the sources I reviewed.

The implication is powerful:

- refinement should not be blind rewriting
- each revision should be tested for whether it actually improved the manuscript

For our harness, this suggests a future refinement layer that scores edits across dimensions like:

- factual consistency
- citation support
- venue compliance
- figure-table-text alignment
- readability without scientific drift

## Benchmark Design: PaperWritingBench

PaperOrchestra introduces `PaperWritingBench`, which the official project page describes as:

- the first standardized benchmark of reverse-engineered raw materials from `200` top-tier AI conference papers
- `100` papers from `CVPR 2025`
- `100` papers from `ICLR 2025`

The benchmark is designed to isolate writing from experimentation by supplying pre-writing materials only.

Crucially, the project page says:

- numeric data from tables are fully extracted
- insights from figures are converted into standalone factual observations

That design is excellent.

It means the benchmark avoids one major confound:

- requiring the model to infer all meaning directly from final published figures

For our harness, this suggests a very useful future principle:

- every figure and table should have a parallel `fact sheet` or structured evidence record

That would help both:

- manuscript generation
- systematic review traceability

## Evaluation Results

From the arXiv abstract and official project page:

- in side-by-side human evaluations, PaperOrchestra reports an absolute win-margin of `50%–68%` in literature review quality
- and `14%–38%` in overall manuscript quality against autonomous baselines

The project page's evaluation chart makes the comparisons more concrete.

### Literature review quality

Against `Single Agent`:

- baseline win: `5%`
- tie: `22%`
- PaperOrchestra win: `73%`

Against `AI Scientist-v2`:

- baseline win: `17%`
- tie: `17%`
- PaperOrchestra win: `67%`

### Overall quality

Against `Single Agent`:

- baseline win: `19%`
- tie: `24%`
- PaperOrchestra win: `57%`

Against `AI Scientist-v2`:

- baseline win: `36%`
- tie: `14%`
- PaperOrchestra win: `50%`

The same chart also shows a remaining gap relative to human-written ground truth:

- in literature review quality, human GT beats PaperOrchestra by `57%` to `19%`
- in overall quality, human GT beats PaperOrchestra by `81%` to `5%`

This is one of the most important takeaways.

PaperOrchestra is better than current autonomous baselines, but it does **not** eliminate the need for human scientific authorship and verification.

## What Is Strong In This Paper

### 1. It models manuscript generation as a structured pipeline

This is the paper's biggest strength.

The paper is not saying "one big LLM can write papers." It says:

- planning
- literature grounding
- figure generation
- drafting
- refinement

should be separate, coordinated activities.

That is exactly the right direction for a serious manuscript harness.

### 2. It treats literature grounding as a first-class system concern

The `web search + API verification + citation graph` framing is much better than free-form citation generation.

### 3. It uses venue templates and guidelines explicitly

This is very relevant to us because we are building for:

- `Nature`
- `Cell`
- `Science`
- conferences

PaperOrchestra reinforces the idea that venue constraints must be externalized as artifacts, not hidden assumptions.

### 4. It separates figures from prose generation

The plotting subsystem is independent from section writing, which is the right architectural instinct.

### 5. It evaluates with both benchmarked inputs and human review

That is much more meaningful than reporting only token-level or rubric-only automated scores.

## What Is Weak Or Limited For Our Use Case

### 1. It is AI-paper-first, not journal-science-first

The benchmark is built around `CVPR 2025` and `ICLR 2025`.

That means the system is tested on:

- AI conference structure
- AI paper rhetoric
- AI-style figures and tables

This is useful for us conceptually, but it is not enough evidence for:

- biomedical manuscripts
- systematic reviews
- source-data-heavy journal workflows
- image-integrity-sensitive figures

### 2. The visible primary sources do not show a strong provenance model for high-risk scientific figures

PaperOrchestra generates visuals, but from the primary sources I reviewed I do not see evidence of explicit handling for:

- wet-lab image provenance
- microscopy integrity rules
- source-data export conventions
- journal production constraints such as editable text layers and font policies

That is a major gap for our repository.

### 3. The manuscript source is LaTeX-native

That is not a criticism by itself, but it means the system is not directly aligned with our chosen semantic authoring substrate.

For us, this implies:

- borrow the pipeline logic
- do not copy the exact manuscript substrate

### 4. The human gap remains large

Their own results show that human-written ground truth remains clearly ahead.

So we should position any PaperOrchestra-inspired capability in this repo as:

- `assistive`
- not `authoritative`

## What We Should Borrow

### 1. Planning artifacts before drafting

We should add a pre-writing layer that emits structured files such as:

- `outline.json`
- `display_items.json`
- `citation_graph.json`
- `writing_plan.json`

This is probably the single best PaperOrchestra idea to import.

### 2. Literature retrieval plus verification as separate stages

Our future literature module should explicitly separate:

- paper discovery
- metadata verification
- citation acceptance
- narrative synthesis

### 3. Display-item planning before section writing

The writing system should know:

- which claims map to which figures/tables
- which figures already exist
- which ones are still placeholders
- what evidence supports each display item

### 4. Refinement with quality gates

We should add revision checks that can classify edits as:

- improved
- neutral
- degraded

especially for:

- citation support
- factual consistency
- venue compliance
- figure/table/text consistency

### 5. Venue rules as explicit inputs

PaperOrchestra reinforces our current overlay direction.

The system should always consume:

- template constraints
- guideline constraints
- venue-specific section requirements

as data, not buried prompt text.

## What We Should Not Borrow Directly

### 1. Prompt-driven figure generation as the source of truth

For our repository, figures must remain:

- spec-driven
- source-data-backed
- reproducible in CI

PaperOrchestra's plotting agent is useful as inspiration, but not as the authoritative backend for scientific figures.

### 2. Fully autonomous manuscript authorship

The paper itself positions the system as an assistive tool, and we should keep the same stance.

### 3. AI-conference assumptions

We should not assume the same pipeline transfers unchanged to:

- biology journals
- clinical systematic reviews
- wet-lab supplementary packages

## Recommended Adaptation For This Repository

### Near-term

Add a `planning` layer before section drafting with files such as:

- `manuscript/plans/outline.json`
- `manuscript/plans/display_item_map.json`
- `manuscript/plans/citation_graph.json`
- `manuscript/plans/revision_checks.json`

### Mid-term

Create an optional `assistive writing` workflow with specialized agents for:

- outline generation
- literature retrieval and verification
- display-item planning
- section drafting
- refinement

but keep the authoritative outputs in:

- `MyST`
- spec-backed figures
- metadata-backed citations

### Figure-specific implication

PaperOrchestra strengthens the case that figure planning should begin before prose drafting.

For our repo, that means we should eventually add:

- a `visualization_plan` artifact
- figure claim mapping
- per-figure fact sheets
- figure/table/text consistency checks

## Final Take

PaperOrchestra is worth taking seriously.

Its biggest value for us is **not** that it can "write a paper automatically." Its real value is that it formalizes the manuscript-writing process into separable, inspectable stages:

- plan
- gather evidence
- generate visuals
- draft
- refine

That is exactly the right abstraction layer for evolving this repository beyond a static manuscript scaffold into a high-quality scientific writing system.

But we should import its ideas selectively.

Best adaptation:

- `yes` to multi-stage orchestration
- `yes` to explicit planning artifacts
- `yes` to validated literature grounding
- `yes` to refinement quality gates
- `no` to replacing deterministic figure/reference/manuscript contracts with prompt-only generation

## Sources

- arXiv abstract page: https://arxiv.org/abs/2604.05018
- official project page: https://yiwen-song.github.io/paper_orchestra/
- framework overview image: https://yiwen-song.github.io/paper_orchestra/figures/overview.png
- human evaluation figure: https://yiwen-song.github.io/paper_orchestra/figures/human_eval_bar.png
