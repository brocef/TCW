# Implementation plan

Compressed cycle — no separate spec. The epic plan and `stage-postmortem.md`
(shipped by child 4) already specify this at spec-level detail, and child 4
settled the artifact's *structure*. What is left is the **methodology**: how to
actually conduct a post-mortem.

## What child 4 already shipped

`references/stage-postmortem.md` defines the contract: inputs (the spine read
backwards, `## Notes` as the primary trail), `post-mortem.md` as the artifact,
its required content, and the out-of-band rule that it never changes status and
is legal both in `review` and after `completed`. The `verify` stage already
carries the step offering a post-mortem when verification surfaced serious
unforeseen problems.

**So this child must not re-specify any of that.** Duplicating the stage document
into a skill is the failure mode the whole epic exists to remove.

## Task 1 — `skills/tcw-post-mortem/`

A standalone skill, because a post-mortem is invoked on its own — often days
after the work closed — rather than as part of driving an item.

`SKILL.md`, thin, covering the part `stage-postmortem.md` deliberately does not:

- **How to read the spine backwards** and find the earliest stage that could have
  caught the problem. The mechanics: what `## Notes` usually reveals, how to use
  the commit range, what an artifact's *absence* tells you.
- **Distinguishing "nobody could have known" from "nobody checked."** Only the
  second is actionable, and conflating them manufactures process nobody needs.
- **When not to write one.** A one-off miss with no generalizable cause should
  end the post-mortem, not produce a recommendation.
- A pointer to `tcw-work/references/stage-postmortem.md` for the contract —
  named once, never restated.

## Task 2 — `agents/tcw-post-mortem.md`

Read-only, same shape as `tcw-verifier`. It reads the spine and the history and
reports; it writes nothing. Claude-only accelerator — the skill stands alone
without it, and Codex runs the same analysis inline.

## Task 3 — `commands/tcw-post-mortem.md`

Thin wrapper naming the stage and pointing at the skill. Also reachable by
invoking the skill directly, since Codex has no slash commands.

## Task 4 — doc sync

`README.md` (the new skill, agent, and command), the changelog, release notes,
and a `plugin/run-a-post-mortem` capability.

No parity-test change: `postmortem` is already in `LIFECYCLE_STEPS` and already
has its stage document, so `test_skill_lifecycle_parity.py` covers it unchanged.

## Verification

1. Full suite and `tcw validate`.
2. The parity test still passes — this child adds no lifecycle id.
3. Confirm the skill does not restate the stage document's contract. That is a
   manual check, and it is the one that matters here.

## Notes

**Delete `pr` in this child.** Five children have now passed without consuming
it, and stage documents have no reason to read a field. It is a persisted field
nothing reads — exactly what this epic removed twice, in `phase` and `dod`.
Removing it here rather than at epic close keeps the pattern applied by the child
that proves the prediction failed.
