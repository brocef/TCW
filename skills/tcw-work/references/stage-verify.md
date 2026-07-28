# Stage: verify

## Purpose

Obtain the user's acceptance decision on finished work. Not "check the tests
pass" — that is `implement`'s job. This stage exists to get an answer only the
user can give.

## Inputs

`spec.md` (what was promised) and `outcome.md` (what was delivered), plus the
diff.

Repository discovery is unrestricted.

## Produce

**One of two, and which one *is* the verdict:**

- `refined-outcome.md` — accepted. Records the decision, the evidence, deferred
  follow-ups, and the closeout choices.
- `rework.md` — rejected. Records what the implementation still has to do.

Never both. On the rejection path the agent **deletes `refined-outcome.md`** if
one exists: it asserts the work was verified, and after a rejection that is
false. TCW does not delete it for you — `tcw work rework` refuses while it is
present, so forgetting is caught rather than silent.

Optional `## Notes`.

## Steps

1. Run `tcw work lifecycle --stage verify` and honor any binding it reports.
   — agent `[judgment]`
2. `tcw work submit <slug>` so the item's status says `review` while it waits,
   rather than reading as still in progress. Optional — a small change may
   complete straight from `active`, and `complete` then prints a note that verify
   was skipped. — agent `[gated]`
3. Assess: read the diff against the spec's acceptance criteria, run the checks,
   form an opinion. **This half is delegable** to a read-only subagent — the
   `tcw-verifier` agent exists for it under Claude, and `delegation.md` has the
   rules. Codex has no custom agents, so do this inline there; nothing about the
   stage depends on the agent. — agent `[judgment]`
4. **Present the assessment and stop for the user's decision.** This half is not
   delegable — a subagent cannot ask the user, and nothing in the tool enforces
   the stop. — user `[judgment]`
5. Reconcile capabilities before closeout. **REQUIRED SUB-SKILL: Use
   tcw-capabilities.** — agent `[judgment]`
6. Write the artifact the verdict calls for, and commit it. — agent `[judgment]`
7. On rejection: delete `refined-outcome.md`, update any other artifact the
   rework invalidates, then `tcw work rework <slug>`. The tool refuses while
   `refined-outcome.md` is present. — agent `[gated]`
8. If verification surfaced serious unforeseen problems, offer a post-mortem —
   see `stage-postmortem.md`. Only on the user's assent. — agent `[judgment]`

## Exit

**Well:** the user has decided, the matching artifact records it, and the item
moves to `complete` or back to `active`.

**Badly:**

- *The user is unavailable.* Do not complete on their behalf. Leave the item in
  `review`; that status exists precisely so waiting is a visible state.
- *Acceptance criteria are unverifiable as written.* Say so plainly and record it
  — that is a `spec` defect worth a post-mortem, not something to wave through.
- *Verification finds the spec solved the wrong problem.* `rework.md` is the
  wrong instrument. Return to `spec`, or discard and re-request.
