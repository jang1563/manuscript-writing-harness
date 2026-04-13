# Table Generation Best Practices

Reviewed: 2026-04-09

## Objective

Make tables script-generated, schema-driven, and journal-portable, so the manuscript never depends on manually edited tables as its authoritative source.

## Quality Bar

Best-practice manuscript tables should be:

- generated from source data or model outputs
- type-safe and schema-aware
- easy to restyle across venues
- easy to export for supplementary spreadsheets
- easy to audit for rounding and missingness

## Recommended Tooling

R-first options:

- `gt` for polished publication tables
- `gtsummary` for clinical and statistical summary tables
- `flextable` when Word-oriented outputs matter

Python-first options:

- `pandas` for data wrangling and table staging
- `great_tables` where polished table rendering is needed
- plain CSV plus manuscript-layer rendering when journal simplicity matters more than styling

Recommendation:

- keep canonical table data as `CSV` or `Parquet`
- treat formatted tables as render targets

## Table Classes The Harness Should Support

- manuscript main tables
- supplementary tables
- cohort and baseline characteristic tables
- model performance tables
- ablation tables
- differential analysis result tables
- search strategy and screening tables
- data dictionary tables
- risk-of-bias tables
- reagent and resource tables

## Best-Practice Workflow

### 1. Define table schemas early

Each table should specify:

- column names
- units
- value types
- rounding rules
- sort order
- missing-value handling
- footnote rules

This prevents last-minute editorial cleanup from turning into scientific drift.

### 2. Separate canonical data from display formatting

For each table:

- canonical data lives in machine-readable files
- formatting logic lives in scripts
- manuscript embedding points to the rendered artifact

### 3. Encode footnotes and abbreviations as metadata

Do not hard-code them repeatedly.

Instead:

- store abbreviations centrally
- generate consistent footnotes
- ensure symbols and superscripts are stable across venues

### 4. Keep supplementary exports easy

Every main or supplementary table should be exportable to:

- manuscript-ready markdown or LaTeX
- CSV
- Excel when collaborators need it

### 5. Lint numerical integrity

Automate checks for:

- percentages summing incorrectly
- inconsistent decimal precision
- p-value formatting drift
- impossible confidence interval ordering
- inconsistent sample sizes between figure and table outputs

## Journal-Specific Considerations

### Nature-family

- plan for `Extended Data` tables as a separate class
- preserve source files because some extended-data items behave differently from print tables

### Cell-family

- support `Key Resources Table` as a structured special case

### Conferences

- compact style and page-aware row reduction matter more than decorative formatting

## Acceptance Criteria

- every table is code-generated from canonical data
- supplementary spreadsheets can be emitted automatically
- table formatting can change by venue without editing the scientific values
- CI can detect rounding or schema regressions

## Sources

- pandas project: https://github.com/pandas-dev/pandas
- gt project: https://gt.rstudio.com/
- gtsummary project: https://www.danieldsjoberg.com/gtsummary/
- Quarto tables docs: https://quarto.org/docs/authoring/tables.html
- Nature formatting guide: https://www.nature.com/nature/for-authors/formatting-guide
- Cell Press STAR Methods update: https://crosstalk.cell.com/blog/a-star-upgrade

