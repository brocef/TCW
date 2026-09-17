# Judge a worktree item's completion from its branch, not the primary checkout's stale copy

## Request

An item started with `tcw work start --worktree` is worked on its own branch, and
every lifecycle move made during that work — `submit` to `review`, `rework` back
to `active`, the verify artifacts, blockers resolved, fields edited — is committed
on that branch. `tcw work complete` has to be run from the primary checkout, where
the item's copy has not changed since `start` and still reads `active` until the
merge-back.

`complete` currently makes its judgments about the item from that out-of-date
copy, so it can report things that are not true. On 2026-09-16, completing
`2026-09-16-route-agents-to-tcw-work-stage-for-stage-instructions-and-validate-its-arguments`
printed:

> tcw work complete: completing … directly from active; the verify stage was skipped

On the branch, that item had been submitted to `review` (`dc14ca2b`), gone
through a rework cycle, and carried `refined-outcome.md` (`3b4f843a`). The
warning was false.

What is wanted: when `complete` runs for an item started with `--worktree`,
**every judgment it makes about the item before the merge-back is made from the
branch's copy of the item**, which is where the work happened. That covers, at
least:

- the "directly from active; the verify stage was skipped" warning;
- the unresolved-blocker check;
- the strict tracker-mode refusal (`_strict_refusal`);
- anything else read from the item before the merge — including the status
  handed on to hooks and tracker delivery, if it turns out to be read too early.

The requester's view: "Our worktree support isn't great and this is a good
example."

## Constraints

- A refusal still has to leave the item, its branch and its worktree exactly as
  they were — so these judgments cannot simply move after the merge. They must
  be made before the merge can fail, but from the branch's copy.
- `complete` still runs from the primary checkout (`CLAUDE.md` § "Working in a
  `--worktree` branch"); this request does not change that rule.

## Out of scope

- Other commands run from the primary checkout that read a worktree item's
  out-of-date copy (`show`, `list`, and so on). The requester chose to limit
  this item to `complete`'s pre-merge judgments.
- `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies` (GitHub #39), a
  separate worktree defect.

## Notes

- Asked for reference material beyond the intake's; none provided.
- Confirmed against the code at request time: in `tcw/work/cli.py` `_complete`,
  the status warning, the blocker check and `_strict_refusal` all run before
  `merge_worktree`; the item is re-read only after the merge, for the capability
  gate.

## References

- `tcw/work/cli.py`, `_complete` — where the stale read and the post-merge
  re-read both live.
- `2026-09-10-record-a-work-item-s-branch-and-let-a-node-declare-its-own-state-fields`
  — defines the item's `worktree`/`branch` fields a fix would read. Not a blocker.
- `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies` — related worktree
  defect (GitHub #39). Not a blocker.
- `CLAUDE.md` § "Working in a `--worktree` branch" — why `complete` runs from the
  primary checkout.
