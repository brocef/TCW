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

## Changed

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
