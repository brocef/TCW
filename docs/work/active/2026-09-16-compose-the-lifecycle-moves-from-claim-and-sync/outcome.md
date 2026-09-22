# Outcome: compose the lifecycle moves from claim and sync

Worked in the worktree on `work/2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`,
from a private virtual environment, so the shared editable install was not touched.
The `tcw work` lifecycle was not driven from this code (it was under change); the
plan's corrections were written into `plan.md` by hand.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `2502bb56` | Five characterisation tests pinning the guards the rewrite must keep. |
| 2 | `1283182a` | `owed` split into `takes_ticket` and the ticket's own assignee. The pre-backlog step, the catch-up walk and the `pre-backlog` hint moved out of the claim (see below). A recorded `start` gets the live start's empty window. |
| 3 | `e2bfad98` | Forward only: a lifecycle move with no window whose ticket is above the target is `HELD`, with no record. |
| 4 | `9692b310` | `deliver` takes the ticket through `assert_ownership` (asserting through `exclusive-claim-transition`); landing refusal and the start's early return deleted; `claim_refusal`'s lifecycle call sites gone. `_strict_claim` kept and rewritten on `assert_ownership`. A recorded start the item moved past is delivered first. The walk looks for a shortcut before every hop. |
| 5 | `de51625b` | `OwnershipOutcome.retry`; an unanswered claim records `pending`. |
| 6 | `36caaff5` | `MOVES_NEEDING_NO_CLAIM = {complete, discard}`; the assignee check is skipped for them; `progress.py` follows. |
| 7 | `b69ec603` | The claim gate on `submit`/`rework` (every mode, refuses only on an answer); strict `complete` stops asking who holds the ticket but still asks where it is. New `tests/test_tracker_gate.py`. |
| 8 | `b49f2566` | `link --sync-status` retired (hidden, refuses naming link → claim → sync); nothing writes `catch-up`; `tracker create` records the start instead; `start` takes an active item with no owner; `AlreadyClaimed` names `tcw work tracker claim <slug> --take-over`. New `tests/test_work_start.py`. |
| Docs | `e7151787` | README, `docs/guide/jira.md`, release notes (after the strict-mode entry), changelog, `skills/work/references/commands.md`, `skills/configure/references/tracker.md`, and eight capability descriptions. |

## Test result

Full suite, `pytest -n auto` from the worktree (import confirmed to resolve into
it): **4348 passed, 3 skipped, 3 failed**. The three failures are timing tests —
`test_capabilities_federation.py::test_federation_stays_linear_in_chain_depth` and
both `test_check_versions.py::test_a_hanging_cli_is_abandoned_silently` cases —
and they fail the same way when run from the primary checkout on `main`, alone, on
this machine right now (load average about 16, other sessions running). At the
start of the session, under lower load, the baseline was 4312 passed, 3 skipped,
0 failed, and these three passed. They touch none of this change's code. A rerun
on a quiet machine (or CI) is still owed before trusting "green".

## Mutation checks

Every new assertion was broken on purpose and seen to go red for the stated reason:

- **Task 1.** Rework pin: no delivery → ticket stayed `In Review`. Drift pin: window
  check off → "offers no transition", not drift. Part hold: hold off → sync reported
  conflicting. No-request pin: early exit on `not owed` only → a completed item
  claimed its ticket. Claim-block resolved pin: guard off → "Claiming it from there
  could move it back".
- **Task 2.** `owed = assignee != me` (the collapse the spec warns about) → all three
  of `submit`, `rework`, `complete` sent an assignment.
- **Task 3.** `HELD` → `CONFLICTING`: red at the exit code, and a separate probe
  confirmed a conflicting record naming the start was written. Rule off → start
  refused. Rule applied to `sync` too → criterion 18c red.
