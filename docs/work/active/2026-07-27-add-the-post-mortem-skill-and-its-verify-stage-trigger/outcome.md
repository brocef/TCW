# Outcome

All four tasks shipped. **943 Python tests**, `tcw validate` OK.

## What shipped

`skills/tcw-post-mortem/` — the **methodology** half of the `postmortem` stage.
Child 4's `stage-postmortem.md` already defined the contract (inputs, artifact,
required content, the out-of-band rule), so this skill deliberately does not
restate any of it. It covers what that document does not: how to read the spine
backwards, what each layer tends to reveal, and when to stop *without* a
recommendation.

The distinction the whole skill turns on: **"nobody could have known" versus
"nobody checked."** Only the second is actionable, and conflating them
manufactures process for non-recurring events — which is how a lifecycle
accumulates ceremony nobody believes in.

Plus the read-only `tcw-post-mortem` agent, the `/tcw-post-mortem` command, and
the `plugin/run-a-post-mortem` capability.

**The `verify`-stage trigger already existed** — child 4 wrote it into
`stage-verify.md` step 8. Nothing to add.

## `pr` deleted

Added by child 1 of this epic on the prediction that
`complete --already-integrated` would read it. That flag needs only the
pre-existing `worktree` and `branch` fields. Children 2a, 2b, and 4 each passed
without a consumer, and stage documents have no reason to read a field.

Four children with no consumer is enough. Deleted, with the test replaced by one
recording *why* — the third time this epic applied the pattern, after `phase` and
`dod`, and the only time it removed a field it had itself added. That is the more
useful lesson of the three: the pattern is not just for legacy cruft.

## Notes

**This child was smaller than planned, and that is the plan working.** The
compressed cycle assumed `stage-postmortem.md` had already specified the
contract, so only methodology remained — and that assumption held. Had child 4
not written the stage document first, this child would have had to invent the
contract and child 4 would have had to match it, which is the ordering the epic
plan's dependency graph existed to prevent.

**Nothing here consumes `LIFECYCLE_STEPS` differently.** `postmortem` was already
in the table with its stage document, so `test_skill_lifecycle_parity.py` covers
this child unchanged — the guard child 4 built was immediately load-bearing for
the child after it.
