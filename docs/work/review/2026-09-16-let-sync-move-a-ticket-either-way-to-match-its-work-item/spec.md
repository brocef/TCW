# Spec: Let sync move a ticket either way to match its work item

## Capability changes

Planned deltas only; no ledger record is written here.

- **changed** `work/synchronize-external-tracker-work` (`cap-207f2c`) — three
  sentences of its description stop being true: "It never follows Jira and never
  pulls a ticket back", "Forward only, never on a ticket already resolved", and
  "`sync <slug>` checks such an item without moving its ticket". A fourth, "`tcw
  work tracker sync <slug>` or `--all` retries it, including a claim that did not
  succeed at start", stops being true for the claim.
- **changed** `work/require-tracker-backed-work` — its line "A claim retried
  later — by the next lifecycle command or `tcw work tracker sync` — is checked
  the same way, and stays owed while the check fails" describes the retry this
  item removes.

No new capability. Nothing is flipped to `Supported` here; that is closeout's.

## Problem

`tcw work tracker sync` cannot make a bound ticket match its work item. Two
separate rules stop it, and the second one is a piece of state that should not
exist.

**One — a sync with nothing recorded moves nothing.** The command calls
`deliver(..., move=None, previous_status=None, check_only=not usable)`
(`tcw/work/cli.py:2844-2845`), where `usable` is "there is a readable `sync`
record" (`:2837`). With no usable record it is check-only, and `deliver` ends at
a refusal — `"{key} is in '{status}', not '{target}', and no undelivered change
is recorded, so it is not moved."` (`tcw/tracker/sync.py:580-584`). So a ticket
somebody moved by hand, in either direction, is reported and left alone. The
module says as much in its own first paragraphs: "**TCW never follows the tracker
and never pulls a ticket back**" (`tcw/tracker/sync.py:11`).

This is the rule GitHub #42 runs into — linking an item that is already under way
strands its ticket, because `link` cannot move it and `sync` reads the gap as
drift it must not undo.

**Two — the claim lives in the `sync` record.** `SYNC_FIELDS`
(`tcw/store/base.py:423`) carries a `claim` field, validated to `done` or `owed`
(`:442-443`), mirrored in the projection schema (`tcw/work/projection.py:125`,
`:129`) and in the web client's type (`web/client/src/model/types.ts:33`), and
printed by `tcw work show` as "; the claim is still owed"
(`tcw/work/cli.py:216`). It is written in three places: `deliver`'s `finish`
(`tcw/tracker/sync.py:338`), `record_unsent` (`:623`), and `link --sync-status`
(`tcw/work/cli.py:2528`).

What it actually decides is `owed` (`tcw/tracker/sync.py:293`), and `owed`
decides which tickets `deliver` claims: an item whose `start` never reached the
tracker has its ticket claimed by whatever command runs next, including `sync`.
That is the coupling the parent epic exists to take apart. Claiming now has its
own verb — `tcw work tracker claim`, on `tcw/tracker/ownership.py`, landed by the
first child — so a claim that did not happen has somewhere to go that is not a
side effect of an unrelated command.

The key is also the one thing in this module that is believed rather than read.
Its own docstring says "Every decision is taken from what the tracker says, read
fresh; the binding is never proof of anything" (`tcw/tracker/sync.py:19-20`).

**Every fact the epic's spec states about this code was checked**, and all of
them hold: `finish` writes `"claim": "owed"` at `:338`; `record_unsent` at
`:623`; neither writes `catch-up`, which only `link --sync-status` writes
(`tcw/work/cli.py:2494`, `:2528`); the two pinned tests are at
`tests/test_tracker_sync.py:983` and `:1710`; and `deliver` reconciles a stale
`owed` against the ticket's real assignee at `tcw/tracker/sync.py:456-461` and
`:496-517`. The epic cites `:504-517` for the second; the block begins at `:496`.

## Goals

1. `tcw work tracker sync <slug>` puts the ticket where the item's status says it
   should be, whether the ticket is ahead of the item or behind it.
2. A ticket that several work items share as different parts is not reconciled
   against any one of them, whether or not the other parts are visible in this
   checkout.
3. A backwards move is not silent.
4. `claim` is gone from the `sync` record, from every place that writes, reads,
   validates, types or prints it.
