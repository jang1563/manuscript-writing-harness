# Scientific Figure Generation Harness Deep Dive

Reviewed: 2026-04-09

## Objective

Define a publication-grade scientific figure harness for this repository that supports both `Python` and `R`, produces professional and visually strong figures, preserves scientific accuracy, and can survive the expectations of `Nature`, `Cell`, `Science`, and strong conference venues.

## Bottom Line

The best figure harness for this repo is not "Python or R." It is a `shared contract` with `two first-class renderers`:

- `Python` for general plotting, custom panel engineering, image overlays, and tight low-level layout control
- `R` for statistical graphics, composition-heavy `ggplot2` workflows, and dense domain-specific figures such as `ComplexHeatmap`

The shared contract should define:

- canonical input data
- a figure spec
- centralized theme tokens
- vector and raster export rules
- source-data exports
- machine-readable manifests
- CI checks
- visual regression testing

In other words: `one harness, two languages, one output standard`.

## What "Best Quality" Actually Means

For this harness, "beautiful" is not ornamental. It means the figure is:

- scientifically faithful
- legible at journal size
- typographically consistent
- accessible to readers with colour-vision deficiency
- editable by production teams
- reproducible from raw inputs
- auditable months later during revision

This is consistent with both official publisher guidance and the strongest open-source tooling patterns.

## What Official Guidance Says

### Nature is unusually explicit, and that is useful

Nature's current figure guidance is detailed enough to serve as the strict baseline for the harness, even when the final target is not Nature.

Key requirements from the Nature Research Figure Guide:

- all figure text must be `legible` and `editable`
- use standard sans-serif fonts such as `Arial` or `Helvetica`
- do not outline text
- embed fonts as `True Type 2` or `42`
- text should generally stay between `5 pt` and `7 pt`
- multi-panel figure labels should be `8 pt`, `bold`, `upright`, and `lowercase a, b, c`
- main figures should be `vector` files with editable layers
- preferred main-figure formats are `.pdf` or `.eps`; `.svg` is acceptable
- for images, Nature recommends `RGB`
- photographic images should be at least `300 dpi`, with `450 dpi` effectively the upper useful target for proofs
- scale bars should remain on a separate editable layer rather than being flattened into the image

Nature also gives concrete figure size targets:

- `89 mm` single column
- `183 mm` double column
- `170 mm` maximum height

This has an important harness implication:

- `PNG` should be a preview artifact, not the authoritative main-figure source
- the authoritative artifact should usually be `PDF` or `SVG`

### Nature's image-integrity rules are directly relevant to the harness

Nature's image-integrity page is also strong enough to shape implementation policy:

- the final image must correctly represent the original data
- images from different samples or time points should not be silently combined
- if juxtaposition or splicing is necessary, it must be visibly marked and explained
- cloning, healing, erasing, and content-aware tools are disallowed on scientific image data
- adjustments such as contrast changes should be applied to the whole image and equally to controls
- generative AI is not permitted in figures, including content-aware editing tools

This means the harness should treat microscopy, gel, and blot panels as `high-risk figure classes` with stricter provenance and linting than ordinary charts.

### Publisher ethics reinforce the same direction

Elsevier's publishing-ethics policy is broader and less technical than Nature's figure guide, but it reinforces the same point: the scholarly record depends on transparent, ethical, and auditable presentation practices. For our purposes, the most important inference is that image processing and figure assembly should be governed by explicit rules, not taste.

## What Top Researchers and Mature Toolchains Suggest

The strongest recurring pattern across top research practice, mature plotting libraries, and figure-design guidance is:

1. explore however you need to
2. present programmatically
3. separate content from styling
4. separate panel generation from panel assembly
5. keep the plotted data and figure metadata versioned

Claus Wilke's discussion of reproducibility and repeatability is especially relevant here. He distinguishes:

- `reproducibility`: another person can regenerate a figure that conveys the same message from the same data and transformations
- `repeatability`: another person can recreate the exact same appearance, down to random jitter and rendering choices

That distinction matters for a manuscript harness. We want both:

- reproducibility for science
- repeatability for submission revisions and CI

His recommendation to move away from interactive figure production and toward scripted generation aligns directly with the direction of this repo.

## Recommended Architecture

### Core design

The harness should be built around a shared figure contract, not around a single plotting library.

Recommended build model:

1. ingest frozen input data
2. generate one or more panel-level plots
3. export panel-level source data
4. assemble multi-panel figures in a dedicated composition step
5. export authoritative vector outputs plus preview rasters
6. write a manifest describing exactly what was built
7. run QA and regression checks

