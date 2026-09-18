# Plan: Let sync move a ticket either way to match its work item

Five code tasks, then one documentation block, then the capability declaration.
Tasks 1 and 2 are the two halves of the change and are ordered so the suite is
green at each commit boundary: task 1 removes the claim key (a field), task 2
changes what `sync` does with it gone.

Every new assertion is mutation-checked before it is trusted: after writing it,
break the line of production code it claims to observe, run just that test,
confirm it goes red, read why, and restore. Each task names what to break.

## Task 1 — Remove `claim` from the sync record

**Modify**

- `tcw/store/base.py` — drop `"claim"` from `SYNC_FIELDS` (`:423`) and delete the
  `if record["claim"] not in ("done", "owed")` check and its message
  (`:442-443`).
- `tcw/work/projection.py` — delete the `"claim"` property (`:125`) and its entry
  in `"required"` (`:129`).
- `tcw/work/cli.py` — delete the `owed` suffix in `tcw work show` (`:216-218`),
  so the line is `tracker sync: {state} after {move} ({at}): {reason}`; delete
  `"claim": "owed",` from the `link --sync-status` record (`:2528`) and the
  comment above it explaining why the reason has no full stop (`:2529-2530`),
  which only existed for the suffix being deleted; fix the surrounding prose
  comments at `:2445` and `:2494` that describe the claim as recorded.
- `tcw/tracker/sync.py` — delete `"claim": ...` from `finish` (`:338`) and from
  `record_unsent` (`:623-624`).
- `web/client/src/model/types.ts` — delete `claim: "done" | "owed"` (`:33`).

**Tests**

- `tests/test_tracker_sync.py` — remove `"claim"` from `RECORD` (`:36`) and drop
  the `{**RECORD, "claim": "maybe"}` case and its `"claim"` id from the
  malformed-record parametrization (`:58`, `:61`). Add
  `test_a_record_on_disk_that_still_names_a_claim_is_read_and_ignored`: write a
  `tracker.yaml` whose `sync` record has all five fields plus `claim: owed`,
  then assert `classify_binding` reports no problem, `tcw work show <slug>`
  exits 0, prints the ticket key and the record's state, move and reason, and
  does not print "owed", and `tcw work show <slug> --json` validates against
  `WORK_ITEM_SCHEMA` with no `claim` key in the projected record. (Criteria 10,
  11.)
- `tests/test_tracker_sync.py` — add
  `test_no_command_writes_a_claim_into_the_record`: after a `start` with the
  tracker down, a `submit` with it down, and a `link --sync-status`, assert
  `set(record(...)) == {"state", "move", "since", "reason", "at"}` in each case.
  (Criterion 9.)
- `tests/test_tracker_strict.py:765` and `web/client/src/ui/content-views.test.tsx:208`
  — remove the `claim` key from the fixture records they build.

**Proves it**: `pytest tests/test_tracker_sync.py tests/test_tracker_strict.py`
and `pnpm vitest run` are green with no `claim` key anywhere in a sync record.

**Mutation check**: put `"claim": "owed"` back into `finish`'s record and confirm
`test_no_command_writes_a_claim_into_the_record` fails naming the extra key; put
the `claim` property back into the projection schema's `required` list and
confirm the stale-key test fails on schema validation.

**Note**: `owed` still works at the end of this task — it falls back to
`starting` alone, because `record["claim"]` is gone. That changes behaviour for
a recorded owed claim, which is what task 2 settles; the two tests the epic named
are rewritten there, so **task 1 and task 2 are one commit boundary, not two**,
and are committed together once both are done.

## Task 2 — Replace `owed` with `starting or catch_up`, and let `sync` reconcile

**Modify** `tcw/tracker/sync.py` only.

- The module docstring (`:11-18`): rewrite the paragraph that begins "**TCW never
  follows the tracker and never pulls a ticket back**" to state the new rule —
  the item's status is what the ticket is moved to, in either direction, when no
  undelivered move is recorded and the binding is not for a named part; and the
  three things that still stop a move (another account holds it, nobody holds it
  and this is not a discard, the ticket is resolved).
- `deliver` (`:276-277`): delete the `check_only` parameter and compute it as a
  local immediately after `record` and `bound` are in hand:
  `check_only = move is None and record is None and bound.part != "default"`,
  with the comment the spec gives for each of the three terms.
