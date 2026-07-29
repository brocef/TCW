# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- `tcw work edit <slug> --title "<title>"` — retitle an existing work item.
  `update_work` already accepted `title` and `tcw serve` already drove it that
  way; `_edit` now passes it through, so the CLI is no longer the one surface
  that cannot rename an item. The slug is not recomputed, so existing references
  keep resolving.
- `_nonempty` argparse validator in `tcw/work/cli.py`. `--title ""` (or
  whitespace) is rejected at the parser with exit 2. Without it, `_provided`
  passes the empty string to `update_work`, which writes `state["title"] = ""` —
  a titleless item, which `create_work` explicitly refuses to create.

## Changed

- The `tcw work edit` subcommand help now reads "change an item's title,
  estimates, tags, or blocking links". It previously claimed the command changes
  blocking links, which had been incomplete since `--priority`, `--effort`,
  `--complexity`, `--initiative`, and `--tag` were added.
- `FsWorkStore.create` now delegates to `create_work` and returns
  `get_detail(...).item`; its duplicate write path (`_unique_slug`, parent
  resolution, `mkdir`, `write_text`, `dump_yaml`, `_stage`) is deleted. Two
  behavioral deltas follow, both deliberate: an empty title now raises
  `ValueError` where it previously produced a degenerate item, and `priority` is
  omitted from `state.yaml` when unset rather than written as `null` (every
  reader goes through `load_yaml` + `.get()`, so the two are equivalent).
  `tcw/store/base.py` is unchanged — `WorkStore.create` stays declared.

## Fixed

- `_atomic_write_all(pairs)` in `tcw/store/fs.py` — a module-level sibling of
  `_atomic_write` that writes several files as one unit: stage every
  `<path>.tmp`, then `replace` each in turn. A content-production failure
  (ENOSPC, EACCES, a serialization error) can only happen in the staging phase,
  before anything is promoted, so the targets are untouched. A single
  `except BaseException` spans both phases and unlinks every temp, so no `.tmp`
  is left beside a real file and a `KeyboardInterrupt` mid-batch still cleans up.
- `FsTreeStore._write_node` uses the helper and rolls back with
  `shutil.rmtree(..., ignore_errors=True)` when — and only when — it created the
  directory (`existed` captured before `mkdir`). This is the shared helper behind
  every taxonomy and capability add/update, so `add`, `update_term`, and
  `update_capability` all inherit it without being patched individually.
- `FsCapabilitiesStore.update_capability` additionally carries the same rollback
  itself. It `mkdir`s before dispatching, so `_write_node`'s `existed` is already
  `True` by the time it runs, and its other two branches go through `_write_meta`,
  which does not create the directory at all. The guard wraps all three, which is
  what makes fresh-override materialization all-or-nothing.
- `FsCapabilitiesStore.set` — the path `tcw capabilities set` actually uses,
  where `update_capability` is web-editor-only — carries the same guard. It
  materializes a fresh override through `_write_target` and previously wrote
  `meta.yaml` with no rollback, leaving an empty override directory on failure.
  Single-file, so never a partial object; the residue is what changed.
- `_write_node` and `_write_meta` now document that they stage internally, so any
  caller wrapping them in a rollback must key it on whether content landed.
- `FsWorkStore.create_work` wraps its two writes in the same rollback. `mkdir`
  without `exist_ok` proves the directory is ours, so the rmtree is
  unconditional.
- `FsWorkStore.update_work` writes `state.yaml` and the body through the helper.
  The pair list is 1 or 2 entries — the body is still written only when one is
  supplied, so an unchanged body never churns its revision hash.
- No rollback destroys content that landed. In `_write_node` and `create_work`,
  staging (`self._stage`) simply sits outside the rollback, so a git failure
  after both files are written leaves a fully valid object on disk. In
  `update_capability` it cannot: staging happens inside `_write_node`, which the
  guard has to wrap. That rollback therefore keys on whether `meta.yaml` landed
  rather than on who created the directory — a content failure promotes nothing
  and rolls back, a successful write followed by a failed `git add` keeps the
  files and leaves them merely unstaged.
- Known ceilings, carried as `# ponytail:` comments in the code: the promote loop
  is not atomic across files (a process death between two `replace()` calls still
  leaves a partial update; the upgrade is a journal or the whole-directory swap
  `accept_inbox` already uses), and `_write_node`'s `existed` check is TOCTOU-racy
  under concurrent writers — tracked by
  `2026-06-22-concurrency-safe-work-claims-for-multi-agent-repos`.

## Internal

- New capability `work/retitle-a-work-item`.
- Backlog maintenance: findings from the 2026-07-28 audit trial folded into
  `2026-07-03-transactional-multi-file-writes-in-the-fs-store`,
  `2026-06-22-concurrency-safe-work-claims-…`, and
  `2026-07-01-transitive-taxonomy-inheritance`. The concurrency item's assumption
  that an external work root is "the only new branching" is corrected in place —
  `FsTreeStore` derives `node_root` from `root`, and `node_root` is what git
  operations, the sentinel reader, and hook cwd key off.
