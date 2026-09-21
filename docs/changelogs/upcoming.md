# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

The `v2.5.0` tag was pushed but never published: the release workflow's test job
failed, so the PyPI upload never ran. `v2.5.1` is the first published release
carrying everything listed under `v2.5.0`.

### Fixed

- `tests/test_tracker_cli.py`'s `node` fixture sets `TCW_WORK_OWNER`.
  `test_an_owed_item_can_still_be_started` and
  `test_one_owed_item_does_not_break_lifecycle_moves_on_every_other_item` run
  `tcw work start`, which needs a claimant and otherwise falls back to the git
  identity. The CI runner has none, so both failed there and passed locally.
- `docs/release-notes/v2.5.0.md` linked #43 under the wrong repository.
- A `--parent` child created under an already-active parent was born `active`
  (its status was the top-level folder it was nested in), so its `request`,
  `spec` and `plan` stage gates refused it. A child's own transition also moved
  it to the top level and dropped the relation, and re-parenting through
  `update_work` changed an item's status by moving its folder.
- `tcw validate` reported a nested child carried into `completed/` by its parent
  as having no resolution.
- `delete_resolved` under `work.retain: false` removed children nested in a
  resolved item's folder without recording them in the graveyard.

### Changed

- **A child records its parent and has its own status.** `create_work` writes a
  child to `backlog/<slug>` with `parent: <slug>` in `state.yaml`, whatever the
  parent's status. `FsWorkStore._parent_slug` reads the field and falls back to
  folder nesting only when it is absent, so children written by earlier versions
  (nested, no field) keep following their parent. A nested child's own
  transition or claim writes `parent:` in the same move; a claim writes it
  before the folder enters `.claiming/`, and take-over stages the vacated path
  found from the git index (`_tracked_source`). `start --worktree` commits the
  real source path.
- `WorkStore` gains `parent_children`, `independent_descendants` and
  `open_descendants` (whole subtree, walking through children that follow their
  parent, cycle-safe; the filesystem store also counts items mid-claim, including
  anything nested in a claimed folder), `require_nothing_open_beneath` and
  `_require_live_parent`.
- `complete` refuses while `open_descendants` is non-empty, for either
  resolution, outside the `--force` block. `drop` refuses while any independent
  descendant exists, open or resolved. `epic_completable` is false while any
  descendant is open, so `reconcile --complete-when-ready` agrees with
  `complete`. `tcw work complete` runs the check before merging a worktree
  branch, against the primary and the branch copy of the store.
- `create_work` and `update_work` refuse a parent that is missing, resolved or
  has a resolved ancestor (for an open item), and a cycle. Re-parenting is a
  field write; only a nested child is moved, to the top of its status folder.
- `delete_resolved` lists nested children from `git ls-tree` and records them
  with the parent in one graveyard write (`_write_tombstones`);
  `_require_writable_graveyard(also=...)` tolerates their uncommitted entries on
  a resumed removal. `_committed_item_path` and `_commit_holds` find a nested
  item in a past commit.
- `tcw validate` reports a `parent:` naming no item or tombstone, and one that
  disagrees with the folder a nested item sits in.
