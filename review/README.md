# Review Workflow

This directory supports narrative review, systematic review, and meta-analysis workflows.

Guiding standards:

- `PRISMA 2020`
- `PROSPERO`
- `Cochrane Handbook`

## Directory Structure

```
review/
├── schemas/        YAML schema definitions for each pipeline stage
├── protocol/       Review protocol and amendments
├── queries/        Versioned search strategies (one file per database)
├── retrieval/      Raw exports, normalized records, deduplication logs
├── screening/      Screening log (title/abstract and full-text)
├── extraction/     Structured study-level data extraction
├── bias/           Risk-of-bias assessments (RoB 2, ROBINS-I)
├── prisma/         Generated PRISMA counts, exclusion summaries, evidence tables
└── demo/           Synthetic demo data generator
```

## Quick Start

All operations are available through the review CLI:

```bash
cd scripts/

# Run the full demo with synthetic data
python review_cli.py demo

# Generate a package-ready evidence summary
python review_cli.py evidence

# Check pipeline status
python review_cli.py status

# Validate all artifacts
python review_cli.py validate
```

## Pipeline Stages

### 1. Initialize Protocol

```bash
python review_cli.py init
# Edit review/protocol/protocol.yml with your PICO question and criteria
```

### 2. Add Search Queries

```bash
python review_cli.py add-query --database PubMed
python review_cli.py add-query --database "Europe PMC"
# Edit each query file and place raw exports in review/retrieval/raw/
```

### 3. Retrieve and Deduplicate

```bash
python review_cli.py retrieve
# Produces: retrieval/normalized/, retrieval/dedup/, screening/screening_input.csv
```

### 4. Screen Records

```bash
python review_cli.py init-screening

# Screen title/abstract: edit screening_log.csv or prepare a decisions batch CSV
python review_cli.py apply-decisions --decisions path/to/decisions.csv

# Promote included records to full-text stage
python review_cli.py promote-fulltext

# Screen full-text: apply another batch of decisions
python review_cli.py apply-decisions --decisions path/to/ft_decisions.csv
```

### 5. Extract Data

```bash
python review_cli.py init-extraction
# Fill in review/extraction/extraction_table.csv with study data
```

### 6. Assess Risk of Bias

```bash
python review_cli.py init-bias --tool rob2
# Fill in review/bias/bias_assessments.csv with domain judgments
```

### 7. Generate PRISMA Outputs

```bash
python review_cli.py prisma
# Produces: prisma/prisma_counts.yml, prisma/exclusion_summary.csv, prisma/evidence_table.csv
```

### 8. Generate Evidence Summary And Package Manifest

```bash
python review_cli.py evidence
# Produces: reports/evidence_summary.md, reports/evidence_summary.json, manifests/review_evidence_package.json
```

## Key Design Principles

- **PRISMA counts are always derived**, never manually entered. They are computed from the versioned screening log and query files.
- **Human-in-the-loop**: AI tools (ASReview, RobotReviewer) assist but do not replace human screening or bias decisions.
- **CSV for record-level data** (screening, extraction, bias) -- editable in spreadsheets, ASReview-compatible, git-diff-friendly.
- **YAML for configuration** (protocol, queries, PRISMA counts) -- structured and human-readable.
- **Every decision is traceable**: reviewer identity, timestamps, and exclusion reasons are logged.

## Testing

```bash
python -m pytest tests/review/ -v
```