### Contract fields

Each figure should have a spec with fields like:

- `figure_id`
- `title`
- `figure_class`
- `renderer` (`python` or `r`)
- `panel_order`
- `target_profile`
- `width_mm`
- `height_mm`
- `theme_id`
- `font_policy`
- `data_inputs`
- `source_data_outputs`
- `output_files`
- `legend_owner`
- `image_integrity_flags`
- `qa_checks`
- `random_seed`

Each build should emit a manifest with fields like:

- Git commit or working-tree hash
- build timestamp
- package versions
- exact input files and checksums
- exact output files and checksums
- final canvas dimensions
- declared fonts
- palette identifiers
- whether any layers were rasterized

### Panels should be first-class build units

This is one of the biggest improvements we can make over ad hoc lab workflows.

The harness should prefer:

- `panel_a.py` / `panel_a.R`
- `panel_b.py` / `panel_b.R`
- an explicit `assemble_figure_01.*`

instead of:

- one huge script that draws everything at once
- or worse, a manual Illustrator/PowerPoint assembly as the only final truth

Panel-first architecture makes revision easier, improves source-data export, and maps well to how reviewers actually discuss figures.

### Keep captions and legends outside the image

Inference from publisher guidance and top figure-design practice:

- the figure image should carry only essential visual payload
- the full figure legend should live in manuscript source
- narrative prose should not be baked into the artwork

Exceptions exist for schematics or workflows, but even then the harness should prefer short labels over paragraph-like annotation.

## Recommended Python Stack

### Canonical renderer: `matplotlib`

`matplotlib` should remain the Python authority because it gives the most control over:

- typography
- vector export
- panel layout
- rasterization of selected artists
- metadata-aware saving
- stable CI rendering

Important current Matplotlib guidance:

- `constrained layout` is the preferred automatic layout engine for clean multi-panel figures
- it handles labels, legends, colorbars, nested layouts, `subfigures`, and `subplot_mosaic`
- it should be enabled `before` axes are created
- calling `tight_layout()` disables constrained layout

That implies our harness should standardize on:

- `layout="constrained"`
- `subplot_mosaic()` or `subfigures()` for compound figures
- explicit `Axes.legend()` rather than `Figure.legend()` when we want constrained layout to behave well

### Statistical layer: `seaborn`

`seaborn` is useful for higher-level statistical plotting, but the final object model should still terminate in Matplotlib. In practice:

- use seaborn for convenient statistical layers
- use Matplotlib for final typography, layout, export, and multi-panel assembly

### Label collision handling: `adjustText`

`adjustText` is the Python equivalent of `ggrepel` for many use cases. It is specifically designed to minimize overlapping labels in Matplotlib plots. That makes it appropriate for:

- direct labeling of highlighted points
- reducing overreliance on legends
- creating clean scatter and volcano plots

### Style accelerant, not source of truth: `SciencePlots`

`SciencePlots` is a good convenience layer and has venue-inspired styles such as `science`, `ieee`, and `nature`. It is useful as a reference or optional style preset, but it should not be our canonical style authority.

Reasons:

- it is still a style library, not a manuscript-specific design system
- it brings `LaTeX` requirements for some modes
- it cannot encode our project-specific source-data, QA, or venue rules

Best use:

- borrow good defaults
- keep our own central theme as the source of truth

### Visual regression: `pytest-mpl`

`pytest-mpl` is one of the most valuable Python additions for a serious figure harness.

It supports:

- image comparison against reference figures
- RMS-difference thresholds
- hash comparison modes

This gives us a real way to catch:

- broken layout
- clipped text
- accidental style drift
- unexpected rendering changes after library upgrades

### Python recommendation summary

Default Python stack:

- `matplotlib`
- `seaborn`
- `adjustText`
- `pytest-mpl`

Optional and situational:

- `SciencePlots`
- domain libraries that still return stable Matplotlib artists

## Recommended R Stack

### Canonical renderer: `ggplot2`

`ggplot2` should be the R authority for statistical plots, especially when the research team already thinks in grammar-of-graphics terms.

Its biggest strengths for this harness are:

- clear data-to-aesthetic mappings
- strong theme system
- excellent ecosystem for statistical layers
- good interoperability with composition and device packages

`ggsave()` is a perfectly reasonable export wrapper if we are explicit about:

- filename
- device
- width
- height
- units
- dpi for raster outputs

The harness should never rely on "whatever the last displayed plot was" in CI.

### Multi-panel composition: `patchwork`

`patchwork` is the best default for composition-heavy `ggplot2` workflows.

