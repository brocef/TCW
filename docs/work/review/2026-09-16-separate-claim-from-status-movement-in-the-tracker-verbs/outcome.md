# Outcome: separate claim from status movement in the tracker verbs

This epic wrote no code. Its `implement` stage is coordination: open the children,
record their order, dispatch them, read the rollup at each checkpoint, and answer
the questions a child could not answer for itself. What shipped is six children,
each with its own artifacts retained in git.

## What shipped, task by task

| Plan task | What it produced | Retained in |
| --- | --- | --- |
| Task 1 — open C1 | `2026-09-16-make-claim-and-release-assert-ownership-without-moving-a-ticket` | `ee59c22a` |
| Task 2 — open C2 and C3 | `2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item` | `108446fa` |
| | `2026-09-16-retire-the-claim-transition-key-into-a-named-start-transition` | `a2b72dac` |
| Task 3 — open C4 | `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync` | `8e9937b4` |
| Task 4 — start the epic | epic active from `2026-09-17` | — |
| Task 5 — rollup checkpoints | three checkpoints, below | — |
| Task 6 — closeout | this stage and `refined-outcome.md` | — |

**Two children the plan did not contain.** Both were opened during the run because
a child's own review found the epic's scope was drawn a line short:

| Child | Retained in | Why it exists |
| --- | --- | --- |
| `2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode` | `2bbac5b7` | C1 put the exclusivity assertion behind an optional key. Strict mode promises only one person can take a ticket, and without that key nothing keeps the promise, so strict mode has to require it. |
| `2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move` | `a20cc1c4` | C3 deliberately kept `transitions.start` required, because at C3 a start still rode the claim. C4 made a start go through `assess_move` like every other move, which is what made the key droppable. The spec's open question 5 named this and left it to a later change. |

The plan said four children. Six is not scope creep: each addition is a consequence
the spec anticipated and parked, and each was opened as its own item with its own
spec rather than folded into a child already in flight.

## Test result

Full suite on the merged tree, run in a private virtual environment from the primary
checkout: **4404 passed, 3 skipped, 0 failed**. `tcw validate` OK,
`tcw capabilities check` OK.

For comparison, the suite stood at 4387 before the last two children.

## Checkpoints

**Checkpoint 1 — after C1** (`b64e0b76`, 2026-09-17). The reconcile ran at the point
the plan asks for, and C2 was allowed to proceed, so the decision the checkpoint
exists to make was made in C2's favour. What is *not* recorded anywhere is the
reasoning: the commit message is bare, and no note says criteria 1 to 4 were checked
against C1's delivered behavior rather than the checkpoint being treated as a
formality. C1 was not reworked.

**Checkpoint 2 — after C2 and C3** (`229cc9b1`, 2026-09-17). Same shape, and the same
gap: the reconcile ran, both children stood, and nothing records whether criteria 8
and 10 or the `--part` hold were actually re-checked at that moment. The spec's
risk 3 named the `--part` hold as the likeliest thing to break silently under C2, so
this is the checkpoint whose missing reasoning matters most.

**On those two gaps.** A checkpoint that leaves no record of what it decided cannot
be distinguished afterwards from one that was skipped. The criteria in question are
all covered by checkpoint 3 below, run against the merged tree, so nothing is left
unverified — but it is verified later and in bulk rather than at the moment the
plan wanted it, which is weaker. The fix for a future epic is a sentence in the
reconcile commit saying what was checked, not a heavier process.

**Checkpoint 3 — before closeout.** Recorded in `refined-outcome.md`, because it is
the verification the `verify` stage exists to weigh rather than a coordination note.

## What the plan and the spec got wrong

**1. The request claimed the whole epic would ship in one version cut. It did not.**
C1 and C3 shipped in v2.4.0, v2.5.0 and v2.5.1 before C4 was written. Found by the
spec stage, confirmed with `git tag --contains ee59c22a`, and corrected by a note on
`initial-request.md` rather than by rewriting it — the record of what was believed
at request time is worth more than a tidy document.

**2. The plan said C3 was blocked by C1. It was not.** C3's premise is that the
claim no longer transitions, and that becomes true at C4, not at C1, which edits no
delivery code. The false blocker was removed and the plan amended in place. A
blocker that is not real is a lie the tool then enforces, so this was worth
correcting rather than working around.

**3. The plan's Documentation Sync table said `skills/configure/references/` fires
in C3 only.** C1 also added a configuration key — `exclusive-claim-transition` —
which the table predated. Amended.

**4. The plan said C4 would delete `_strict_claim`.** C4 kept it and changed what it
asserts through. The plan was corrected at C4's own implement stage rather than the
function being deleted to match a document.

**5. Four children was an underestimate**, for the reason given above.

**6. Task 5 asked for checkpoints to "earn a decision rather than a read", and gave
them nowhere to record one.** Both of the first two checkpoints ran and left only a
bare reconcile commit, so whether a decision was earned is now unrecoverable. The
plan should have named the artifact the decision goes in.

## Notes

**On how much review this epic needed.** C4 took four review rounds. Rounds 3 found
holes in round 2's repairs rather than in the original work, which is the exact
pattern this project's guidance warns about, and is why the split between "belongs
to this change" and "needs a separate change" went to the requester instead of being
decided quietly.

**What actually found the defects, across every child: not the test suite.** It was
green at every submission, including the two that carried blocking defects. What
found them was review that traced properties rather than routes, and probes run
against the in-repo fake tracker. Several times a deliberate break of the code
stayed green, which each time proved a test too narrow rather than the code right.
