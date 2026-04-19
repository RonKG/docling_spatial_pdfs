---
name: docs
description: Map of the Kenya Gazette library's canonical reference docs (spec, roadmap, layout-detection changelog). Use when the user asks about output envelope shape, public API, identity keys, schema versioning, milestones, MVP scope, architecture blueprints, comparability rules, or the history of two-column / spatial reading-order changes. Reads only the one doc that answers the question rather than skimming all three.
---

# Kenya Gazette reference docs

The project keeps three canonical reference docs. Pick the one that answers the question; do not read all three.

## Lookup table

| If the user asks about... | Read this doc |
| --- | --- |
| Output shape, `Envelope` / `Notice` / `Corrigendum` fields, public API (`parse_file`, `parse_bytes`, `write_envelope`, `GazetteConfig`, `Bundles`), identity keys (`gazette_issue_id`, `notice_id`, `pdf_sha256`, `content_sha256`), key-strategy options A vs B (composite vs surrogate), `schema_version` / `output_format_version` rules | [`docs/library-contract-v1.md`](../../../docs/library-contract-v1.md) |
| Architecture blueprints (notebook + wrapper / clean package / swappable stages), MVP-1.0 scope, M0-M6 milestone list, comparability rules across versions, post-1.0 plans (Stage `Protocol`s, ML stages, CLI, PyPI publish) | [`docs/library-roadmap-v1.md`](../../../docs/library-roadmap-v1.md) |
| Spatial reading-order algorithm history, two-column merge fixes, band-classification heuristic changes, layout-detection regressions, the reasoning behind a specific reordering decision | [`docs/spatial_reorder_changelog.md`](../../../docs/spatial_reorder_changelog.md) |

## Day-to-day execution

For "what should I do next?" questions, **do not read these reference docs.** The answer lives in [`PROGRESS.md`](../../../PROGRESS.md) at the repo root — find the next ⬜ row in its features table. This skill is for design and history questions only.