- **Task 4.** Landing refusal back → criterion 1/2/18b red. `_strict_claim` without
  the assertion → the race test red (Bob's start was settled by read-after-write and
  moved; Alice's start inside the hook was the one refused) and the key test red
  (`['21']`, `transitions.start`, instead of `['61']`, the key). Hint's found-status
  check off → hint named after TCW's own transition moved the ticket. Shortcut only
  before the first hop → `['21','41','31']`. Recorded-start delivery off →
  pre-backlog `[start-record]` red. Recorded start's empty window reverted →
  `test_open_work_with_no_mapping_still_owes_a_recorded_start` red.
- **Task 5.** `retry` always false → criterion 17d red (recorded conflicting) and the
  read-back unit test red; always true → "an answer is not worth retrying" red.
- **Task 6.** Assignee check back for `complete` → criterion 8 red (probe confirmed
  "assigned to Bob"). Check skipped only for an unassigned ticket (widening the set
  alone) → criterion 8b red. `progress.py` back to discard only → completion
  comment test red. Owed-block exemption back to discard only → **no test went
  red**; that gap was closed with `test_a_completion_owing_a_start_still_takes_no_ticket`,
  which is red under it.
- **Task 7.** Gate refuses on silence → criterion 10 red. Gate off → criterion 6
  red. Gate refuses only another holder → criterion 6b red. Gate reads the local
  owner → criterion 6c red.
- **Task 8.** Store raises for an empty owner → criterion 3 red. Remedy dropped from
  `AlreadyClaimed` → criterion 4 red. `create` records the item's own move → create
  test red. Catch-up walk unreachable → criterion 13 walk test red. Retirement check
  off → criterion 5 red. Flag shown in help → help test red. `check_only` refusal
  deleted, as the plan asked → new test red, and a probe showed a report-only `sync`
  sent `PUT /assignee`.

## What the plan or spec got wrong

1. **Task 2 could not be green on its own.** With `owed` reading the assignee,
   `intake.claim` no longer runs for a ticket already yours, and the pre-backlog step,
   the catch-up walk and the `pre-backlog` hint all lived inside it. They moved out in
   Task 2. The walk now runs for any catch-up binding (with a "past its item" guard),
   and the hint is added only while the ticket is still in the status it was found in.
2. **"`expected` is not touched" broke retrying a failed start.** A start record got
   the window `(statuses.active,)` because the old claim put the ticket there. Without
   that move, every retry of a failed start whose ticket sat in `To Do` was refused as
   drift. A recorded start now gets the live start's empty window (`expected_statuses`),
   and when the item has moved past `active`, that start is delivered first and the
   next move measures from `active` — reproducing what the claim transition did.
3. **Task 4 said to delete `_strict_claim`; the spec said to rewrite it.** Deleting
   it would have moved a strict item locally before its ticket was taken, and
   `test_start_of_someone_elses_ticket_is_refused_and_moves_nothing` forbids that. It
   was kept and now asserts through `exclusive-claim-transition`.
4. **Task 7 said to remove `complete`'s strict gate.** Removing it whole would also
   have dropped the refusal of a ticket a reviewer sent back, which has nothing to do
   with a claim. It now skips only the ownership check (`authorize(..., ownership=False)`).
5. **Task 8 called the `check_only` refusal unreachable.** It is reachable through a
   part binding already carrying `catch-up: true`, which is still read. Deleting it
   would let a report-only `sync` take the ticket. Kept, with a test.
6. **Task 8 missed a writer of `catch-up`.** `tracker create` wrote it through
   `link`'s code for work already under way. It now records the start as undelivered
   (a pending record naming `start`), which the item-4 mechanism delivers.
7. **Smaller.** The retry field is true only when the tracker did not answer (a 400
   on the assignment is an answer), narrower than "every assign failure". `tracker
   sync` now prints what it did to take a ticket, because it takes tickets far more
   often than before and said nothing. `unsynced_hint` could not say "claim then
   sync" alone: `sync` makes one transition, so for a multi-rung gap it says to move
   the ticket yourself.

## Tests changed or removed, with the reason

- `test_a_discard_still_refuses_a_ticket_someone_else_holds` rewritten as
  `test_a_discard_closes_a_ticket_someone_else_holds_and_leaves_it_theirs`: it pinned
  the rule this item reverses.
- Removed: `test_strict_mode_still_asks_whether_an_assignment_is_exclusive_without_a_claim`
  and the `start` half of the strict "cannot exclude" test (`claim_refusal` on the
  lifecycle is gone by design); `test_a_claim_landing_off_the_ladder_stops_the_catch_up`
  (the landing refusal is gone); `test_sync_status_on_a_backlog_item_says_it_did_nothing`,
  `test_sync_status_refuses_an_item_somebody_else_started`,
  `test_the_suggested_link_for_somebody_elses_item_keeps_its_part`,
  `test_a_late_link_records_its_catch_up_without_a_claim`,
  `test_the_link_that_asks_for_a_catch_up_writes_no_claim` (the flag is gone; the last
  would now read only what the test itself wrote).
- Rewritten to the new rules: strict `start` of a ticket already yours in review
  (now succeeds, ticket left there); strict sync of an owed claim (now claims through
  the key); strict `complete` before the worktree merge (now refused for position, not
  holder); several plain-link and recorded-start tests whose `submit` is now refused by
  the gate; the pre-backlog "submit that owes the claim" test (now `sync`).
- `sync_link` in `tests/test_tracker_sync.py` now writes by hand the binding the old
  flag wrote, then runs `sync`, so every walk test still exercises the kept reader.

## Verification by hand

- **A real Jira project refusing an unassign or a transition** — not done; needs a
  live Jira project, and this session was told not to contact it.
- **The six documentation entries read together** — done while writing them; the
  README table, the Jira guide's "Tickets following their items" and strict tables,
  `commands.md` and `tracker.md` describe the same gate, the same resolution rule and
  the same retirement. A second reader would still help.
- **No lifecycle move applies a workflow transition as part of taking a ticket**
  (criterion 14) — asserted against recorded requests in
  `test_a_start_posts_the_one_transition_transitions_start_names` and
  `test_a_start_takes_an_unassigned_ticket_in_review_and_leaves_it_there`. The second
  half of criterion 14 ("none when `transitions.start` is unset too") cannot be tested
  here: the key is still required until the follow-up item makes it optional.

## Notes for the verifier

- `deliver` gained real mechanism beyond the plan (item 2 above, and the per-hop
  shortcut). It is the likeliest place for an unexamined interaction.
- The gate reads the ticket once before the move and `deliver` reads it again, so a
  reassignment between the two reads is reported after the move (one comment test
  now uses exactly that window).
- The past-the-claim refusal (`rung > 0`, "Claiming it from there could move it
  back") was kept as the spec's table says, although with no assertion transition a
  claim can no longer move anything back. A `sync` of a recorded start whose unowned
  ticket sits in review is therefore refused where a live `start` would claim it.
- The originating GitHub issue, if any, is answered only after the version is cut.
