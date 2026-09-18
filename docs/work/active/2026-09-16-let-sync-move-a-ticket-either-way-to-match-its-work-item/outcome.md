# Outcome: Let sync move a ticket either way to match its work item

## What shipped

Four commits, in order. The worktree is
`.worktrees/2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item`
on `work/2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item`.
Nothing was merged, submitted or pushed.

| Commit | What |
| ------ | ---- |
| `112eed51` | `initial-request.md` |
| `6461981a` | `spec.md` |
| `88dc8243` | `plan.md` |
| `42f28ce2` | the code: `sync` reconciles in either direction, and the `claim` key leaves the record |
| `8c6bec60` | documentation, capability descriptions |
| `5fd8da5e` | `capabilities.yaml` |
| `8c05871f` | a late fix the by-hand verification found, with its documentation |

### `42f28ce2` — the change itself

**One — `tcw work tracker sync` reconciles.** `deliver` lost its `check_only`
parameter and decides for itself:
`check_only = syncing and record is None and bound.part != "default"`. The
direction rule needed no new code: with `move=None` and `previous_status=None`,
`expected_statuses` already returns `()` and `assess_move` applies no status test
on an empty window, so removing the refusal at the end of `deliver` lets the
ticket be moved to the item's mapped status from wherever it sits, in whichever
direction that is. A lifecycle move's window is untouched. `tcw/work/cli.py`
stopped passing `check_only`, and `usable` went with it.

**Two — the backwards warning.** `Outcome` gained `note`, set by `finish` only
for `CURRENT` when the ticket's `lowest_rung` was above the item's own. It reads,
through the real CLI:

```
$ tcw work tracker sync 2026-09-17-bound-item
2026-09-17-bound-item: SYNC-1 was in 'In Review', past where 2026-09-17-bound-item is, and was put back to 'In Progress'.
2026-09-17-bound-item: current
```

**Three — the `--part` limit.** A binding whose part the user named is reported
on rather than reconciled when nothing is recorded for it. That is the answer to
the epic's risk 3, reached after reading
`docs/work/backlog/2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`
as the epic requires: a hold leaves no evidence outside the checkout it happened
in, so `sync` cannot tell a hold from drift, and the safe direction is to report.

**Four — `claim` left the sync record**, from `SYNC_FIELDS` and `_sync_record`
(`tcw/store/base.py`), the projection schema, `web/client/src/model/types.ts`,
`tcw work show`, `deliver`'s `finish`, `record_unsent`, and
`link --sync-status`. `owed` is now
`starting or bound.catch_up or (record is not None and record["move"] == "start")`.
`finish`'s `drop_record` and the held branch's `stale` each lost an `owed` term
that existed only to keep the key alive.

**Five — two fixes in `assess_move`**, both reachable for the first time from a
record-less `sync`: the resolved check moved above the assignment checks, and the
unassigned refusal names `tcw work tracker claim` instead of `tcw work start`.

### `8c05871f` — what the by-hand verification found

A claim `deliver` attempts and cannot make reported only what `intake.claim`
said. Running the plan's second by-hand check through the real CLI produced:

```
$ tcw work submit 2026-09-17-second
tcw work submit: ... SYNC-2 is in 'In Progress', unassigned, and does not offer
'Start Progress'. It offers: 'Ready for Review', 'Finish', "Won't Do", ...
```

That is the pre-existing message, and it names no way out. The way out is
`tcw work tracker claim`, which takes a ticket without applying any transition,
so the refusal now names it and the `sync` to run after it — but only when the
ticket is unassigned or already this account's, since sending somebody to claim a
ticket another account holds would produce a second refusal naming the same
person. Confirmed end to end against the fake tracker: `claim` → exit 0, ticket
assigned and unmoved; `sync` → exit 0, ticket at `In Review`, record gone.

## Test result

Full suite, from the worktree root against the private virtual environment,
redirected to a file and read from it:

```
3750 passed in 868.23s (0:14:28)
pytest exit 0
```

Also green: `pnpm test` — `Test Files 11 passed (11)`, `Tests 64 passed (64)`;
`npx tsc --noEmit` — clean; `tcw validate` — `validate OK`.

`npx prettier --check` reports `README.md`, `docs/guide/jira.md`, both
`upcoming.md` files and `skills/work/references/commands.md` as unformatted. It
reports the same five on the tree with this change stashed, so they were already
failing; reformatting them is
`2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout`.

## Mutations run, and what went red

