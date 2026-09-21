# Outcome: Let tracker sync bring a ticket forward from a pre-backlog status such as Triage

Worked in `.worktrees/<slug>` on `work/<slug>`, with a private virtual environment
pinned to the worktree (the shared editable install was never touched). Every test
ran as bare `pytest`, as CI runs it. No real Jira was contacted; everything ran
against `tests/tracker_fake.py`.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `25e5047c` | `work.tracker.pre-backlog` parsed in `tcw/store/base.py`: `TrackerConfig.pre_backlog`, `_parse_tracker_pre_backlog`, `pre_backlog_entry`. Fails closed with the rest of the tracker block. |
| 2 | `c48baef0` | `intake.leave_pre_backlog`, called first by `intake.claim` (old body renamed `_claim_from`, now given the fresh read). `ClaimOutcome.left_status`, the same attribute on a `TrackerError` raised after the step, `moved_out`, `pre_backlog_hint` on row `1f`, and `deliver` treating rows `0-read`/`0f` as pending. |
| 3 | `d40222e9` | `deliver` reports the move on success, refusal and a raised error; the "claimed …, but it is in …" refusal names the key only when the claim applied no transition. |
| 4 | `4c4ee12b` | `_strict_claim`, `_tracker_import` (so `inbox accept`) and `_print_ticket` in `tcw/work/cli.py`: the moved-out line, "run `start` again" after a strict refusal, the row-`1e` warning, and the `show` note. |
| 5 | `877fa255` | `capabilities.yaml` and the three capability descriptions. `tcw capabilities check` → `capabilities OK`. |
| 6 | `d434cd9a` | Documentation: `docs/guide/jira.md` ("Tickets waiting in triage", key table, example), `docs/guide/work.md`, `skills/configure/references/tracker.md`, `skills/work/references/commands.md`, `skills/commands-process-inbox/SKILL.md`, `README.md`, both `upcoming.md` files. `skills/work/SKILL.md` was re-read: it names no tracker claim behaviour, so it is unchanged. `tcw validate` → `validate OK`. |

All new tests are in `tests/test_tracker_pre_backlog.py`: 43 test functions, 61 cases once parametrized.

## Test result

Full suite, with no git identity, as instructed:

```
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null PATH=$V/bin:$PATH pytest -q -p no:cacheprovider
3949 passed in 1188.30s (0:19:48)
```

## Criteria

| Criterion | Test(s) |
| --- | --- |
| 1 | `test_a_bad_pre_backlog_fails_closed_naming_the_key` (7 cases), `test_a_valid_pre_backlog_parses`, `test_validate_names_pre_backlog`, `test_a_child_inherits_pre_backlog_entries` |
| 2, 3 | `test_link_sync_status_accepts_then_claims[unassigned / already-yours]` |
| 4 | `test_sync_finishes_an_owed_catch_up_from_triage` |
| 5 | `test_start_accepts_then_claims`, `test_strict_start_accepts_then_claims` |
| 6 | `test_import_and_inbox_accept_accept_then_claim` |
| 7 | `test_a_triage_ticket_already_yours_is_accepted_then_claimed`, `test_import_of_a_triage_ticket_already_yours`, `test_without_the_setting_import_of_a_triage_ticket_already_yours_warns` |
| 8 | `test_another_holder_or_a_resolved_ticket_sends_nothing` |
| 9 | `test_someone_acting_between_the_hops_is_refused_on_the_fresh_read[taken / resolved]` |
| 10 | `test_a_misconfigured_step_sends_nothing` |
| 11 | `test_the_step_is_chosen_by_status_not_by_transition_name`, `test_the_configured_status_is_matched_as_statuses_are` |
| 12 | `test_an_unanswered_accept_that_did_not_land_is_pending`, `…_that_landed_carries_on`, `test_a_refused_accept_is_conflicting`, `test_a_failed_read_back_after_accept_is_pending_and_says_it_was_sent`, `test_an_accept_landing_somewhere_else_is_conflicting`, `test_a_step_that_may_not_have_applied_is_recorded_pending` |
| 13 | `test_a_claim_that_raises_after_the_step_carries_left_status`, `test_a_claim_raising_after_the_step_still_reports_the_move`, `test_import_that_raises_after_the_step_reports_the_move` |
| 14 | `test_a_claim_refused_after_the_step_is_resumed_by_sync`, `test_strict_start_refused_after_the_step_is_retried_by_start`, `test_import_refused_after_the_step_is_retried_by_import` |
| 15 (a)-(d) | `test_moves_with_no_claim_owed_never_accept` (6 cases), `test_a_submit_that_owes_the_claim_accepts_then_claims` (2), `test_a_discard_never_accepts`, `test_a_part_bound_report_only_sync_sends_nothing` |
| 15 (e)-(f) | `test_tracker_claim_moves_nothing`, `test_import_of_an_already_bound_ticket_moves_nothing` |
| 16 | `test_row_1f_names_pre_backlog_only_for_an_unmapped_status`, `test_without_the_setting_the_reporters_case_names_it`, `test_without_the_setting_import_names_it`, `test_a_claim_landing_off_the_ladder_does_not_name_pre_backlog`, `test_show_notes_the_step` |
| 17 | the full suite above |

