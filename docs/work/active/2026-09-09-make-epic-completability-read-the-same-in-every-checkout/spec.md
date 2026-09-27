# Spec — Make epic completability read the same in every checkout

## Capability changes

`changed` for the work capability covering epic completion, if the ledger
describes the "all children resolved" rule in terms of visible items; decided
at implement by the capabilities step.

## Reproduction

Scratch node, epic E, child C with `initiative: E`; complete C. In the resolving
checkout `initiative_children(E) == [C]` and `epic_completable(E)` is true.
Remove C's resolved folder (what every other clone sees): children `[]`,
`epic_completable` false, and `complete E --resolution done` from backlog
refuses "cannot complete from backlog as 'done'" even with `--force`
(legality, `WorkStore.complete` base.py ~4127, is checked before the force-able
gates). Second defect: a node whose declared parent is not checked out cannot
complete an epic ("Cannot verify the initiative children…") or run
`edit --type ""` on one, although only descendants can hold its children.

## Problem

- `epic_children_all_resolved` / `epic_completable` (base.py ~3961-4000) and
  `check_type_change` (base.py ~3763) read `initiative_children`, a live
  `query()` (fs.py:5845). A tombstone (`graveyard.yaml`, tracked) records
  `resolution`, `resolved`, `location` — not the epic.
- `incomplete_graph_note()` (fs.py:5804) reports every unreachable declared
  project; the registry walk (project.py ~395) follows parent and children
  edges alike, and `UnreachableProject` (base.py:131) does not record which.

## Goals

1. **The tombstone records `initiative`** — the child's `initiative` at the
   moment it is resolved; omitted when empty. Every path that writes or
   rewrites a record carries it: resolution, `retain: false` deletion and its
   retry, nested items. Editing `initiative` on a retained resolved item keeps
   its tombstone in step.
2. **Store operation** `resolved_initiative_children(epic_slug) -> list[tuple[str, str]]`
   — `(node_id, slug)` pairs of tombstoned children. Base default `[]`;
   `FsWorkStore` reads the graveyard of this node and of `descendant_nodes`.
3. `epic_children_all_resolved`: no live child is open, and at least one child
   is known — live, or tombstoned and not also live (the live item wins,
   matched per node and slug). A genuinely childless epic stays
   non-completable. Discarded children count as resolved, as today.
4. `check_type_change` counts tombstoned children as children (its contract is
   "any child counts, resolved or not"); its refusal must not advise editing an
   absent child.
5. `reconcile`'s table lists tombstoned children as `node | slug | <resolution>`
   rows (no capability details), so "Ready to close" can appear when every child
   is absent.
6. **Descendant-only graph note.** `UnreachableProject` gains `relation`
   (`"child"` / `"parent"`); the registry offers the unreachable entries on child
   edges declared by this node or its descendants; the store offers
   `incomplete_graph_note(below=True)` (base default ""). The epic gate in
   `complete`, `epic_completable` and `check_type_change` use it. `start`'s
   upward epic resolution and CLI graph reporting keep the full note.

## Non-goals

- Backfilling old tombstones from git history (git-only, and impossible for
  gitignored completions — the case this fixes). Epics whose children were
  tombstoned before this change keep today's behaviour; the recovery is
  documented: `tcw work start <epic>` then `complete --force`.
- `open_descendants` (the `parent` relation; a tombstone is never open).
- The rollup as a source of truth.

## Abstraction litmus test

- `resolved_initiative_children` — store interface; any store that remembers
  resolved items can answer it (a tracker: resolved issues whose epic link is
  E). Default `[]` keeps today's behaviour for a store that cannot.
- `incomplete_graph_note(below=True)` — store interface, default "".
- The `initiative` field on the graveyard record and `relation` on the registry
  entry — filesystem-adapter detail and registry data.

## Acceptance criteria

1. The reproduction: after removing C's folder, `epic_completable(E)` is true
   and `complete E --resolution done` from backlog succeeds (no `--force`).
2. Same with C in a descendant node, including behind a routing node.
3. A childless epic stays non-completable; an epic with one open live child
   and one tombstoned child is not completable; a child whose `initiative` was
   changed before resolution counts only for its new epic.
4. In the resolving checkout (folder and tombstone both present) the child is
   counted once.
5. `retain: false` deletion keeps `initiative` in the record; editing a
   retained resolved child's `initiative` updates its record.
6. `edit --type ""` on an epic whose only child is tombstoned is refused.
7. `reconcile` on E with every child absent shows the children and
   "Ready to close".
8. A node whose parent is not checked out can complete an epic and demote one;
   a missing child project still refuses both.
9. An old tombstone without `initiative` behaves as today.
10. Full suite passes.

## Risks

- `UnreachableProject` gains a field; every constructor must pass it.
- Graveyard rewrites are concurrency-sensitive (`_graveyard_lock`).

## Notes

Advisors (2026-09-27), in agreement: option A over the rollup (which erases
itself on reconcile) and over reading retained commits (git-only). Opus: pairs
not bare slugs; live wins; carry the field through the deletion rewrite; a
`relation` field for the descendant note. Codex: counting in
`check_type_change` and `reconcile`; `--force` does not reach backlog legality,
so legacy recovery must be documented; keep the full note for `start`.
Keeping the tombstone in step on an `initiative` edit (rather than refusing the
edit) was my choice: it changes no existing edit behaviour.
