# Plan — give a recordless sync a move, and let strict mode work without `transitions.start`

Four defects, three independent code changes, one shared documentation pass. The
spec's Design sections D1–D10 settle *what* to do; this plan settles the order, the
files, and what proves each step.

## How every task in this plan is worked

Two rules apply to all of them, stated once rather than repeated per task.

1. **The failing test comes first, and is seen failing.** Every task below that
   changes behaviour names the test that must go red before any source file is
   edited, and what it must say when it goes red. A test that has never been red
   proves nothing. Where a task names a test that is *not* expected to go red — a
   guard on behaviour that must not change — the task says so explicitly, and that
   test is written and seen passing before the change, then run again after.
2. **The commit boundary is green, the middle of a task is not.** Each task writes
   its tests and its code, and commits both together. The suite must pass at the end
   of every task, so a task that would leave the tree broken for the next one has
   been split.

Tasks 1, 2 and 4 are the three independent code changes. Task 4 depends on task 3
only for its measurement, and task 5 depends on task 4 only for the meaning of the
key it reads. Tasks 6 onwards depend on everything before them.

## Task order and dependency

| # | Task | Depends on |
| --- | --- | --- |
| 1 | Findings 1 and 2 — separate the assessed move from the recorded move | nothing |
| 2 | Finding 3 — strict mode requires `work.tracker.transitions.start` | nothing |
| 3 | Measure finding 4 against the pre-epic tree (commits nothing) | nothing |
| 4 | Finding 4 (a) and (b) — one exclusivity detector, one key, every strict claim path | 3 for its baseline, 2 for the test it deletes |
| 5 | Finding 4 sweep — `tracker show` and `inbox show` answer about their own key | 4 |
| 6 | Finding 4 (c) — a strict claim refusal that names a way forward | 4 |
| 7 | Deleted-and-narrowed-test coverage audit | 1, 2, 4, 5, 6 |
| 8 | Documentation Sync block (five documents, two capability entries) | 1–6 |
| 9 | Full suite, `tcw validate`, and the acceptance-criteria sweep | everything |

Tasks 1 and 2 may be done in either order, or by two people at once: they touch
different source files (`tcw/tracker/sync.py` against `tcw/store/base.py`) and
different tests. Task 2 must land before task 4, because task 2 is what deletes
`tests/test_tracker_strict.py:489` and lands its replacement, and task 4 would
otherwise delete a test that task 2 still needs to account for.

---

## Task 1 — Findings 1 and 2: separate the assessed move from the recorded move

Implements D1, D2, D3, D4 and D6. One root cause, one fix, in `deliver`.

**Red first.** Write these before touching `tcw/tracker/sync.py`, and run them. Each
must fail with the message named, not merely fail.

In `tests/test_tracker_sync.py` (from `probes/test_probe_nullmove.py`,
`test_probe_reopened.py`, `test_probe_recovery.py`):

- `test_a_recordless_sync_that_cannot_reach_the_tracker_writes_no_record` — criterion 1.
  Red as: the binding grows `sync: {move: null, …}` and `tcw work show` prints
  `tracker sync: record cannot be read ('sync' has no text for: move)`.
- `test_a_recordless_sync_the_tracker_refuses_writes_no_record` — criterion 2. Same
  red, reached through a conflicting answer rather than an outage.
- `test_a_failed_recordless_sync_does_not_claim_the_ticket_next_time` — criterion 4,
  **the trap**. An `active` item whose ticket another account holds: after a failed
  bare sync, the next successful `tcw work tracker sync` must not assign the ticket
  and must not apply the claim transition. Assert on the fake's `applied` list and on
  the ticket's assignee, not on the exit code. This test passes today and must keep
  passing; it is what fails against a fix that writes `start` into the record, so it
  is written first and re-run after.
- `test_sync_of_a_reopened_ticket_on_a_completed_item` — criterion 6, parametrised
  over the ticket unassigned, held by the caller, held by another account. Red as:
  two of the three refuse with `is unassigned, so it was not moved` /
  `is assigned to Bob, not to you`.
- `test_sync_of_a_reopened_ticket_on_a_discarded_item` — criterion 7, parametrised
  over each discard resolution the fixture maps.
- `test_a_catch_up_binding_heading_for_a_completion_still_needs_the_ticket_held` —
  criterion 9. A guard, not a red test: it passes today, and it is what catches the
  derived move widening the resolution exemption into the catch-up walk.
- `test_a_bare_sync_still_brings_back_a_ticket_moved_on_by_hand` — criterion 10. Also
  a guard; the two existing tests it restates
  (`test_tracker_sync.py:2025`, `:2477`) must pass unchanged as well.

In `tests/test_tracker_strict.py` (from `probes/test_probe_outage_blocks.py`,
`test_probe_strict_wedge.py`, `test_probe_reopen_exclusive.py`):

- `test_a_failed_recordless_sync_does_not_block_the_next_strict_move` — criterion 3,
  covering `submit`, `rework` and `complete`. Red as: refused with `has a change that
  has not reached the tracker (an unreadable record)`.
- `test_a_failed_recordless_sync_leaves_the_accurate_strict_refusal_in_place` —
  criterion 3's second half, the wedge. On an item that already had a real problem,
  the refusal after the sync must still be `SYNC-1 is unassigned. Assign it to
  yourself in the tracker and put it in 'In Progress' or 'In Review'`, not the
  unreadable-record one. Red as: the second refusal is the unreadable-record message.
