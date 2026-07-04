# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added

- 0ccc0b1..HEAD — `resolve_qualified_work_ref(anchor, ref)` in `tcw/store/fs.py`:
  a shared FS-adapter-local resolver mapping a work ref to `(FsWorkStore, bare_slug)`.
  A bare slug (no `/`) stays on the anchor node; `sub/proj/<slug>` resolves to the
  descendant node's store — the qualifier is the node path relative to the anchor.
  Fails closed (returns `None`) on an unknown qualifier, a traversal/absolute/symlink
  *escape*, or a path whose *resolved* segments include `.git`/`.worktrees`. No
  abstract-store change (litmus test): the qualifier is assigned by the anchor at
  render time, not stored on `WorkItem`.
- 0ccc0b1..HEAD — `tcw serve --include-descendants` (default off). When on,
  `GET /api/work` aggregates the anchor plus every descendant node's board with
  qualified slugs, and a gated `TcwHandler._resolve_work` routes every
  `/api/work/<slug>…` handler (detail, artifacts, sidecars, actions, PATCH, DELETE,
  `/open`) to the resolved descendant store. Detail/action/PATCH responses echo the
  *qualified* slug so the unchanged web UI keeps addressing the descendant when it
  derives sub-resource URLs from `item.slug`. Flag off: serve is byte-for-byte
  unchanged — a qualified slug 404s on every route, read and mutate.

## Changed

- 0ccc0b1..HEAD — `tcw work list --include-descendants` now prints descendant items
  with a subproject-qualified slug (`sub/proj/<slug>`) instead of the bare
  node-local slug, so each printed slug is a usable address. Group headers
  (`# ./sub/proj`) and filters are unchanged; anchor items stay bare.
- 0ccc0b1..HEAD — All `tcw work` slug-taking commands (`show`, `path`, `start`,
  `edit`, `complete`, `drop`) resolve a qualified `sub/proj/<slug>` to the
  descendant node via a new `_resolve` helper — equivalent to `cd`-ing into that
  node — while store/git calls use the bare slug (including the reverse
  `add_blocker` and the `remove_worktree` teardown) and echoes print the qualified
  ref. A bare slug still resolves against the current node only (unchanged). `_path`
  now also catches `MultipleMatch` consistently with `_show`/`_complete`.

## Internal

- 0ccc0b1..HEAD — Removed the now-unused `_run` helper in `tcw/work/cli.py`
  (`_drop` was its only caller and now resolves like the other commands).
