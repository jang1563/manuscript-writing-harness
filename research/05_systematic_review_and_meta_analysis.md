# Systematic Review And Meta-Analysis Best Practices

Reviewed: 2026-04-09

## Objective

Create a rigorous, reproducible review workflow that can support narrative reviews, systematic reviews, and quantitative meta-analysis with full audit trails.

## Quality Bar

The harness should satisfy:

- protocol-first planning
- search reproducibility
- deduplication traceability
- screening traceability
- extraction traceability
- bias assessment transparency
- PRISMA-aligned reporting

## Primary Standards

- `PRISMA 2020` for reporting
- `PROSPERO` for protocol registration when eligible
- `Cochrane Handbook` for systematic review methodology

These should anchor the process even when automation is added.

## Recommended Tooling

Search and metadata acquisition:

- `PubMed E-utilities`
- `Europe PMC REST API`
- optional `OpenAlex` for citation graph support

Screening:

- `ASReview`

Literature analytics:

- `litstudy`

Risk-of-bias support:

- `robvis` for visualization
- `RobotReviewer` only as assistive triage, never as final judgment

Quantitative synthesis:

- `metafor` in R
- `meta` in R where appropriate

## Best-Practice Workflow

### 1. Register or freeze the protocol early

Before screening begins:

- define question, population, intervention/exposure, comparator, outcomes, and study types
- define inclusion and exclusion rules
- define search databases and query logic
- define primary and secondary outcomes

If eligible:

- register in `PROSPERO`

If not:

- version the protocol in the repo and treat it as immutable once screening starts, except through tracked amendments

### 2. Version search strategies

Store each database query as a versioned artifact with:

- date run
- database
- query text
- filters
- export format
- hit count

This is essential for auditability.

### 3. Separate retrieval, deduplication, and screening

Do not collapse these into a single opaque spreadsheet step.

Instead:

- harvest records
- normalize metadata
- deduplicate
- log retained and removed records
- feed deduplicated records into screening

### 4. Use ASReview for prioritization, not for unsupervised decision making

Best practice:

- humans remain responsible for include or exclude decisions
- active learning accelerates ranking and triage
- screening state and model-assisted prioritization should be logged separately

### 5. Capture full-text reasons for exclusion

Store:

- study-level exclusion reasons
- reviewer identity
- timestamps or revision logs

This makes PRISMA generation straightforward later.

### 6. Use structured extraction forms

For each included study, capture:

- citation identifiers
- cohort and intervention details
- sample sizes
- outcome definitions
- effect sizes and uncertainty
- measurement timing
- risk-of-bias fields
- notes on heterogeneity and subgroup relevance

### 7. Treat risk-of-bias support tools as assistive only

Use `RobotReviewer` to speed triage or suggest domains.

Do not let it become the final arbiter.

Use human-reviewed structured assessments and render final bias visuals with `robvis`.

### 8. Generate PRISMA and evidence tables automatically

Required outputs:

- PRISMA flow counts
- inclusion and exclusion logs
- characteristics of included studies
- risk-of-bias tables and figures
- meta-analysis forest and funnel plots where applicable

## What The Harness Should Produce

- `protocol.md`
- search query files
- dedup logs
- screening decisions
- extraction tables
- bias assessments
- PRISMA counts and diagram inputs
- meta-analysis scripts and outputs

## Acceptance Criteria

- every screening decision is traceable
- PRISMA counts can be rebuilt from logs
- meta-analysis inputs are separated cleanly from manuscript prose
- assistive AI does not overwrite human methodological judgment

## Sources

- PRISMA official site: https://www.prisma-statement.org/
- PROSPERO official site: https://www.crd.york.ac.uk/CRDWeb/maintenancePROSPERO.html
- Cochrane Handbook: https://training.cochrane.org/handbook/current
- ASReview repo: https://github.com/asreview/asreview
- ASReview documentation: https://docs.asreview.nl/
- litstudy repo: https://github.com/NLeSC/litstudy
- robvis repo: https://github.com/mcguinlu/robvis
- RobotReviewer repo: https://github.com/ijmarshall/robotreviewer
- Europe PMC REST API: https://europepmc.org/RestfulWebService
- NCBI E-utilities book: https://www.ncbi.nlm.nih.gov/books/NBK25501/

