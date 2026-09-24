# Outcome — give a recordless sync a move, and let strict mode work without `transitions.start`

All four findings are fixed, in six commits: four code tasks, one documentation
pass, and the task 1 fix, which was committed separately because it came first. The
plan's order held. Three things in the plan were wrong, all found while testing and
all recorded below.

The lifecycle was driven by hand from the first code edit onwards, as this repo's
CLAUDE.md asks while `tcw/` is being changed: `tcw work start` ran before any edit,
and this file and the item's folder were then maintained directly.

## What shipped, task by task

| # | Task | Commit |
| --- | --- | --- |
| 1 | Findings 1 and 2: `deliver` assesses a recordless `sync` against the item's status and records nothing; D6 punctuation | `9c4091f3` |
| 2 | Finding 3: strict mode requires `transitions.start`; the test at `:489` deleted with its replacement; `probes/` removed | `59f8c4c1` |
| 3 | Measurement against the pre-epic tree (no commit) | — |
| 4 | Finding 4 (a) and (b): `claim_refusal` asks about `exclusive-claim-transition` and runs on every strict claim path | `f78b4c31` |
| 5 | Sweep: `tracker show` / `inbox show` answer `workflow:` about `exclusive-claim-transition` | `90da4f18` |
| 6 | Finding 4 (c): a released item's ticket gets a refusal naming two ways forward | `89dcef35` |
| 7 | Deleted-test audit (no commit; results below) | — |
| 8 | Documentation | `ca7e9aae` |
| 9 | Full suite, `tcw validate`, criteria sweep | below |

### Task 1

`assessed = move or MOVE_ONTO.get(local)` sits beside the unchanged `move = …` line,
and only `resolving` and `assess_move(move=…)` use it. In `finish`, a pending or
conflicting run whose owed move is `None` returns without writing anything, and
without dropping an existing record. The two reconciliation tests
(`test_tracker_sync.py` `test_sync_brings_a_ticket_someone_moved_on_back_to_its_item`,
`test_sync_still_brings_back_a_ticket_a_start_left_alone`) passed unchanged.

### Task 2

`STRICT_NEEDS_START_TRANSITION` is appended after `_parse_tracker_transitions`, and
only when `start` is absent from the `transitions` mapping. The attribution test
confirmed the spec's reasoning: a parent `transitions` block without `start` is
reported against the child that turned strict on. All nine must-not-break tests for
optional `transitions.start` passed unchanged.

### Task 3 — the five-row measurement

The same probe body was run on both trees. Each ran from its own checkout root,
which made `tcw.__file__` resolve to that checkout (printed on every row to confirm
it). The pre-epic copy set no `exclusive-claim-transition`, because that tree
rejects the key as unknown, exactly as the plan said. Both columns match the plan:

| row | ticket state | pre-epic `bfb2ff33` | main before task 4 (`59f8c4c1`) | after task 4 (`f78b4c31`) |
| --- | --- | --- | --- | --- |
| 1 | GLOBAL, unassigned, To Do | exit 1, "still offers 'Start Progress' from 'In Progress'"; item backlog; applied `['21']`; ticket left claimed | exit 0, started | exit 1, refused; item backlog; applied `['21']`; ticket left claimed |
| 2 | GLOBAL, caller's, In Progress | exit 1, same refusal; item backlog; applied `['21']` | exit 0, started, nothing applied | exit 1, refused; item backlog; **nothing applied** |
| 3 | GLOBAL, caller's, To Do | exit 1, same refusal | exit 0, started; `['21']` applied by `deliver` | exit 0 — the documented unprovable path |
| 4 | SYNC, caller's, In Progress | exit 0, nothing applied | exit 0, nothing applied | exit 0, nothing applied |
| 5 | SYNC, caller's, To Do | exit 0, `['21']` | exit 0, `['21']` | exit 0, `['21']` |

One detail the plan's table did not show: in row 2, the pre-epic claim re-applied
`Start Progress` to a ticket already on In Progress. The fixed tree does not, as
criterion 25 requires.

### Task 4

The check stayed in `claim_refusal`, placed where the plan put it. `OwnershipOutcome`
gained `key`, set by a thin `assert_ownership` wrapper around the renamed
`_assert_ownership`, so every return path carries it without editing each one.
`claim_refusal` gained the keyword-only argument `off_active_refuses=True`. The two
lifecycle callers pass `False`.

### Task 5