## Mutation checks (each made, run, read, and reverted)

| Mutation | Went red | Why it went red |
| --- | --- | --- |
| Drop the "also mapped under `statuses`" check | `…fails_closed…[also-active]`, `[also-a-discard-resolution]` | the config parsed |
| Drop the `statuses.backlog` requirement | `[no-backlog]`, `test_validate_names_pre_backlog` | no problem reported |
| Remove the `leave_pre_backlog` call in `claim` | 14 unit tests; 5 `deliver` tests; 7 CLI tests | the claim met Triage directly (row `1f`/`1e`) |
| Hand `_claim_from` the pre-step snapshot | 7 tests, including both between-the-hops cases | read as row `1f` from the stale Triage read instead of `1b` naming Bob |
| Decide the step by transition name, not status | `test_the_step_is_chosen_by_status_not_by_transition_name`, `…misconfigured…[not-offered]` | `Accept` applied from `To Do` |
| Drop `0f` from `deliver`'s pending rows | `test_a_step_that_may_not_have_applied_is_recorded_pending` | recorded `conflicting` |
| Revert Task 3's `sync.py` changes | 6 `deliver` tests | no "moved out" line; no hint |
| Make the off-ladder hint unconditional | `test_a_claim_landing_off_the_ladder_does_not_name_pre_backlog` | hint printed after a claim transition led there |
| Run the step in `deliver` before the `owed` check | all 8 "no claim owed" / discard / part-bound tests | `Accept` applied on moves that owe no claim |
| Revert Task 4's `cli.py` changes | 8 CLI tests | no moved-out line, warning, retry advice or note |
| Remove the strict "run start again" sentence | `test_strict_start_refused_after_the_step_is_retried_by_start` | stderr assertion |

The guard tests for `tracker claim` and for import's already-bound short-circuit
stay green under every mutation above. That is expected, because the change never
touched either path. They pin that it stays that way; nothing in this item could
turn them red except breaking that promise.

## What the plan or spec got wrong

1. **The hook fragment for "between the hops."** The plan gave
   `fake.before("GET", "/rest/api/3/issue/10052", …)`. That fragment also matches
   the transitions `GET` (`/issue/10052/transitions`), so it would fire on the
   wrong request. The tests use `/rest/api/3/issue/10052?`, which matches only the
   issue read by id — the step's read-back.
2. **Where the pending classification is tested.** The plan put criterion 12's
   `deliver`-level test on `link --sync-status`. But `link --sync-status` writes a
   `pending` record *before* delivering, so the test would pass even with `0f`
   classified as conflicting. It runs through `tcw work start` instead, where the
   recorded state comes only from `deliver`. The "drop `0f`" mutation confirms it.
3. **A second-POST failure cannot use `fake.fail`.** Adding a `fail` hook from
   inside a `before` hook appends to the list being iterated, so it fires on the
   first POST. The tests wrap `fake.answer` with a counter (`post_fails`), like
   `transitions_fail` in `test_tracker_sync.py`.
4. **Pre-parsed test configs are not stripped.** A `TrackerConfig` built directly
   in a test with the key `"triage "` keeps the trailing space as `left_status`;
   only the parser strips. The test uses `"triage"`. Behaviour is unaffected,
   because real configurations always go through the parser.
5. **`docs/release-notes/upcoming.md` says "Nothing else changed"** in its opening
   paragraph about v2.5.0. This item's section is appended below it, so that
   sentence is now untrue. It is left for the team lead to reword when merging the
   five proposit-app items, all of which append to this file.

## Deferred

- **Real-Jira check** (plan, Verification): one throwaway Triage ticket with
  `pre-backlog: {Triage: Accept}`. It is arranged by the team lead for `verify`, and
  no agent in this run contacted a real Jira.
- **No GitHub issue** is attached to this item. The version cut is batched across
  the five proposit-app items.
