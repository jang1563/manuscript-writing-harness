# Manuscript Project

This folder contains the primary MyST manuscript project.

Phase 1 goals:

- one semantic manuscript source
- section-based authoring
- display-item wrappers in `display_items/` for generated figures and tables
- bibliography hookup to `../references/library.bib`
- venue-agnostic content with venue-specific overlays stored elsewhere
- explicit planning artifacts in `plans/` before drafting and refinement

Local build commands:

```bash
cd manuscript
myst build --html
```

The resulting static site will be written to:

- `_build/html`
