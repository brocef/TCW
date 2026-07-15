# Flag or auto-advance an epic as completable when all child slices are resolved

Source: https://github.com/brocef/TCW/issues/2.

## Product changes

When an epic's children all reach a terminal state, the parent doesn't advance.
It sits wherever it was (often `backlog`), so the board shows finished work as
pending. You only find it by auditing, then hand-walk the epic `start` →
`complete` — and `complete` refuses from `backlog`, so you `start` an epic into
`active` purely to close it.

Compounding it, `<!-- tcw:rollup -->` tables can go stale: one rollup read "all
blocked or complete" while omitting a still-open child in another node. The
`complete` blocker-gate independently caught it, but the rollup would otherwise
have invited a premature completion.

When the last open child reaches a terminal resolution (via `complete` on the
child, or during `reconcile`):

1. **Flag the parent as completable** — `reconcile`/`list` marks the epic "ready
   to close (all children resolved)" and prints the exact `complete` command.
2. Optionally **auto-complete** the epic behind a flag or config, allowing
   `complete` directly from `backlog` for an epic whose children are all
   resolved — no `start`-just-to-`complete` dance for coordinator epics that
   never had their own spec/plan.
3. Ensure the rollup driving this reflects true child status across all nodes, so
   the "all complete" signal and the blocker-gate can't disagree.

## Technical changes

## Meta changes
