# Make epic completability read the same in every checkout

## What is wanted

An epic whose children have all been resolved should read as ready to close in
every checkout, not only on the machine that resolved them — and should actually
be closeable there.

## The observation

`epic_completable` asks `initiative_children`, which filters `query()`. A
resolved child's folder is gitignored, so it is absent from `query()` in every
clone but the one that resolved it. An epic whose children have **all** been
resolved therefore has zero visible children, and the "an empty epic is not
completable" guard makes it report not completable.

Measured on a scratch node, before and after removing the child's `completed/`
folder:

```
HERE  (completed/ present):    children: ['…-a-child']   epic_completable: True
CLONE (completed/ absent):     children: []              epic_completable: False
```

## Why it matters

This does not merely under-report — **it blocks an operation.**
`epic_completable` gates the backlog→completed bypass, so an epic that
legitimately can close refuses to in every checkout but one, with
`cannot complete from backlog as 'done'`. That is the same shape as the defect
that made *any* completion impossible in a fresh checkout of this repository.

It also drives the `| ready-to-close` hint in `tcw work list` and `reconcile`'s
auto-completion, both of which therefore read differently per machine.

## Constraints

- **The tombstone as it exists cannot answer this.** The record carries `slug`,
  `resolution` and `resolved`, and nothing about which epic a child belonged to.
  Confirmed in the same run: the child's tombstone survives into the clone and
  says nothing that would let `initiative_children` reconstruct it.
- **Widening the record is on the table.** Recording the `initiative` would
  answer it, at the cost of moving the record from "did this slug exist here"
  toward "what was this item" — a boundary the original spec argued at length to
  keep minimal and locator-free. The requester has confirmed that argument is
  reopenable, so the spec may propose growing the record. It is a decision the
  spec must make explicitly, not a detail it may assume either way.
- **A cheaper alternative comes first in the reasoning, not last.** The epic's
  own rollup sidecar already records its children, and may survive into other
  clones without the record growing at all. Whether that is sound depends on
  whether the rollup is tracked and kept current — the spec should establish
  that before concluding the record has to change.
- **Keep the `bool(children)` guard's intent.** "An empty epic is not
  completable" is deliberate. Any fix has to keep a genuinely childless epic
  non-completable while letting an epic whose children are all
  resolved-and-absent close. Those two states look identical to `query()` today,
  which is the crux.
- **A discarded child still counts as resolved here.** `epic_completable` uses
  `RESOLVED_STATUSES`, not `completed` alone, because a child nobody will do no
  longer holds its epic open. That is deliberately the opposite of the `drift`
  rule and must survive.

## Out of scope

The `tcw capabilities drift` defect this was found beside. It was fixed
separately, and its rule is deliberately different from this one's.

## References

- [Answer capabilities drift from the tombstone so it reports the same in every checkout](tcw://W/2026-09-02-answer-capabilities-drift-from-the-tombstone-so-it-reports-the-same-in-every-checkout)
  — the repo-wide sweep that found this; its `spec.md` carries the full sweep
  table, and it is the precedent for answering a per-checkout question from the
  record rather than the local tree.
- [Tombstone resolved work items so references to them stay resolvable](tcw://W/2026-09-02-tombstone-resolved-work-items-so-references-to-them-stay-resolvable)
  — the item that drew the record's minimal, locator-free boundary this one may
  reopen.

## Notes

- Asked for further reference material; none provided beyond what the intake
  already cites.
- The intake was written by the requester from a measured scratch-node run, so
  the before/after figures above are observation rather than inference.

## Folded in: inbox entry 2026-09-17-a-missing-parent-project-blocks-epic-gates-that-only-look-down

_Merged here during the 2026-09-24 backlog cleanup; the source was closed as superseded._

## A missing parent project blocks epic gates that only look down

### Desired outcome

Completing an epic, and making an epic a plain item (`tcw work edit --type ""`),
refuse over a partial project graph only when a project that could hold the epic's
children is missing — a child or descendant — not when only a parent is.

### Context

Found by code review of
`2026-09-15-let-tcw-work-edit-change-an-item-s-type-to-or-from-epic`.

- `FsWorkStore.initiative_children` (`tcw/store/fs.py`) looks at this node and its
  descendants only, and `initiative_epic` resolves an epic upward. A slice in a
  parent node is therefore never a child of an epic here.
- Both gates refuse on `incomplete_graph_note()`, which comes from
  `FsProjectRegistry.unreachable()` (`tcw/store/project.py`) and lists **every**
  declared project that is missing, parents included.
- Reproduced by the reviewer: a node whose `connected-projects.parent` is not checked
  out, holding an epic with no children — `update_work(epic, type="")` refuses with
  "this checkout is missing connected project(s): away-parent. Run from a checkout
  that has them." The same holds for `complete`'s epic gate
  (`tcw/store/base.py`, "Cannot verify the initiative children").

So in a multi-repository setup where only a child repository is cloned, no epic
there can be completed without `--force`, or made plain at all, and the message
sends the user to fetch a repository that cannot hold any children.

### Notes

- Fix both gates together; they share the note on purpose.
- `edit --type ""` has no `--force`, so it is the harder of the two to get past.