- `test_a_reopened_ticket_closes_again_under_an_exclusive_claim_transition` —
  criterion 8. Red as: `Take it with \`tcw work tracker claim\``, which is step one of
  the four-step loop.
- `test_the_strict_binding_refusal_reads_as_ordinary_prose` — criterion 19. Asserts on
  the assembled sentence: no `; It`, no `. it`. Red today.

Also confirm, without adding a test for it, that
`test_a_binding_with_a_null_move_record_is_cleared_by_the_next_sync` (criterion 5)
already exists or is added here — it is what makes the "no migration" non-goal true,
and it must pass both before and after.

**Then the code.** `tcw/tracker/sync.py`, in `deliver`, three edits:

1. Leave line 386's `move = move or (…)` **exactly as it is**. It is what makes the
   `named` transition lookup at `:879` and the record write at `:467` behave as they
   do today for every case that has a record, and D2 requires both to keep doing so.
2. Add one derived value beside it — the move the ticket is *assessed* against —
   falling back to `MOVE_ONTO.get(local)` when `move` is still `None`. Feed it to
   `resolving` (`:391-392`) and to the `move=` argument of `assess_move` (`:881`),
   and to nothing else. It is safe to pass into `assess_move`: the only other place
   that function reads `move` is the `Fix work.tracker.transitions.{move}` message,
   which is inside the `named_transition` branch, and `named` is `""` whenever the
   derived value differs from `move`.
3. Guard the record write at `:454-468`. The value it would store,
   `"start" if start_owed else move`, is `None` in exactly one case — a bare `sync`
   with no readable record — and that is the case D3 says writes nothing. Return the
   `Outcome` without writing, and **without falling through to the `drop_record`
   branch at `:471`**: clearing a legacy unreadable record on a *failed* sync is a
   wider change than this item asked for, and criterion 5 already covers clearing it
   on a successful one.

Then D6, in the same file: fix the punctuation of the strict binding refusal at
`:986-991`.

**Files:** `tcw/tracker/sync.py`, `tests/test_tracker_sync.py`,
`tests/test_tracker_strict.py`.

**What proves it landed:** the ten tests above pass; `pytest tests/test_tracker_sync.py
tests/test_tracker_strict.py tests/test_tracker_claimability.py
tests/test_tracker_ownership.py` passes; and the two reconciliation tests named in the
spec's **What this must not break** — `test_tracker_sync.py:2025` and `:2477` — pass
**unchanged**, which is the check that the derived move did not reach the transition
lookup.

---

## Task 2 — Finding 3: strict mode requires `work.tracker.transitions.start`

Implements D5. Parser only; touches nothing in `tcw/tracker/`.

**Red first**, in `tests/test_tracker_strict.py`, alongside the existing
`CLAIM` / `parsed()` configuration tests:

- `test_strict_without_a_start_transition_is_refused` — criterion 11. Red as:
  `problems == []`, because the strict block approves it today. Pair it with a
  command-level test that `tcw validate` on such a node exits non-zero and names
  `work.tracker.transitions.start`, converted from
  `probes/test_probe_strict_import.py`.
- `test_a_null_or_blank_start_transition_keeps_its_one_problem` — criterion 12,
  parametrised over `None` and `"  "`. A guard: it must show exactly one problem both
  before and after, so it is written and seen passing first.
- `test_the_missing_start_transition_is_attributed_to_the_node_being_validated` —
  criterion 13. A guard on `attribute_tracker_problems`; the spec argues from the
  prefix match that it needs no special handling, and this test is what checks the
  argument rather than trusting it.
- `test_a_node_that_is_not_strict_needs_no_transitions_block` — criterion 14, both as
  a parser test and as a CLI test converted from
  `probes/test_probe_strict_import.py::test_strict_without_transitions_start_can_start_and_finish`.

**Then the code.** `tcw/store/base.py`:

1. A new module-level problem string beside `STRICT_NEEDS_EXCLUSIVE_CLAIM` (`:1281-1286`),
   worded to match it: the key path, `required when strict is true`, why in plain
   words — strict mode creates work only from a ticket, and the two commands that do
   that (`tcw work tracker import`, `tcw work inbox accept`) claim through this
   transition — then what to set.
2. The check itself **after** `move_transitions = _parse_tracker_transitions(…)`
   (`:1508`), not in the strict block at `:1470-1490`, which runs before `transitions`
   is parsed. Reported only when the key is **absent** from the raw `transitions`
   mapping, matching the `if "exclusive-claim-transition" not in raw` rule at `:1486`.

**Then the one existing test that must change.** Delete
`tests/test_tracker_strict.py:489 test_strict_import_of_a_held_ticket_needs_no_start_transition`,
**and land its replacement in the same commit** so no property is uncovered at any
commit boundary. I confirmed the spec's reading against the code and I agree with
deleting it rather than converting it — see **Notes → On deleting the test at
`:489`** for what it actually held and where each half goes.

The replacement is criterion 25's test, written here rather than in task 4 because
the behaviour it asserts is true today and must stay true through task 4 as well:

- `test_a_strict_claim_of_a_ticket_you_already_hold_sends_nothing` in
  `tests/test_tracker_strict.py` — directed (`SYNC`) workflow, ticket in the active
  status assigned to the caller, `transitions.start` **and**
  `exclusive-claim-transition` both set. `tcw work tracker import`,
  `tcw work tracker claim` and `tcw work start` each exit 0 and leave
  `fake.applied == []`. A guard, seen passing before the change and again after.

