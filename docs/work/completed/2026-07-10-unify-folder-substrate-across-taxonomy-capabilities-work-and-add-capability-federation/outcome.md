# Outcome

Work completed successfully. Both phases implemented, verified, and committed on
the work branch; full suite green (497 passed).

## What changed

**Phase A — unified folder substrate**
- `FsTreeStore` gained shared folder read/write (`_load_node`/`_write_node`);
  `FsTaxonomyStore` rewired onto it with zero behaviour change (its tests are the
  safety net).
- `Capability` is now a path-addressed folder node (`meta.yaml` + `description.md`)
  with an opaque stable `id`, `origin`, `qualified`; dropped `file_id`,
  `heading_slug`, `ref`, `CapabilityFile`, `add_entry`, `--folder`,
  `#heading`/`[state]` addressing, and the dead state-variant/sidecar code.
  `Subject` is multi-valued.
- `tcw capabilities add/show/list/set/search/check` are path-addressed; new
  `extends` subcommand; serve create route + SPA (`app.js`) use `path`/`id`/
  `origin`, create form takes a path.
- Work path-input locator in `resolve_qualified_work_ref` (`<status>/…/<slug>`),
  status segment validated against the item's real status.
- `scripts/migrate_capabilities_to_folders.py` (dry-run default, `--apply`,
  reproducible sha1 ids, single-heading collapse, equality-gated delete); ran it
  on `docs/capabilities/` (38 capabilities migrated).

**Phase B — capability federation**
- `extends` for capabilities (nested stores, `_seen` cycle guard) — plumbing
  landed in Phase A.
- Override resolution: a local folder with `overrides: <id>` (bare or
  `<alias>/<id>`) is a delta merged onto an inherited capability by upstream id.
  Fields partial-merge (YAML `null` clears); body =
  `prependedDocs` + (local `description.md` else upstream raw) + `appendedDocs`.
- `check` validates override targets (dangling / ambiguous / must-be-inherited),
  attachment lists (missing / unlisted-extra), and federation cycles.

## Verification performed

- **Full pytest suite green: 497 passed** (baseline 473 + 24 net new; capability
  tests migrated to the folder model, new `test_capabilities_federation.py`,
  status-path-locator tests).
- **End-to-end CLI federation smoke test** reproducing the original scenario: a
  `base` repo declares "Upload an image"; a `mobile` repo `extends` it, overrides
  status to `Missing`, and appends a camera note — `tcw capabilities show` renders
  the composed body (upstream prose + appended camera sentence) with the
  overridden status; `check` clean.
- **Serve smoke test**: `/api/capabilities` list/detail/create return
  `path`/`id`/`origin`/`qualified`; nested paths resolve via `%2F`.
- **Migration idempotence**: re-running the script is a no-op; equality test over
  the full `CAP_FIELDS` set passes.

## Deviations from plan.md

- Docs (A-T7 + B-T4) were done in a **single sync pass after Phase B** rather than
  per-phase, to avoid rewriting the same README/SKILL/changelog twice. All four
  Documentation Sync entries updated (+ tcw-work SKILL for the path locator).
- Federation *plumbing* (`extends`/`get_by_id`/`origin`/`qualified`/cycle guard)
  landed in the Phase A commit rather than Phase B, since splitting a single store
  class mid-implementation was artificial; Phase B added only override + body
  composition on top.

## Follow-up notes (not yet TCW items — closeout decision)

- **③ deferred spec**: `tcw://(namespace/)[T|C|W]/[path-or-slug]` URI scheme +
  `tcw validate` + web-view link navigation. Phase A's stable ids are its designed
  target. Worth filing as a new backlog item.
- **Editable-install restore**: this session re-pointed the editable install at
  the worktree (`pip install -e <worktree>`) so tests exercise worktree source.
  Before the worktree is torn down at `complete`, restore it:
  `pip install -e /Users/brian/Projects/TCW`.
- The migration script is one-time; consider deleting it after this ships (it has
  no further use once the tree is migrated) — or keep as historical record.
