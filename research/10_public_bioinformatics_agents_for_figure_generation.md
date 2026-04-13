# Public Bioinformatics Agents For Figure Generation

Reviewed: 2026-04-09

## Objective

Check whether there are any public bioinformatics AI agents with either:

- strong public appraisal or adoption
- explicit emphasis on scientific or bioinformatics figure generation

and determine whether they help this repository's figure harness.

## Short Answer

Yes, but the landscape is uneven.

As of `2026-04-09`, I do **not** see a public project that is simultaneously:

- strongly adopted by the community
- bioinformatics-native
- and already mature as a deterministic, publication-grade figure harness

The closest direct match is `ggplotAgent`, which is explicitly about publication-ready bioinformatics visualization. The strongest general biomedical agent by adoption is `Biomni`, but it is not figure-focused. `SRAgent` is useful for data and manuscript retrieval, not figure rendering. `PlotGen` is an important research reference for agent architecture, but appears to be a paper-level framework rather than a mature public software stack.

So the practical answer is:

- `borrow ideas`, especially from `ggplotAgent` and `PlotGen`
- `do not replace our current harness` with an external agent

## Most Relevant Public Projects

| Project | Public signal as of 2026-04-09 | Figure relevance | Should it influence this repo? |
|---|---:|---|---|
| `ggplotAgent` | GitHub shows `0 stars`, `1 fork`; published in *Bioinformatics Advances* on `2026-01-02` | Very high | `Yes`, as an architectural reference |
| `Biomni` | GitHub shows `2.9k stars`, `536 forks`; HF model card for `Biomni-R0-32B-Preview` shows `19 likes` and `5,138` downloads last month | Low-direct, moderate-indirect | `Yes`, but only for upstream analysis/planning ideas |
| `SRAgent` | GitHub shows `163 stars`, `33 forks` | Low-direct | `Yes`, for dataset/publication retrieval, not plotting |
| `PlotGen` | Paper-level visibility via Hugging Face Papers and Adobe Research | Medium-high conceptually | `Yes`, as a design pattern, not as a dependency |

## 1. ggplotAgent

### What it is

`ggplotAgent` is the closest public project to what you asked for.

Its own paper and public repo describe it as:

- a `self-debugging`
- `multi-modal`
- `scientific visualization`
- system for generating `publication-quality` plots

The paper is bioinformatics-facing, not generic charting only. It explicitly frames publication-quality visualization as a bioinformatics bottleneck and uses common bioinformatics plot types such as:

- volcano plots
- heatmaps
- GO dot plots
- violin plots

The Oxford paper also reports:

- `100%` code executability versus `85%` for the baseline
- a higher publication-ready score (`1.9` versus `0.7`)
- a positive insight score from making useful visual improvements beyond the literal prompt

### Why it matters to us

This project is directly relevant because it combines several ideas we already care about:

- agent planning before plotting
- automatic code repair
- image-based critique of the produced plot
- reference-image-guided styling
- R-centric plotting with practical bioinformatics examples

Its GitHub repo is also notably mixed-language:

- `R 52.6%`
- `Python 47.4%`

That fits our Python-plus-R direction well.

### Why I would not adopt it as the core harness

Despite the strong fit, I would not make it our primary figure engine.

Reasons:

- public adoption still looks early: the GitHub page showed `0 stars` and `1 fork` on `2026-04-09`
- it is prompt-driven, whereas our harness needs deterministic figure specs and CI-rebuildable outputs
- it is optimized for `generate a plot from a prompt`, which is adjacent to, but not the same as, a submission-grade manuscript artifact system

### What to borrow

We should borrow these ideas:

- a `planner -> code generator -> code debugger -> visual critic` loop for optional draft generation
- reference-image conditioning as a convenience mode
- benchmark tasks for volcano, heatmap, and GO-style figures

### Verdict

`ggplotAgent` is the best external reference project for a future `agent-assisted figure drafting mode`, but not a replacement for our contract-first figure pipeline.

## 2. Biomni

### What it is

`Biomni` is the strongest public biomedical AI agent by visible adoption in this search pass.

The GitHub repo describes it as a `general-purpose biomedical AI agent` that can autonomously execute a wide range of biomedical tasks using reasoning, retrieval, and code execution.

The public signals are substantial:

- `2.9k stars`
- `536 forks`

The repo also exposes:

- a no-code web interface
- a know-how library
- PDF report generation
- a broad benchmark and model ecosystem

On Hugging Face, the `biomni/Biomni-R0-32B-Preview` model card says the model is a biomedical reasoning preview trained with the Biomni environment, and it showed:

- `19 likes`
- `5,138` downloads in the last month

### Why it matters to us

Biomni could help upstream of figures, for example:

- retrieving biological background
- generating candidate analysis plans
- surfacing relevant protocols or best-practice know-how
- producing draft narrative around an analysis

### Why it does not solve our figure problem

Biomni is not a figure-generation harness.

It does not present itself as:

- a publication-figure system
- a deterministic plotting engine
- a renderer with explicit font/export/source-data contracts

