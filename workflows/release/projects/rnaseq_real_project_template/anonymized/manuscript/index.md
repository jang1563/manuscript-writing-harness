---
title: Working Manuscript
subtitle: Venue-agnostic scientific article scaffold
short_title: Working Manuscript
authors:
- name: Anonymous Authors
affiliations:
- id: anon-1
  institution: Withheld for blind review
date: 2026-04-09
keywords:
- placeholder
parts:
  abstract: 'Replace this placeholder with a structured abstract or journal-appropriate
    summary.

    Keep the abstract venue-agnostic here and let the overlay decide final placement
    if needed.

    '
  data_availability: 'Add the data availability statement here.

    '
  code_availability: 'Add the code availability statement here.

    '
  competing_interests: 'Declare competing interests here.

    '
  author_contributions: Add CRediT-aligned author contribution details here.
---

# Working Manuscript

This document is the single semantic source of truth for the manuscript body.

Use venue overlays to adapt it for:

- `Nature`
- `Cell`
- `Science`
- top-conference variants

## Abstract

Replace this placeholder with a structured abstract or journal-appropriate summary.
Keep the abstract venue-agnostic here and let the overlay decide final placement if needed.

## Sections

```{include} sections/01_summary.md
```

```{include} sections/02_introduction.md
```

```{include} sections/03_results.md
```

```{include} sections/04_discussion.md
```

```{include} sections/05_methods.md
```

```{include} sections/06_acknowledgements.md
```

```{include} sections/07_funding_and_statements.md
```