Every new assertion was broken before it was trusted. Each mutation was applied
to the working tree, the named tests run, and the file restored.

| # | Mutation | What went red, and why |
| - | -------- | ---------------------- |
| 1 | `check_only` computed without the part term, so every record-less `sync` is check-only again | the four reconcile tests, on `conflicting — … no undelivered change is recorded, so it is not moved` |
| 2 | the part rule inverted to `bound.part == "default"` | `…named_part`, because the ticket moved and the run reported `current` |
| 3 | `backwards` never set | `…moved_a_ticket_backwards`, on output that was only `<slug>: current` |
| 4 | the resolved guard deleted from `assess_move` | `…never_reopens_a_resolved_ticket`, which reported the backwards note and moved a `Done` ticket to `In Progress` |
| 5 | the resolved guard restored to its old place, after the assignment check | the same test's second half, on `unassigned, so it was not moved from 'Done'` |
| 6 | `claim` written back into `finish` and `record_unsent` | `…writes_a_claim…` and `…late_link_records…`, on `Extra items in the left set: 'claim'` — **only after the test was fixed.** Its first version read the record through `_sync_record`, which filters the key out, so it passed under this mutation. `written_record` reads the file instead. |
| 7 | `claim` back in `SYNC_FIELDS` | `…still_names_a_claim…`, on the parsed record carrying the key |
| 8 | `claim` back in the projection's `required` | that test and `…json_document_validates…`, on schema validation |
| 9 | `owed` without the record-move term | `…claimed_before_the_next_move`, `…still_owes_a_recorded_start`, `…one_transition_only`, and `test_sync_rechecks_an_owed_claim_under_strict_mode` |
| 10 | `owed = True`, so every move claims | `…written_over_is_made_by_the_claim_verb`, on a claim made where none should be |
| 11 | the claim verb never named in a failed claim | `…names_the_verb_that_can`, on the missing command |
| 12 | named even for a ticket somebody else holds | the same test's first assertion |
| 13 | `_siblings` never reporting an open sibling as holding | `test_sync_reports_a_held_item_without_failing`, which reported `current` — that is, `sync` moved a ticket another part was holding |
| 14 | `_sync_record` keeping every key on disk instead of the five in `SYNC_FIELDS` | `…still_names_a_claim…`, on both `owed` and `done` |

## Acceptance criteria

| # | Covered by |
| - | ---------- |
| 1 | `test_sync_brings_a_ticket_someone_moved_on_back_to_its_item` |
| 2 | `test_sync_says_when_it_moved_a_ticket_backwards`, and by hand through the CLI |
| 3 | `test_sync_brings_a_ticket_someone_moved_back_forward_again` |
| 4 | `test_sync_moves_a_ticket_from_a_status_the_project_maps_to_nothing` |
| 5 | `test_sync_never_moves_a_ticket_somebody_else_holds` |
| 6 | `test_sync_never_reopens_a_resolved_ticket` |
| 7 | `test_sync_reports_a_held_item_without_failing` — extended during implementation: it reported the hold but never checked that the ticket stayed put, which is the thing this change could break. It now asserts the other item is named, `fake.writes() == []`, and the ticket is still at `In Progress`, both with a record and with none (the reconciling path) |
| 8 | `test_sync_does_not_reconcile_a_ticket_bound_as_a_named_part` |
| 9 | `test_no_command_writes_a_claim_into_the_record` (the failed `start` and `submit` legs), `test_record_unsent_writes_no_claim`, `test_the_link_that_asks_for_a_catch_up_writes_no_claim`. The last two were added in the second pass: the first two legs were the only ones genuinely covered before it |
| 10 | `test_a_record_on_disk_that_still_names_a_claim_is_read_and_ignored`, parametrized over `owed` and `done`, and by hand |
| 11 | that test's `show --json`, plus `test_the_json_document_validates_with_a_record_a_problem_and_none` |
| 12, 13 | **rewritten during implementation** — see below. Now `test_a_claim_a_second_failure_has_written_over_is_made_by_the_claim_verb` and `test_a_claim_deliver_cannot_make_names_the_verb_that_can` |
| 14 | `test_a_late_link_records_its_catch_up_without_a_claim`, plus the existing `sync_status` catch-up tests, unchanged |

## What the spec and the plan got wrong

**The spec's replacement for `owed` was wrong, and running it is what showed
that.** The spec designed `owed = starting or bound.catch_up`, deliberately
giving up the retry of a `start`'s failed claim and sending users to
`tcw work tracker claim` instead. Two things broke when it was built:

- After `tcw work tracker claim` takes the ticket, `sync` could not deliver,
  because the record's own window still refused a ticket below it. The refusal
  named a verb that did not unblock anything.
- Worse, a ticket sitting in a status the project maps to nothing — which is
  where a ticket whose claim never landed usually sits — cannot be walked onto
  the ladder at all, because the claim transition was the only thing that ever
  put it there. That is the coupling the epic's third and fourth children exist
  to take apart, and it is not repaired inside this one.

The fix is smaller than the spec's design, not larger: the record's own `move`
field already says a `start`'s delivery never finished, so
`record["move"] == "start"` carries the fact with no new state and no lost
behaviour. **The spec's "What this deliberately gives up" section is therefore
much narrower than written**, and so is its risk 3. What is actually given up is
one corner: when a second failure records its own move over the `start`, no later
command claims the ticket, and `tcw work tracker claim` does. The guide, the
release notes and the capability text describe the narrow version.

**The epic's premise that both pinned tests had to change was half right.**
`tests/test_tracker_sync.py:1710` behaves identically — it changed only its name
and the one assertion about the removed key. `:983` did change, and it is exactly
the corner above.

**The spec's note about `docs/capabilities/work/view-the-board/description.md:19`
was wrong.** That sentence's "still owed" is about a progress comment, not a
claim, and the board really does print `comment pending`. Nothing was changed
there, and `view-the-board` is not among this item's capability deltas.

**Two `assess_move` changes the plan did not predict.** The plan named the
unassigned message. It did not foresee that the resolved check had to move above
the assignment check: with `check_only` gone, a record-less `sync` reaches
`assess_move` for a resolved ticket for the first time, and the old order told
users to take a closed ticket. Mutation 5 is that fix, earned.

**Criterion 14 was not covered by an existing test, as the plan assumed.** Every
existing `--sync-status` test asserted the claim key, so all of them had to be
rewritten anyway; `test_a_late_link_records_its_catch_up_without_a_claim` is the
one that pins what the plan meant.

**The plan's `pnpm vitest run` is `pnpm test`,** and `node_modules` had to be
installed in the worktree first (`pnpm install --frozen-lockfile`).

**The plan predicted five code tasks and one commit; it took two code commits.**
The second is `8c05871f`, from a defect the plan's own by-hand verification
found — which is the verification section earning its place rather than a plan
error.

## What was deliberately left undone

- **The epic's acceptance criterion 7** (`link` then `sync` leaves the ticket at
  `statuses.active`, with no `--sync-status` flag) is the fourth child's:
  retiring the flag is listed under C4 in the epic. `--sync-status` is left
  working and pinned.
- **A ticket ahead of its item while an undelivered move is recorded** is still
  refused by that record's own window. Widening it there would break the catch-up
  walk's resume path, which reads the same window. Recorded as the spec's risk 5;
  the fourth child, which composes the moves out of these primitives, is where it
  returns.
- **`--all` still visits only items with a record or an owed comment.** Sweeping
  every bound item would read one ticket per item on every sweep. Named as a
  non-goal in the spec and as a limit in the guide and the capability text.
- **Durable evidence of a `--part` hold** stays
  `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`.
  This item works around the missing evidence; it does not supply it.
- **`intake.claim` was not touched.** The confusing "does not offer 'Start
  Progress'" message it produces is now followed by a way out, but the message
  itself, and the coupling that produces it, belong to the third and fourth
  children.
- **The five documents prettier already rejected were not reformatted**, for the
  reason under "Test result".
- **Nothing was flipped to `Supported`.** `capabilities.yaml` declares
  `work/synchronize-external-tracker-work` and `work/require-tracker-backed-work`
  as changed; the ledger statuses are closeout's.

## A second pass, after the verify assessment

Four findings, all real. Commits `RANGE`.

**1 — the sibling hold drops a record that still owes the `start`'s claim, and I
left the guard out.** The assessment was right that this is a second corner
`outcome.md` did not admit, and right that my spec's justification for removing
the `(record is None or record["claim"] != "owed")` term covered only the
late-link half of `owed`. The assessment preferred restoring it as
`record["move"] != "start"`. **I built that and rejected it**, because it makes
`tests/test_tracker_strict.py:760` fail: with the record kept,
`binding_refusal` refuses every local move on a held item, so someone whose
`start` did not reach the tracker cannot submit finished work until an unrelated
part closes. That test exists precisely to prevent that lock. The trade is a hard
block on work in progress against a claim one command recovers, so the record
still goes. What changed instead: the corner is now stated where it happens (a
fifteen-line comment on the held branch saying what is lost, that keeping it was
tried, and why claim state riding on this record is what `claim: owed | done`
was), and it is pinned by two tests rather than left implicit.