5. A `tracker.yaml` on disk that still carries the key is read with no complaint
   and no loss.

## Non-goals

- **Retiring `link --sync-status`**, and making the lifecycle moves compose
  `claim` and `sync`. That is the epic's fourth child, which also answers the
  epic's acceptance criterion 7.
- **Renaming `transitions.claim` to `transitions.start`.** Third child, being
  implemented alongside this one.
- **Durable evidence of a `--part` hold.** That is
  `docs/work/backlog/2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`,
  which was read before deciding goal 2, as the epic requires. This item works
  around the missing evidence rather than supplying it.
- **Making `--all` find drift.** The sweep selects items that already have a
  record or a comment (`tcw/work/cli.py:2802-2804`). Widening it to every bound
  item would read one ticket per item on every sweep; reconciling drift stays
  something you ask for by naming an item.
- **Changing what a lifecycle move accepts.** `start`, `submit`, `rework`,
  `complete` and `discard` pass a `previous_status`, which gives them a window of
  statuses the ticket may be in, and that window is untouched.
- **The catch-up walk's own defects**, which are
  `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery`.

## Design

### The item is the source of truth, where nothing else claims the ticket

`deliver` loses its `check_only` parameter. Nothing outside the module passes it
any more; instead `deliver` decides for itself, from two facts it already has:

```
check_only = move is None and record is None and bound.part != "default"
```

- `move is None` is a `sync`: no local transition just happened, so there is no
  window of statuses the ticket was left in. `expected_statuses` already returns
  `()` for that case — `previous_status` is `None` and there is no record, so
  `_EARLIER.get("")` is empty (`tcw/tracker/sync.py:180-181`). With an empty
  window `assess_move` applies no status test at all (`:209`), so once the ticket
  is read, the transition it looks for is simply the one leading to the item's
  mapped status, from wherever the ticket sits. **Both directions fall out of
  removing the check-only refusal; no new direction rule is written.**
- `record is None` keeps a recorded, undelivered move governed by its own window.
  A record is TCW saying "I owe this ticket a specific move from a specific
  place"; that statement is more precise than "put it where the item is", and
  overruling it would also break the interrupted catch-up walk, which resumes by
  testing the ticket against that window (`tcw/tracker/sync.py:570-576`).
- `bound.part != "default"` is goal 2. A binding whose part the user named is one
  they told us serves several items. `deliver` already refuses to move such a
  ticket while another part's item is open *in this checkout* (`_siblings` →
  `HELD`, `:296-318`), but a hold leaves no evidence outside the checkout it
  happened in, so a part in another clone is invisible. Without a record, nothing
  here can tell a ticket another part is holding from a ticket that drifted, so
  the sync reports what it sees instead of moving it. A `default` part — the only
  kind a single-item binding has — is reconciled.

Three protections stay exactly where they are, and all three are reached before
any transition is applied, from `assess_move` (`tcw/tracker/sync.py:186-250`):

- a ticket assigned to another account is never moved, in either direction;
- a ticket nobody holds is never moved except by a discard
  (`MOVES_ALLOWING_UNASSIGNED`);
- a ticket in a resolved status is never moved. With an empty window this is the
  `elif ticket.category == "done"` branch (`:217-218`), so **a ticket somebody
  closed is still refused rather than reopened.** TCW does not change a ticket's
  resolution, which the walk enforces separately (`:387-393`), and a closed
  ticket is the one "ahead" a workflow rarely offers a way back from.

### A backwards move says so

`Outcome` gains a `note` field, set by `deliver` when the move it made was
backwards — the ticket's lowest mapped rung was above the item's own
(`lowest_rung`, `_RUNG_ORDER`, both already in the module). The two callers that
print `outcome.claimed` print `outcome.note` the same way. The answer to the
epic's risk 2 is **a warning, not a confirmation and not a record**: `sync` on a
named item is already something a person asked for, a prompt would break `--all`
and every non-interactive caller, and "only failures are recorded" is a rule
worth more than this. What the user gets is a line naming the ticket, the status
it was in and the status it was put in, so a deliberate move that got undone is
visible in the transcript.

### The claim record is replaced by two facts that already exist

`owed` becomes:

```
owed = starting or bound.catch_up
```

