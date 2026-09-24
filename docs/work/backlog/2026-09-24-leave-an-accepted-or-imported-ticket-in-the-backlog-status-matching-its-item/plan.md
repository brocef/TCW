# Plan: leave an accepted or imported ticket in the backlog status, matching its item

Three tasks. The suite is green after each one.

## Task 1 — the claim records where it found the ticket

**Modifies** `tcw/tracker/intake.py`.

- Add `claimed_from: str = ""` to `ClaimOutcome`, commented: the status the claim
  found the ticket in, after any pre-backlog step. It is set only on a successful
  claim.
- In `claim`, on the success path, return `replace(outcome, left_status=left,
  claimed_from=ticket.status)` when `outcome.claimed`. `ticket` there is the read
  `leave_pre_backlog` returned, so after triage it holds the backlog status.

**Proves it:** a test in `tests/test_tracker_claim.py` showing that a claim from
To Do records `claimed_from == "To Do"`. A test in
`tests/test_tracker_pre_backlog.py` showing that a claim of a Triage ticket
records the backlog status, not "Triage".

## Task 2 — import puts a ticket it moved back

**Modifies** `tcw/tracker/intake.py`, `tcw/work/cli.py`; **creates**
`tests/test_tracker_import_returns.py`.

- `intake.py`: add `put_back(client, outcome) -> tuple[str, str]`, returning
  `(status the ticket ends in, reason it is not in claimed_from or "")`:
  1. `ticket = read_ticket(client, outcome.issue_id)`.
  2. `state, found = assess_move(ticket, target=outcome.claimed_from,
     expected=(), move=None)`, imported from `tcw.tracker.sync` inside the
     function, as the module already does for its other `sync` imports.
     `CURRENT` means `(ticket.status, "")`. Anything but `"apply"` means
     `(ticket.status, found)`.
  3. `client.apply_transition(ticket.issue_id, found.id)`, then read the status
     back with `_fields(client.issue(ticket.issue_id))`. If it is `claimed_from`,
     return `(status, "")`. If not, return `(status, "it is in '<status>' after
     '<name>'")`.
  4. Any `TrackerError` from steps 1–3 returns `(outcome.status, str(error))`.
- `cli.py` `_tracker_import`: after the binding is written, and only when
  `outcome.transitioned and outcome.claimed_from and not client.config.strict`
  and `claimed_from` differs from `outcome.status` (case-folded with
  `tcw.tracker.claim._normalize`), call `put_back`. Replace `outcome` with its
  `status` set to the returned status, so `_claim_summary` names where the ticket
  ended. When the reason is non-empty, print
  `warning: <KEY> stays in '<status>', although its item is in the backlog: <reason>. Move it back in the tracker, or leave it until the item starts.`
  The exit code stays 0.
- Tests, in the new file, reusing `make_node`/`run`/`fake` from
  `tests/test_tracker_import.py` by import, and `pre_backlog` setup the way
  `tests/test_tracker_pre_backlog.py` builds it:
  - AC1: on `GLOBAL`, the ticket ends in To Do, assigned to A. The writes are
    claim transition, assign, transition back. The summary names 'To Do' (AC8).
  - AC2: the same through `tcw work inbox accept` (needs `inbox-query` set).
  - AC3: a Triage ticket with `pre-backlog` ends in To Do.
  - AC4: a ticket In Progress and assigned to A gets no writes and stays.
  - AC5: on `DIRECTED`, exit 0, the item is bound, the ticket stays In Progress,
    one `warning:` line naming the key and 'In Progress' (AC8).
  - AC6: `fake.fail("POST", "/transitions", …)` armed only for the second
    transition (use `before` on the first to arm it), so exit 0, bound, warning.
  - AC7: strict mode on an exclusive workflow sends no transition back.
- Adjust existing assertions that pinned the old stderr or writes, if any fail.
  On the default `DIRECTED` workflow, the old tests now also see the warning.

**Proves it:** the new tests, plus `pytest tests/test_tracker_import.py
tests/test_tracker_pre_backlog.py tests/test_tracker_strict.py
tests/test_tracker_claim.py`.

**Mutation check:** remove the `outcome.transitioned` condition and AC4 must fail;
remove the `strict` condition and AC7 must fail.

## Task 3 — Documentation Sync

- `docs/guide/jira.md` **[Tracker-Change]**: in the claim steps (`:249-256`) and
  "What `import` creates" (`:263`), say that the ticket goes back where the claim
  found it (not under strict mode), what happens when it cannot, and the race
  limit (spec R1).
- `docs/capabilities/work/manage-external-tracker-intake/description.md`: the
  spec's capability delta (one sentence plus one accepted limit).
- `README.md` **[Public-API]**: the table row at `:514` ("starts it and assigns it
  to you"), and Example 1 at `:584`/`:586` (Jira: To Do, assigned to you; start
  then moves it to In Progress).
- `skills/work/references/commands.md` **[Skill-Driven-Component]**: the line at
  `:88` ("`import` claims it and then writes the store") gets that the ticket is
  put back where the claim found it.
- `skills/configure/references/tracker.md` **[Configuration-Key-Change]**: no key
  changes. Evaluated; no edit unless its text says import leaves the ticket
  active.
- `docs/guide/<topic>.md` **[Guide-Topic-Change]**: covered by jira.md.
- `docs/changelogs/upcoming.md` **[Any-Code-Change]** and
  `docs/release-notes/upcoming.md` **[Public-API]**: a Fixed/Changed entry each.
  The release notes include R2 (import no longer marks the ticket In Progress).

## Verification

- Bare `pytest` (how CI runs it) is green, and `tcw validate` is OK.
- Not checkable by the suite: behavior against the real Jira workflow. After the
  patch is cut, the next real `inbox accept` of a Triage ticket on this project
  should end with the ticket in To Do. Stop now exists in the TCW workflow, so it
  can. Record the observation when it happens.

## Notes

- The acceptance criteria are covered: AC1–AC8 by Task 2's tests, the Task 1
  tests support AC3, and AC9 by Verification.
