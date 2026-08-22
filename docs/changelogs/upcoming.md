# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Changed

- `work.documentation` entry uniqueness is keyed on the `(path, trigger)` pair
  rather than on `path` alone (`parse_documentation_entries`,
  `tcw/store/base.py`). One file may now carry several entries so long as their
  triggers differ; two entries agreeing on both halves are still rejected, and
  every other shape check is unchanged. This matches the identity
  `_parse_bindings` already uses for lifecycle bindings, `(kind, value, when)`.
- The duplicate-entry problem names the trigger as well as the path —
  `duplicate 'path' 'README.md' under trigger 'Public-CLI-API', already declared
  by entry 0` — so a reader can tell which of two near-identical entries
  collided. The message still begins `work.documentation entry N: duplicate`.

## Internal

- Wrote the two capability records the `work.documentation` item declared in its
  spec but never created — *Declare which documents track which changes* and
  *Read the documentation gate for a change*, both `Supported` under
  `docs/capabilities/work/`. Filed
  `2026-08-21-nothing-enforces-a-spec-s-declared-capability-deltas-without-a-capabilities-yaml`
  for the gap that let a declared delta complete with the ledger untouched:
  `capabilities.yaml` is what the completion gate reads, and nothing requires
  one even when a spec's `## Capability changes` section is non-empty.
