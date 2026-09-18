# Plan: compose the lifecycle moves from claim and sync

Ten code tasks, then one documentation block. The suite is green at every task
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
  `:613-620` — with the transition applied through `assess_move` instead, a
  ticket at an unmapped status is what `transitions.start` is for.
- Delete `if starting: return finish(CURRENT)` at `:621`; a start's ticket still
  has to be delivered.
- `since` becomes the ticket's status at claim time. `expected` is **not**
  touched.

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

## Task 8 — Strict mode requires `exclusive-claim-transition`

**Modifies:** `tcw/store/base.py`, `tcw/tracker/sync.py`, `tcw/work/cli.py`.
**Adds:** tests in `tests/test_tracker_config.py`,
`tests/test_tracker_validate.py`.

- `tcw validate` refuses `work.tracker.strict: true` without
  `exclusive-claim-transition`, naming the key — the migration shape C3 used for
  `transitions.claim`.
- Remove `claim_refusal`'s lifecycle call sites (`sync.py:575`, `:607`,
  `cli.py:412`). `_tracker_import`'s at `cli.py:2347` stays: `import` still
  claims through `intake.claim`.
- Delete `_strict_claim` (`cli.py:379`).

**Proves:** spec criterion 15.

**Mutation:** remove the validate check and confirm the test goes red.

## Task 9 — `transitions.start` becomes optional

**Modifies:** `tcw/store/base.py`, `tcw/tracker/sync.py`. **Adds:** tests in
`tests/test_tracker_config.py`.

Drop the required check at `base.py:1267-1269`. Delete the hardcoded branch at
`sync.py:247-252` that withholds the "or remove it" advice for `transitions.start`
— its stated reason (a start has no status-derived fallback) is gone once task 4
routes the start through `assess_move` — and update the test C3 added for it.

**Proves:** spec criterion 16 — a configuration with no `transitions.start`
validates.

**Mutation:** restore the required check and confirm the test goes red.

## Task 10 — Retire `link --sync-status` and answer the unowned active item

**Modifies:** `tcw/work/cli.py`, `tcw/store/base.py`, `tcw/tracker/intake.py`,
`tcw/tracker/sync.py`. **Adds:** tests in `tests/test_tracker_link.py`,
`tests/test_work_start.py`.

- `link --sync-status` exits non-zero naming `link`, then `claim`, then `sync`,
  and leaves no such flag in any help text.
- Stop writing `catch-up: true`; drop the field from `Bound` (`base.py:419`) and
  decide `_BINDING_KEYS` (`intake.py:189`) — dropping it is the tidier answer and
  loses nothing, since an old binding still parses either way.
- Delete the now-unreachable `check_only` refusal at `sync.py:543-544`.
- Rewrite `unsynced_hint` (`sync.py:803-806`) to advise `claim` then `sync`.
- `FsWorkStore.start` takes the claim instead of raising `AlreadyClaimed` when
  the item is active with an empty `owner`. Active **and** held by somebody else
  is still refused, naming `tcw work tracker claim --take-over`.
- `start --take-over` is **not** touched. It is the only recovery for an
  interrupted claim; the spec's Design 7 says why.

**Proves:** spec criteria 3, 4, 5, 12, 13, 13b.

**Mutation:** make `FsWorkStore.start` raise for an empty owner again and confirm
criterion 3 goes red.

## Documentation Sync

One pass over the finished diff, after task 10, before `outcome.md`.

| Entry | Trigger | Fires | Why |
| --- | --- | --- | --- |
| `README.md` | Public-API | **yes** | `link --sync-status` is gone and `submit`/`rework` gain a refusal. |
| `docs/guide/jira.md` | Tracker-Change | **yes** | Every `work.tracker` behaviour here changes: the gate, resolution overriding ownership, strict mode's new required key, `transitions.start` becoming optional. |
| `docs/release-notes/upcoming.md` | Public-API | **yes** | Must **lead** with strict mode's new required key — it is the breaking change — then the gate, then the retirement. |
| `docs/changelogs/upcoming.md` | Any-Code-Change | **yes** | Added / Changed / Removed. |
| `skills/work/SKILL.md` and `skills/work/references/` | Skill-Driven-Component | **yes** | The lifecycle's guardrails change; `commands.md`'s rows for the five moves and for `link`. |
| `skills/configure/references/tracker.md` | Configuration-Key-Change | **yes** | `transitions.start` optional; `strict` requiring `exclusive-claim-transition`. |

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
13b → task 10. 6, 6b, 6c, 10, 11 → task 7. 8, 8b → task 6. 9 → task 6 (its
delivery) and task 7 (its gate). 14 → Verification. 15 → task 8. 16 → task 9. 17,
17b → tasks 2 and 3. 17c → task 2. 17d → task 5. 18, 18b, 18c, 18d → tasks 1 and 3.

**Three tasks carry mechanism questions the spec deliberately left open** —
3, 5 and 6. Each is proved by a test rather than by argument. A task that cannot
be made to pass is evidence the design is wrong and goes back to `spec` rather
than being worked around; the spec says so too.

**Task 1 is not optional and not busywork.** Three of the six spec review rounds
found a guard being changed without its other callers traced. Those five
characterisation tests are the cheapest available defence against the same
mistake landing in code.
