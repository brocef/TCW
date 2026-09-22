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

---

# Rework, 2026-09-22

Sent back at verify. `rework.md` is the work list; this section records what each
item changed and the evidence for it. Same worktree, same private virtual
environment, `tcw work` still driven by hand.

## Commits

| Commit | Item | What |
| --- | --- | --- |
| `3f00b942` | B1 | A completion or a discard never delivers a recorded start first. |
| `c9088ae7` | B2 | A failure during the recorded-start hop leaves the record naming `start`. |
| `d724b270` | B3 | No claim applies `exclusive-claim-transition` from above the claim's own status. |
| `4c498e03` | B3 (spec) | Design 3 and criterion 1 restated, because B3 changes a rule the spec describes. |
| `a57fcffa` | S1 | A claim whose transition landed and whose assignment did not says so, and how to recover. |
| `0f3bbb94` | S2, false text, coverage gap | The claim's false sentences corrected, the catch-up completion documented, the created record's fields covered. |

## B1 — a resolution never delivers a recorded start first

**Changed.** `not resolving` added to the recorded-start block
(`tcw/tracker/sync.py`), with the reason in the comment above it: a completion or a
discard is where work stops, so a start it never delivered is not owed any more,
and marching the ticket up into a working status only to close it is what
`ladder_steps` already refuses to do for a discard. `resolving` is true for both
`complete` and `discard`, so the one condition covers the completion side the
rework asked about. A catch-up binding toward a completion never reaches this
block — it returns through `walk()` first — so nothing there changes.

**Proof.**
`test_a_resolution_carrying_a_start_record_does_not_deliver_the_start_first`
(`tests/test_tracker_sync.py`), parametrized over a discard and a completion, on a
workflow offering a way onto the ladder and both ways off it from every status, so
nothing but the rule under test decides how many transitions are sent.

**Mutation.** `not resolving` removed → both cases red, `['21', '31']` where
`['31']` was asserted: the march through `In Progress` the rework's probe saw.

## B2 — a failed start hop keeps the record naming `start`

**Changed.** All three failure returns in the recorded-start block set
`move = "start"` before calling `finish`. The comment says why: a record naming the
later move gives that move a window beginning at `statuses.active`, where the hop
never managed to put the ticket, so every later `sync` reads the ticket as drift.

**Proof.** Two tests.
`test_a_failure_delivering_a_recorded_start_keeps_the_record_naming_the_start`
covers all three failure points — a hop with no transition offered, an unreachable
`POST`, and a read-back that fails after the `POST` landed (armed from inside the
`POST`, so it cannot catch an earlier read). `test_a_submit_whose_start_hop_was_
unreachable_is_recovered_by_a_later_sync` runs the whole cycle through to the
`sync` that finishes both moves.

**Mutations.** All three assignments removed → all four cases red with
`'submit' == 'start'`. Separately, the transition-failure assignment removed *and*
the record assertion deleted from the recovery test → the `sync` refused with
exactly the drift message `rework.md` predicted, "TCW does not move it back: put it
in 'In Progress' or 'In Review'".

## B3 — the claim never moves a ticket back

**Changed**, as the requester decided, in two places.

- `deliver` (`tcw/tracker/sync.py`): where the key is set and the ticket's rung is
  above 0, the assertion is not passed to `assert_ownership`. The ticket is taken
  by the assignment and its read-back alone and left where it is, and the claim's
  message says so, naming the setting, so nobody reads a weaker claim as the
  stronger one they configured.
- `_strict_claim` (`tcw/work/cli.py`): the same case is refused before the item
  moves, naming both ways out — move the ticket back to `statuses.active`, or turn
  strict mode off.

**One narrowing the rework did not name, and it came from a shipped test.** The
strict refusal fires only where the assertion would really be applied: not for a
ticket already this account's (`assert_ownership` returns before the transition, so
nothing could move back and exclusivity is already settled), not for a resolved one,
and not for one somebody else holds — `assert_ownership` refuses those itself with
far better messages. Without the narrowing,
`test_start_of_a_ticket_already_yours_in_review_leaves_it_there` went red, which is
how it was found.

