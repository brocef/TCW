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
- Every writer of a node's `tcw-config.yaml` now changes only the lines of the
  key it writes, instead of re-serialising the whole file with `yaml.safe_dump`
  (which deleted comments, reflowed long strings and re-indented the file):
  `tcw taxonomy extends add|rm`, `tcw capabilities extends [--rm]`,
  `tcw work tags add|rm`, `tcw init`'s `<component>.path`, and
  `write_sentinel`'s `id` backfill. `\r\n` line endings and a leading
  byte-order mark are preserved. A change that alters nothing writes and stages
  nothing. Every edit is verified before it is written: the result must parse to
  the intended mapping and differ from the original only inside the edited
  lines, with no anchor or unrelated comment inside them.
- `write_sentinel` read `id: null` as "no id", then wrote it back unchanged
  (`{"id": new, **existing}` let the old `None` win) while returning `True`. It
  now sets the id.
- `tcw init` wrote the config twice with the default work store's deletion
  between the writes; it now writes it once, after verifying, before any folder
  is deleted or created.
- `_persist_extends` updated the store's in-memory `config` before writing, so a
  failed write left the object disagreeing with the file. It now updates after.

### Changed

- A `tcw-config.yaml` these commands cannot edit in place is refused with a
  `ValueError` naming the key and the hand edit to make, never rewritten: a
  section written in braces (`taxonomy: {path: x}`) that needs a key added or
  removed (an empty `work: {}` is not refused: it is opened into a block and
  takes the key), a file that is one brace mapping, an alias or anchored value in the
  way, a multi-line scalar as the target, and a hand-ordered `tags` list holding
  comments that `tags add|rm` would have to re-sort.
- Three shapes that were silently replaced are now refused: a `work` section
  that is not a mapping on `tcw work tags add|rm`, a `work.tags` that is not a
  list, and a non-mapping `<component>` section on `tcw init --<component>-path`.
  Missing and empty files are still written in full, so a fresh `tcw init` is
  unaffected.

### Internal

- New `tcw/store/config_edit.py`, private to the filesystem adapter, does the
  in-place editing with `yaml.compose` positions; no new dependency.
  `FsTreeStore._write_node_config` takes a list of key edits instead of the whole
  mapping, and `_atomic_write_all` writes with `newline=""`.
