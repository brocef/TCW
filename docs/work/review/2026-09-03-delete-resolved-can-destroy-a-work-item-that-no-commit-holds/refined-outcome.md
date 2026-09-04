# Refined outcome — `delete_resolved` can destroy a work item that no commit holds

_Accepted._

## Decision

Accepted. Every reproduced destroy path now refuses, each with its own test, and
the guard that replaced three partial ones asks a strictly stronger question than
any of them.

## Evidence

- **Suite:** 2322 passed; the five environmental failures only.
- **The headline case refuses.** On a default node — the shipped ignore rules in
  place, so no commit holds the item — `tcw work delete <slug>` exits 1 saying
  "no commit holds", and the folder is still there. Before, it exited 0 and
  removed it.
- **The three cases an existence check would have missed** are each covered: a
  receipt written into the folder after the resolving commit, an uncommitted
  move under `auto-commit-transitions: false`, and the ignore-rule case above.
  That is the advisor's correction, tested rather than taken on trust.
- **The re-run keeps the good pointer**, asserted by resolving the recorded SHA
  and finding the item's `state.yaml` in it.
- **The moved-away removal is committed**, asserted by `git status --porcelain --
  docs/work` being empty afterwards — the state that previously left a remote
  holding an item the store had deleted.

## Deferred follow-ups

- **A detached HEAD is still permitted.** The advisor noted both commits would be
  reachable only from HEAD and the reflog, and that `_publish_branch` already
  refuses detachment but only for a publishing store. The retrievability check
  passes there, correctly — the content *is* in the commit — so this is a
  durability question about the repository, not about the removal. Worth its own
  item; not folded in here.
- **The read side of a squash-merged history.** `describe_location` reports an
  unresolvable commit honestly, which is all it can do.

## Closeout choices

- **Merge route:** the session branch. The `autonomous-work` skill says to merge
  into main locally and never push; this session's own instructions say to push
  to the designated branch and never push elsewhere. The session instruction
  wins, and this deviation applies to every item in the run.
- **Documentation:** changelog only. No user-facing surface changed — a command
  that used to destroy data now refuses — and the release-note entry for
  retention already describes the intended behaviour.
- **Capabilities:** none. `work/keep-resolved-work-out-of-git` already claims the
  content stays retrievable; this makes the claim true.
- **Version:** accumulating into `upcoming.md` per the skill; no cut.
- **Originating GitHub issue:** none.

## Notes

The advisor rejected my central premise and was right. Worth recording that the
premise was reasonable-sounding — "one condition, three explanations" — and that
what made it wrong was a distinction I had not drawn: *has this path* versus *has
these bytes*. The verify stage that passed the original work would not have found
it either, because it checked the criteria I wrote.