`_print_ticket` now makes two assessments. `workflow:` is asked about
`exclusive_claim_transition or start_transition` (the fallback covers a project
without strict mode that names no exclusive transition), with `statuses.active` as
the landing status. Passing the landing status goes one step past the plan: without
it, a transition absent from In Progress reads as "not determined" rather than
"exclusive", and the criterion 33 test could not tell the two keys apart in that
direction. `note:` stays with the `claimable:` assessment, and
`test_show_says_the_start_transition_is_unset_rather_than_wrong` passed unchanged.

### Task 6

The plan's "widen `past`" became a separate helper, `_unclaimable_on_active`, because
the rung-0 case needs its own condition (the transition is *not* offered there) and
its own sentence. `_strict_claim` and `_tracker_claim` both call it, so the three
commands give identical advice, which the test asserts. The rung-above-zero test at
`:711` passed unchanged.

## Test result

Bare `pytest` from the repository root, the way CI runs it:

- **Baseline** on `03bc9e4b` (the start commit, before any edit): `4404 passed, 3 skipped`.
- **After** `ca7e9aae`: `4459 passed, 3 skipped in 3224.99s`, with no failures and
  no errors.
- **Reconciliation:** collecting the two changed test files gave 283 test cases
  before and 338 after, a net +55: one test deleted, and 56 test cases (after
  parametrisation) added or split out. 4404 + 55 = 4459. The skip count is
  unchanged at 3.
- `tcw validate`: `validate OK`.

### Criteria sweep

| Criteria | Where they are held |
| --- | --- |
| 1, 2, 4, 5, 6, 7, 9, 10 | `tests/test_tracker_sync.py`, section "a `sync` with nothing recorded" |
| 3, 8, 19 | `tests/test_tracker_strict.py`, section "a failed `sync` with nothing recorded…" |
| 11–14 | `tests/test_tracker_strict.py`, section "strict mode requires transitions.start" |
| 20 | `probes/` deleted in `59f8c4c1`; the file-by-file audit is in task 7 below |
| 21, 35 | the suite run above |
| 22–24, 26–28 | `tests/test_tracker_strict.py`, section "strict mode checks that its claim transition excludes…"; 22's pre-epic half is task 3's table |
| 25 | `test_a_strict_claim_of_a_ticket_you_already_hold_sends_nothing` |
| 29, 30 | `test_a_strict_claim_of_a_released_item_names_a_way_forward`, `test_following_that_advice_lets_the_claim_succeed` |
| 33 | `test_show_answers_each_line_about_its_own_key` |
| 15–18, 31, 32, 34, 36 | **[read]**: the documentation commit `ca7e9aae`, for a person to read at verify |

## Task 7 — the deleted-test audit

The list was built with `git diff 03bc9e4b -- tests/`. Every successor was checked
by mutation: break the code the property depends on, then confirm the named test
goes red for that reason.

| Removed or rewritten | Successor | Mutation that turned it red |
| --- | --- | --- |
| `test_strict_import_of_a_held_ticket_needs_no_start_transition` — held ticket imports, sends nothing | `test_a_strict_claim_of_a_ticket_you_already_hold_sends_nothing` | removing `assert_ownership`'s already-held early return |
| the same test — with `transitions.start` unset | **deliberately gone**: task 2 makes that node invalid. The half without strict mode is held by `test_tracker_import.py::test_import_of_a_ticket_already_held_needs_no_start_transition` | — |
| `…_on_the_claims_own_status_still_asserts_through_it[below-the-ladder]` | `test_a_strict_start_below_the_claims_status_still_asserts_through_it` (now on SYNC) | see note 1 |
| `…[on-the-claims-own-rung]` | the property is reversed, not moved: `test_a_strict_start_on_the_claims_own_status_is_refused_where_it_is_offered_again` | skipping `_strict_claim`'s `claim_refusal` call |
| `test_a_strict_start_reports_a_claim_the_delivery_had_to_make_again` | **unreachable now** (see "What the plan got wrong", item 2). Replaced by `test_a_ticket_let_go_between_a_strict_claim_and_its_delivery_is_not_retaken` | — |
| `…says_it_took_the_ticket…`, `…whose_commit_is_refused…` (moved from GLOBAL to SYNC, assertions unchanged) | themselves | making `_strict_claim` print "already held by you" |
| probe `nullmove` | `test_a_recordless_sync_that_cannot_reach_the_tracker_writes_no_record` | re-enabling the record write |
| probe `outage_blocks` | `test_a_failed_recordless_sync_does_not_block_the_next_strict_move` | re-enabling the record write |
| probe `strict_wedge` | `test_a_failed_recordless_sync_leaves_the_accurate_strict_refusal_in_place` | re-enabling the record write |
| probe `reopened` | `test_sync_of_a_reopened_ticket_on_a_completed_item` / `…_on_a_discarded_item` | `assessed = move` |
| probe `recovery` | `test_sync_of_a_reopened_ticket_on_a_completed_item[bobs]` | `assessed = move` |
| probe `reopen_exclusive` | `test_a_reopened_ticket_closes_again_under_an_exclusive_claim_transition` | `assessed = move` |
| probe `strict_import` | `test_strict_without_a_start_transition_is_refused`, `test_validate_refuses_a_strict_node_with_no_start_transition`; its second half is `test_a_node_that_is_not_strict_starts_and_finishes_with_no_transitions_block` | removing the parser check |

