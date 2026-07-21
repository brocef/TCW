---
description: Drive a TCW work item through every remaining lifecycle stage up to user verification, then close out only after explicit approval.
argument-hint: <work-item-slug>
allowed-tools: Bash(tcw *)
disable-model-invocation: true
---

Current state of the requested item (empty if no/invalid slug):

!`tcw work show $ARGUMENTS 2>/dev/null`

Use the `tcw-work` skill. Read `skills/tcw-work/references/lifecycle.md` and detect the
current lifecycle path and stage from the item type, item status, and existing
artifacts:

- missing `initial-request.md` -> start at request ingestion;
- missing `spec.md` -> continue with request processing;
- missing `plan.md` -> continue with spec processing;
- missing `outcome.md` -> start/continue task implementation or epic coordination;
- missing or stale `refined-outcome.md` -> stop for verification and refinement.

When `plan.md` declares stages, read it first and then load only the stage
document relevant to the current slice. Run its pre-stage checks before
implementation and post-stage checks afterward. Dependency ordering is guidance,
not a transition gate; record informal progress in `plan.md` or `outcome.md`
without treating it as formal stage state.

After writing or materially updating any lifecycle artifact, commit that stage's
artifact and related TCW work files before continuing to the next missing stage.
If this command runs several stages, produce separate ordered commits rather
than one batched lifecycle commit. Inspect each diff, stage narrowly, and do not
create empty commits for unchanged stages. Commit `tcw work start` and
`tcw work complete` status moves separately at their transition boundaries.

Run all remaining stages through task implementation or epic coordination. Before
that stage begins, run `tcw work start <slug>` if the item is not active and ask
whether to execute sequentially or parallelize genuinely independent phases with
subagents.

Do not silently complete the item after implementation. Stop in verification and
refinement until the user explicitly approves closeout. At closeout, confirm merge
or PR route, documentation updates, follow-up TCW item creation, and version bump
choice before running `tcw work complete <slug> --resolution ... --confirm`.