It extends the `+` idiom to plot assembly, supports:

- hierarchical composition
- layout control
- tables
- non-ggplot content
- multi-page alignment workflows

This makes it the natural R counterpart to Matplotlib's `subplot_mosaic` and `subfigures`.

### Alignment specialist: `cowplot`

`cowplot` remains valuable even in a patchwork-first setup because it separates `alignment` from `arrangement`.

That is exactly the kind of behavior we want for difficult figure sets where:

- one panel is faceted
- another is not
- axes differ
- or a panel must be aligned first and arranged later

### Label collision handling: `ggrepel`

`ggrepel` remains one of the best examples of mature scientific plotting ergonomics. It exists specifically to repel overlapping labels away from points, edges, and each other.

This makes it a core package for:

- labeled scatter plots
- volcano plots
- Manhattan plots
- endpoint highlighting

### Vector output: `svglite`

`svglite` is highly relevant to a journal-grade harness because it:

- produces clean SVG output
- leaves text as text, which improves editability
- generates smaller files than base `svg()`
- supports web-font embedding

That lines up well with publisher requirements for editable text and vector outputs.

For venue profiles that prefer `PDF`, the device choice and resulting font behavior should also be made explicit and validated in CI rather than left to defaults.

### Raster output: `ragg`

`ragg` is the best default raster device in R for this harness.

Important properties:

- higher-quality raster rendering than standard grDevices raster devices
- system-independent rendering across macOS, Windows, and Linux
- direct access to system fonts
- strong anti-aliasing
- good rotated-text quality
- easy drop-in replacement for `png()`, `jpeg()`, and `tiff()`

That OS-consistency point is especially important for CI.

### Font management: `systemfonts`

`systemfonts` gives us a real answer to the usual "works on my laptop" font problem in R.

It can:

- locate installed fonts across platforms
- map requested families to actual files
- work with project-local `./fonts`
- declare font dependencies programmatically

This is exactly what we want for a reproducible manuscript repo.

### Accessibility and palette tooling: `colorspace` and `colorblindr`

For R, the accessibility story is strongest when we combine:

- a curated project palette
- `colorspace` for perceptual colour work and colour-vision-deficiency checks
- `colorblindr` when explicit simulated previews are useful

### Dense scientific heatmaps: `ComplexHeatmap`

`ComplexHeatmap` is important enough to treat as a special recommendation rather than just another package.

For genomics, multi-omics, and annotation-heavy heatmaps, it is often stronger than trying to force `ggplot2` to do everything. Its reference book emphasizes:

- annotations
- heatmap lists
- legends
- decorations
- integration with other packages

For a bioinformatics-oriented harness, that matters a lot.

### Visual regression: `vdiffr`

`vdiffr` is the R analogue to `pytest-mpl` and should be part of the long-term plan.

It:

- records reproducible SVG snapshots
- stores them as testthat snapshots
- supports human review of changed plot outputs

That gives us a way to guard against silent layout and rendering drift in the R pipeline.

### R recommendation summary

Default R stack:

- `ggplot2`
- `patchwork`
- `ggrepel`
- `svglite`
- `ragg`
- `systemfonts`
- `vdiffr`

Specialized but highly recommended:

- `cowplot`
- `colorspace`
- `colorblindr`
- `ComplexHeatmap`

## Cross-Language Design Policy

This is where the harness becomes more than a set of packages.

### Theme tokens should be shared

Both Python and R should consume the same theme definition:

- font families
- font fallbacks
- base sizes
- panel-label sizes
- line widths
- color tokens
- grayscale tokens
- spacing
- export sizes

Recommended policy:

- define theme in `YAML` or `JSON`
- resolve it into language-specific settings
- never hand-style figures ad hoc in each script

### Use a real font policy

Current repo note: our example theme still uses `DejaVu Sans`. That is fine for development, but it should not be the long-term publication default.

Recommended publication font policy:

- preferred: `Arial` or `Helvetica`
- OSS-compatible fallback: `Nimbus Sans` or an explicitly vendored sans-serif
- development fallback only: `DejaVu Sans`

The key is not only which font we prefer, but that the font choice is:

- declared
- discoverable
- portable
- embedded correctly

### Use direct labeling more often

Wilke's colour guidance and the Nature figure guide both push in the same direction:

- do not force the reader to decode crowded legends if direct labels will do
- avoid large categorical colour vocabularies
- avoid coloured text where lines, keys, or keylines would work better

Inference for the harness:

- prefer direct labels for highlighted series or selected points
- reserve legends for cases with genuine scale or group complexity

### Avoid rainbow defaults and inaccessible palettes

