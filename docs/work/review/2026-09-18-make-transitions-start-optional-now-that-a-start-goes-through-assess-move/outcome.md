# Outcome — Make `transitions.start` optional now that a start goes through `assess_move`

Five commits, one per plan task plus the documentation pass. The full suite is
green: **4404 passed, 3 skipped** (bare `pytest -q -n auto`, in a virtual
environment pointed at this worktree; the primary checkout's editable install was
never re-pointed).

| Commit | Task |
| ------ | ---- |
| `4c04bac8` | 1 — make `transitions` and `transitions.start` optional |
| `336f87b5` | 2 — one removal message for all five moves |
| `3f80038e` | 3 — prove a start with no configured name derives, on every path |
| `3b6d8c16` | 4 — the three readers that have no status to derive from |
| `e57b8f92` | 5 — documentation sync |

## Task 1 — both required checks go

`tcw/store/base.py`: the `nested("transitions", …)` call became the
optional-with-a-null-guard shape the plan specified, and the
`if "start" not in transitions` check was deleted. Three comments and a docstring
that stated a start had no status-derived fallback were rewritten, and
`attribute_tracker_problems`' worked example moved from
`transitions.start: required` to `credentials.token-env: required`, a message the
parser can still produce.

## Task 2 — one removal message

`assess_move`'s `drop` variable and its comment are gone; the refusal now always
ends `Fix work.tracker.transitions.<move>, or remove it to let TCW find the
transition itself.`

## Task 3 — no source change, as the spec predicted

`git diff --stat -- tcw/` over this task's commit is empty. A start with no
configured name already reaches `assess_move`'s status-derived tail, on all three
paths, and the tests are what says so rather than a reading of the code.

## Task 4 — the three readers

`claim.assess` gains a `NOT_CONFIGURED` verdict returned before anything else when
the name is blank. `intake._claim_from` gains row `1d`, placed **after** row `1e`.
`tcw/work/cli.py` needed no edit, as the spec said: `_print_ticket` already prints
`result.detail` on a `note:` line.

## What the plan and the spec got wrong

Four things. None changed the design; three are additions the plan did not
predict, and one is a mutation that had to be re-expressed before it would work.

1. **A seventh test failed under task 1, not the six the spec's table named.**
   `tests/test_tracker_validate.py::test_a_missing_required_key_is_reported_by_validate[transitions]`
   parametrizes the same requiredness claim through `tcw validate`. The spec's
   table was built by running `tests/test_tracker_config.py` and
   `tests/test_tracker_inheritance.py` only, so this file was never measured. The
   `transitions` parameter is dropped and replaced by
   `test_a_tracker_block_with_no_transitions_is_validated_by_the_cli`, which makes
   the same claim through the command rather than only through the parser.

2. **Task 2 broke a test in `tests/test_tracker_pre_backlog.py`, which no task's
   test list named.** Making the removal advice uniform added 50 characters to
   `assess_move`'s longest refusal, and the reason recorded in the binding is cut
   at `REASON_LIMIT`, which was 300. The full message measures 331 characters, so
   the cut took the `pre-backlog` hint — the part of the message that says what to
   do — off the end.
   This is a real regression rather than a test artifact: the record is what
   `tcw work tracker sync` shows the reader later. Fixed at the root by raising
   `REASON_LIMIT` to 400, with a comment stating the measurement and the rule that
   it is raised again rather than letting a message grow past it.
   `test_without_the_setting_the_reporters_case_names_it` is the guard, and it is
   what went red.
   **This was my process error, not the plan's**: I ran only the files task 2
   named before committing it, rather than the full suite at the commit boundary.
   The defect was caught one task later.

3. **Criterion 17's mutation, as the spec words it, does not express what it
   means.** "Match a problem on the nearest enclosing recorded mapping instead of
   the longest recorded key-path prefix" reads as a change to the sort order, and
   reversing the sort alone leaves both criterion-17 tests green. The load-bearing
   part is not the ordering but the trailing `": "` in
   `problem.startswith(f"work.tracker.{spelling}: ")`: without it, `credentials`
   matches `credentials.token-env: required` and the problem is blamed on the
   ancestor. Both tests go red once the mutation drops that suffix **and** sorts
   shortest-first. Recorded here because a reader applying the spec's wording
   literally would conclude the tests are too narrow when they are not.

4. **`ladder_node` and `strict_node` needed the `transitions` argument too**, not
   only `make_node` as the plan says. Both build their node through `make_node`,
   and both are the entry point for tests that need the key unset.

### A fixture default, and why it stands