- `:293`: `owed = starting or bound.catch_up`.
- `:306-307`: `stale = bound.sync is not None and local not in RESOLVED_STATUSES`.
- `:342`: `drop_record = bound.sync is not None`.
- `assess_move`'s unassigned message (`:206-208`): "Take it first — `tcw work
  start` claims a bound ticket —" becomes "Take it with `tcw work tracker
  claim`,", so a user whose claim never landed is sent to the verb that exists
  for it rather than to a lifecycle command.
- `Outcome` (`:133-137`): add `note: str = ""`, documented as "a warning the
  caller prints; set when the move made was backwards".
- `deliver`, after the ticket read and before `assess_move`: set a `backwards`
  note when `lowest_rung(config.statuses, ticket.status)` is not `None` and is
  greater than `_RUNG_ORDER.get(local, that rung)`, naming the ticket, the status
  it is in and `target`. `finish` passes it into the `Outcome` only for `CURRENT`,
  so a refused move never claims to have moved anything.

**Modify** `tcw/work/cli.py`: drop `check_only=not usable` and the now-unused
`usable` local from the sync command (`:2837`, `:2845`); print `outcome.note`
beside `outcome.claimed` in both places that print the latter (`:1066-1068` and
`:2861` area, and the `link` path at `:2560`).

**Tests** — `tests/test_tracker_sync.py`, new section "reconciling a ticket to
its item". `deliver_now` (`:240-250`) loses its `check_only` argument.

- `test_sync_brings_a_ticket_someone_moved_on_back_to_its_item` — active item, no
  record, ticket moved by hand to "In Review": sync exits 0 and the ticket is "In
  Progress". (Criterion 1.)
- `test_sync_says_when_it_moved_a_ticket_backwards` — the same run prints the
  ticket key, "In Review" and "In Progress". (Criterion 2.)
- `test_sync_brings_a_ticket_someone_moved_back_forward_again` — item in `review`
  via `moved_to`, ticket in "In Progress", no record: sync exits 0 and the ticket
  is "In Review". (Criterion 3.)
- `test_sync_moves_a_ticket_from_a_status_the_project_maps_to_nothing` — ticket
  in "To Do": sync exits 0 and the ticket reaches the item's mapped status.
  (Criterion 4.)
- `test_sync_never_moves_a_ticket_somebody_else_holds` — ticket in "In Review"
  assigned to Bob: sync exits 1, names Bob, ticket unmoved. (Criterion 5.)
- `test_sync_never_reopens_a_resolved_ticket` — ticket in "Done": sync exits 1,
  says already resolved, ticket unmoved. (Criterion 6.)
- `test_sync_does_not_reconcile_a_ticket_bound_as_a_named_part` — item bound with
  `--part api`, no other item bound here, ticket out of step: sync exits 1 and
  the ticket is unmoved. (Criterion 8.)
- Rewrite `test_open_work_with_no_mapping_keeps_its_owed_claim` (`:983`) as
  `test_a_start_whose_claim_failed_is_not_claimed_by_a_later_command`: the ticket
  stays unassigned, the record is dropped because nothing is mapped, and
  `tcw work tracker claim <slug>` then assigns it. (Criteria 12, 13.)
- Rewrite `test_an_owed_claim_without_sync_status_is_followed_by_one_transition_only`
  (`:1710`) as `test_sync_does_not_claim_a_ticket_a_failed_start_never_took`:
  nothing is applied, the run exits 1, and the message names `tcw work tracker
  claim`. (Criterion 12.)
- Check every other test in `tests/test_tracker_sync.py`,
  `tests/test_tracker_strict.py` and `tests/test_tracker_hold.py` that asserts a
  refusal `sync` used to make, and rewrite the ones this change turns into a
  move. `tests/test_tracker_strict.py:740-756` is known to be one: it starts with
  a failed claim and expects `sync` to retry it.
- Criteria 7 and 14 are already covered by existing tests
  (`tests/test_tracker_hold.py`, and the `--sync-status` catch-up tests around
  `tests/test_tracker_sync.py:1600-1700`); confirm they still pass unchanged
  rather than writing new ones.

**Proves it**: the three criteria groups above, plus the full suite.

**Mutation checks**, one per new assertion:

- restore the `check_only` refusal branch at the end of `deliver` → the four
  reconcile tests must fail on the ticket not having moved;
- make the part rule `bound.part == "default"` → the named-part test must fail
  because the ticket moved;
- make `owed = starting or bound.catch_up or True` → the two rewritten claim
  tests must fail because the ticket got claimed;
- drop the `note` from `finish` → the warning test must fail on the missing line;
- remove `ticket.category == "done"` from `assess_move` → the resolved test must
  fail.

## Task 3 — `deliver`'s callers and the `--part` limit in the guide's terms

`tcw/tracker/sync.py`'s `binding_refusal` and `authorize` (`:637`, `:668`) read
the record but never its `claim`; confirm by reading them that neither needs a
change, and say so here rather than leaving it unstated. `tcw/serve/` has no
delivery path (`tcw/serve/__init__.py:905` calls `work.start` on the store), so
nothing there changes.

**Proves it**: `grep -rn 'claim' tcw/ web/client/src/ | grep -v transitions`
returns only the ownership verb, the `transitions.claim` config key (the third
child's subject) and prose.

## Task 4 — Run the full suite

`pytest` from the worktree root with output redirected to a file, and
`pnpm vitest run` for the web client. Read the last lines of the file, not the
exit code. Any failure is fixed before the code commit, not after.

## Task 5 — Commit the code

One commit for tasks 1–3 together, since task 1 alone leaves `owed` half
replaced. Message: what changed and why, in plain language, no co-authoring line
and no session trailer.

## Documentation Sync

One pass over the finished diff, after the code commit, committed on its own.

- **`docs/guide/jira.md` — [Tracker-Change], fires.** The sync section
  (`:500-540`) describes the record as naming an owed claim and describes `sync`
  as checking an item without moving its ticket. Rewrite for: the item is the
  source of truth; a ticket ahead is brought back and one behind brought forward;
  the warning printed for a backwards move; the three things that still stop a
  move; a claim that failed at `start` is taken with `tcw work tracker claim`;
  and the limit on a binding with a named part.
- **`README.md` — [Public-API], fires.** The tracker section's summary of what
  `sync` does changes; check for the "never pulls a ticket back" phrasing and any
  mention of an owed claim.
- **`docs/release-notes/upcoming.md` — [Public-API], fires.** Plain language: what
  `sync` now does, that a failed claim is taken with `tcw work tracker claim`,
  and that `tracker.yaml` files carrying the old key keep working.
- **`docs/changelogs/upcoming.md` — [Any-Code-Change], fires.** Changed and
  Removed entries.
- **`skills/work/SKILL.md` and `skills/work/references/commands.md` —
  [Skill-Driven-Component], fires.** `commands.md:159` explains `claim: owed` in
  the record and `:177` explains what `--sync-status` records; both change.
- **`skills/configure/references/<document>.md` — [Configuration-Key-Change], does
  not fire.** No key in `tcw-config.yaml`, a component config file or
  `docs/work/dod.yaml` changes; `claim` here is a field of the `tracker.yaml`
  binding sidecar, which is written by TCW and not configured by a user.
- **`docs/capabilities/work/synchronize-external-tracker-work/description.md`** —
  rewrite the sentences the spec's capability section names. Also correct
  `docs/capabilities/work/view-the-board/description.md:19`, which claims a board
  row shows a claim still owed; it never did.
- **`docs/capabilities/work/require-tracker-backed-work/description.md:25-26`** —
  the claim-retry sentence.

## Capabilities

`capabilities.yaml` in the item folder, declaring
`changed: [work/synchronize-external-tracker-work,
work/require-tracker-backed-work]`. No new capability, and nothing is set to
`Supported` here — that is closeout's, which the requester runs.

## Verification

What the suite cannot check, to be done by hand and written into `outcome.md`:

- **The warning reads as a warning.** Run the backwards-move case through the
  real CLI and read the line as a user would, rather than asserting a substring.
- **The refusal sends people somewhere that works.** Follow the message from a
  failed `start` — `tcw work tracker claim <slug>`, then `tcw work tracker sync
  <slug>` — end to end against the fake tracker and confirm the ticket ends up
  where the item says.
- **An old `tracker.yaml` survives a round trip.** Take a file carrying
  `claim: owed`, run `show`, `list`, a `sync` that writes a new record, and
  confirm the stale key is gone afterwards and nothing was lost.
- **The third child's edits and this one's do not overlap.** Before the code
  commit, `git diff main --stat` and confirm this item's only change to
  `tcw/store/base.py` is `SYNC_FIELDS` and `_sync_record`.

## Notes

- The work is done in `.worktrees/2026-09-16-let-sync-move-a-ticket-either-way-to-match-its-work-item`
  against a private virtual environment at `/tmp/c2-venv`, so the repository's
  shared editable install is left pointing where it was for the agent working the
  third child.
- `tests/fixtures/prompt_fallback/capture.py` re-baselines its fixture from
  whatever `tcw` is on PATH and is not run by this work.
- Because this item edits `tcw/`, every lifecycle transition from here on is made
  by editing `docs/work/` directly rather than through the `tcw` CLI, as this
  repository's guide requires. `tcw work stage gate` and `tcw work stage prompt`
  are still used: they only print.
