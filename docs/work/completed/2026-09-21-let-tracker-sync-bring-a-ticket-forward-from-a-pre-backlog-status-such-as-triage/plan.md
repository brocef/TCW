# Plan: Let tracker sync bring a ticket forward from a pre-backlog status such as Triage

Implements `spec.md` (commit `45dc3ecd`). Criterion numbers below are the spec's.
Line numbers were checked on 2026-09-21. Other items are editing
`tcw/tracker/` and `tcw/work/cli.py` in parallel, so re-find each anchor by the
quoted text before editing, not by the number.

## Before Task 1: the working environment

- **Blockers.** None to record. This item already blocks C4
  (`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`), recorded in
  `27b1b559`, and nothing blocks this item.
- **Worktree.** `tcw work start <slug> --worktree` puts the work in
  `.worktrees/<slug>/` on `work/<slug>`.
- **Private environment.** Other sessions are working in this repository, so do
  not re-point the shared editable install. Use a private environment instead:

  ```sh
  python -m venv --system-site-packages <scratchpad>/venv
  <scratchpad>/venv/bin/pip install -e /Users/brian/Projects/TCW/.worktrees/<slug> --no-deps
  <scratchpad>/venv/bin/pip install --ignore-installed pytest
  ```

  Run every test as `PATH="<scratchpad>/venv/bin:$PATH" pytest …`, from the
  worktree root. That is bare `pytest`, as CI runs it. The `--ignore-installed
  pytest` step matters: without it, bare `pytest` falls through to the system
  interpreter and imports the shared install instead of the worktree.
- **No real Jira.** Every test uses `tests/tracker_fake.py`'s `FakeJira`.

## Shared test fixtures (created in Task 1, extended by later tasks)

New file **`tests/test_tracker_pre_backlog.py`**. Every new test for this item
lives here, following the precedent of `tests/test_tracker_strict.py:19`, which
imports the helpers it needs from `test_tracker_sync`:

```python
from test_tracker_sync import (A, B, KEY, SENTINEL, STATUSES, TICKET_ID,
                               cli, ladder_node, make_node, record,
                               sync_link, under_way, binding_text, status,
                               transitions_fail, with_record)
```

It defines:

- **`TRIAGE`**: `tracker_fake.SYNC` plus
  `"Triage": [("11", "Accept", "To Do"), ("12", "Cancel", "Won't Do")]`.
- **`WITH_BACKLOG`**: `{**STATUSES, "backlog": "To Do"}`.
- **`set_pre_backlog(root, value)`**: loads the root's `tcw-config.yaml`, sets
  `work.tracker.statuses` to `WITH_BACKLOG` and `work.tracker.pre-backlog` to
  `value` (`None` removes the key), writes it back, then runs `git add -A` and
  `git commit -q`. This is the same shape as `set_tracker_key` in
  `tests/test_tracker_strict.py:39`.
- **`triage_node(tmp_path, monkeypatch, *, assignee=None, pre_backlog={"Triage": "Accept"})`**:
  `ladder_node(tmp_path, monkeypatch, TRIAGE, status="Triage", assignee=assignee)`,
  followed by `set_pre_backlog`.

Unit tests of `claim` reuse the pattern in `tests/test_tracker_claim.py`: a
`TrackerConfig` built directly, and `intake.claim(client,
intake.read_ticket(client, key))`. They add `statuses=WITH_BACKLOG` and
`pre_backlog={"Triage": "Accept"}`.

---

## Task 1 — Parse and validate `work.tracker.pre-backlog`