**Proof.** In `tests/test_tracker_strict.py`, on the `GLOBAL` workflow, which offers
the claim transition from every status:
`test_a_start_above_the_claim_transition_takes_the_ticket_without_applying_it`,
`test_a_strict_start_above_the_claim_transition_is_refused_before_the_item_moves`,
and `test_a_strict_start_on_the_claims_own_status_still_asserts_through_it`
(parametrized over a ticket below the ladder and one on the claim's own rung).

**Mutations.** `weaker = False` in `deliver` → the non-strict test red, `['21']`
applied: the backwards move. `past = ""` in `_strict_claim` → the strict test red,
exit 0 with the ticket dragged back. `rung > 0` widened to `rung is not None` in
`_strict_claim` → the on-the-claim's-own-rung case red. The same widening in
`deliver` → `test_start_of_a_ticket_already_yours_in_review_leaves_it_there` red.
Dropping the "would the assertion really apply" narrowing → that same test red.
The first version of the rung test only covered a ticket below the ladder and went
**green** under the widening mutation; it was widened until it went red.

**Spec.** Design 3 gains a subsection stating the rule and why the two modes differ,
and criterion 1 now says the start is refused under strict mode with the key set.
Committed separately as `4c498e03`.

## S1 — a claim whose transition landed and whose assignment did not

**Changed.** (a) In `tcw/tracker/ownership.py`, `refused()` carries `transitioned`,
and `OwnershipOutcome.status` now reports where an applied assertion left the
ticket rather than where it was found — a caller told the old status cannot tell
the user what to put right. (b) `deliver` and `_strict_claim` both say "{key} was
moved to '{status}' but is not assigned to you. Assign it to yourself in the
tracker, then run this again.", in place of advice that would send the user in a
circle: re-running cannot finish the claim, because the assertion transition is no
longer offered from where the ticket now sits, which is the very property that makes
it exclusive.

**Proof.** `test_a_failure_after_the_assertion_reports_the_transition_and_where_it_led`
(`tests/test_tracker_ownership.py`), over a refused assignment and a failed
read-back, and its negative twin
`test_a_refusal_before_the_assertion_reports_no_transition`. Through the two
callers: `test_a_strict_start_whose_assignment_failed_says_the_ticket_moved` and
`test_a_start_whose_assignment_failed_after_the_transition_says_the_ticket_moved`.

**Mutations.** `refused()` dropping `transitioned` → all four red. `landed` not
updated after the transition → all four red. `deliver` back to the old advice → the
`deliver` test red. `_strict_claim` back to the old advice → the strict test red.

## S2 — completing an older catch-up binding still needs the ticket

**Documented, not changed**, as `rework.md` asked, and the fix did not fall out of
B1: `resolving` is false for a `complete` on a catch-up binding, so such a
completion goes through `walk()` and is still refused when somebody else holds the
ticket. Recorded in the Jira guide's "`complete` and a discard need no claim"
paragraph as a named exception, with the remedy, and in the changelog. Only
bindings written before `link --sync-status` was retired are affected, and nothing
writes the key any more.

## False text

- **The triage sentence** (`docs/guide/jira.md`): `submit` and `rework` *do* take a
  ticket out of triage when the item still carries an undelivered start, because
  the recorded start is what takes the ticket. Said, with the condition. The list
  of commands that never do keeps `complete`, a discard, `tracker claim` and
  `tracker create`.
- **"Only `tcw work tracker sync` moves a ticket backwards"** (release notes and
  the Jira guide): replaced with the actual rule — no lifecycle move takes a ticket
  back out of its own window, which is why `rework` still brings a ticket from
  review down to active (criterion 18d) while a `start` leaves a ticket somebody
  moved on alone.
- **The `submit`/`rework` release-note bullet**: "If Jira cannot be reached they go
  ahead" now says what strict mode does instead — refuses, and the item does not
  move (criterion 11).
- **`sync.py`'s past-the-claim refusal**: "Claiming it from there could move it
  back" is said only where `exclusive-claim-transition` is set; without the key a
  claim is an assignment and moves nothing, and the refusal gives the true reason
  instead. The refusal itself is unchanged, as the spec's Design 2 table asks.
  Pinned by
  `test_the_past_the_claim_refusal_only_blames_the_claim_transition_when_there_is_one`,
  parametrized both ways; mutation — the reason stopped depending on the key — red
  on the no-key case.
- **"is already held by you"**: printed only for a `start` now, not for every move
  that takes the ticket, so a `submit` carrying a leftover start record no longer
  reports something about a move nobody asked for. The strict half needed the CLI,
  which is the only layer that knows: `_strict_claim` prints its own claim line
  ("{key} is held by you.") and passes `say_claim=False` to `_deliver_after`, so the
  claim this command just made is never reported as *already* held. Pinned by
  `test_only_a_start_says_the_ticket_was_already_held`,
  `test_a_start_on_a_ticket_already_yours_still_says_so` and
  `test_a_strict_start_says_it_took_the_ticket_not_that_it_was_already_held`;
  three mutations (the old condition restored, the strict line removed, `say_claim`
  ignored) each red.
- **The catch-up walk's "past where its item is" refusal** no longer says the
  ticket was not *claimed*: this run may well have just claimed it.
- **The `walk()` comment**: both paths into it need `catch-up: true` on the
  binding, and neither depends on a claim being owed any more. Rewritten to say
  that, and that nothing writes the key so every walk is on an older binding.

## Coverage gap

`test_create_brings_its_ticket_to_work_under_way_without_a_catch_up` now asserts
that the record `tracker create` writes has exactly `RECORD_FIELDS`, restoring the
guard the removed `test_the_link_that_asks_for_a_catch_up_writes_no_claim` gave:
no command writes a claim into the record. Mutation — a `claim: owed` key added to
what `create` writes — red.

## Known effects, recorded and not fixed

From `rework.md`'s "not this item's" list, carried here so they are not lost:

- The web app's `work.start` on an active item nobody holds now returns HTTP 422
  (`ValueError("takeover requires an owner")`): the store accepts the case and the
  web app passes no owner (`tcw/serve/__init__.py:953`, `tcw/store/fs.py:4056-4059`).
  A candidate follow-up item.
- Two simultaneous starts of an unowned active item from different checkouts: the
  last writer wins.
- The contradictory "resolved … take it with `tracker claim`" advice, which is on
  `main` already, and the untested backup refusal in `_tracker_link` for an item
  somebody else holds.

And one this rework adds:

- Under B1, a completion carrying an undelivered start, on a workflow with no
  transition from the ticket's current status straight to `statuses.completed`, is
  now reported as conflicting rather than walked up through the working statuses.
  That is the honest answer — the alternative is the march B1 exists to stop — but
  it is a refusal where there used to be a move, and a project on such a workflow
  finishes the ticket by hand or through `tcw work tracker sync`.