More importantly, the repo warns that it currently executes LLM-generated code with full system privileges and recommends isolated or sandboxed environments for production use.

That is fine for exploratory research tooling, but it is a bad fit for the core of our reproducible manuscript build.

### Verdict

`Biomni` is valuable as an upstream biomedical reasoning/planning reference, but not as the core figure engine.

## 3. SRAgent

### What it is

`SRAgent` is a focused bioinformatics agent for working with the Sequence Read Archive and related metadata and publications.

Its GitHub page showed:

- `163 stars`
- `33 forks`

It supports:

- finding datasets in SRA
- extracting sequencing metadata
- retrieving associated publications
- operating as a Claude skill for natural-language querying

### Why it matters to us

This is relevant to the manuscript harness because figure work often starts with:

- dataset discovery
- accession resolution
- manuscript retrieval
- metadata cleanup

SRAgent could therefore help our `review/` or upstream data-acquisition workflows.

### Why it does not solve our figure problem

It is not a visualization agent. I found no evidence in the public materials I reviewed that it focuses on scientific plotting, layout, export quality, or figure QA.

### Verdict

Useful for `data retrieval`, not for `figure generation`.

## 4. PlotGen

### What it is

`PlotGen` is a research framework for scientific visualization that is important conceptually even though it does not yet look like a mature public software stack.

The paper summary available via Hugging Face Papers and Adobe Research describes:

- a `Query Planning Agent`
- a `Code Generation Agent`
- a `Numeric Feedback Agent`
- a `Lexical Feedback Agent`
- a `Visual Feedback Agent`

It reports improvements over baselines on `MatPlotBench`.

### Why it matters to us

PlotGen reinforces a design pattern that matches what we want for high-quality figures:

- split planning from execution
- use multiple critics, not one
- distinguish numeric correctness from text correctness from visual correctness

That is a better mental model for figure QA than a single "did the code run?" check.

### Why I would not adopt it directly

I did not find evidence in the sources I reviewed of a mature public repo that is clearly ready to adopt as-is for our harness.

So I would treat PlotGen as:

- an architecture paper
- not a production dependency

### Verdict

Strong idea source. Weak candidate for direct adoption right now.

## Emerging Lead: PlotGDP

I found signs of a very recent `2026` bioRxiv preprint titled `PlotGDP: an AI Agent for Bioinformatics Plotting`, along with a public web server.

However, the primary bioRxiv page was not directly accessible through the browser tool in this session, so I could not fully verify the abstract from a primary source. Secondary pages describe it as:

- a web-based AI plotting agent
- based on LLM-generated code
- aimed at publication-ready bioinformatics plots
- using curated template scripts to reduce hallucinations

This is promising, but I would treat it as an `unverified lead` until we inspect the primary preprint and public code directly.

## Recommendation For This Repo

### Best decision now

Do **not** replace the current harness with any public agent.

Instead:

1. Keep our current `spec-first`, `manifest-first`, `Python+R`, `CI-reproducible` harness as the source of truth.
2. Treat `ggplotAgent` as the best external reference for an optional `agent-assisted figure drafting` layer.
3. Treat `Biomni` and `SRAgent` as upstream data-analysis and retrieval references, not renderers.
4. Borrow the `multi-critic` idea from `PlotGen` for future QA:
   - numeric critic
   - label/text critic
   - visual/layout critic

### Concretely, what we should import into our roadmap

- optional natural-language-to-figure-spec drafting
- optional reference-image-to-style drafting
- automatic code-debugging for exploratory figure generation only
- image-based figure QA as a warning system, not a source of truth
- benchmark tasks modeled on real bioinformatics figure families

### What we should not import

- prompt-only figure generation as the authoritative pipeline
- unrestricted execution of arbitrary agent-generated code inside the main build
- cloud-only figure generation with no deterministic local rebuild

## Final Assessment

If the question is:

- "Is there a public bioinformatics AI agent we should watch for figures?"

then the answer is:

- `Yes: ggplotAgent`

If the question is:

- "Should we swap our manuscript figure harness for one of these public agents?"

then the answer is:

- `No`

The right move is to build our deterministic figure harness first and later add an `agent-assisted drafting` mode inspired by the best parts of these systems.

## Sources

- ggplotAgent paper page: https://academic.oup.com/bioinformaticsadvances/article/6/1/vbaf332/8416062
- ggplotAgent PubMed: https://pubmed.ncbi.nlm.nih.gov/41542365/
- ggplotAgent GitHub: https://github.com/charlin90/ggplotAgent
- Biomni GitHub: https://github.com/snap-stanford/Biomni
- Biomni model card: https://huggingface.co/biomni/Biomni-R0-32B-Preview
- Biomni Eval1 dataset: https://huggingface.co/datasets/biomni/Eval1
- SRAgent GitHub: https://github.com/ArcInstitute/SRAgent
- PlotGen Hugging Face paper page: https://huggingface.co/papers/2502.00988
- PlotGen Adobe Research page: https://research.adobe.com/publication/plotgen-multi-agent-llm-based-scientific-data-visualization-via-multimodal-feedback/
