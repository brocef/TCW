# Stage: plan

**Purpose.** Decide _how_, in ordered steps someone else could follow — where
sequencing risk is found, before a half-finished implementation finds it.

**Inputs.** `initial-request.md` and `spec.md`. Repository discovery is
unrestricted.

**Produce** `plan.md`, in the item's folder. Required: ordered tasks, each
naming the **exact files it creates or modifies** and what proves it; a
**Documentation Sync** block; and a **Verification** section covering anything
the suite cannot check. Optional `## Notes`.

## Steps

1. Order tasks so the suite is green at every commit boundary. A task that
   leaves the tree broken for the next one is two tasks.
2. Put the riskiest change where it is _isolated_, not where it is convenient —
   typically after its infrastructure exists and its tests are already written.
3. {{tcw:documentation}}Evaluate every Documentation Sync entry in the project's agent guide
   (`AGENTS.md` or `CLAUDE.md`) and name a task for each trigger that will
   fire.{{/tcw:documentation}} **Schedule them as one block at the end**, after the code tasks —
   implementation answers them in one pass over the finished diff. If the scope
   is too exploratory to predict per file, name one final "re-evaluate
   Documentation Sync triggers" task instead.
4. Record dependencies between items as blockers, not prose — `start` refuses
   past a blocker: `tcw work edit <slug> --blocked-by <ref>`.
5. **No placeholders.** "TBD", "add error handling", "similar to Task 3" — a
   task nobody can execute without asking you a question is not a task.
6. **Self-review.** Re-read the finished plan against the spec: every
   acceptance criterion is covered by at least one task and every task traces
   back to one; inconsistent names; tasks that appear twice.
7. Commit `plan.md` on its own, before `tcw work start`.

## Exit badly

- _Planning reveals the spec is wrong._ Return to `spec` and fix it. Do not
  plan around a spec you no longer believe.
- _A task cannot be verified._ Say so in the task rather than inventing a test
  that would pass either way.
- _The work is too large._ Better found here than at `implement`. Decompose.
