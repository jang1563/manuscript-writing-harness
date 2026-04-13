# Literature Intelligence And Model-Assisted Research

Reviewed: 2026-04-09

## Objective

Use modern retrieval and biomedical language models to accelerate discovery, screening, clustering, and metadata enrichment without letting models invent evidence or citations.

## Guiding Rule

Models should help with:

- finding papers
- ranking or clustering papers
- suggesting related concepts
- labeling or triaging records

Models should not be treated as:

- citation authorities
- ground-truth fact sources
- replacements for human evidence appraisal

## Strong Model Categories

### 1. Scientific embedding models

Primary recommendation:

- `SPECTER2`

Best use cases:

- finding related papers
- semantic clustering
- query expansion
- “papers like this one” retrieval

### 2. Biomedical encoder models

Primary recommendations:

- `BiomedBERT`
- `BioBERT`

Best use cases:

- biomedical text classification
- eligibility screening support
- named-entity extraction prototypes
- claim or outcome tagging

### 3. Task-specific review assistants

Use carefully for:

- abstract triage
- outcome labeling
- intervention tagging
- study-design suggestion

These should stay downstream of human review.

## Recommended Harness Uses

### Retrieval augmentation

Pipeline:

- seed with trusted known papers
- embed seed papers with `SPECTER2`
- retrieve semantically nearby works
- validate with metadata APIs before citation

### Screening assistance

Pipeline:

- use `ASReview` as the main active-learning workflow
- optionally add biomedical encoders for auxiliary relevance scoring
- keep final screening labels human-authored

### Taxonomy and outcome extraction

Pipeline:

- use biomedical encoders or controlled prompting to suggest:
  - study type
  - disease area
  - intervention class
  - outcome domains

Then:

- route all suggested labels into human review queues

### Claim verification support

Pipeline:

- detect claims in draft text
- map claims to candidate references
- require the manuscript author to approve or replace the suggested evidence

## Hard Safety Boundaries

- never insert a citation that has not been inspected by a human
- never let an LLM write the final scientific claim without visible source linkage
- store model suggestions in separate files from accepted references
- keep prompt logs for high-impact automated steps

## Recommended Data Sources

- Crossref for DOI-backed metadata
- PubMed and Europe PMC for biomedical literature metadata
- OpenAlex for citation-graph and related-work exploration
- Hugging Face models for local or hosted ranking and labeling support

## Acceptance Criteria

- model-assisted retrieval improves breadth without reducing auditability
- all accepted citations are human-verified
- model outputs can be traced and regenerated
- the harness can distinguish suggested evidence from accepted evidence

## Sources

- SPECTER2 repo: https://github.com/allenai/SPECTER2
- SPECTER2 model card: https://huggingface.co/allenai/specter2_aug2023refresh_classification
- BiomedBERT model card: https://huggingface.co/microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext
- BioBERT model card: https://huggingface.co/dmis-lab/biobert-base-cased-v1.2
- ASReview repo: https://github.com/asreview/asreview
- Europe PMC REST API: https://europepmc.org/RestfulWebService
- Crossref REST API docs: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- OpenAlex help center: https://help.openalex.org/