**Then remove the probes.** Delete the `probes/` folder from this item's folder
(criterion 20) — every one of its seven files has a successor named in task 1 or
task 2. The successor list goes in task 7's audit.

**Files:** `tcw/store/base.py`, `tests/test_tracker_strict.py`, and deletion of
`docs/work/backlog/2026-09-22-give-a-recordless-sync-a-move-and-let-strict-mode-work-without-transitions-start/probes/`.

**What proves it landed:** the four tests above; `tcw validate` in a fixture node with
`strict: true` and no `transitions.start` exits 1 with exactly one new problem; and
the five tests the spec names as holding `transitions.start` optional for ordinary
projects pass **unchanged** — `tests/test_tracker_import.py:213`, `:219`, `:227`,
`tests/test_tracker_claimability.py:227`, `tests/test_tracker_cli.py:202` — plus the
four `test_tracker_sync.py` derive-from-status tests at `:2522`, `:2538`, `:2557`,
`:2578`.

---

## Task 3 — Measure finding 4 against the pre-epic tree

Commits nothing. It exists so that criterion 22's "fails on `f2a9523e`, passes on
`bfb2ff33`" is a measurement the implementer makes rather than a claim inherited from
the spec. **Do this before writing task 4's fix**, so the target behaviour is known
rather than guessed.

The comparison checkout is already at
`/private/tmp/claude-501/-Users-brian-Projects-TCW/ac161ba6-4ff5-46b9-82e3-92cae9351f30/scratchpad/work/pre-epic`
(`git rev-parse --short HEAD` → `bfb2ff33`), with a virtual environment at
`…/scratchpad/venv-preepic`.

**Three corrections to the recipe, each measured while writing this plan.** Without
them the comparison silently measures the wrong tree or refuses to run at all.

1. **The pre-epic virtual environment resolves `tcw` to the primary checkout.**
   `venv-preepic/bin/python -c "import tcw; print(tcw.__file__)"` prints
   `/Users/brian/Projects/TCW/tcw/__init__.py`. That is the editable-install import
   hook described in this repo's CLAUDE.md: it wins over `PYTHONPATH`. The only thing
   that makes the pre-epic source run is setting the shell's current directory to the
   pre-epic root, so its own `tcw/` comes first on the search path. Confirm it every
   time by checking that the probe's own configuration errors are pre-epic ones.
2. **The probe cannot be one file run on both trees.** The pre-epic tree spells the
   key `work.tracker.transitions.claim`, not `.start`, and `strict_node` there has a
   different signature (no `claim_transition` keyword). Build the probe from
   `make_node` and `set_tracker_key`, which both trees have, and write two copies
   differing only in the transitions key.