**2 — the comment above it.** Rewritten, along with the "Held even when this
item's claim is owed" line two lines further up, which named the same removed
rule.

**3 — `rework` printed a note calling the user's own move a pull-back.** Fixed at
the source: `backwards` is set only when `syncing`, so no caller of `deliver` can
print one for a lifecycle move. `rework` takes an item from review to active, so
its ticket is legitimately one rung up every single time. The two prints that can
no longer fire — `_deliver_after`'s and `_tracker_link`'s — are deleted.

**4 — two of criterion 9's four legs were unpinned**, and the assessment
identified the cause exactly: both writes are masked by a later read. Now pinned
by a test each, both mutation-checked to go red with the key put back.

Also done: the three dead things. `not check_only` in the walk-resume and
`or record is None` in the held guard were tautologies (`check_only` implies
`record is None`) and are deleted rather than tested.

### Tests added or changed in this pass

| Test | What it pins |
| ---- | ------------ |
| `test_a_hold_drops_a_record_that_still_owes_the_start_s_claim` | the corner itself, end to end: the hold drops the record, the next move after the other part closes names `tcw work tracker claim`, and that verb plus a `sync` is the whole recovery |
| `test_a_hold_drops_a_record_so_strict_mode_cannot_lock_the_item` | why it is dropped, in this repository's own fixture rather than only in `tests/test_tracker_strict.py` |
| `test_rework_does_not_call_the_user_s_own_move_a_pull_back` | both the command output and, through `deliver_now`, that `deliver` sets no note for a lifecycle move while still setting one for a `sync` of the same ticket |
| `test_record_unsent_writes_no_claim` | the record `record_unsent` writes, reached by breaking the tracker block so no client exists |
| `test_the_link_that_asks_for_a_catch_up_writes_no_claim` | the record `_tracker_link` writes, read from a hook on the delivery's first ticket read — the one moment between that write and `finish` replacing it |
| `test_sync_reports_a_held_item_without_failing` (existing) | extended earlier in this pass: the ticket does not move, in either direction, with a record and without one |
| `test_a_record_on_disk_that_still_names_a_claim_is_read_and_ignored` (existing) | extended earlier: parametrized over `owed` and `done` |

### Mutations run in this pass

| # | Mutation | What went red |
| - | -------- | ------------- |
| 13 | `_siblings` never reporting an open sibling as holding | the hold test, on `current` — `sync` moved a ticket another part was holding |
| 14 | `_sync_record` keeping every key on disk | the stale-key test, on both `owed` and `done` |
| 15 | `stale` with the `record["move"] != "start"` guard restored | `…drops_a_record_that_still_owes…`, which is how the guard's cost was measured |
| 16 | `stale` never true | `…drops_a_record_so_strict_mode_cannot_lock…` and `test_a_held_item_drops_its_record…` |
| 17 | the `syncing` term dropped from the note | `…does_not_call_the_user_s_own_move…`, on a note set for a `rework`. **The first version of that test did not catch this** — it observed only the command's output, which the deleted print already silenced. The `deliver_now` assertions are what earn it. |
| 18 | `"claim": "done"` back in `record_unsent` | `test_record_unsent_writes_no_claim` |
| 19 | `"claim": "owed"` back in `_tracker_link` | `test_the_link_that_asks_for_a_catch_up_writes_no_claim` |

## Notes

- **Every lifecycle transition from the first edit to `tcw/` onward was made by
  editing `docs/work/` directly**, as this repository's guide requires while
  TCW's own code is in flux. `tcw work stage gate` and `tcw work stage prompt`
  were still used throughout — they only print. The `request`, `spec` and `plan`
  gates all refused on status, because the item was started before its artifacts
  were written; their prompts were read and followed regardless.
- **The shared editable install was never re-pointed.** All work ran against a
  private virtual environment at `/tmp/c2-venv`, so the agent working the third
  child in the other worktree was not disturbed.
- **This item's only change to `tcw/store/base.py` is `SYNC_FIELDS` and
  `_sync_record`** — `1 insertion, 3 deletions`, around 700 lines from the
  tracker transition keys the third child edits. Confirmed with
  `git diff main --stat -- tcw/store/base.py` before each code commit.
- `tests/fixtures/prompt_fallback/capture.py` was not run.
