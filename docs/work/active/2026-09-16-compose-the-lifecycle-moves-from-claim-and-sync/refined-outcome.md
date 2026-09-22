# Refined outcome: compose the lifecycle moves from claim and sync

## Decision

**Accepted** on 2026-09-22 by the coordinating session. For this epic the requester
approves at the epic's own `verify` stage and lets each child complete on a clean
assessment, stopping only where a finding needs a decision. One did (B3), and they
answered it on 2026-09-22.

## Evidence

- Full suite, run by the coordinating session from the worktree in a private
  virtual environment, bare `pytest -n auto`, `import tcw` confirmed to resolve
  into the worktree: **4387 passed, 3 skipped, 0 failed**. `tcw validate` and
  `tcw capabilities check` both OK.
- `tcw:verifier` on the first submission: every checkable criterion met, eight
  mutations redone and red. Criterion 14's second half stays unverifiable until
  `transitions.start` becomes optional, which is the next child.
- Four review rounds, recorded below.

## How this item was reviewed, and what that cost

| Round | Reviewer | Verdict |
| --- | --- | --- |
| 1 | `tcw:verifier` | Accept after three documentation corrections |
| 1 | `adversarial-code-reviewer` | NOT DONE — three blocking defects, none covered by a spec criterion |
| 2 | rework | All fixed, 17 mutations, suite green |
| 3 | `adversarial-code-reviewer`, bounded | NOT DONE — B1 and B2 each fixed on one of two paths; S1's message false on one of its two failures |
| 4 | rework, then `adversarial-code-reviewer`, bounded | No blockers; one significant finding, now fixed |

The pattern the project's guidance warns about appeared exactly as described:
round 3 found holes in round 2's repairs rather than in the original work. The
requester chose one more round and it converged.

**What actually caught the defects.** Not the test suite, which was green at every
submission. Reviews that traced properties rather than routes, and probes run
against the fake tracker. Three times a deliberate code break stayed green,
proving the test too narrow rather than the code right; each time the test was
widened until it went red.

## Decisions taken during verification

- **B3, by the requester.** When the ticket is already past the claim's own status
  and `exclusive-claim-transition` is set: outside strict mode, skip the assertion
  transition and take the ticket by assigning it and reading the assignment back,
  leaving the ticket where it is; under strict mode, refuse the start before the
  item moves. Spec Design 3 and criteria 1 and 2 were amended to match, because the
  spec is where a rule changes.
- **The final fix was not shipped as instructed, and that was right.** The
  coordinating session asked for `since = ticket.status` on the fallback path. The
  implementer measured it first and found it would break the one recovery that
  works today, and shipped `if syncing and resolving: since, expected = ticket.status, ()`
  instead — a rule the module already states in two places. The mutation that
  applies the literal instruction turns the delivery assertion red, so the test
  pins the difference.

## Known effects, deliberately accepted

- A completion carrying an undelivered start, on a workflow with no single
  transition to the closing status, is now reported as a conflict rather than
  walked up through the working statuses. The walk is what B1 exists to stop. The
  user closes the ticket in the tracker, or moves it to a status that does offer
  the closing transition and runs `sync` again.
- On that same path `work.tracker.transitions.complete` and `.discard` are now
  enforced, where a recorded start used to bypass them. Recorded in the changelog.
- The web application's `work.start` on an active item nobody holds now answers
  HTTP 422, because the store accepts the case and the web application passes no
  owner. A candidate follow-up, not this item's.
- Two simultaneous starts of an unowned active item from different checkouts: the
  last writer wins.

## Deferred to a separate item

Both were found in round 4 and confirmed as older than this change:

- A leftover start record leaves an empty window, and the forward-only guard then
  refuses a legitimate `rework` with "a rework does not move a ticket back" — while
  moving In Review back to In Progress is exactly what a rework is (criterion 18d).
- The catch-up walk's re-entry (`sync.py:864-868`) looks unreachable: it needs a
  record, and a record makes `check_only` false, and the non-`check_only` catch-up
  path has already returned.

## Not done

- **The real-Jira check.** Every criterion here was proved against the in-repo fake
  tracker. The originating issues were all found in real use, so one throwaway
  ticket walked through the whole lifecycle against a live project is still the
  check that has not been run. It needs the requester's consent to create a ticket.
- GitHub #41 and #42 are answered only after the version carrying this epic is cut
  and pushed, as `CLAUDE.md` requires.

## Closeout

`tcw work complete` merges `work/<slug>` into `main` locally. The push goes with
the epic's release.
