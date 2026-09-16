# Judge a worktree item's completion from its merged branch, not the primary checkout's stale copy

`tcw work complete` must run from the primary checkout for an item started with
`tcw work start --worktree`. But the lifecycle moves made during the work (`submit`
to `review`, `rework` back to `active`, the verify artifacts) are committed on the
work branch, so the primary checkout's copy of the item still reads `active`
until the merge-back. `complete` judges the item from that stale copy, and so
misreports what happened. Completion should judge an item started with
`--worktree` by the branch's state, which is where the work actually happened.

## Symptom

Completing `2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
on 2026-09-16 printed:

> tcw work complete: completing … directly from active; the verify stage was skipped

But on the branch the item had been submitted to `review` (`dc14ca2b`), had gone
through a rework cycle, and carried `refined-outcome.md` (`3b4f843a`). The
warning was false.

## Where it happens

`tcw/work/cli.py`, in the `complete` handler. The "directly from active" warning
reads `item.status` (around line 2454) **before** `merge_worktree` runs (around
line 2497). The item is re-read only after the merge, for the capability gate,
whose comment says why it waits: "so both the declared list and the capability
statuses are read from the merged primary tree".

The same shape probably affects the other checks that run before the merge.
Whoever picks this up should check each one against the branch copy of the item:

- `st.unresolved_blockers(item)`;
- `_strict_refusal`;
- anything else read from `item` before the merge.

A blocker resolved, or a field edited, on the branch would be judged from the
stale copy. The warning has to be decided before the merge can fail, but it has
to be decided from the branch's copy of the item.

## Origin

Found while completing the item above, the user's first `--worktree` item in
this session. The user: "Our worktree support isn't great and this is a good
example."

## References

- `tcw/work/cli.py`, the `complete` handler — the status read before
  `merge_worktree`, and the re-read after it.
- `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies` — related
  worktree defect (GitHub #39). Not a blocker.
- `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
  — related: the item's `worktree`/`branch` fields this fix would read. Not a
  blocker.
- `CLAUDE.md` § "Working in a `--worktree` branch" — the rule that `complete`
  runs from the primary checkout.
