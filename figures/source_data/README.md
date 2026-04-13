# Figure Source Data

Write journal-ready source-data exports here.

Recommended future convention:

- one subfolder per figure
- one file per panel or derived summary table
- include units and column descriptions in companion metadata

Current example convention:

- `figure_01_panel_a.csv`
- `figure_01_panel_b.csv`

Each source-data export should be readable without the plotting code and should expose enough columns to reconstruct the plotted values.

These files are figure-level artifacts shared by both the Python and R renderers.

They should also stay aligned with the corresponding figure fact sheet and display-item map.
