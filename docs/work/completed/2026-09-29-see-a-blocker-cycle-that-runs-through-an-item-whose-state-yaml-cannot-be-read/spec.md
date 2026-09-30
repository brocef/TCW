# Spec — See a blocker cycle that runs through an item whose state.yaml cannot be read

Builds on `2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes` (merged
first), whose walk this changes. Line numbers are from that branch.

## Capability changes

- **changed:** `work/manage-blocking-relations` — a blocker edit whose cycle
  check cannot see through an item is refused, naming the item.

## Problem

A blocker write is refused when it would close a cycle, found by
`WorkStore._reaches` (`tcw/store/base.py`, "def _reaches"), which follows each
visited item's `blocked_by`. The board reads a damaged `state.yaml` — unparseable
YAML, invalid UTF-8, not a regular file (`FsWorkStore._state_damage`,
`tcw/store/fs.py:5101-5116`) — as `{}` through `_safe_yaml`, so the item's
`blocked_by` is `[]`. The walk cannot follow edges through it, finds nothing,
and the edit is accepted without a word. Nothing reports a stored cycle later:
`tcw validate` has no cycle check and `topo_order` (`base.py:3287`) quietly
falls back to input order on one.

The same silence covers an item whose read raises `MultipleMatch` — two
folders holding one slug, raised by `_find` (`fs.py:4792`) only after five
re-scans rule out a move in flight. Which folder's blockers apply is as unknown
as for a damaged file.

Precedent: completing an epic is refused while an open item that may be its
slice cannot be read (`require_readable_slices`, `_unreadable_refusal`,
`base.py:3977-3998`); moving a damaged item is refused
(`_require_readable_state`, `fs.py:5119-5131`).

## Goals

1. A blocker write whose cycle walk reaches an item it cannot read — damaged
   `state.yaml`, or a slug held by more than one folder — and finds no cycle
   is **refused**, writing nothing, naming each such item (qualified with its
   project id when it is in another project) and why, and saying that whether
   the edit makes a cycle is unknown until it is fixed.
2. A cycle found through other edges is refused as a cycle, whatever else the
   walks met — across every blocker one call adds (`--blocked-by` repeated,
   `update_work`, `create_work`), and across every proposed blocker of a
   `--blocks` check. *(Narrowed at implementation: an edit combining
   `--blocked-by` with `--blocks` decides the added blockers first, so an
   unreadable item there is reported before a cycle only the `--blocks` half
   would find. Nothing is written either way.)*
3. Every blocker-write path behaves the same: `--blocked-by`, `--blocks`,
   `update_work` (web `PATCH`), `create_work` (`tcw work new --blocked-by`,
   web `POST`).

## Non-goals

- **Interrupted claims stay silent.** An item left in `.claiming/` is a stuck
  claim with a named fix (`tcw work start <slug> --take-over`); the previous
  item made the walk pass it by deliberately, so `tcw work new` does not fail
  on an unrelated stuck claim.
- **Unreachable projects stay silent.** A `<project-id>/<slug>` blocker whose
  project is not in this checkout is not followed, as before. A partial
  checkout is routine; refusing every blocker edit that leads into one would
  make it unusable.
- Detecting cycles already stored; removing blockers (never walked, so a bad
  edge can always be cleared).
- The damaged item itself: the item being edited, and the goal of the walk,
  are never read by it. Writing to a damaged item is already refused by
  `set_field`/`update_work`.

## Design

- A new `WorkStore` hook, `unreadable_reason(slug) -> str | None`: why this
  store cannot read the item's recorded fields. Base: `None`. `FsWorkStore`:
  `_state_damage` of the item's folder found through `_find`, `None` for a
  missing item; never raises except that `MultipleMatch` from `_find` is
  answered as "more than one folder holds this slug". `unreadable_open_items`
  reuses it.
- A new `WorkStore` hook, `_item_label(store, slug)`: how this store names
  another store's item in a message. Base: the bare slug. `FsWorkStore`:
  `<project-id>/<slug>` for another node's store, via
  `registered_project_id`.