Nature explicitly warns against inaccessible colour choices, and Matplotlib's colormap guide strongly favors perceptually uniform colormaps for many tasks.

Practical harness defaults:

- sequential: `viridis` or `cividis`
- diverging: field-appropriate diverging maps with monotonic lightness behavior
- categorical: a small, curated accessible palette
- do not use `jet`/rainbow-style defaults
- do not use red/green pairs as the main discriminant

### Prefer raw data plus summary

This is partly inference and partly experience, but it is very consistent with top-tier review culture:

- do not default to bar-only summaries when raw observations matter
- where appropriate, show individual points, intervals, densities, or distributions
- record exactly what summary statistic and uncertainty band is being shown

The harness should make "show raw data + summary" easier than "show bar + SEM and hide everything else."

## Export Policy

### Authoritative outputs

For main figures:

- `PDF` or `SVG` should be authoritative
- `PNG` should be preview-only
- `TIFF` should be produced only for venues or workflows that explicitly require it

### Selective rasterization is acceptable

Dense layers such as:

- huge scatter clouds
- very large heatmaps
- microscopy images inside a panel

can be rasterized inside an otherwise vector figure if:

- the figure remains faithful
- the rasterization is intentional and documented
- the final output still keeps text, keys, and shapes editable where possible

### Venue profiles should be explicit

The harness should define export profiles like:

- `nature_main`
- `nature_extended_data`
- `cell_main`
- `science_main`
- `conference_camera_ready`

These profiles should control:

- width and height
- accepted file types
- panel-label casing
- dpi targets for raster layers
- font policies
- grayscale or black-and-white fallback requirements

## Quality Assurance and CI

This is where a good figure harness becomes a great one.

### Mandatory checks

Every figure build should check:

- source data exists for every panel that requires it
- all declared outputs were produced
- file dimensions match the selected venue profile
- text sizes are within allowed range
- panel labels are present and ordered
- required fonts were resolved
- vector outputs contain text layers where expected
- raster previews exist
- manifest is complete

### Accessibility checks

The harness should also check:

- palette passes colour-vision-deficiency simulation
- contrast is sufficient for text and annotations
- no key scientific distinction is carried by colour alone

### Visual regression checks

Long-term target:

- `pytest-mpl` for Python figures
- `vdiffr` for R figures

These tests should run in CI for stable example figures and for any panel classes we treat as canonical templates.

### Integrity checks for scientific images

For image-heavy figures, the harness should support stricter provenance:

- original image hash
- crop coordinates
- contrast parameters
- normalization flag
- splice markers
- raw-gel or raw-image attachment path

This should be separate from ordinary chart QA.

## How Hugging Face Models Can Help

The right role for Hugging Face here is `QA augmentation`, not figure generation.

That is a crucial distinction.

The harness should not use generative models to invent figure content. That would be incompatible with strong scientific practice and, for Nature, would directly conflict with current figure policy.

Useful model roles instead:

### 1. Chart-to-table extraction

`google/deplot` is useful because it is explicitly chart-focused. It can help with:

- extracting chart structure from rendered figures
- cross-checking that a simple chart still encodes the expected values
- catching export-time corruption in axes or legends

`ChartQA` is relevant as a benchmark/data resource for chart understanding tasks.

### 2. OCR and label validation

`microsoft/trocr-base-printed` and `naver-clova-ix/donut-base-finetuned-docvqa` are useful for:

- OCR-style checks on axis labels and legends
- verifying that text remains readable after export
- catching missing or malformed labels in preview images

### 3. General multimodal QA

For broader figure QA, a recent multimodal model can act as a secondary checker.

As of `2026-04-09`, the `Qwen/Qwen2.5-VL-7B-Instruct` model card explicitly says it is capable of analyzing `texts, charts, icons, graphics, and layouts within images`, and it reports stronger `ChartQA` performance than the older `Qwen2-VL-7B-Instruct` page.

That makes it a plausible optional QA assistant for prompts like:

- "How many panels are visible?"
- "What is the x-axis label?"
- "Are there two conditions or three?"
- "Does the legend mention the same groups as the source data?"

### Hard rule for model-assisted QA

These models should only produce:

- warnings
- candidate discrepancies
- human-review suggestions

They should never:

- approve figures automatically
- replace source-data validation
- determine scientific correctness on their own

## Recommendation for This Repository

### Strategic choice

Move from the current single example Python figure to a `dual-language figure harness` with one shared contract.

### Proposed next repo shape

Recommended expansion under `figures/`:

```text
figures/
├── config/
│   ├── project_theme.yml
│   ├── venue_profiles.yml
│   └── font_policy.yml
├── specs/
│   ├── figure_01.yml
│   └── ...
├── src/
│   ├── python/
│   ├── r/
│   └── shared/
├── panels/
│   └── source_data/
├── output/
├── manifests/
├── tests/
│   ├── python/
│   └── r/
└── fonts/
```

### Immediate implementation priorities

1. Keep `matplotlib` as the Python core renderer.
2. Add an `R` path with `ggplot2 + patchwork + svglite + ragg`.
3. Replace the current informal theme with a stricter shared theme and font policy.
4. Add a figure manifest schema shared by Python and R.
5. Add at least one `pytest-mpl` example and one `vdiffr` example.
6. Add venue-aware export profiles, with Nature as the strictest starting profile.
7. Add an accessibility preflight.
8. Add a high-risk image-figure policy for microscopy/gels/blots.

### Design choice I would make now

If we are aiming for `Cell/Nature/Science` quality, the harness should be:

- `Matplotlib-first` on the Python side
- `ggplot2-first` on the R side
- `vector-first` on export
- `manifest-first` on reproducibility
- `panel-first` on architecture
- `QA-first` on CI

That is the clearest path to professional, beautiful, accurate figures without turning style into manual labor.

## Sources

### Official and primary sources

- Nature formatting guide: https://www.nature.com/nature/for-authors/formatting-guide
- Nature research figure guide overview: https://research-figure-guide.nature.com/figures/
- Nature research figure guide, specifications: https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/
- Nature research figure guide, building and exporting panels: https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/
- Nature research figure guide, image integrity: https://research-figure-guide.nature.com/figures/image-integrity/
- Elsevier publishing ethics: https://www.elsevier.com/about/policies-and-standards/publishing-ethics
- Matplotlib constrained layout guide: https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html
- Matplotlib colormap guide: https://matplotlib.org/stable/users/explain/colors/colormaps.html
- Matplotlib font family example: https://matplotlib.org/stable/gallery/text_labels_and_annotations/font_family_rc.html
- ggplot2 `ggsave()` reference: https://ggplot2.tidyverse.org/reference/ggsave.html
- patchwork assembly guide: https://patchwork.data-imaginist.com/articles/guides/assembly.html
- cowplot alignment guide: https://wilkelab.org/cowplot/articles/aligning_plots.html
- svglite docs: https://svglite.r-lib.org/
- ragg docs: https://ragg.r-lib.org/
- systemfonts docs: https://systemfonts.r-lib.org/
- colorspace docs: https://colorspace.r-forge.r-project.org/
- vdiffr docs: https://vdiffr.r-lib.org/
- pytest-mpl docs: https://pytest-mpl.readthedocs.io/en/latest/
- Wilke, choosing visualization software: https://clauswilke.com/dataviz/choosing-visualization-software.html
- Wilke, common pitfalls of colour use: https://clauswilke.com/dataviz/color-pitfalls.html
- Wilke, multi-panel figures: https://clauswilke.com/dataviz/multi-panel-figures.html
- ComplexHeatmap reference book: https://jokergoo.github.io/ComplexHeatmap-reference/book/

### GitHub repositories worth learning from

- Matplotlib: https://github.com/matplotlib/matplotlib
- seaborn: https://github.com/mwaskom/seaborn
- SciencePlots: https://github.com/garrettj403/SciencePlots
- adjustText: https://github.com/Phlya/adjustText
- ggplot2: https://github.com/tidyverse/ggplot2
- patchwork: https://github.com/thomasp85/patchwork
- cowplot: https://github.com/wilkelab/cowplot
- ggrepel: https://github.com/slowkow/ggrepel
- svglite: https://github.com/r-lib/svglite
- ragg: https://github.com/r-lib/ragg
- systemfonts: https://github.com/r-lib/systemfonts
- vdiffr: https://github.com/r-lib/vdiffr
- ComplexHeatmap: https://github.com/jokergoo/ComplexHeatmap
- colorblindr: https://github.com/clauswilke/colorblindr

### Hugging Face models and datasets

- `google/deplot`: https://huggingface.co/google/deplot
- `HuggingFaceM4/ChartQA`: https://huggingface.co/datasets/HuggingFaceM4/ChartQA
- `microsoft/trocr-base-printed`: https://huggingface.co/microsoft/trocr-base-printed
- `naver-clova-ix/donut-base-finetuned-docvqa`: https://huggingface.co/naver-clova-ix/donut-base-finetuned-docvqa
- `Qwen/Qwen2.5-VL-7B-Instruct`: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
