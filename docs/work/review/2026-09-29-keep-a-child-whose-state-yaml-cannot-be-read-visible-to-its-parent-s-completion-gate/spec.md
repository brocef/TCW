# Spec — Keep a child whose state.yaml cannot be read visible to its parent's completion gate

## Capability changes

None. This is a correction to how an existing gate behaves, and it does not
add a new capability.

## Reproduction

Taken from the combined review of branch `bug-run` (2026-09-29).

- **Epic.** Set up an epic with one slice already discarded and one slice still
  open in `backlog`, then append the bytes `\xff\xfe` to the open slice's
  `state.yaml`.
  - On `bug-run`, `epic_completable` becomes True and
    `complete(epic, "done", …)` succeeds.
  - On `main` the same steps raised `UnicodeDecodeError`, so the gate failed
    closed.
- **Parent.** Set up a parent item and an open child that records `parent:`,
  then make the child's `state.yaml` malformed YAML. The parent then
  completes. This already happened before
  `2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`,
  and that item widened it to non-UTF-8 files and to a `state.yaml` that is
  not a regular file.

## Problem

`FsWorkStore._safe_yaml` (tcw/store/fs.py:5043) reads a damaged `state.yaml` as
`{}` so that one damaged file does not break the whole board. An item read
this way has lost its `parent:` and its `initiative:` fields:

- **Parent gate.** `_parent_slug` (fs.py:4614) falls back to folder nesting.
  `_relation_snapshot` (fs.py:4641) therefore no longer places the child
  beneath its parent. `open_descendants` then misses the child, and so does
  `require_nothing_open_beneath` (tcw/store/base.py:4365), which `complete`
  calls at base.py:4272.
- **Epic gate.** The item has `initiative=None`, so `initiative_slices`
  (fs.py:6213) drops it. The epic gate in `complete` (base.py:4274–4282) and
  `epic_children_all_resolved` (base.py:4077) then see no open slice.
  `reconcile --complete-when-ready` (tcw/work/recursion.py:432–438) acts on
  that same wrong answer.

Both gates exist to stop an item from resolving while work beneath it is
still open. A damaged file silently switches both of them off.

## Goals

1. **Parent gate.** `complete` refuses, before anything moves, while an
   **open** item on the same board (backlog, active or review) has a
   `state.yaml` that cannot be read. The refusal names each such item and
   the reason it cannot be read.
   - This applies to every resolution (done and discarded), matching
     `require_nothing_open_beneath`.
   - Like that gate, `--force` does not bypass it.
2. **Epic gate.** Completing an epic also refuses while an open item in any
   descendant node that the slice walk opens has a `state.yaml` that cannot
   be read. The refusal names the node and the item.
   - Like the partial-graph refusal next to it, `--force` bypasses this one.
   - It is checked before the backlog-epic shortcut is decided, so the user
     sees this refusal rather than a misleading "cannot complete from
     backlog".
3. **One storage-neutral question.** Both gates ask the store the same
   thing: "which open items can you not read?"

4. **Amended at review:** `drop` makes the parent gate's check too, since a
   drop leaves no record for a hidden child to name. The damaged item itself
   is excluded from both checks, so its own move gets
   `_require_readable_state`'s plainer refusal and it can still be dropped.
   `tcw work complete` runs the store's checks before merging a worktree
   branch. `--force` bypasses the epic refusal only for items in nodes below:
   one on the epic's own board is also caught by the parent gate.

## Non-goals

- **Damaged resolved items are left alone.** A damaged item in `completed/`
  or `discarded/` holds nothing open, so it does not block anything.
- **Blocker cycles.** A cycle that runs through a damaged item goes
  undetected, because that item's `blocked_by` reads as `[]`. That is under-
  detection at edit time, and nothing resolves wrongly because of it. Filed
  separately.
- **Items in `.claiming/`.** A claim refuses to move an item whose state
  cannot be read (fs.py:4348, 4417), so a damaged item is not found there
  in practice.
- **The "ready-to-close" label.** `epic_completable`, which drives the
  label in `tcw work list` (cli.py:993), may still say "ready" for a damaged
  slice. Only `complete` acts on that answer, and `complete` now refuses.

## Design

- **The shared question.** A new `AbstractWorkStore.unreadable_open_items()`
  returns `list[tuple[str, str]]` pairs of `(slug, reason)`. By default it
  returns `[]`: a store that cannot hold a record it fails to read has
  nothing to report.
- **The filesystem answer.** `FsWorkStore` walks `_item_dirs()` and, for
  each item folder in an open status, asks for the damage reason.
  - That reason is `_state_damage(path) -> str | None`, pulled out of
    `_require_readable_state` (fs.py:5065) so that both use the same
    wording.
  - `_require_readable_state` keeps its current message.
- **Parent gate.** In `require_nothing_open_beneath`, before the open-
  descendant check: if any open items cannot be read, raise
  `Cannot {verb} {slug}: the state of these open items cannot be read, so whether they sit beneath it is unknown: a (reason), … Fix or replace each state.yaml (`tcw validate` lists them) and retry.`
- **Epic gate.** In `complete`, for an epic and without `force`, before
  `from_backlog_epic` is computed: collect `unreadable_open_items()` from
  this store and from each descendant node's store (the same
  `descendant_nodes` walk the slice walk uses), and refuse with a message of
  the same shape that names each item's node.
  - The epic check reaches stores in other nodes, so it needs a store-level
    hook. It is `unreadable_slice_candidates()`, which by default returns
    this store's own answer. `FsWorkStore` overrides it to add the answers
    from its descendant nodes, labelled by node.

## Abstraction litmus test

"Which open records can you not read?" is a question a tracker-backed store
can answer too, for example with issues whose fields fail to parse. The
default answer is empty, and only the filesystem adapter knows about files.

## Acceptance criteria

1. **Epic reproduction.** With an open slice in the epic's own node whose
   `state.yaml` has `\xff\xfe` appended, `complete(epic, "done")` raises
   `ValueError`. The message names the slice, and the epic is still in
   `backlog`.
2. **Epic, slice in a child node.** The same holds when the damaged open
   slice is in a child node. The message names that node. With
   `force=True`, the epic completes.
3. **Parent reproduction.** With an open child whose `state.yaml` is
   malformed YAML, completing its parent raises. The message names the
   child, and the parent does not move. It also raises with `force=True`,
   and when discarding.
4. **Damaged resolved items do not block.** A damaged `state.yaml` in
   `completed/` does not block the parent or the epic from completing.
5. **`reconcile --complete-when-ready`** leaves the epic open in the
   reproduction of criterion 1.
6. The full suite passes.

## Risks

- **An unrelated damaged item blocks all completion on its board** until it
  is fixed. This is deliberate. Main failed closed in the same way for
  non-UTF-8 files (every read crashed). The message says which file to fix,
  and `tcw validate` already reports it.
- **Cost.** Each `complete` now reads every open item's state once more.
  Boards are small, and the relation snapshot already reads the same files.