This repository's implementation rules say a shared fixture may not default an
axis the code branches on. `make_node`'s new `transitions` argument does have a
default, which the plan chose deliberately to leave 58 existing call sites alone.
The rule exists because a default leaves cells no test can reach; here both cells
are reached — six new tests pass `transitions=None` — so the failure mode the rule
guards against does not arise. Noted rather than silently done.

## Code paths checked, per behavior changed

Each was found by grepping the whole tree, not by reading the call site the item
named. This epic's earlier children each shipped a fix that covered one of two
paths.

**A start with no configured name derives its transition.** Every call of
`transition_name` in `tcw/`: `sync.py:553` and `:561` (the two ladder hops inside
`walk()`), `:827` (the owed-start catch-up) and `:874` (the ordinary lifecycle
move). The first three are the three start-bearing paths, and each has a test
under criterion 9; one mutation reddens all three.

**A blank `config.start_transition` reaching a reader with no status to derive
from.** Every mention of `start_transition` in `tcw/`, `web/src`, `evals/` and
`scripts/`: `sync.py:1064` and `:1068` (`claim_refusal`), `intake.py:650`
(`_claim_from`), `cli.py:2468` (`_print_ticket`), plus the field's declaration and
assignment in `store/base.py`. `tcw/tracker/ownership.py:10` is a comment
explaining why `intake.claim` is not reused, and stays true.
`web/src` and `tcw/serve/` contain no reference. All three readers call
`claim.assess`, which is the only other caller list that matters: `assess(` in
`tcw/` resolves to exactly those three plus its own definition. The guard is
therefore in `assess`, where all three route through, rather than in each caller.

**The refusal message's length.** Both writers of a truncated reason,
`sync.py:455` (`record_unsent`) and `:933` (`finish`), use the same
`REASON_LIMIT`, so raising it covers both.

## Every criterion, and the test that proves it

| # | Test |
| - | ---- |
| 1 | `test_tracker_config.py::test_a_tracker_block_with_no_transitions_validates[key-absent]` |
| 2 | `…::test_a_tracker_block_with_no_transitions_validates[empty-mapping]` |
| 3 | `…::test_a_null_transitions_block_is_a_wrong_value_not_a_missing_one` |
| 4 | `…::test_a_present_but_unusable_start_transition_is_reported` (4 parameters) |
| 5 | `…::test_the_retired_claim_key_names_its_replacement` |
| 6 | `test_tracker_sync.py::test_a_start_posts_the_one_transition_transitions_start_names` |
| 7 | `…::test_a_start_with_no_configured_name_derives_from_the_target_status` |
| 8 | `…::test_a_start_with_no_configured_name_consults_no_name` |
| 9 | (a) criterion 7's test · (b) `…::test_an_owed_start_with_no_configured_name_derives_too` · (c) `…::test_a_ladder_hop_onto_the_active_rung_with_no_configured_name_derives_too` |
| 10 | `test_tracker_import.py::test_import_with_no_start_transition_names_the_key` |
| 11 | `…::test_inbox_accept_with_no_start_transition_refuses_the_same_way` |
| 12 | `…::test_import_of_a_ticket_already_held_needs_no_start_transition` |
| 13 | `test_tracker_strict.py::test_strict_import_of_a_held_ticket_needs_no_start_transition` |
| 14 | `test_tracker_cli.py::test_show_says_the_start_transition_is_unset_rather_than_wrong` (both `tracker show` and `inbox show`) |
| 15 | `test_tracker_sync.py::test_every_transition_key_is_offered_for_removal` (5 parameters) |
| 16 | `test_tracker_strict.py::test_strict_without_the_claim_transition_is_one_problem_naming_it` and `test_tracker_config.py::test_a_block_with_an_exclusive_claim_and_no_transitions_validates` |
| 17 | `test_tracker_inheritance.py::test_a_missing_nested_key_under_an_ancestors_mapping_is_blamed_on_the_node` and `…::test_a_nested_required_key_nobody_set_is_blamed_on_the_child` |

Criteria 10, 11 and 14 also assert the **absence** of the message each replaces
(`does not offer ''`, `work.tracker.transitions.start is ''`), so deleting the new
wording without restoring the old one cannot pass them. Criteria 10 and 11 share
one named assertion helper, so a sibling that skips half of it is visible in the
diff.

## Every mutation, and whether it went red

Each was applied alone, run, the failure message read, and reverted.

