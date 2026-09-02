# Epic completability depends on which checkout is asking

## Desired outcome

An epic whose children have all been resolved reads as ready to close in every
checkout, not only on the machine that resolved them — and can actually be
closed there.

## Context

`epic_completable` (`tcw/store/base.py:2141-2150`) calls `initiative_children`,
which filters `query()`. A resolved child's folder is gitignored, so it is absent
from `query()` in every clone but the one that resolved it. An epic whose
children have **all** been resolved therefore has zero visible children, and the
`bool(children)` guard — "an empty epic is not completable" — makes it report
not completable.

Measured on a scratch node, before and after removing the child's `completed/`
folder:

```
HERE  (completed/ present):    children: ['…-a-child']   epic_completable: True
CLONE (completed/ absent):     children: []              epic_completable: False
```

This is worse than the `tcw capabilities drift` defect it was found beside,
because it does not merely under-report — **it blocks an operation.**
`epic_completable` gates the backlog→completed bypass at `tcw/store/base.py:2271`,
so an epic that legitimately can close refuses to in every checkout but one, with
`cannot complete from backlog as 'done'`. That is the same shape as the bug that
made *any* completion impossible in a fresh checkout of this repository.

It also drives the `| ready-to-close` hint in `tcw work list`
(`tcw/work/cli.py:350`) and `reconcile`'s auto-completion
(`tcw/work/recursion.py:210`), both of which read differently per machine.

Found by the repo-wide sweep in
`2026-09-02-answer-capabilities-drift-from-the-tombstone-so-it-reports-the-same-in-every-checkout`,
whose `spec.md` carries the full sweep table.

## Constraints

- **The tombstone as it exists cannot answer this.** The record carries `slug`,
  `resolution` and `resolved`, and nothing about which epic a child belonged to.
  Confirmed in the same run: the child's tombstone survives into the clone and
  says nothing that would let `initiative_children` reconstruct it.
- So this needs a decision about **what a tombstone carries**, which is why it
  was not folded into the drift item. Recording the `initiative` would answer it,
  but it widens the record from "did this slug exist here" toward "what was this
  item", and that boundary was drawn deliberately — the original spec argued at
  length for keeping the record minimal and locator-free. Reopening it is the
  substance of this item, not a detail of it.
- **Watch the `bool(children)` guard.** "An empty epic is not completable" is
  deliberate. Any fix has to keep a genuinely childless epic non-completable
  while letting an epic whose children are all resolved-and-absent close.
- Existing behaviour to preserve: a child that was **discarded** still counts as
  resolved for this purpose — `epic_completable` uses `RESOLVED_STATUSES`, not
  `completed` alone, because a child nobody will do no longer holds its epic
  open. That is the opposite of the `drift` rule, on purpose.

## Notes

A cheaper alternative worth considering before changing the record: the epic
could read its children from something that survives into other clones without
the tombstone carrying the pointer — the epic's own rollup sidecar already
records its children, for instance. Whether that is sound depends on whether the
rollup is tracked and kept current, which this item should check before assuming
the record has to grow.