3. **`work.tracker.exclusive-claim-transition` does not exist on the pre-epic tree.**
   Its parser rejects the key outright: `work.tracker.exclusive-claim-transition:
   unknown key`. The spec's statement that the probe "sets `exclusive-claim-transition:
   Start Progress` … and was run unchanged on both trees" cannot be true of the
   pre-epic half. The pre-epic refusal comes from `claim_refusal` reading
   `transitions.claim`; the pre-epic copy of the probe therefore sets no exclusivity
   key at all. See **Notes → What I could not confirm in the spec**.

**The measurement, run on both trees.** Strict mode, `GLOBAL` workflow, a bound item,
`tcw work start`, over five ticket states. Measured while writing this plan:

| ticket state | pre-epic `bfb2ff33` | main `8ee9bc01` |
| --- | --- | --- |
| `GLOBAL`, unassigned | exit 1, refused `still offers 'Start Progress' from 'In Progress', so a second person could claim it too`; item stays `backlog`; ticket moved to `In Progress` and left claimed | exit 0, item started |
| `GLOBAL`, held by caller, ticket on the **active** status | exit 1, the identical refusal; item stays `backlog` | exit 0, item started, nothing applied |
| `GLOBAL`, held by caller, ticket on the **backlog** status | exit 1, the identical refusal (the pre-epic claim moved it to `In Progress` first) | exit 0, item started, `Start Progress` applied by `deliver` |
| `SYNC` (directed), held by caller, ticket on the active status | exit 0, started, nothing applied | exit 0, started, nothing applied |
| `SYNC` (directed), held by caller, ticket on the backlog status | exit 0, started, `Start Progress` applied | exit 0, started, `Start Progress` applied |

Row 3 is not in the spec and it is the row that decides task 4's shape: see
**Notes → The case D8 does not cover**.

**Files:** none in `/Users/brian/Projects/TCW`. The probe lives in the scratchpad and,
for the pre-epic half, in that checkout's `tests/` folder; delete it afterwards.

**What proves it landed:** the five-row table above, reproduced by the implementer,
pasted into the task 9 verification notes. If any row disagrees with this plan, stop
and say so before writing task 4 — the disagreement is more informative than the fix.

---

## Task 4 — Finding 4 (a) and (b): one exclusivity detector, one key, every strict claim path

Implements D8. This is the riskiest change in the item, and it is placed here — after
its measurement exists (task 3) and after the test that contradicts it is gone (task 2).

**Where the check lives — the placement D8 left to the plan.** Keep it in
`claim_refusal` (`tcw/tracker/sync.py:1053-1075`) and give that function two more
callers. Do **not** move it into `assert_ownership`. Four reasons, all checked
against the code:

- `assert_ownership` has a third production caller, `deliver` at
  `tcw/tracker/sync.py:734`, where the exclusivity check must not run. Moving the check
  there means adding a flag to switch it off again for `deliver` — the same number of
  call-site edits, with a worse shape.
- `assert_ownership` answers one question, "who holds this ticket", and its module
  docstring says so at length. A strict-mode configuration question is not that.
- `claim_refusal`'s only surviving caller already puts it behind `config.strict`
  (`tcw/work/cli.py:2606-2609`), which is where the spec's non-goal about checking
  exclusivity outside strict mode requires it to stay.
- Three existing tests call `claim_refusal(client, config, TICKET_ID, outcome)`
  directly (`tests/test_tracker_strict.py:281`, `:299`, `:307`) and must pass
  unchanged, so its positional signature is fixed. That rules out rewriting it into
  something `assert_ownership` could host.

**Red first**, in `tests/test_tracker_strict.py`:

- `test_a_strict_start_on_a_workflow_that_cannot_exclude_is_refused_unassigned` —
  criterion 22, the regression criterion. `GLOBAL`, ticket unassigned, item must stay
  `backlog`, refusal must name the transition and the status it is still offered from.
  Red as: exit 0 and the item `active`.
- `test_a_strict_start_on_a_workflow_that_cannot_exclude_is_refused_when_already_yours` —
  criterion 23. Same, with the ticket already assigned to the caller **on the active
  status**. Red the same way. The status matters: see **Notes → The case D8 does not
  cover**.
- `test_a_strict_tracker_claim_on_a_workflow_that_cannot_exclude_is_refused` —
  criterion 24. Red as: exit 0.
- `test_the_exclusivity_verdict_comes_from_the_exclusive_claim_transition` —
  criterion 26, in both directions. Needs a fixture where the two keys name
  **different** transitions, which no existing test has; see the fixture note below.
  Red as: the verdict follows `transitions.start` in both directions.
- `test_the_exclusivity_refusal_names_the_exclusive_claim_transition_key` —
  criterion 27. Red as: the refusal names `work.tracker.transitions.start`.
- `test_a_project_that_is_not_strict_is_unaffected_on_both_workflows` — criterion 28.
  A guard: it passes today, is seen passing first, and is what bounds the change.

**The fixture criterion 26 needs.** `tests/tracker_fake.py` gains one workflow beside
`SYNC` and `TWO_ROUTES_IN`: `SYNC` with a second route into the active status that is
**also offered from** the active status, so one of the two routes is a mutex and the
other is not. Then criterion 26 is two nodes:

- `transitions.start` = the non-exclusive route, `exclusive-claim-transition` = the
  exclusive one → a strict claim **succeeds**.
- the two reversed → a strict claim is **refused**.

Today both nodes behave the same, because the verdict comes from the wrong key. That
is what makes the test red, and it is the only way to tell the two keys apart —
`TWO_ROUTES_IN` cannot, because both of its routes are exclusive.

**Then the code.**

1. `tcw/tracker/ownership.py` — `OwnershipOutcome` gains `key: str = ""`, set from
   `ticket.key` on every return. `claim_refusal` reads `outcome.key`, and
   `intake.claim`'s outcome already has one; this is the smallest bridge that lets one
   function serve both outcome shapes without changing its signature.
2. `tcw/tracker/sync.py` — `claim_refusal` asks
   `assess(config.exclusive_claim_transition, …)` instead of `config.start_transition`
   (`:1069`) and names that key in its refusal (`:1072-1074`).
3. `tcw/tracker/sync.py` — `claim_refusal` gains one keyword-only argument,
   defaulting to today's behaviour, that says whether a ticket found **off** the
   active status is a refusal (`is assigned to you but is in '…', not '…', so this is
   not a claim of it`) or simply a question this run cannot answer. `import` and
   `inbox accept` keep the refusal — `tests/test_tracker_strict.py:305` holds it. The
   two lifecycle callers pass the other value, because a strict `tcw work start` of a
   ticket you hold in the backlog status goes on to move it onto the active status
   itself, and refusing it there would be wrong. Without this, criterion 25's directed
   case starts failing; I measured that in task 3's row 5.
4. `tcw/work/cli.py` — `_strict_claim` calls `claim_refusal` after a settled
   `assert_ownership` (after `:502`), and returns `_strict_says_no("start", f"{bare}
   was not started", refusal)` on a refusal.
5. `tcw/work/cli.py` — `_tracker_claim` does the same after `:3337`, **guarded on
   `client.config.strict`**, which that function does not currently check at all.
   Criterion 28 is what holds the guard honest.
6. `tests/test_tracker_strict.py:471` — the docstring of
   `test_a_workflow_that_cannot_exclude_refuses_import` says "A strict `start` no
   longer does". That becomes false here. Rewrite the docstring; the assertions are
   unchanged.

**Files:** `tcw/tracker/ownership.py`, `tcw/tracker/sync.py`, `tcw/work/cli.py`,
`tests/tracker_fake.py`, `tests/test_tracker_strict.py`.

**What proves it landed:** criteria 22–28's tests pass; the three surviving exclusivity
tests (`tests/test_tracker_strict.py:279`, `:297`, `:471`) pass unchanged; the two
idempotence tests (`tests/test_tracker_strict.py:305`,
`tests/test_tracker_import.py:227`) pass unchanged; criterion 25's test from task 2
still passes; and task 3's probe, re-run on the fixed tree, now agrees with the
pre-epic column for rows 1 and 2.

---

## Task 5 — Finding 4's sweep: `tracker show` and `inbox show` answer about their own key

Implements the spec's **Design → Sweep**, criterion 33. **Folded in, not filed** — the
spec already records that decision and the reason: it is the same defect as 4(b) at a
second call site, and fixing a defect everywhere its callers reach it is this
project's rule. It is a handful of lines in a file task 4 already opens.

**Red first**, in `tests/test_tracker_cli.py`: on a node whose `transitions.start` and
`exclusive-claim-transition` name **different** transitions (the fixture task 4 added),
`tcw work tracker show` prints a `claimable:` line that answers about
`transitions.start` and a `workflow:` line that answers about
`exclusive-claim-transition`. Red as: both lines answer about `transitions.start`.

**Then the code.** `tcw/work/cli.py` `_print_ticket` (`:2468-2469`): split the single
`assess` call into two — `claimable:` from `client.config.start_transition`,
`workflow:` from `client.config.exclusive_claim_transition`. The `note:` line prints
`result.detail`; decide which assessment it belongs to and say so in a comment.

**Files:** `tcw/work/cli.py`, `tests/test_tracker_cli.py`.

**What proves it landed:** the new test, and `tests/test_tracker_cli.py:202
test_show_says_the_start_transition_is_unset_rather_than_wrong` passing **unchanged** —
it is the test that holds the `claimable:` half about the right key.

---

## Task 6 — Finding 4 (c): a strict claim refusal that names a way forward

Implements D9, criteria 29 and 30. Separate from task 4 because it changes refusal
text rather than whether anything is refused, and because its three commands must be
made to agree, which is easier to check once task 4 has settled what they refuse.

**Red first**, in `tests/test_tracker_strict.py`: build the D9 state — directed
(`SYNC`) workflow, item started, strict turned on, `tcw work tracker release` run, so
the item is `active` with no owner and the ticket sits unassigned on the active status.

- `test_a_strict_claim_of_a_released_item_names_a_way_forward` — criterion 29, over
  `tcw work tracker claim`, `tcw work tracker claim --take-over` and
  `tcw work start --take-over`. Assert that each names the ticket's state and at least
  one thing to do, and that all three produce the same advice. Red as: all three print
  `It offers: 'Ready for Review', 'Finish', "Won't Do", 'Mark Duplicate'.` and name
  nothing to do.
- `test_following_that_advice_lets_the_claim_succeed` — criterion 30. Do what the
  refusal says on the directed workflow, re-run the command, assert it succeeds. This
  is the criterion that fails if the advice is merely present rather than correct.

**Then the code.** `tcw/work/cli.py`:

1. Widen the `past` condition at `:490-491`. It requires `rung > 0`, so a ticket
   sitting **on** the active status is rung 0 and falls through to the bare
   `assert_ownership` refusal. Rung 0 needs its own branch, not the `past` message:
   "is in 'In Progress', past 'In Progress'" is not true and "move it back to 'In
   Progress'" is not advice.
2. The rung-0 message names both ways out, mirroring `authorize`
   (`tcw/tracker/sync.py:1030-1035`): assign the ticket to yourself in the tracker —
   which after task 4 reaches an exclusivity check rather than skipping one — or move
   it back to the status the claim transition leads from.
3. `_tracker_claim` (`:3337`) refuses from `assert_ownership`'s own "does not offer"
   message, not through `_strict_claim`, so it needs the same branch. Put the sentence
   in one helper in `tcw/work/cli.py` and call it from both, or criterion 29's "all
   three agree" becomes a thing that has to be kept agreeing by hand.

Nothing here changes whether the claim is refused. It stays refused.

**Files:** `tcw/work/cli.py`, `tests/test_tracker_strict.py`.

**What proves it landed:** criteria 29 and 30's tests, and
`tests/test_tracker_strict.py:711
test_the_strict_past_the_claim_refusal_only_says_it_would_move_it_back_if_it_could`
passing **unchanged** — it holds the rung-above-zero message this task must not
disturb.

---

## Task 7 — Deleted-and-narrowed-test coverage audit

The regression in finding 4 escaped because a test was deleted during the epic and its
docstring handed its responsibility to successors that cover a different property.
This task is the named check that stops that happening again here. It changes no
source file.

**The check, run as three steps:**

1. **Build the list mechanically**, not from memory:
   `git diff main -- tests/ | grep '^-.*def test_'` gives every deleted test, and
   `git diff main -- tests/ | grep '^-.*assert'` every removed assertion. Include the
   seven files deleted from `probes/`.
2. **For each entry, name the successor test** — the specific test, by file and name,
   that asserts the same property afterwards. Write the list down; it goes into the
   task 9 verification notes.
3. **Prove each successor actually holds that property**, by mutation rather than by
   reading: break the code the property depends on, run the named successor, and
   confirm it goes red *for that reason*. A successor that stays green, or goes red
   for a different reason, is not a successor — either keep the original test or write
   a real replacement.

Two entries are known in advance and must appear in the list:

- `tests/test_tracker_strict.py:489 test_strict_import_of_a_held_ticket_needs_no_start_transition`,
  deleted in task 2. Its three properties and their successors are set out in
  **Notes → On deleting the test at `:489`**; one of the three is deliberately gone,
  and the audit must record that as a decision rather than as coverage.
- Each of the seven `probes/` files, deleted in task 2. Criterion 20 requires them
  replaced by asserting tests covering criteria 1–10 and 19; the audit is where that
  claim is checked file by file.

**Files:** none modified. Its output is the successor list, carried into task 9 and
into the changelog entry written in task 8.

**What proves it landed:** the list exists, every entry names a successor or a recorded
decision, and every successor was seen going red under mutation.

---

## Documentation Sync

Task 8, worked as one pass over the finished diff. Every entry from `tcw work docs`
was evaluated; the ones that fire and the ones that do not are both listed, because a
trigger judged not to fire is a judgement someone should be able to check.

### Fires

**8a — `docs/guide/jira.md` [Tracker-Change].** Four passages, criteria 16, 31 and 32:

- `:958-962`, the strict-mode requirement list, and the sentence after it that explains
  why: add `transitions.start` alongside `exclusive-claim-transition`, with the reason
  — strict mode creates work only from a ticket, and the two commands that do that
  claim through this transition. The command table's description of `tracker import`
  as the way into strict work must no longer stand without the key.
- `:441-446`, the promise that a claim "applies that transition before assigning, so a
  second person's transition is refused and they never reach the assignment". D10 says
  this becomes true again by task 4 rather than by rewriting the sentence — with one
  addition: on a ticket the caller already holds no transition is applied and none can
  be, and what is checked instead is that the workflow would still refuse a second
  person. Add that as a clause; keep the promise.
- `:405-411`, the passage saying a released item "stays active with no owner until
  somebody claims it — with `tracker claim`, or with `tcw work start`". True without
  strict mode, false under it. Add what strict mode does instead, and point at the way
  forward task 6 adds.
- `:469-474`, "`tcw work tracker claim` is the deliberate exception: it applies the
  transition from wherever the ticket is". Under strict mode it does not. State the
  strict case beside the ordinary one.

**8b — `docs/release-notes/upcoming.md` [Public-API / Tracker-Change].** Criteria 15
and 34, in plain words, no module names:

- The existing **"Naming the start transition is now optional"** section gains the
  strict-mode exception.
- The existing **"Strict mode needs one more setting"** section gains the second
  setting, stated as a breaking change for a project that has `strict: true` today
  with no `transitions.start`: `tcw validate` will report it on upgrade, and here is
  what to set.
- A new note that strict claims are checked for exclusivity again, and that a project
  whose workflow never excluded a second claimant will now be refused where it was
  previously accepted. Say what the refusal leaves behind — on an unassigned ticket
  the claim has already moved and assigned it before the check runs, so the ticket is
  left claimed while the item stays in the backlog. That is measured, not guessed
  (task 3, row 1).
- The `sync` fix in user terms: running the diagnostic command can no longer leave an
  item worse than it found it, and a ticket somebody reopened on finished work can be
  closed again without taking it.

**8c — `skills/configure/references/tracker.md` [Configuration-Key-Change].**
Criterion 17. The `transitions.start` paragraph (`:53-77`) gains "optional **except
under strict mode**", in the same shape as the `exclusive-claim-transition` sentence at
`:96-97`; the `strict` paragraph (`:187-196`) gains the key in its requirement list.

**8d — `docs/changelogs/upcoming.md` [Any-Code-Change].** Criteria 18 and 36, grouped
Added / Changed / Fixed:

- The parser change (`tcw/store/base.py`), the `deliver` change
  (`tcw/tracker/sync.py`), `claim_refusal`'s change of key and its two new callers,
  `OwnershipOutcome.key`, `_print_ticket`'s split, and `_strict_claim`'s rung-0 branch.
- The one existing test deleted and why, plus task 7's successor list in summary.
- Finding 4 recorded **as a regression**, naming the three children whose combination
  caused it — the one that made `exclusive-claim-transition` required under strict
  mode, the one that composed the lifecycle moves out of claim and sync and so removed
  `claim_refusal`'s lifecycle call sites, and the one that made `transitions.start`
  optional and so broke the single surviving check — so a later reader can see why six
  rounds of per-child review did not find it.

**8e — the capability ledger.** The spec's **Capability changes** section names two
entries, both staying **Supported**:

- `docs/capabilities/work/require-tracker-backed-work/description.md` (`cap-38f44c`):
  the requirement paragraph gains `work.tracker.transitions.start` with its reason, and
  the entry says which key carries the exclusivity check. Its closing line — "A claim
  only authorizes work when the workflow could have refused a second person" — becomes
  true of the shipped behaviour again by task 4; it needs the qualification that on a
  ticket the caller already holds, what is checked is that the workflow would still
  refuse a second person, rather than that a transition was applied.
- `docs/capabilities/work/synchronize-external-tracker-work/description.md`
  (`cap-207f2c`): narrow "records whether that is pending or conflicting" to lifecycle
  moves — a `tcw work tracker sync` on an item with nothing recorded reports what it
  found and writes nothing at all — and extend "a claim gates work, not resolution" to
  cover a `sync`.

No taxonomy change: both entries sit under the existing `external-work-tracker`
Feature, and "sync record", "claim" and "strict mode" are all already registered.

### Does not fire

- **`README.md` [Public-API].** It does not name individual `work.tracker` keys, and
  no CLI subcommand is added or removed. Re-check against the finished diff before
  concluding this — `tcw work tracker claim` changes what it refuses under strict mode,
  and if the README describes that at all, it fires after all.
- **`skills/work/SKILL.md` [Skill-Driven-Component].** No CLI surface, model, field,
  lifecycle stage or guardrail of the work component changes. The guardrail that is
  closest to changing is strict mode's, which is configuration and lives in
  `skills/configure/references/tracker.md` (8c) by that entry's own rule.
- **`docs/guide/<topic>.md` [Guide-Topic-Change]** for guides other than `jira.md`.
  `jira.md` has its own entry and is covered by 8a. Grep the rest of `docs/guide/` for
  `transitions.start`, `exclusive-claim-transition` and `strict` before concluding it;
  a guide that names a key goes stale silently.

**Files:** `docs/guide/jira.md`, `docs/release-notes/upcoming.md`,
`skills/configure/references/tracker.md`, `docs/changelogs/upcoming.md`,
`docs/capabilities/work/require-tracker-backed-work/description.md`,
`docs/capabilities/work/synchronize-external-tracker-work/description.md`.

**What proves it landed:** `tcw validate` passes; `tcw capabilities` reports both
entries as Supported with no drift; criteria 15, 16, 17, 18, 31, 32, 34 and 36 are
read against the edited documents by a person, since all eight are marked **[read]**.

---

## Task 9 — Full suite, validate, and the acceptance-criteria sweep

**The suite.** `pytest` from the repository root, the whole thing, once with all four
findings fixed. This is criteria 21 and 35.

**What counts as passing:**

- **Zero failures and zero errors.** Nothing else counts, and a targeted run of the
  tracker test files is not a substitute — the derived move reaches `assess_move`,
  which is shared, and the parser change reaches every node fixture in the repository.
- **Skips unchanged at 3.** A skip that appears or disappears is a test that stopped
  running, which is a silent loss of coverage.
- **The passing count reconciles**: baseline, minus 1 for the test deleted in task 2,
  plus the number of tests added. Measure the baseline with `pytest -q` on `main`
  **before** task 1 and write the number down; do not carry a number forward from the
  spec, which quotes 4414 from a throwaway copy at `f2a9523e` while the coordinating
  session measured 4404 on `main`. Whichever it is, the number that matters is the one
  measured at the start of this implementation, and the reconciliation is what proves
  no test was lost.
- CI runs bare `pytest`, so run it that way rather than `python -m pytest`, which puts
  the current directory on the import path and can hide a packaging mistake.

**`tcw validate`** on this repository, which is bound as a `pre` hook on `complete`
and will run the changed parser against this project's own configuration.

**The criteria sweep.** Walk all 36 acceptance criteria and mark each one against the
task that delivered it and the test or document that proves it. The mapping this plan
intends:

| Criteria | Task |
| --- | --- |
| 1–10, 19 | 1 |
| 11–14, 20, 25 | 2 |
| 22 (pre-epic half) | 3 |
| 22–24, 26–28 | 4 |
| 33 | 5 |
| 29, 30 | 6 |
| 20 (the audit half) | 7 |
| 15–18, 31, 32, 34, 36 | 8 |
| 21, 35 | 9 |

**Files:** none modified.

---

## Verification

What the suite cannot decide, and who decides it.

- **Eight criteria are marked [read]** — 15, 16, 17, 18, 31, 32, 34, 36. No test can
  check that a paragraph says a true thing in plain words. A person reads the four
  documents and the two capability entries against those criteria.
- **Criterion 22's pre-epic half is not a test.** It is a comparison against a second
  checkout, run by hand (task 3). The repository's suite can only hold the `main`
  half. Record the five-row table in the verification notes so a later reader can see
  what was compared, on which commits, and with which corrections to the spec's
  recipe.
- **Criterion 30 needs judgement about wording.** "Following the advice leaves the user
  better off" is testable for the directed workflow, and the test is named in task 6.
  Whether the sentence is *good* advice — whether a user reading it would do the right
  thing — is a reading, not an assertion.
- **The spec's own risk list names a state nobody can test out of.** A strict user on a
  workflow where the ticket cannot be moved back to the status the claim transition
  leads from, and where assigning it in the tracker then meets a non-exclusive verdict,
  has no option left but turning strict mode off. Task 8b's release note is where that
  gets said out loud. Whether it is acceptable is the requester's call, not a test's.
- **Task 7's mutation check is the item's real safety net**, and it is worth more than
  a green suite. A green suite is exactly what the epic had when it shipped this
  regression.
- **`tcw work docs` triggers judged not to fire** (README, the `work` skill, the other
  guides) are a judgement, re-checked against the finished diff in task 8 rather than
  decided here.

---

## Notes

### On deleting the test at `:489`

The team lead asked me to confirm the spec's reading against the code. I did, and **I
agree it should be deleted**, but the spec understates by one the number of properties
it holds, and one of the three is deliberately being given up rather than transferred.
That distinction belongs in task 7's audit, not in a silent deletion.

`tests/test_tracker_strict.py:489 test_strict_import_of_a_held_ticket_needs_no_start_transition`
builds `strict_node(strict=True, claim_transition="Start Progress", transitions=None)`
and asserts `tcw work tracker import` exits 0, creates one item, and leaves
`fake_.applied == []`. Three properties:

1. **A strict import of a ticket the caller already holds succeeds.** Transferred to
   criterion 25's test, written in task 2.
2. **It sends nothing to the tracker** (`fake_.applied == []`). Also criterion 25's,
   and the test there must assert on `applied` and not only on the exit code, or this
   property is lost.
3. **Both of the above hold with `transitions.start` unset.** This one is
   **deliberately gone**, because task 2 makes that node illegal under strict mode.
   The non-strict half of the property survives in
   `tests/test_tracker_import.py:227 test_import_of_a_ticket_already_held_needs_no_start_transition`,
   which is in the spec's must-not-break list and does not set `strict`.

The test's premise fails twice over, as the spec says: its node stops validating under
task 2, and its docstring's subject — "`claim_refusal` reads `transitions.start`" —
stops being true under task 4. Converting it would mean inventing a new premise for it,
which is writing a new test with an old name.

One thing the spec does not mention and task 4 must handle:
`tests/test_tracker_strict.py:471`'s docstring says "A strict `start` no longer does:
its exclusivity is `exclusive-claim-transition`'s". Task 4 makes a strict `start` do it
again, so that docstring becomes false. Its assertions are fine; only the prose is
wrong. Task 4 lists it.

### The case D8 does not cover

D8's table has two rows, both for a ticket "already the caller's". It does not say
which status the ticket is in, and the answer changes the behaviour. Measured on both
trees while writing this plan (task 3, rows 2 and 3):

- **Ticket held by the caller, on the active status.** `assert_ownership` returns early
  with `status` = the active status, so `claim_refusal` can ask its question and does:
  refused on `GLOBAL`, accepted on `SYNC`. This is the case D8's table describes, and
  criteria 23 and 25 both land here. It works.
- **Ticket held by the caller, on the backlog status.** `assert_ownership` returns early
  with `status` = the backlog status. Two things follow, neither of them in the spec:
  1. `claim_refusal`'s first branch would refuse it outright — "is assigned to you but
     is in 'To Do', not 'In Progress', so this is not a claim of it" — on the
     **directed** workflow too, where the claim is perfectly good and exits 0 today
     and pre-epic alike. That is why task 4 gives `claim_refusal` a keyword letting its
     two lifecycle callers treat an off-active ticket as a question they cannot answer
     rather than as a refusal. Without it, task 4 breaks criterion 25.
  2. Even with that, the exclusivity question is **unanswerable** from the backlog
     status: what the ticket offers from `To Do` says nothing about what it will offer
     from `In Progress`, and `assess` correctly returns `NOT_DETERMINED` rather than
     `NOT_EXCLUSIVE`. So on `GLOBAL`, a strict `start` of a ticket you hold in the
     backlog status stays **accepted** after task 4, where the pre-epic tree refused
     it. The pre-epic tree could refuse it only because its claim moved the ticket onto
     the active status first, and task 4 must not do that — re-applying an already
     applied transition is exactly what `tcw/tracker/ownership.py:117-121` exists to
     avoid, and criterion 25 forbids it.

So task 4 restores the promise on every path the spec's criteria name, and leaves one
narrow path where it remains unprovable. That is not a reason to change the design —
the only way to answer the question there is to read the project's workflow definition,
which the spec rules out as a non-goal and which is already filed as
`2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`. It is
a reason to write it down, which task 8d does.

### What I could not confirm in the spec

Three things. The first two are the ones worth acting on.

1. **The pre-epic comparison recipe does not run as described.**
   `work.tracker.exclusive-claim-transition` does not exist at `bfb2ff33` — the parser
   there rejects it as an unknown key — so the probe the spec describes, which "sets
   `exclusive-claim-transition: Start Progress`", cannot have run unchanged on that
   tree. The pre-epic refusal comes from `claim_refusal` reading `transitions.claim`,
   which is what that tree calls `transitions.start`. The regression is real and
   reproduces, and the refusal text the spec quotes is exactly right; only the recipe
   for getting there is wrong. Task 3 carries the corrected recipe. This does not
   change any design decision, but it would have cost the implementer an hour.
2. **The spec's test counts are stale.** Criterion 21 says 4413 passing against 4414
   before, measured on a throwaway copy at `f2a9523e`; the coordinating session
   measured 4404 on `main`. Task 9 replaces both with a baseline measured at the start
   of implementation and a reconciliation, which is the check those numbers were
   standing in for.
3. **D8 leaves the placement question open in a way the code closes.** The spec offers
   "`claim_refusal` gaining a second caller, or the shared check moving into
   `assert_ownership`", and says either answer satisfies the criteria. The second does
   not, quite: `assert_ownership` has a third caller in `deliver`, and three existing
   tests pin `claim_refusal`'s signature. Task 4 records the decision and the reasons.
   Not a defect in the spec — it explicitly handed the choice here — but the choice was
   narrower than it looked.

### Why this is not split into two items

The spec's last risk offers splitting finding 4 out, being a regression with its own
measurement. I recommend against it. The epic stays open until all four land, so
splitting buys no earlier closure; the three changes already sit in separate tasks with
separate tests; and tasks 2 and 4 interact over one deleted test, which is easier to
get right inside one item than across two. The thing the split would buy — a smaller
diff to review — is better bought by reviewing the combined diff deliberately, which
is what found all four of these in the first place.