**Note 1.** Removing the claim transition from a strict start's claim did **not**
turn the below-the-status test red. The delivery that follows applies the same
transition, so `applied == ['21']` holds either way. The GLOBAL version it replaced
had the same blind spot, so this was not introduced here. The property is held by
`test_a_strict_start_takes_the_ticket_through_the_exclusive_claim_transition` and
`test_a_strict_start_refuses_a_second_claimant_the_workflow_excludes`, and both went
red under that mutation.

## What the plan or spec got wrong

1. **The trap test's scenario could not catch the trap.** Criterion 4 and the plan
   describe the ticket as held by another account. Against the wrong fix (writing
   `start` into the record), that version stays green: a claim never takes Bob's
   ticket without `--take-over`, so nothing observable changes. Only a *released*
   ticket shows the trap, because the wrong fix then assigns it to the caller. The
   test is parametrised over both, and the released case went red when that
   mutation was applied (the assignee became `acct-a`).
2. **"Exactly one existing test must change" was false: six did.** Five strict tests
   ran a strict `start` on `GLOBAL`, which excludes nobody, and expected success.
   They were written during the window the regression opened, so they encoded it,
   and neither the spec's nor the plan's sweep listed them. None of them was about
   exclusivity. Three moved to `SYNC` with their assertions unchanged, one was
   split so its on-the-active-status case asserts the refusal, and the helper
   became `claim_node` with a required `workflow` argument, as the rule against
   fixture defaults asks. `test_a_strict_start_reports_a_claim_the_delivery_had_to_make_again`
   could not be kept. On an exclusive workflow, a delivery cannot take back a
   ticket released onto `statuses.active`: that needs the transition offered from
   there, which is exactly the workflow strict mode now refuses. Its replacement
   holds what actually happens: the item moves, the delivery reports a conflict,
   and "held by you" is printed once.
3. **Criterion 30 cannot go red before its advice exists.** Assigning yourself the
   ticket already makes a retake succeed on the directed workflow. The test is a
   check on the advice, not a red-first test.
4. Smaller: the plan put criterion 33's test in `tests/test_tracker_cli.py`. It went
   into `tests/test_tracker_strict.py` beside the other exclusivity tests, because
   the fake tracker and `exclusivity_node` live there. The criterion 22 recipe
   corrections in the plan's task 3 were accurate.

## Documentation

These entries fired: `docs/guide/jira.md` (Tracker-Change; the four passages the
plan named, plus the `sync` section), `docs/release-notes/upcoming.md`,
`docs/changelogs/upcoming.md`, `skills/configure/references/tracker.md`, and both
capability entries (both still **Supported**; `tcw capabilities check` and
`drift` are clean). Two entries the plan judged would not fire did fire once checked
against the finished diff:

- **`README.md`.** Its strict-mode list described what a strict `start` checks. It
  now names the exclusivity check and the second required setting.
- **The `work` skill.** `SKILL.md` itself needed no change, but
  `skills/work/references/commands.md` had three statements this change made false.
  The strict table (`start`, `tracker import`, and a new `tracker claim` row) was
  one. The `show` passage said a started ticket on an exclusive workflow reports
  "not determined", which task 5 changed. The "No `transitions.start`" bullet was
  the third.

Checked and not changed: `docs/guide/work.md` names strict mode only as a link to
`jira.md`.

## Notes

- The one path still unprovable, as the plan predicted: a strict `start` of a ticket
  the caller already holds, sitting in the backlog status, on a workflow that
  excludes nobody. It is accepted (row 3). The changelog and the capability entry
  say so. Deciding it needs the workflow definition, which is the backlog item
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`.
- Unchanged, as the spec's non-goals require: `binding_refusal`'s unlink-and-discard
  advice, the sync-record reader, and `transitions.start` being optional without
  strict mode.
