---
description: Drive a TCW work item from wherever it is through implementation, stopping for user verification before closeout.
---

Use the `tcw-work` skill. This command covers **the current stage through
`complete`**.

Read `skills/tcw-work/SKILL.md` and detect the current stage from the item's
type, status, and existing artifacts. Load **only** the document for the stage
you are in; the router's "Finding your place" table maps missing artifacts to
stages.

If `plan.md` declares bounded stage documents, read the manifest first and then
only the stage document relevant to the current slice. Dependency ordering there
is guidance, not a transition gate.

Commit each lifecycle artifact as you write it, in separate ordered commits —
never one batched lifecycle commit. Inspect each diff and stage narrowly. TCW
commits the `start`, `submit`, `rework`, and `complete` status moves itself; do
not commit those by hand.

Before implementation begins, run `tcw work start <slug>` if the item is not
already active, and ask whether to run the remaining stages sequentially or
dispatch independent ones to subagents (`references/delegation.md`).

**Do not complete the item silently.** Stop at `verify` and hold there until the
user explicitly approves closeout — see `references/stage-verify.md`. At closeout,
confirm the merge or PR route, the documentation updates, any follow-up items,
and the version choice before running `tcw work complete`.

$ARGUMENTS