- `_reaches` never raises. It returns whether the goal was reached, and fills a
  caller-supplied list with `(label, reason)` for each item it expanded but
  could not read: an item whose `get` raised `MultipleMatch`, or whose
  `blocked_by` is empty and whose store gives an `unreadable_reason` (a
  damaged file always reads as no blockers, so only those need asking). An
  interrupted claim, or any other exception, stays "not followed" and is not
  listed.
- One helper decides for a set of walks: a cycle in any of them → the cycle
  refusal; otherwise any unreadable items → the unreadable refusal; otherwise
  accept. `_check_new_blocker` uses it for one blocker; the `--blocks` half of
  `check_blocker_edits` uses it for all of the proposed blockers together, so a
  damaged path checked first cannot hide a cycle through a later one.
- Message: `Cannot add <ref> as a blocker of <slug>: the state of these items
  cannot be read, so whether this makes a blocking cycle is unknown: <label>
  (<reason>), …. Fix or replace each state.yaml (`tcw validate` lists them) and
  retry.` `_unreadable_refusal` gains a parameter for its noun so it can say
  "items" here and keep "open items" for epics.

Litmus: any store can say "this record exists but its fields cannot be read";
the hooks are in the model, and only folder damage and project-id naming are
the filesystem adapter's.

## Acceptance criteria

In a scratch graph, root `r` with children `pa`, `pb`, each keeping a board.
"Damaged" means `state.yaml` overwritten with `key: [unclosed`.

1. In `pa`: `x` blocked by `y`, `y` blocked by `z`; `y`'s state then damaged.
   `tcw work edit z --blocked-by x` exits non-zero; stderr names `y`, contains
   "cannot be read" and "unknown"; `z`'s `state.yaml` is unchanged.
2. Across nodes: `pa/x` blocked by `pb/y`; `pb/y` damaged. `tcw work edit z
   --blocked-by x` in `pa` names `pb/y`.
3. A real cycle wins: as 1, but `z` also has a path to itself through
   readable items (`x` blocked by `w`, `w` blocked by `z`). The refusal says
   `would create a blocking cycle`, not "cannot be read".
4. `--blocks` with two proposed blockers, the first leading through a damaged
   item and the second closing a real cycle: the cycle refusal.
5. `update_work` and `create_work` refuse as 1 (`ValueError` matching "cannot be
   read").
6. An ambiguous slug on the path (two folders holding `y`, in `backlog/` and
   `active/`) is refused as in 1 with "more than one folder".
7. Not refused: a damaged item not on the walk's path; an interrupted claim on
   the path; an unreachable project on the path; `--unblocked-by` of any
   blocker; editing the damaged item's own blockers is refused by the
   existing rule, not this one.
8. Existing blocker, epic-completion and cycle tests pass unchanged; the full
   suite passes as CI runs it.

## Risks

- **A refusal where there is no cycle.** Intended: the answer is unknown and the
  fix is named. It fires only on the path the new blocker leads into.
- **Cost.** One extra read per visited item with no blockers.

## Notes

- Designed with two advisors (Opus; Sonnet in place of Codex, which was at its
  usage limit). Both: refuse, a cycle wins, collect across walks and decide
  once, claims silent. Split on ambiguous slugs — taken as unreadable on the
  Opus argument that `MultipleMatch` is raised only after re-scans rule out a
  transient move. Resolved items count too, with neutral wording, rather than
  open-only: the walk does not check status and a simpler rule is easier to
  explain.
- *Implementation notes.* `unreadable_open_items` was not rewritten over
  `unreadable_reason`: that calls `_find`, which scans the store per call, so
  the listing would become quadratic, and a duplicate slug would change its
  output. `_item_label` searches every project in the graph
  (`FsProjectRegistry.projects()`, compared with `samefile`) rather than
  `registered_project_id`, which knows only ancestors and descendants and so
  would leave a sibling's item unqualified. The refusal's remedy is worded per
  reason: fix the `state.yaml` for damage, remove the extra folder for a slug
  held twice (`tcw validate` crashes on a duplicate slug today, so it is not
  named there). Cost is one extra scan of the store's folders plus a parse per
  visited item with no blockers, not one read as Risks said.
