# Stage: verify

**Purpose.** Obtain the user's acceptance decision on finished work. Not "check
the tests pass" — that is `implement`'s job — but an answer only they can give.

**Inputs.** `spec.md` (what was promised), `outcome.md` (what was delivered),
and the diff. Repository discovery is unrestricted.

**Produce exactly one of two, and which one _is_ the verdict:**
`refined-outcome.md` on acceptance — the decision, the evidence, deferred
follow-ups, and the closeout choices — or `rework.md` on rejection, recording
what the implementation still has to do. **Never both.** Optional `## Notes`.

## Steps

1. `tcw work submit <slug>`, so the item reads `review` while it waits, not as
   still in progress. Optional: a small change may complete from `active`.
2. Assess: read the diff against the spec's acceptance criteria and run the
   checks. **No claim without output from a command you ran just now.**
3. **Present the assessment and stop for the user's decision.** Nothing in the
   tool enforces this stop.
4. Reconcile the capability ledger against what shipped, before closeout.
5. Write the artifact the verdict calls for, and commit it.
6. On rejection: **delete `refined-outcome.md`** if one exists — it asserts the
   work was verified — update any other artifact the rework invalidates, then
   `tcw work rework <slug>`, which refuses while that file is present.
7. On acceptance: `tcw work complete <slug>`.
8. If verification surfaced serious unforeseen problems, **offer** a
   post-mortem. Only on the user's assent.
9. After `complete`, **offer** a version cut if the change set warrants one —
   the user's call, after the item closes, never during implementation.

## Exit badly

- _The user is unavailable._ Do not complete on their behalf. Leave the item in
  `review`; that status exists so waiting is a visible state.
- _Acceptance criteria are unverifiable as written._ Say so plainly and record
  it — a `spec` defect worth a post-mortem, not something to wave through.
- _Verification finds the spec solved the wrong problem._ `rework.md` is the
  wrong instrument. Return to `spec`, or discard and re-request.