| Mutation | Reddened | Why it went red |
| -------- | -------- | --------------- |
| restore `if "start" not in transitions: …` | 1, 2, 3, 5, 16 — **red** | the extra `work.tracker.transitions.start: required` problem appears in `problems`; criterion 3's exact-list assertion catches it too |
| restore the unconditional `nested("transitions", …)` | 1 (key-absent), 3, 16 — **red**; 2 (empty-mapping) green, correctly | `work.tracker.transitions: required` for an absent mapping and for an explicit null |
| delete the `"transitions" in raw and raw["transitions"] is None` guard | 3 — **red** | `transitions: null` parses to a config instead of being refused |
| remove `"start"` from `TRACKER_MOVE_TRANSITION_KEYS` | 4 (all four parameters) — **red**; 8 other tests too | a present-but-unusable value produces no problem, so the block validates |
| delete `problems.append(STRICT_NEEDS_EXCLUSIVE_CLAIM)` | 16 — **red** (4 tests) | strict mode without the key stops being refused |
| `attribute_tracker_problems` matches the nearest enclosing recorded mapping (drop the `": "` and sort shortest-first) | 17 — **red** (both tests) | `credentials.token-env: required` is blamed on `root`, not on the node being checked. The spec's wording alone (sort order only) left both green — see "What the plan and the spec got wrong" |
| restore `drop = ("" if move == "start" else …)` | 15 — **red**, on the `start` parameter only | the `start` refusal loses the removal advice; the other four parameters stay green, which is the check on the parametrization |
| the status-derived tail returns `CONFLICTING` | 7, 9(b), 9(c) — **all three red** | each path refuses with the mutated reason instead of applying `21`; criterion 6 and 8's tests stay green, correctly |
| delete the `if named_transition:` block | 6 — **red**; criterion 8's test green | the start on the two-route workflow refuses as ambiguous |
| `transition_name` returns `"Start Progress"` for an unconfigured `start` | 8 — **red** | the start succeeds where it must refuse |
| remove the row `1d` branch from `_claim_from` | 10, 11 — **red** | the old `does not offer ''` message returns, naming no key |
| move row `1d` above row `1e` | 12 — **red**; 13 also red | a ticket the account already holds is refused instead of imported |
| `assess`'s empty-name return carries `exclusivity=NOT_EXCLUSIVE` | 13 — **red**; the claimability test too | strict mode refuses the import with `still offers '' from 'In Progress'` |
| remove `assess`'s empty-name early return | 14 (both parameters), the claimability test, 10, 11 — **red** | the `note:` line prints `work.tracker.transitions.start is ''` verbatim |

No mutation left its criterion green once expressed correctly.

## Verification the suite cannot make

- **This repository's own configuration is untouched and still validates.**
  `tcw validate` → `validate OK`; `git diff HEAD -- tcw-config.yaml` is empty;
  `transitions: start: Start` is still at lines 12–13, a live example of the
  setting being honoured.
- **Nothing contacted a real tracker.** Every test drives `FakeJira`. The only
  absolute URLs in `tests/` are `example.invalid`, `example.atlassian.net`,
  `github.invalid` and one `Origin` header value in a cross-origin test.
- **The retired message appears nowhere it should not.**
  `transitions.start: required` survives only in a negative assertion in
  `tests/test_tracker_config.py`, in `docs/changelogs/v2.4.0.md` (a released
  version's record, not edited) and in this item's own artifacts and the new
  changelog entry describing its removal.
- **The four comments and docstrings changed in tasks 1 and 2 were read back**
  against the code they sit above, after the change landed. No test can catch a
  stale comment.
- **`tcw work docs` was re-run** before the documentation pass: seven entries, the
  same seven the plan evaluated. Nothing was added between the plan and the
  implementation.

## Notes

- Three of the seven documentation entries did not fire, for the reasons the plan
  gave and re-checked here. `README.md` states no tracker key's requiredness
  (`grep -c required README.md` is 0) and its sample still sets the key.
  `docs/guide/<topic>.md` is excluded for `jira.md` by its own wording, and the
  only other guide mentioning `work.tracker` is `docs/guide/work.md`, whose three
  mentions are `inbox-query`, `pre-backlog` and a list of command names. The
  `transitions:` blocks in `docs/guide/configuration.md:23` and
  `docs/guide/work.md:149` are `work.lifecycle.transitions`, a different key ending
  in the same word. `skills/work/SKILL.md` itself needed no edit; the file that
  changed is `skills/work/references/commands.md`.
- `docs/{changelogs,release-notes}/upcoming.md` are written but **not rotated**.
  This is the last open child of
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`, and the
  version cut covering the whole epic follows it.
- The worktree carries no virtual environment of its own: the one used is in this
  session's scratchpad, outside the repository, so there is nothing to remove
  before `tcw work complete` tears the worktree down.