**Modifies** `tcw/store/base.py`. **Creates** `tests/test_tracker_pre_backlog.py`
(the fixtures above, plus this task's tests).

- Add `"pre-backlog"` to `TRACKER_KEYS` (`base.py:1238`).
- Add a field to `TrackerConfig`, after `statuses` (`base.py:1216`):
  `pre_backlog: dict = field(default_factory=dict)`. Its comment says it maps a
  tracker status to the transition name that takes a ticket from that status to
  `statuses.backlog`, and that no local status maps to it.
- Add `_parse_tracker_pre_backlog(raw, statuses, problems) -> dict`, next to
  `_parse_tracker_statuses` (`base.py:1559`). Absent (`None`) returns `{}`. It
  appends a problem prefixed `work.tracker.pre-backlog` for each of:
  - not a mapping: `work.tracker.pre-backlog: expected a mapping, got <type>`;
  - a key that is not a non-empty string: `work.tracker.pre-backlog: a status
    name must be a non-empty string`;
  - a value that is not a non-empty string: `work.tracker.pre-backlog.<key>:
    expected a non-empty tracker transition name, got <type>`;
  - two keys equal after normalizing: `work.tracker.pre-backlog.<key>: the same
    status as '<other>'`;
  - a key equal after normalizing to any value under `statuses`, including every
    value of a per-resolution `discarded` mapping:
    `work.tracker.pre-backlog.<key>: also mapped under work.tracker.statuses; a
    status cannot come both before the backlog and on it`;
  - a non-empty mapping while `statuses.backlog` is unset:
    `work.tracker.statuses.backlog: required when pre-backlog is set`.

  The keys and values are stored stripped.
- **Normalizing** is written inline as `" ".join(s.split()).casefold()`, with a
  comment saying it must match `tcw/tracker/claim.py`'s `_normalize`. It is not
  imported from there, because `base.py` must not load tracker code:
  `test_with_no_tracker_a_bound_item_moves_as_before_and_loads_no_tracker_code`
  (`tests/test_tracker_sync.py:633`) guards that.
- Call it in `parse_tracker_config` right after `statuses` is parsed
  (`base.py:1439`): `pre_backlog = _parse_tracker_pre_backlog(raw.get("pre-backlog"), statuses, problems)`.
  Pass `pre_backlog=pre_backlog` to the `TrackerConfig(...)` call.
- Add `pre_backlog_entry(pre_backlog: dict, status: str) -> tuple[str, str]`
  next to `transition_name` (`base.py:1642`). It returns the configured
  `(key, transition)` whose key normalizes equal to `status`, or `("", "")`.
  Every later task decides whether the step applies through this function, and
  only through it.

**Proves criterion 1.** These tests go in `tests/test_tracker_pre_backlog.py`:

- `test_a_bad_pre_backlog_fails_closed_naming_the_key`, parametrized over six
  cases: not a mapping, a blank status, a non-string transition, `Triage` beside
  `triage `, a key equal to `statuses.active`, and a key equal to a
  `discarded.wontfix` value. A seventh case sets the key without
  `statuses.backlog`. Each case asserts `config is None` and that some problem
  starts with the expected key path. This is the shape of
  `test_a_bad_block_fails_closed_naming_the_key` in
  `tests/test_tracker_sync_config.py:77`.
- `test_a_valid_pre_backlog_parses`: `config.pre_backlog == {"Triage": "Accept"}`.
  `pre_backlog_entry(config.pre_backlog, "  triage ")` returns
  `("Triage", "Accept")`, and `pre_backlog_entry(config.pre_backlog, "To Do")`
  returns `("", "")`.
- `test_validate_names_pre_backlog`: `tcw validate` on a node configured with
  `pre-backlog` and no `statuses.backlog` lists the backlog problem.
- `test_a_child_inherits_pre_backlog_entries`: `merge_tracker_blocks` of a
  parent with `{Triage: Accept}` and a child with `{Needs Info: Accept}` yields
  both entries, and it parses.

**Mutation.** Delete the check that a key is also mapped under `statuses`. The
matching parametrized case must go red.

The suite is green after this task: the key is parsed and nothing reads it yet.

---

## Task 2 — The step, called by `claim`

The riskiest change. It is placed after the key exists, and before any caller
depends on it.

**Modifies** `tcw/tracker/intake.py`, and one line of `tcw/tracker/sync.py`.
**Extends** `tests/test_tracker_pre_backlog.py`.

### 2a. `ClaimOutcome` gains `left_status`

Add `left_status: str = ""` to `ClaimOutcome` (`intake.py:431`). It holds the
configured `pre-backlog` key the ticket was taken out of, and stays empty when
no step ran.

Also add `moved_out(key: str, left_status: str) -> str`. It returns
`f"{key} was moved out of '{left_status}' to the backlog status first. "`, or
`""` when `left_status` is empty. Every caller in Tasks 3 and 4 prints the fact
through it, so the wording is written once.

### 2b. `leave_pre_backlog(client, ticket) -> tuple[TicketRead, ClaimOutcome | None, str]`

A new function in `intake.py`, directly above `claim`. It returns
`(ticket to continue with, refusal or None, left_status)`. Its docstring states
the spec's rules. Its logic, in order:

1. `key, name = pre_backlog_entry(client.config.pre_backlog, ticket.status)`. If
   `key` is empty, or `ticket.category == "done"`, or the ticket is assigned to
   another account, return `(ticket, None, "")` and send nothing. The last two
   are left for `claim`'s own rows `1a` and `1b` to refuse. So the step is
   decided by the ticket's status alone, and never by what it offers
   (criterion 11).
2. `backlog = target_status(client.config.statuses, "backlog", None)`.
   `matches` is the offered transitions whose `_normalize(t.name) ==
   _normalize(name)`, taken from `ticket.offered`, the read the caller just made.
   Refuse, sending nothing, with row **`0a`**, if any of these holds:
   - zero matches;
   - more than one match (name the sorted ids);
   - `matches[0].to_status` is not `backlog`.

   The message names `work.tracker.pre-backlog.<key>` and lists the offers as
   `'<name>' to '<status>'`, as `assess_move` does (`sync.py:243-268`).
3. Apply the transition, classifying exactly as `claim` step 2 does
   (`intake.py:531-540`):
   - `TrackerRequestInvalid` means **refused**;
   - auth, permission, rate-limit and not-found errors **propagate**;
   - any other `TrackerError` means **unknown**.
4. Re-read with `read_ticket(client, ticket.issue_id)`. If the read raises
   `TrackerError`, return row **`0-read`**, with `left_status = key` when the
   result was "applied" or "unknown". The message says `'<name>'` was sent and
   the read-back failed.
5. The fresh read is in `backlog`: return `(fresh, None, key)`.
6. The fresh read is still in the original status:
   - **`0d`** if the result was "refused": "the tracker refused '<name>'";
     conflicting;
   - **`0f`** if the result was "unknown": "could not tell whether '<name>'
     applied"; pending.

   `left_status` is `""` in both cases.
7. Anywhere else: row **`0b`**, "`<key>` did not reach '<backlog>': it is in
   '<status>'", with `left_status = key`.

The step never loops. It is called once per claim, and it has no retry.

### 2c. `claim` calls it

At the top of `claim` (`intake.py:475`), before `key, status = …`:

```python
ticket, refusal, left = leave_pre_backlog(client, ticket)
if refusal is not None:
    return replace(refusal, left_status=left)
try:
    outcome = _claim_from(client, ticket)
except TrackerError as error:
    if left:
        error.left_status = left       # read by every caller; see moved_out
    raise
return replace(outcome, left_status=left)
```

- `_claim_from` is the existing body of `claim`, renamed and otherwise unchanged.
  It is called with the **fresh** ticket, so rows `1a` and `1b`, the
  transitions offered, and where the claim lands are all decided from the read
  taken after the step (criterion 9). The "reuse the snapshot" mutation below is
  exactly the bug this call order prevents.
- `replace` is `dataclasses.replace`.
- The exception attribute is the whole mechanism for partial success
  (criterion 13). A bare `raise` keeps the exception's type, so `classify_error`
  (`sync.py:161`) still sorts it into pending or conflicting correctly.

### 2d. The hint when the setting is absent

Add `pre_backlog_hint(config, status: str, category: str) -> str` to
`intake.py`. It returns `""` when any of these holds:

- `category == "done"`;
- `pre_backlog_entry(config.pre_backlog, status)` finds an entry;
- `status` normalizes equal to any value under `config.statuses`, including
  per-resolution `discarded` values.

Otherwise it returns: `" If '<status>' is where tickets wait before your
backlog, name it and the transition out of it under work.tracker.pre-backlog."`
Append it to row `1f`'s message (`intake.py:524`).

### 2e. `deliver` treats the step's uncertain rows as pending

In `deliver` (`sync.py:607`), change
`outcome.row in ("3-read", "3f")` to
`outcome.row in ("0-read", "0f", "3-read", "3f")`.

**Proves** criteria 8, 9, 10, 11, 12, and the row-level part of 7(a) and 13.
All are unit tests in `tests/test_tracker_pre_backlog.py` against `claim`
directly. Each asserts `fake.applied` (the transition ids) and `outcome.row`:

- `test_an_unassigned_triage_ticket_is_accepted_then_claimed`: `applied == ["11", "21"]`,
  row `3a`, `left_status == "Triage"`.
- `test_a_triage_ticket_already_yours_is_accepted_then_claimed`: the same, with
  `assignee=A` (criterion 7(a) at claim level).
- `test_another_holder_or_a_resolved_ticket_sends_nothing`: two cases,
  `assignee=B` gives row `1b`, and a `Triage` ticket whose category is set to
  `done` gives row `1a`. Both have `fake.writes() == []`. (For the resolved
  case, the test sets `tracker_fake.CATEGORY` through `monkeypatch.setitem`.)
- `test_someone_taking_it_between_the_hops_is_refused_on_the_fresh_read`:
  `fake.before("GET", "/rest/api/3/issue/10052", lambda: setattr(fake.tickets["10052"], "assignee", B))`
  is registered after the initial read, so it fires on the re-read. The result
  is row `1b` naming Bob, `applied == ["11"]`, `left_status == "Triage"`. A
  second case resolves the ticket in the same hook, and the result is row `1a`.
- `test_a_misconfigured_step_sends_nothing`: three cases, a name not offered,
  `Accept` leading to `Won't Do`, and `Accept` offered twice. Each gives row
  `0a`, a message containing `work.tracker.pre-backlog.Triage`, and
  `fake.writes() == []`. The twice case adds `("13", "Accept", "To Do")` to
  `Triage` and names `11, 13`.
- `test_the_step_is_chosen_by_status_not_by_name`: the ticket is in `To Do`,
  and the workflow's `To Do` also offers `("11", "Accept", "To Do Later")`.
  `"11"` is not in `applied`. With the key written `triage` and the ticket in
  `Triage`, the step still runs.
- `test_failures_keep_pending_and_conflicting_apart`, four cases:
  - `fake.fail("POST", "/transitions", TrackerUnavailable(...))`, not applied:
    row `0f`;
  - the same with `apply_first=True`: the claim proceeds to row `3a`;
  - `Accept` applies, then
    `fake.fail("GET", "/rest/api/3/issue/10052", TrackerUnavailable(...))` on
    the re-read: row `0-read` with `left_status == "Triage"`;
  - a `before` hook on the re-read sets the status to `In Review`: row `0b`.
- `test_a_claim_that_raises_after_the_step_carries_left_status`:
  `Accept` applies, then
  `fake.fail("POST", "/transitions", TrackerRateLimited("…"))` is registered
  after the first POST, so it hits `Start Progress`. The test asserts
  `pytest.raises(TrackerRateLimited)` and `error.left_status == "Triage"`.
- `test_row_1f_names_pre_backlog_only_for_an_unmapped_status`: with
  `pre-backlog` unset and an unassigned `Triage` ticket, row `1f` contains
  `work.tracker.pre-backlog`. For an unassigned `To Do` ticket in a workflow
  whose `To Do` offers nothing, the message does not contain it.

**Mutations.** Each of these must turn the named test red:

- Remove the `leave_pre_backlog` call: the first two tests.
- Pass the original `ticket` to `_claim_from` instead of the fresh one: the
  between-the-hops test.
- Decide step 1 by `any(t.name == name for t in ticket.offered)` instead of by
  status: the status-not-name test.
- Drop `"0f"` from `deliver`'s pending set: Task 3's pending test.

The suite is green: with `pre-backlog` unset, `leave_pre_backlog` returns at
step 1 and sends nothing. The only change existing tests can see is the
appended hint, and the one existing assertion on that message
(`tests/test_tracker_sync.py:2120`, `"does not offer 'Start Progress'" in err`)
still holds.

---

## Task 3 — `deliver`: link, sync, start, and the owed moves

**Modifies** `tcw/tracker/sync.py`. **Extends** `tests/test_tracker_pre_backlog.py`.

In `deliver`'s claim branch (`sync.py:601-640`):

- `except TrackerError as error:` around `claim(...)` becomes
  `finish(classify_error(error), moved_out(bound.ticket_key, getattr(error, "left_status", "")) + str(error))`.
- The not-claimed return prefixes `moved_out(outcome.key, outcome.left_status)`
  to `outcome.message + detail + where`.
- `claimed_message = moved_out(outcome.key, outcome.left_status) + outcome.message`.
  `_deliver_after` already prints it as `→ …` (`cli.py:1162-1163`).
- The "claimed …, but it is in …, not …" refusal (`sync.py:631-634`) appends
  `pre_backlog_hint(config, outcome.status, "")`, only when
  `not outcome.transitioned and not outcome.left_status`. The status category is
  not known at that point, but that does no harm: row `1e` is never a resolved
  ticket, because row `1a` refuses those first.

Nothing else in `deliver` changes. The step lives inside `claim`, so it runs
only where `deliver` already claims. That is inside `if owed:`, past the
discard and `check_only` exits (`sync.py:546-557`). That placement is what
delivers criterion 15(a)-(d) with no new condition.

**Proves** criteria 2, 3, 4, 5 (not strict), 14 (the `deliver` rows), 15(a)-(d),
and the `deliver` halves of 13 and 16. All are CLI tests through `cli(...)` on
`triage_node`:

- `test_link_sync_status_accepts_then_claims`, parametrized with `assignee` set
  to `None` and to `A`, the reporter's case. For each: `sync_link` exits 0, the
  ticket ends `In Progress` assigned to A, `applied == ["11", "21"]`, and stderr
  contains `moved out of 'Triage'` (criteria 2 and 3).
- `test_sync_finishes_an_owed_catch_up_from_triage`: `transitions_fail(fake_, 1)`
  makes the link's delivery record a pending catch-up. The ticket is still in
  `Triage`. Restore the fake, then `tcw work tracker sync <slug>` exits 0 and
  `applied == ["11", "21"]`. On an item in `review` with
  `STRICT_LADDER + Triage`, the ticket ends `In Review` (criterion 4).
- `test_start_accepts_then_claims`: a backlog item bound with plain `tracker
  link`, then `tcw work start` exits 0 and the ticket ends `In Progress`
  (criterion 5, not strict).
- `test_a_claim_refused_after_the_step_is_resumed_by_sync`: the workflow's
  `To Do` offers nothing for one run. Swap the workflow entry in the test, then
  put it back. The result is exit 1, the ticket in `To Do`, stderr naming
  `moved out of 'Triage'`, and the record's `state` is `conflicting`. After
  restoring, `sync` exits 0 and `applied.count("11") == 1` (criterion 14,
  `deliver` rows).
- `test_a_pending_step_is_recorded_pending`:
  `fake.fail("POST", "/transitions", TrackerUnavailable(...))` makes
  `record(root, slug)["state"] == "pending"` (criterion 12 at the `deliver`
  level).
- `test_a_raised_claim_after_the_step_still_reports_the_move`: the first POST
  succeeds, and the second raises `TrackerRateLimited`. The link's stderr
  contains `moved out of 'Triage'` (criterion 13, `deliver`).
- `test_moves_with_no_claim_owed_never_accept`: the item is started while the
  ticket is in `In Progress`, then the fake puts the ticket in `Triage`.
  `submit`, `rework` and `complete` each apply no `"11"`. Run it once with no
  record, and once with a record `{"state": "pending", "move": "submit", …}`
  written by the existing `with_record` helper (`tests/test_tracker_sync.py:692`)
  (criterion 15(a)).
- `test_a_submit_that_owes_the_claim_accepts_then_claims`, two cases: a binding
  with `catch-up: true`, and a record whose `move` is `start`. For each,
  `tcw work submit` applies `"11"` then `"21"` (criterion 15(b)).
- `test_a_discard_never_accepts`: `tcw work complete <slug> --resolution wontfix
  --confirm` on a bound backlog item whose ticket is in `Triage` applies `["12"]`
  (Cancel) or nothing, and never `"11"` (criterion 15(c)).
- `test_a_part_bound_report_only_sync_sends_nothing`: a `--part` binding with a
  catch-up owed. `tcw work tracker sync` applies nothing (criterion 15(d)).
- `test_without_the_setting_the_reporters_case_names_it`: `triage_node(...,
  assignee=A, pre_backlog=None)`. `sync_link` exits 1, `applied == []`, and the
  recorded reason contains `work.tracker.pre-backlog` (criterion 16, first
  bullet).
- `test_a_claim_landing_off_the_ladder_does_not_name_pre_backlog`: the workflow
  from `test_a_claim_landing_off_the_ladder_stops_the_catch_up`
  (`tests/test_tracker_sync.py:1612`). The reason does not contain
  `pre-backlog` (criterion 16, third bullet).

**Mutation.** Move the hint condition from `not outcome.transitioned` to always
true. The off-the-ladder test must go red.

---

## Task 4 — Strict start, import, inbox accept, and `show`

**Modifies** `tcw/work/cli.py`. **Extends** `tests/test_tracker_pre_backlog.py`.

- **`_strict_claim`** (`cli.py:393`):
  - on `TrackerError`, prefix `moved_out(key, getattr(error, "left_status", ""))`
    to the "could not answer" text;
  - on a refusal, prefix `moved_out(outcome.key, outcome.left_status)` to
    `outcome.message`, and when `outcome.left_status` is set, append "Run `tcw
    work start <slug>` again to finish the claim." This is needed because a
    strict refusal writes no sync record, so `sync` cannot resume it;
  - on success with `outcome.left_status`, print
    `→ {moved_out(...)}` to stderr before returning `(None, True)`.
- **`_tracker_import`** (`cli.py:2375`):
  - in the `except (TrackerError, …)` branch (`cli.py:2432-2437`), prefix
    `moved_out(ticket.key, getattr(e, "left_status", ""))` when `ticket` is not
    `None`;
  - `_print_refusal(label, outcome)` gains the prefix through the message;
  - after the success summary (`cli.py:2479`), print `→ {moved_out(...)}` when
    `outcome.left_status` is set;
  - when `outcome.row == "1e"` and
    `(hint := pre_backlog_hint(client.config, outcome.status, ""))`, print
    `warning: {outcome.key} stays in '{outcome.status}'.{hint}`.

  The already-bound short-circuit (`cli.py:2407-2430`) comes before `claim` and
  is not touched.
- **`_print_ticket`** (`cli.py:2309`): after the `note:` line, if
  `pre_backlog_entry(client.config.pre_backlog, status)` finds `(key, name)`,
  print `note: a claim first takes it out of '{key}' through '{name}'.`

**Proves** criteria 5 (strict), 6, 7, 14 (strict and import rows), 15(e)-(f), and
the import halves of 13 and 16:

- `test_strict_start_accepts_then_claims`: uses `strict_node` from
  `tests/test_tracker_strict.py:32`, with `WITH_BACKLOG` plus `discarded`, and
  `pre-backlog` set. `tcw work start` exits 0 and the ticket ends `In Progress`.
- `test_strict_start_refused_after_the_step_is_retried_by_start`: `To Do`
  offers nothing for one run. The result is exit 1, the item still `backlog`,
  `record(...) is None`, stderr naming `moved out of 'Triage'` and `tcw work
  start`. After restoring, `tcw work start` exits 0 and
  `applied.count("11") == 1`.
- `test_import_and_inbox_accept_accept_then_claim`: parametrized over
  `tracker import KEY` and `inbox accept KEY` (the node sets `inbox-query`).
  Each exits 0, creates one bound backlog item, gives `applied == ["11", "21"]`,
  and prints `moved out of 'Triage'` on stderr (criterion 6).
- `test_import_of_a_triage_ticket_already_yours`: with the key set,
  `applied == ["11", "21"]` (7(a)). With it unset, the result is row `1e`, the
  item is created, the ticket stays `Triage`, `applied == []`, and stderr has a
  `warning:` line containing `work.tracker.pre-backlog` (7(b)).
- `test_import_refused_after_the_step_is_retried_by_import`: the same shape as
  the strict retry. The re-run of `tracker import KEY` finishes it with one
  `"11"` in total.
- `test_import_that_raises_after_the_step_reports_the_move`: `TrackerRateLimited`
  on the second POST. Exit 1, and stderr contains `moved out of 'Triage'`
  (criterion 13).
- `test_import_without_the_setting_names_it`: an unassigned `Triage` ticket
  with the key unset. The refusal contains `work.tracker.pre-backlog` and
  `applied == []` (criterion 16, second bullet).
- `test_tracker_claim_moves_nothing`: `tcw work tracker claim <slug>` on a bound
  item whose unassigned ticket is in `Triage`. Exit 0, the ticket assigned to A
  and still in `Triage`, and `applied == []` (criterion 15(e)).
- `test_import_of_an_already_bound_ticket_moves_nothing`: the ticket is bound
  by `tracker link` and unassigned in `Triage`. `tracker import KEY` exits 1
  with the existing "already linked" message and `applied == []`
  (criterion 15(f)).
- `test_show_notes_the_step`: `tcw work tracker show KEY` on a `Triage` ticket
  prints a `note:` line containing `Accept` (criterion 16, last sentence).

**Mutation.** Remove the strict "run start again" sentence. The strict retry
test must go red on its stderr assertion.

---

## Task 5 — Capability deltas

**Creates** `docs/work/backlog/<slug>/capabilities.yaml` (after start it lives
in `docs/work/active/<slug>/`):

```yaml
changed:
    - work/synchronize-external-tracker-work
    - work/manage-external-tracker-intake
    - work/inspect-external-tracker-work
```

**Modifies** three capability descriptions:

- `docs/capabilities/work/synchronize-external-tracker-work/description.md`:
  one paragraph on start, catch-up and sync taking a ticket out of a
  `pre-backlog` status before the claim.
- `docs/capabilities/work/manage-external-tracker-intake/description.md`: the
  claim paragraph says import and inbox accept first take a ticket out of a
  configured `pre-backlog` status.
- `docs/capabilities/work/inspect-external-tracker-work/description.md`: the
  configuration list gains `pre-backlog`, and `show` gains its note.

**Proves.** `tcw capabilities check` prints `capabilities OK`.

---

## Task 6 — Documentation Sync

One pass over the finished diff. Every entry was evaluated. Each one that fires
is listed with its file and its change:

| Entry | Fires? | Change |
| --- | --- | --- |
| `docs/guide/jira.md` [Tracker-Change] | **Yes**: a new `work.tracker` key, and what `start`, `link --sync-status`, `sync`, `import` and `inbox accept` do to a bound ticket | Add `pre-backlog` to the example block (`jira.md:44-60`) and to the key table (`:78` area). Add a section "Tickets waiting in triage" after "Where a created ticket lands" (`:407`) covering: what the key maps; that it needs `statuses.backlog`; that the transition must lead there; which commands use it and which do not (`tracker claim`, `create`, `submit`/`rework`/`complete` with no claim owed, discards); what happens if the claim fails after the move, and how each command resumes; the hint when it is unset |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | **Yes**: `docs/guide/work.md:225-227` describes what `inbox accept <KEY>` does | Extend its comment: with `work.tracker.pre-backlog`, accepting first takes the ticket out of triage |
| `skills/configure/references/tracker.md` [Configuration-Key-Change] | **Yes**: a new key | Add `pre-backlog` to the key list (`:33`), and a short subsection after the `statuses.backlog` paragraph (`:144`) with the example and the four validation rules |
| `skills/work/SKILL.md` and references [Skill-Driven-Component] | **Yes** | `skills/work/references/commands.md`: the import and inbox-accept rows (`:6`) and the sync notes (`:156`, `:196`) say a `pre-backlog` status is left first. The refusal table (`:244`) gains the `0a`/`0b` refusals naming `work.tracker.pre-backlog.<status>`. `skills/commands-process-inbox/SKILL.md:20-24`: accepting a ticket may also move it out of triage, so the confirmation asked of the user should say so. `skills/work/SKILL.md` itself names no tracker keys; re-read it, and change it only if a sentence contradicts the above |
| `README.md` [Public-API] | **Yes**: user-facing behaviour of `inbox accept`/`import`/`sync` | One sentence in the inbox paragraph (`README.md:553`), plus `pre-backlog` in the tracker table row for `start`/`import` if one names claim behaviour (`:513-515`) |
| `docs/release-notes/upcoming.md` [Public-API] | **Yes** | Plain-language entry: tickets waiting in Triage can now be linked, synced, started and accepted once `work.tracker.pre-backlog` names the status and its way out; without it the refusal says how. Credit the proposit-app report |
| `docs/changelogs/upcoming.md` [Any-Code-Change] | **Yes** | **Added:** `work.tracker.pre-backlog`, `TrackerConfig.pre_backlog`, `pre_backlog_entry`, `intake.leave_pre_backlog`, `ClaimOutcome.left_status`, rows `0a`/`0b`/`0d`/`0f`/`0-read`. **Changed:** row `1f`'s and `deliver`'s off-ladder refusals carry the hint; `deliver` treats `0-read`/`0f` as pending. **Internal:** the new test file |

**Proves.** `tcw validate` passes on this repository, including its link
check. `grep -l pre-backlog` over the files named above lists every one of
them.

---

## Task 7 — Full suite and closeout checks

- `PATH="<scratchpad>/venv/bin:$PATH" pytest` from the worktree root (bare, as
  CI runs it). This is criterion 17.
- `tcw validate` and `tcw capabilities check`.
- Record in `outcome.md` each mutation from Tasks 1-4, with the test that went
  red and why.
- Before `tcw work complete`, remove the private environment. Nothing re-points
  the shared install, so there is nothing to restore; confirm with
  `pip show tcw` that it still points at `/Users/brian/Projects/TCW`.
- **No GitHub issue** is attached to this item, so there is nothing to close.
  v2.5.1 waits for the five proposit-app items to be accepted, and the version
  cut is batched across them, not done here.

## Coverage check (every criterion has a task; every task traces to one)

| Criterion | Task |
| --- | --- |
| 1 validation | 1 |
| 2, 3 link --sync-status | 3 |
| 4 sync | 3 |
| 5 start / strict start | 3 / 4 |
| 6 import, inbox accept | 4 |
| 7 import of a ticket already yours | 2 (row), 4 (CLI) |
| 8 another holder, resolved | 2 |
| 9 taken in between | 2 |
| 10 misconfigured | 2 |
| 11 status not name | 2 |
| 12 pending vs conflicting | 2, 3 |
| 13 partial success reported | 2 (attribute), 3, 4 |
| 14 resuming | 3 (`deliver`), 4 (strict, import) |
| 15(a)-(d) only where a claim is made | 3 |
| 15(e)-(f) | 4 |
| 16 without the setting; show note | 2 (row 1f), 3, 4 |
| 17 full suite | 7 |

Task 5 traces to the spec's Capability changes. Task 6 traces to the
documentation entries.

## Verification (what the suite cannot check)

- **A real Jira.** The fake proves the order of calls, not Jira's behaviour.
  Once the item is complete and before v2.5.1 is cut, the requester, or
  proposit-app's session, should link one real Triage ticket in a throwaway
  project with `pre-backlog: {Triage: Accept}`. The expected result is Accept,
  then Start Progress, with the ticket in In Progress. That needs a person with
  credentials, so no agent in this run does it.
- **Jira's "uncertain response".** The fake's `fail(..., apply_first=True)`
  stands in for a request that landed but whose reply was lost. Whether real
  Jira produces that shape on a transition is not known. The read-back rule is
  written to be correct either way.
- **Reading the messages.** The tests pin substrings. Whether the wording reads
  well in context is for the verify stage, by a person.

## Notes

- **Abstraction litmus test: passes.** The only new operation is "apply a named
  transition out of a named status, then confirm the landing status". That is
  status, transition and read, which any tracker with a workflow can do. It sits
  in `tcw/tracker/intake.py` beside the claim, not in the filesystem store.
- **Harness: unaffected.** Everything is in the CLI. The skill edits in Task 6
  only describe it.
- **C4 carries this forward.** Its plan (amended in `27b1b559`) keeps calling
  `leave_pre_backlog` from `deliver`'s ownership-then-`assess_move` path,
  regardless of `owed`, and from `import`. The tests in Task 3 are what go red
  if it does not, and when C4 retires `--sync-status` they move to the
  `link`, then `claim`, then `sync` flow.
- The stage asks for `plan.md` to be committed on its own before `tcw work
  start`. That is left to the team lead, whose instructions for this run forbid
  committing.
