---
name: commands-drive-work-to-completion
description: Drive a TCW work item from wherever it is through implementation, stopping for user verification before closeout.
when_to_use: Use when a user asks to drive, finish, or take a TCW work item to completion from wherever it stands — through implementation and verification, stopping for the user's approval before closeout.
allowed-tools: Bash(tcw *), Bash(git *), Read, Edit, Write
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---

Use the `work` skill. This skill covers **the current stage through
`complete`**.

Read the `work` skill's `SKILL.md` and detect the current stage from the item's
type, status, and existing artifacts. Invoke the `work-stage` skill for **only** the stage
you are in; the router's "Finding your place" section maps missing artifacts to
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
dispatch independent ones to subagents (the `work` skill's `delegation.md`).

**Do not complete the item silently.** Stop at `verify` and hold there until the
user explicitly approves closeout — see the `verify` stage (`work-stage verify <slug>`). At closeout,
confirm the merge or PR route, the documentation updates, any follow-up items,
and the version choice before running `tcw work complete`.
