# Figure Source

Place Python and R figure scripts here.

Current layout:

- `python/`: Python renderers
- `r/`: R renderers
- wrapper scripts at this level only for compatibility

Rules:

- one build script per figure or panel family
- no hidden notebook state
- inputs read from `../data`
- renderer-agnostic figure specs live in `../specs`
- outputs written to `../output/<renderer>/`

Current example:

- `python/build_example_figure.py`: builds the Python version of the two-panel example figure
- `r/build_example_figure.R`: builds the R version of the two-panel example figure
- `build_example_figure.py`: compatibility wrapper that dispatches to the Python renderer
