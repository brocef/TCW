# Plan: compose the lifecycle moves from claim and sync

Eight code tasks, then one documentation block. The suite is green at every task
boundary — no task leaves the tree broken for the next.

The ordering principle: **every guard that has to survive is pinned by a test
before the code that could break it is touched.** Six review rounds on the spec
produced three defects that were changes to guards whose other callers had not
been traced; tasks 1 and 2 exist so that class of mistake goes red instead of
shipping.

## Task 1 — Pin the guards that must survive, before touching any of them

Characterisation tests only. No production change. Every one of these passes on
`main` today; each exists so a later task cannot quietly remove the behaviour.

**Modifies:** `tests/test_tracker_sync.py`.

Pin, each with its own test:

1. `tcw work rework` on a bound item whose ticket is at `statuses.review` moves
   the ticket back to `statuses.active` and exits 0. (The case the rejected
   rung-comparison mechanism would have refused — spec Design 3.)
2. A lifecycle move whose ticket is outside a **non-empty** `expected` window is
   refused with the drift message and a record is written.
3. The `--part` hold: a `sync` on a named-part binding whose sibling is open
   reports the hold, writes nothing, and moves nothing. (C2's criterion 9.)
4. A finished item whose local status maps to no tracker status is delivered with
   **no tracker request at all** — the early exit at `tcw/tracker/sync.py:497`.
5. A resolved ticket is refused by the guard inside the claim block
   (`:554-561`), distinct from `assess_move`'s own resolved check at `:221`.

**Proves:** `pytest tests/test_tracker_sync.py` green. Each test is then broken
against `main` — change the assertion's subject, confirm red, read why — and
restored. A test here that cannot be made to fail is not pinning anything and is
rewritten or dropped.

## Task 2 — Split `owed` into `takes_ticket` and the assignee read

**Modifies:** `tcw/tracker/sync.py`. **Adds:** tests in
`tests/test_tracker_sync.py`.

- Rename today's expression at `:328` to `takes_ticket`, unchanged in content:
  `starting or bound.catch_up or (record is not None and record["move"] == "start")`.
- Substitute it at `:497` and `:501`. This is a no-op: nothing reassigns `owed`
  between `:328` and `:497`, so the expression there is already exactly this.
- After `read_ticket` at `:505`, compute
  `owed = takes_ticket and ticket.assignee_id != ticket.me_id`.
- Remove the two now-unreachable disjuncts: `ticket.assignee_id == ticket.me_id`
  at `:526` and at `:545`.

**Proves:** task 1's five tests still green, plus a new test that `submit`,
`rework` and `complete` on a bound item with an **unassigned** ticket assign
nothing (spec criterion 17c).

**Mutation:** restore `owed = assignee != me` alone and confirm the new test goes
red — that collapse is the defect the spec's Design 2 records.

## Task 3 — The forward-only rule, as a window test reporting `HELD`

**Modifies:** `tcw/tracker/sync.py`. **Adds:** tests in
`tests/test_tracker_sync.py`.

A lifecycle move (`not syncing`) whose ticket is above the target **and outside
its `expected` window** returns `HELD` and delivers nothing. `assess_move`
already refuses everything outside a non-empty window (`:232-238`), so the only
new case is the empty one.

**Proves:** spec criteria 18b and 18d — a `start` on a backlog item whose ticket
is unassigned and in the review status assigns the ticket, leaves its status
alone, exits 0 and writes **no** sync record; and task 1's `rework` test still
passes. Plus 18c: `tcw work tracker sync` on the same item still reconciles in
both directions.

**Mutation:** make it return `CONFLICTING` instead of `HELD` and confirm the
"no sync record" assertion goes red — `:385-393` writes a record for
`CONFLICTING` only, and that is the whole difference.

## Task 4 — `assert_ownership` replaces `intake.claim` inside `deliver`

The riskiest change, placed after its guards are pinned and its window rule
exists.

**Modifies:** `tcw/tracker/sync.py`.

- Replace the `claim(client, ticket)` call at `:590` with `assert_ownership`.
- Delete the "claimed {key}, but it is in '{status}', not '{active}'" refusal at
  `:613-621` — with the transition applied through `assess_move` instead, a
  ticket at an unmapped status is what `transitions.start` is for.
- Delete `if starting: return finish(CURRENT)` at `:621`; a start's ticket still
  has to be delivered.
- `since` becomes the ticket's status at claim time. `expected` is **not**
  touched.
- Remove `claim_refusal`'s lifecycle call sites (`sync.py:575`, `:607`) and
  delete `_strict_claim` (`cli.py:379`) with its call at `cli.py:1146`.
  `_tracker_import`'s call at `cli.py:2347` stays: `import` still claims through
  `intake.claim`, which is knowingly the one place Goal 1 is not yet true.
- Set `claimed_message` on the path that skips the claim because the ticket is
  already yours, or the "already held by you" line today's row-`1e` claim prints
  on every such `start` silently disappears. It is set only at `:611` today.

**Proves:** spec criteria 1 and 2 — `tcw work start` on a backlog item whose
ticket is in the review status exits 0, leaves the ticket in that status, and
assigns it to the running account. Task 1's five tests still green.

**Mutation:** re-introduce the landing refusal and confirm criterion 1's test
goes red.

## Task 5 — The retry field on `OwnershipOutcome`

**Modifies:** `tcw/tracker/ownership.py`, `tcw/tracker/sync.py`. **Adds:** tests
in `tests/test_tracker_ownership.py`.

Add a field saying whether a failure is worth retrying. Set it true on the
transient paths (`:128-130` assign failure, `:135-138` read-back failure) and
false on the permanent ones (`:88-93` resolved, `:106-124` another holder and the
workflow refusal). `deliver` uses it where it used `outcome.row in ("3-read",
"3f")`.

**Proves:** spec criterion 17d — a claim that fails because the tracker could not
be reached records `state: pending`, not `state: conflicting`.

**Mutation:** hardcode the field false and confirm the test goes red. `detail` is
**not** a usable proxy — it is set on the permanent workflow refusal as well —
and a test asserting through `detail` would pass while proving nothing.

## Task 6 — Resolution overrides ownership

**Modifies:** `tcw/tracker/sync.py`, `tcw/tracker/progress.py`,
`tests/test_tracker_sync.py`.

- Rename `MOVES_ALLOWING_UNASSIGNED` to `MOVES_NEEDING_NO_CLAIM` and put both
  `complete` and `discard` in it. Rewrite its comment: the prohibition it states
  today is the rule this task reverses, and the replacement says why.
- **Skip the assignee check entirely** for those moves in `assess_move`
  (`:224-233`), not merely consult the set — the set is read only when the
  assignee is empty, so widening it alone does nothing for a ticket held by
  another account.
- Widen `:533`'s `move == "discard"` to test the set, or `complete` on an
  unassigned ticket still reaches `assert_ownership`.
- **Rewrite** `tests/test_tracker_sync.py:436`,
  `test_a_discard_still_refuses_a_ticket_someone_else_holds`. It is not wrong
  today; it pins the rule being reversed. `outcome.md` names it with the reason.

**Proves:** spec criteria 8 and 8b. `tcw/tracker/progress.py:125` is the second
reader — `complete` now posts a progress comment where it skipped one; that gets
its own test rather than being discovered later.

**Mutation:** put the assignee check back for `complete` and confirm criterion 8
goes red.

## Task 7 — The claim gate on `submit` and `rework`

**Modifies:** `tcw/work/cli.py`. **Adds:** `tests/test_tracker_gate.py`.

For a **bound** item, `submit` and `rework` refuse before the local move unless
the ticket is assigned to the running account. Held by another names them;
unassigned names `tcw work tracker claim`. The refusal happens only on a positive
answer — an unreachable tracker does not refuse.

Remove `complete`'s strict gate at `cli.py:3107`. A discard is already ungated
(`:3105`'s `if shipping`), so nothing changes there.

**Proves:** spec criteria 6, 6b, 6c, 8, 10, 11. A new file because
`test_tracker_cli.py` is built on a request recorder and this needs the stateful
fake — the same reason C1's tests went to `test_tracker_hold.py`.

**Mutation:** make the gate refuse on an unreachable tracker and confirm
criterion 10 goes red.

## Task 8 — Retire `link --sync-status` and answer the unowned active item

**Modifies:** `tcw/work/cli.py`, `tcw/store/base.py`, `tcw/tracker/intake.py`,
`tcw/tracker/sync.py`. **Adds:** tests in `tests/test_tracker_link.py`,
`tests/test_work_start.py`.

- `link --sync-status` exits non-zero naming `link`, then `claim`, then `sync`,
  and leaves no such flag in any help text.
- Stop writing `catch-up: true`, but **keep reading it**. The field stays on
  `Bound` (`base.py:419`) and in `_BINDING_KEYS` (`intake.py:189`), on the
  requester's decision, because `walk()` — the multi-rung catch-up — is reachable
  only through `bound.catch_up` (`sync.py:634`, `:660`). Dropping the reader
  would make `walk()` dead code and silently remove the ability to bring a ticket
  up more than one rung, since `assess_move` only ever finds a single transition
  to the target. The writer goes; the walk stays reachable for every binding that
  already carries the key, and ages out with them.
- A test asserts `walk()` is still reached for a binding carrying `catch-up:
  true`, so the retirement cannot quietly take it.
- Delete the now-unreachable `check_only` refusal at `sync.py:543-544`.
- Rewrite `unsynced_hint` (`sync.py:803-806`) to advise `claim` then `sync`.
- `AlreadyClaimed` (`base.py:2611-2613`) names the remedy command; criterion 4
  requires a message that does, and today's names none.
- `FsWorkStore.start` takes the claim instead of raising `AlreadyClaimed` when
  the item is active with an empty `owner`. Active **and** held by somebody else
  is still refused, naming `tcw work tracker claim --take-over`.
- `start --take-over` is **not** touched. It is the only recovery for an
  interrupted claim; the spec's Design 7 says why.

**Proves:** spec criteria 3, 4, 5, 12, 13, 13b.

**Mutation:** make `FsWorkStore.start` raise for an empty owner again and confirm
criterion 3 goes red.

## Documentation Sync

One pass over the finished diff, after task 8, before `outcome.md`.

| Entry | Trigger | Fires | Why |
| --- | --- | --- | --- |
| `README.md` | Public-API | **yes** | `link --sync-status` is gone and `submit`/`rework` gain a refusal. |
| `docs/guide/jira.md` | Tracker-Change | **yes** | Every `work.tracker` behaviour here changes: the gate, resolution overriding ownership, `transitions.start` becoming optional. Strict mode's new required key is written by `2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode`; this item adds only that a strict `start` now takes its ticket through that key. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | Placed **after** the entry `2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode` writes, which leads with strict mode's new required key. This item's entry says that a strict `start` now takes its ticket through `exclusive-claim-transition` and why, then the gate, then the retirement; it does not repeat that the key is required, what `tcw validate` does, or what to set. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Added / Changed / Removed. |
| `skills/work/SKILL.md` and `skills/work/references/` | Skill-Driven-Component | **yes** | The lifecycle's guardrails change; `commands.md`'s rows for the five moves and for `link`. |
| `skills/configure/references/tracker.md` | Configuration-Key-Change | **yes** | That a strict `start` takes its ticket through `exclusive-claim-transition`. The requirement itself is already written by `2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode`, and `transitions.start` becoming optional by `2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`. |

All six fire. That is expected for an item that changes the lifecycle's
behaviour, its configuration surface and its CLI at once.

## Verification

Things the suite cannot answer, to be checked by hand and recorded in
`outcome.md`:

- **A real Jira project refusing an unassign or a transition.** The fake can be
  made to answer anything; only a live project confirms a workflow that forbids
  what TCW now attempts on somebody else's ticket (task 6).
- **That the six documentation entries say the same thing as the code**, read
  together rather than file by file.
- **That no lifecycle move applies a workflow transition as part of taking a
  ticket** (spec criterion 14) — asserted against recorded requests, not against
  resulting status, which is what C1's tests had to do for the same reason.

## Notes

**Every acceptance criterion traces to a task.** 1, 2 → task 4. 3, 4, 5, 12, 13,
13b → task 8. 6, 6b, 6c, 10, 11 → task 7. 8, 8b → task 6. 9 → task 6 (its
delivery) and task 7 (its gate). 14 → Verification. 17,
17b → tasks 2 and 3. 17c → task 2. 17d → task 5. 18, 18b, 18c, 18d → tasks 1 and 3.

**Criteria 15 and 16 are no longer this item's.** They went to
`2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode`,
which blocks this item, and
`2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`,
which this item blocks. What stays here is removing `claim_refusal`'s lifecycle
call sites and deleting `_strict_claim`, both of which belong to task 4's change
rather than to a configuration key.

**Three tasks carry mechanism questions the spec deliberately left open** —
3, 5 and 6. Each is proved by a test rather than by argument. A task that cannot
be made to pass is evidence the design is wrong and goes back to `spec` rather
than being worked around; the spec says so too.

**Task 1 is not optional and not busywork.** Three of the six spec review rounds
found a guard being changed without its other callers traced. Those five
characterisation tests are the cheapest available defence against the same
mistake landing in code.

## Added 2026-09-21 — the pre-backlog step must survive Tasks 4 and 8

`2026-09-21-let-tracker-sync-bring-a-ticket-forward-from-a-pre-backlog-status-such-as-triage`
lands before this item and is recorded as a blocker. It adds `work.tracker.pre-backlog`
and a separate status-movement function that moves a ticket out of a configured
pre-backlog status (for example `Triage` via `Accept`) onto `statuses.backlog`.
For now `intake.claim` calls it. Read that item's `spec.md` before revising this plan.

- **Task 4.** When `deliver` stops calling `intake.claim` and `_strict_claim` is
  deleted (so strict `start` goes through `deliver`), `deliver` must call the
  pre-backlog step itself, **on the moves that take the ticket (a start, or a pending catch-up), before `assess_move`, whether or not `owed`**. It must not run on `submit`, `rework` or `complete`, which also reach `assess_move`: the Triage item's criterion 15(a) tests catch that.
  Under this item's new ownership test, the reporter's already-assigned Triage ticket
  is not owed, yet still needs moving. `tcw work tracker import` keeps its
  `intake.claim` call and so keeps the step. The hint sentence naming
  `work.tracker.pre-backlog` must survive the deletion of the refusal it currently
  lives in, and so must the "moved out of Triage" message (the new `ClaimOutcome`
  field).
- **Task 8.** Retiring `--sync-status` moves that item's regression tests for its
  `link --sync-status` criteria onto the replacement link → claim → sync flow. They
  are not dropped.

## Corrected at implement, 2026-09-22

The code disproved parts of this plan. What was built instead, and why, is in
`outcome.md`; in short:

- **Task 2 could not stay green alone.** Making `owed` depend on the ticket's
  assignee skips `intake.claim` for a ticket already yours, and three things lived
  inside that claim: the pre-backlog step, the catch-up walk, and the hint naming
  `work.tracker.pre-backlog`. All three moved out of the claim in Task 2, not Task 4.
- **A recorded `start` needed its own window.** With the claim no longer moving the
  ticket onto `statuses.active`, the `(active,)` window a start record used to get
  refused every retry of a failed start. It now gets the live start's empty window,
  and when the item has moved past `active` that start is delivered first, then the
  move after it — what the claim transition used to do.
- **Task 4: `_strict_claim` was kept, not deleted.** Deleting it would have moved a
  strict item locally before its ticket was taken, which the spec (Design 1) does not
  ask for and an existing test forbids. It now asserts through
  `exclusive-claim-transition` with `assert_ownership`.
- **Task 7: complete's strict gate was narrowed, not removed.** It keeps asking where
  the ticket is (a reviewer who sent the ticket back still stops a completion) and
  stops asking who holds it.
- **Task 8: the `check_only` refusal is still reachable** through a catch-up binding
  already on disk, since the key is still read. It was kept, with a test.
- **Task 8 missed a writer.** `tracker create` wrote `catch-up: true` through
  `link`'s code; it now records the item's start as undelivered instead.
