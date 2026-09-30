## Added

- `tcw work rename <slug> <new-slug>`: gives an open item a new slug. The date
  prefix is kept, and the new slug must already be in slug form
  (`rename_slug`). It is refused for a resolved item, a worktree or branch,
  another owner, a claim in progress, a taken slug or a different date.
  `FsWorkStore.rename`, under the graveyard lock, does the rest in one commit:
  - writes `renames.yaml` first;
  - runs `git mv` on the folder;
  - rewrites `blocked_by` (`slug` and self-qualified `external`), `parent` and
    `initiative` on this board, graveyard `initiative` entries, and capability
    `Planning doc:` lines;
  - repoints an epic's initiative children on other boards, with a commit in
    each of those repositories.
- The old slug keeps resolving. `WorkStore.renamed` follows a chain of
  renames:
  - `_resolve` follows it for read verbs (`show`, `path`) with a note, and
    refuses it for every verb that changes an item;
  - `unresolved_blockers` and `external_blocker_state` (bare and
    `<project>/<slug>`) follow it;
  - `_unique_slug` treats a renamed-away slug as taken;
  - `tcw validate` reports a `renames.yaml` that does not parse, a loop, or an
    old slug held by an item again.
- Every refusal runs before the first write, and a failure after it is undone
  (`_undo_rename`), so a rename is never left half done. Refused: a folder
  already at the new name, a `renames.yaml` or graveyard that does not parse,
  and uncommitted changes in the item or any file the rename rewrites.
- `tcw://W/<old>` links resolve to the renamed item (`resolve_tcw_ref`), and
  a blocker naming the old slug reads the resolved record under the new one,
  which is what another clone has once the item is completed.
- `slugify`, `rename_slug` and the storage-neutral refusals
  (`WorkStore.rename_refusal`) are in `tcw/store/base.py`; `tcw.store.fs`
  still exports `slugify`.
- The record is kept apart from `graveyard.yaml` because every tombstone
  reader takes a tombstone to mean resolved work.
