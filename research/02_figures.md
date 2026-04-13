# Figure Generation Best Practices

Reviewed: 2026-04-09

## Objective

Build a figure pipeline that produces submission-grade figures from source data and scriptable specifications, with no dependence on manual post-processing as the source of truth.

## Quality Bar

For Cell, Nature, Science, and strong conference papers, figure workflow should guarantee:

- vector-first output where possible
- consistent panel labeling and typography
- colorblind-aware palettes
- explicit legend ownership
- reproducibility from frozen inputs
- source-data export aligned with the manuscript

## Recommended Tooling

Primary Python stack:

- `matplotlib` for low-level publication control
- `seaborn` for high-level statistical plotting
- optional domain libraries only when they can still emit stable matplotlib objects

Primary R stack:

- `ggplot2` for statistical plotting
- `patchwork` for multi-panel composition
- optional `cowplot` or `ggtext` where needed

Output strategy:

- `PDF` or `SVG` as the authoritative vector output
- `PNG` for preview artifacts
- `TIFF` only when the target journal explicitly requires it

## Figure Pipeline Design

### 1. Freeze figure inputs

Each figure should consume:

- a frozen input table or serialized analysis artifact
- a figure config file that records parameters
- a script or notebook that renders the figure

Never let figures depend on hidden interactive state.

### 2. Treat each panel as its own buildable unit

Recommended structure:

- build panels individually
- compose them into multi-panel display items in a separate step
- store panel metadata such as caption stubs, source-data files, and panel letters

This mirrors how top-tier papers are actually reviewed and revised.

### 3. Keep legends and narrative text separate

Best practice:

- the figure image should carry only the visual payload
- the full figure legend should live in the manuscript source
- panel-specific narrative should not be baked into the image unless the journal style clearly expects it

### 4. Enforce style centrally

Define a project-wide figure theme that controls:

- fonts
- font sizes
- line widths
- palette families
- panel label placement
- export size rules
- rasterization thresholds for very dense plots

Do not style each figure ad hoc.

### 5. Export source data automatically

For every figure or panel:

- write the plotted data to `CSV` or `TSV`
- include units and variable labels
- version the exact source-data artifact that supports the rendered figure

This is especially important for Nature-family submissions.

## Journal-Specific Considerations

### Nature-family

Plan for:

- production-quality figures only when requested
- source data files for main figures
- extended data display items
- separate high-resolution export steps

### Cell-family

Plan for:

- main figures plus supplements
- graphical abstract as a distinct figure class
- figure counts and display item organization that match editorial expectations

### Conference submissions

Plan for:

- page-aware figure compression and sizing
- grayscale legibility when printed
- smaller legends without losing interpretability

## What To Avoid

- Illustrator or PowerPoint as the only place where final scientific truth exists
- manual drag-and-drop panel assembly with no reproducible record
- inconsistent significance annotation conventions
- changing axis ranges manually for cosmetic reasons without recording the change
- color maps that obscure values or fail colorblind checks

## Best-Practice Automation

Add automated checks for:

- missing source-data files
- missing captions or legend stubs
- inconsistent figure dimensions
- font-size drift across figures
- non-embedded panel letters
- unexpected raster output where vector output should exist

## Acceptance Criteria

- every figure is reproducible from code and frozen inputs
- every main figure has a matching source-data artifact
- multi-panel figures can be rebuilt without manual layout work
- a venue-specific export target can rebuild the entire figure set

## Sources

- Nature formatting guide: https://www.nature.com/nature/for-authors/formatting-guide
- matplotlib repo: https://github.com/matplotlib/matplotlib
- seaborn repo: https://github.com/mwaskom/seaborn
- ggplot2 repo: https://github.com/tidyverse/ggplot2
- patchwork repo: https://github.com/thomasp85/patchwork
- MyST figures guide: https://mystmd.org/guide/figures

