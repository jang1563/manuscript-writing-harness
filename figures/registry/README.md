# Figure Class Registry

This directory defines reusable figure classes for the manuscript figure library.

The class registry is the source of truth for:

- supported figure classes
- required input shapes
- renderer support expectations
- default QA and review presets
- scaffold generation templates
- implemented family metadata such as `family`, `expertise_track`, and `default_style_profile`

Instance specs still live under `figures/specs/`, but each spec must reference a class declared here.

Planned families and not-yet-implemented classes are tracked separately in `figures/registry/roadmap.yml`.
