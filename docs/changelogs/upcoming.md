# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

- `WorkStore.remove_blocker` (`tcw/store/base.py`) now raises `ValueError` when
  the ref matches no blocker on the item, instead of filtering to an unchanged
  list and returning silently. `tcw work edit --unblocked-by` consequently exits
  non-zero with `no such blocker on <slug>: <ref>` rather than printing
  `edited <slug>` after doing nothing (`fe43e40..HEAD`).
- Blocker refs round-trip with their display form. New
  `WorkStore._normalize_ref` strips one leading `external:` label and is applied
  in `_entry_for` (before the slug probe) and `remove_blocker`, so the
  `external: <text>` string rendered by `unresolved_blockers` / `work show` is
  accepted back as input. Placing it in the two shared helpers means
  `create_work`, `update_work`, and the web app's `blockers` field
  (`tcw/serve/__init__.py:736` → `tcw/store/fs.py:2217,2324`) inherit the fix.
- `resolve_qualified_work_ref` (`tcw/store/fs.py`) resolves a `<project-id>/`
  qualifier via `FsProjectRegistry.get` over the whole registered graph instead of
  a `descendants()`-only table, so cross-node refs work in any direction
  (GitHub #7, `c999f70..HEAD`). Fixes the reported symptom — a cross-node epic
  slice could not link its parent epic: `tcw validate` rejected
  `tcw://W/<parent-id>/<epic-slug>` with `no such work item`. One guard covers
  every consumer: CLI addressing (`tcw/work/cli.py` `_resolve`), `tcw validate`
  (`tcw/validate.py` → `tcw/refs.py`), and `tcw serve`'s `/api/resolve`. The
  docstring's stale path-containment prose was rewritten — the function already
  keyed on canonical IDs, and traversal/`.git`/unregistered-path qualifiers fail
  because they are not registry IDs, not because of a path check.

## Changed

- New `qualified_work_ref_problem(anchor, ref)` (`tcw/store/fs.py`) returns a
  cause-naming failure message: `no such project in this graph: <id>` for an
  unregistered qualifier, `<id> has no work component` for a registered project
  without `docs/work`, else the generic `no such work item: <ref>`. Called on the
  cold failure path by `_resolve` and by `resolve_tcw_ref`'s W branch; wraps its
  registry open in a `try` so `resolve_tcw_ref` stays contractually non-raising.
- `tcw work list -i` / `tcw serve` aggregation is deliberately unchanged
  (`include_descendants` untouched) — addressing and linking are graph-wide,
  board aggregation stays downward-only.
- **Breaking:** `--blocked-by` (on `work new` and `work edit`) and
  `--unblocked-by` (on `work edit`) are now `action="append"` and no longer
  comma-split, matching the `--tag` idiom. One flag occurrence = one blocker, so
  external blocker prose survives a comma. `--blocked-by "a,b"` previously
  recorded two blockers and now records one named `a,b`. `--blocks` is unchanged
  (slugs cannot contain a comma).
- `_edit` (`tcw/work/cli.py`) applies `--unblocked-by` removals before
  `--blocked-by`/`--blocks` additions, so a ref that fails closed aborts the edit
  before any blocker write lands — matching the existing up-front `--blocks`
  validation.

## Internal

- Backlog audit (`cbb52c8..HEAD`): registered the `remote` and `tech-debt` work
  tags; tagged eight backlog items; refreshed four stale request bodies
  (`remote-extends-for-taxonomy` for the ID-based project graph,
  `tracker-sync-for-capabilities` for the `meta.yaml` `Tracker` key,
  `concurrency-safe-work-claims` for the `tcw-config.yaml` sentinel, and the
  rich-Markdown-editor item for the post-rewrite React/Vite web client);
  retargeted `transactional-multi-file-writes` at the shared
  `FsTreeStore._write_node` helper. Closed three items:
  `per-object-capability-revision-token` and `live-browser-test-pass`
  (superseded), `additional-capability-sidecars` (wontfix).
- `web/e2e/parity.spec.ts`: assert the complete modal's
  `.reconciliation-reminder` callout in the lifecycle scenario, closing the last
  coverage gap from the retired live-browser-test item.
