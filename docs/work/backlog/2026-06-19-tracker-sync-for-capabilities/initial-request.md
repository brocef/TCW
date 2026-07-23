# Tracker sync for capabilities

## Product changes

## Technical changes

## Meta changes

Per-tracker capability sync adapters (Jira / GitHub / Linear) keyed on the
`Tracker` field's `<shortname>:<id>` convention.

**Format note (refreshed 2026-07-23):** the original request said `**Tracker:**`,
the Markdown-bold field syntax from phase-3. Capabilities are now folder nodes and
the field lives as a `Tracker` key in `meta.yaml` (still a recognized field —
`tcw/store/base.py`). The shortname convention itself is unchanged; only the
storage syntax moved.

Spec: docs/plan/phase-6-beyond.md; phase-3-capabilities Part C #4.