- `starting` is a live `start` (`move == "start"`), unchanged.
- `bound.catch_up` is `catch-up: true`, written only by `link --sync-status`
  (`tcw/work/cli.py:2528`) and cleared the moment the ticket is in step
  (`with_status_synced`, `tcw/tracker/intake.py:208-211`). It is exactly "this
  binding was linked to work already under way, TCW has never held its ticket,
  and it has not caught up yet" — the late-link half of `owed`, already on disk,
  already durable, already dropped at the right moment.

**What this deliberately gives up.** Today a `start` whose claim did not reach
the tracker leaves `claim: owed` in the record, and the next command of any kind
— a `submit`, a `complete`, a `sync` — claims the ticket on its behalf. After
this change it does not. The item is started locally, the ticket is not held, and
the way to hold it is the verb the first child added: `tcw work tracker claim
<slug>`. That is the epic's first goal ("four verbs, each doing one thing")
applied to the one path that still reached across. The refusal a later command
gives names that verb, so nobody has to guess: `assess_move`'s "Take it first"
sentence changes from "`tcw work start` claims a bound ticket" to "`tcw work
tracker claim`".

This is what makes the two tests the epic named change rather than pass, and it
is why the epic moved the key removal into this child.

Three consequences follow, and each removes code rather than adding it:

- `finish`'s `drop_record` loses its `and not owed` (`tcw/tracker/sync.py:342`).
  The record no longer remembers anything about the claim, so there is nothing to
  preserve by keeping it.
- the held-sibling branch's `stale` test loses `(record is None or
  record["claim"] != "owed")` (`:306-307`) for the same reason; `catch-up` is a
  separate key and survives the record being dropped.
- `record_unsent` writes one field fewer (`:623-624`).

### Reading an old file

`_sync_record` builds the record as `{name: value.get(name) for name in
SYNC_FIELDS}` (`tcw/store/base.py:434`). Dropping `"claim"` from `SYNC_FIELDS`
therefore drops a `claim:` still on disk on the way in: it is not read, not
validated, not carried into the projection — whose `sync` object is
`additionalProperties: false` (`tcw/work/projection.py:120`) and so would have
rejected it had it survived — and not printed. The binding is not made malformed,
which `_sync_record`'s own contract already requires of anything wrong with a
record (`tcw/store/base.py:427-429`). The next write of the record replaces the
whole `sync` key (`with_sync_record` → `_with_key`, `tcw/tracker/intake.py:202`,
`:219-224`), so the stale key leaves with it.

### The abstraction litmus test

Passes. Every fact this change reads or writes is an ordinary field: an item's
status, a binding's `part` and `catch-up`, a ticket's status and assignee. The
rule that replaces the claim key reads *fewer* stored fields than the rule it
replaces, and the one it keeps (`catch-up`) is already part of the abstract
binding. Nothing added here needs a filesystem: a store backed by a database or a
wiki would answer all of it with the same reads and writes.

### Harness compatibility

Unaffected. All of it is in the `tcw` CLI, which behaves identically under Claude
and Codex. No skill, hook or injected context carries any of it.

### Where this collides with work in flight

The third child edits `tcw/store/base.py` around the tracker transition keys
(`TRACKER_TRANSITION_KEYS`, `:1127`) and `tcw validate`'s checks (`:1241`). This
item's only edit to that file is `SYNC_FIELDS` and `_sync_record` (`:423`,
`:442-443`), about 700 lines away and in a different concern. No shared region is
reformatted or refactored.

## Acceptance criteria

Each is checkable by running the named command against a fixture built the way
`tests/test_tracker_sync.py` builds them.

1. On a bound item in `active` whose ticket somebody moved on to the review
   status, `tcw work tracker sync <slug>` leaves the ticket at the status mapped
   for `active` and exits 0.
2. That same run prints a line naming the ticket, the status it was in, and the
   status it was put in.
3. On a bound item in `review` whose ticket somebody moved back to the active
   status, `tcw work tracker sync <slug>` leaves the ticket at the status mapped
   for `review` and exits 0.
4. On a bound item whose ticket is in a status the project maps to nothing,
   `tcw work tracker sync <slug>` moves the ticket to the item's mapped status
   and exits 0.
5. A ticket assigned to another account is not moved by `tcw work tracker sync`
   in either direction: it exits 1 and names the holder.
6. A ticket in a resolved status is not moved by `tcw work tracker sync`: it
   exits 1 and says the ticket is already resolved.
7. Where two items in this checkout are bound to the same ticket as different
   parts and both are open, `tcw work tracker sync` on either moves nothing,
   reports held, and names the other item.
8. Where an item's binding names a part other than `default` and no other item
   here is bound to that ticket, `tcw work tracker sync <slug>` on a ticket that
   does not match the item moves nothing and exits 1.
9. No command writes a `claim` key into `tracker.yaml`: after a failed `start`, a
   failed `submit`, a `tcw work tracker link --sync-status`, and a failed
   `sync`, the `sync` record in `tracker.yaml` has exactly the keys `state`,
   `move`, `since`, `reason`, `at`.
10. A `tracker.yaml` whose `sync` record carries `claim: owed` alongside the five
    remaining fields is read without complaint: `tcw work show <slug>` prints the
    record's state, move and reason, the item still shows its ticket key, and the
    word "owed" does not appear in the output.
11. `tcw work list --json` validates against the projection schema for an item
    whose `tracker.yaml` carries that stale key.
12. A `start` whose claim never reached the tracker is not claimed by a later
    `sync`: the ticket stays unassigned, the run exits 1, and the message names
    `tcw work tracker claim`.
13. `tcw work tracker claim <slug>` after that failed `start` assigns the ticket,
    and a `sync` then delivers the move.
14. `tcw work tracker link <slug> <key> --sync-status` on an item already under
    way still claims the ticket and catches it up on the next `sync`, with no
    `claim` key written at any point.

## Risks

1. **A sync that fails now writes a record where it used to write nothing.**
   Removing check-only means `finish` records a pending or conflicting outcome
   for a reconciliation it could not make. Under `work.tracker.strict`,
   `binding_refusal` (`tcw/tracker/sync.py:637`) refuses every local move on an
   item that has a record, so a drift `sync` cannot resolve can now lock the item
   until the ticket is fixed by hand. This is the record doing its job — a change
   really has not reached the tracker — and the refusal already tells the user to
   run `sync`. It is the same region
   `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`
   edits; whichever lands second rebases.
2. **A ticket somebody moved on purpose gets put back.** Answered with a warning
   (design, "A backwards move says so"), not a confirmation. Anyone who wants the
   ticket to stay where they put it moves the item too, which is the whole point
   of the item being the source of truth.
3. **The claim is no longer chased.** The convenience described under "What this
   deliberately gives up" is real, and someone used to it will notice. The
   replacement verb exists and the refusal names it, but this is the change most
   likely to be argued with at verification.
4. **A `--part` binding becomes harder to reconcile, not easier.** Goal 2 means
   `sync` will not fix a parted ticket's drift at all without a record. That is
   deliberate — it is the safe direction while a hold leaves no durable evidence —
   but it is a limit users of `--part` now have, and it should be named in the
   guide.
5. **The epic's acceptance criterion 8 is met only for the no-record case.** A
   ticket ahead of its item while an undelivered move is recorded is still
   refused by that record's own window. Widening it there would break the
   catch-up walk's resume path, which reads the same window. The fourth child,
   which composes the moves out of these primitives, is where that case naturally
   comes back.

## Notes

- The epic's acceptance criterion 7 ("no `--sync-status` flag is accepted") is
  the fourth child's, not this one's: retiring the flag is listed under C4 in the
  epic's own child boundaries. This item leaves the flag alone and keeps its
  behaviour working, which criterion 14 pins.
- The sweep for sibling defects was repo-wide for the claim record: every reader,
  writer, validator, type and printed mention was found and is listed in the
  problem section. It was **not** widened to every forward-only assumption in
  `tcw/tracker/`, because the lifecycle moves' windows are the fourth child's
  subject and editing them here would collide with it.
- `docs/capabilities/work/view-the-board/description.md:19` says a board row
  shows a claim "still owed". `_tracker_text(row=True)`
  (`tcw/work/cli.py:164-173`) prints only the record's `state`, never the claim,
  so that sentence is already wrong about the board today. It is corrected as
  part of this item's documentation pass rather than left to drift further.
