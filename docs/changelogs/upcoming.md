# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- The claim gate (`_claim_gate`, `tcw/work/cli.py`): `submit` and `rework` of a
  bound item refuse before the local move unless the ticket's assignee is the
  signed-in account, in every mode. Refuses only on an answer; skipped under strict
  mode, where `authorize` already asks.
- `OwnershipOutcome.retry` (`tcw/tracker/ownership.py`): true when an unsettled
  claim failed on an unanswered assignment or read-back; `deliver` records those
  `pending`.
- `OwnershipOutcome.transitioned` is now set on a *refusal* as well as a success,
  and `OwnershipOutcome.status` reports where an applied assertion left the ticket
  rather than where it was found. `deliver` and `_strict_claim` use both to say
  "{key} was moved to '{status}' but is not assigned to you. Assign it to yourself
  in the tracker, then run this again." — the only advice that works, since the
  assertion transition is no longer offered from where the ticket now sits.
- `authorize(..., ownership=False)` and `_strict_refusal(..., ownership=False)`:
  strict `complete` checks where the ticket is, not who holds it.
- `tcw work tracker sync` prints what its delivery did to take the ticket
  (`Outcome.claimed`) on stderr.

### Changed

- `deliver` (`tcw/tracker/sync.py`) takes a ticket through `assert_ownership`
  (asserting through `exclusive-claim-transition`) instead of `intake.claim`. The
  claim-landing refusal and the early `CURRENT` return for a start are gone; the
  start is delivered through `assess_move`. `owed` is split into `takes_ticket` (a
  property of the move, read before the ticket) and the ticket's own assignee
  (`owed = takes_ticket and assignee != me`). The pre-backlog step
  (`leave_pre_backlog`) runs in `deliver` for every move that takes the ticket,
  whoever holds it. The `pre-backlog` hint is appended to a conflicting refusal of
  such a move while the ticket is still in the status it was found in.
- A lifecycle move with an empty `expected` window whose ticket is above the target
  returns `HELD` and writes no record (forward only). `sync` still reconciles both
  ways.
- A claim never applies `exclusive-claim-transition` to a ticket whose
  `lowest_rung` is above 0: in `deliver` the assertion is skipped and the claim's
  message says the claim was the assignment and its read-back only; in
  `_strict_claim` the start is refused before the item moves, naming the two ways
  out. `_strict_claim` refuses only where the assertion would really be applied —
  not for a ticket already this account's, one resolved, or one held by somebody
  else, which `assert_ownership` answers better.
- A record naming `start` has an empty window (`expected_statuses`), like a live
  start. When the item has moved past `active`, that start is delivered first (to
  `statuses.active`, `transitions.start`) and the later move measures from there.
- The catch-up walk runs for any binding carrying `catch-up: true`, not only when
  a claim was owed, and looks for a shortcut before every hop. `resolving` is false
  for a `complete` on such a binding, so that completion still needs the ticket
  held — the walk climbs working statuses, which is work. Documented rather than
  changed; only bindings written before `--sync-status` was retired are affected.
- The delivery says "{key} is already held by you." only for a `start`, not for
  every move that takes the ticket, and `_deliver_after` takes `say_claim=False`
  from a strict `start` — `_strict_claim` now prints the claim's own message, since
  under strict mode the ticket was taken by that same command, not "already".
- The past-the-claim refusal blames `exclusive-claim-transition` only where the key
  is set; without it a claim moves nothing and could not move the ticket back. The
  catch-up walk's "past where its item is" refusal no longer says the ticket was
  not *claimed*: this run may have just claimed it.
- `MOVES_ALLOWING_UNASSIGNED` is renamed `MOVES_NEEDING_NO_CLAIM` and holds
  `complete` and `discard`; `assess_move` skips the assignee check for them
  entirely, and `progress.py` posts a completion's comment on an unassigned ticket.
- `_strict_claim` asserts through `exclusive-claim-transition` with
  `assert_ownership` (after `leave_pre_backlog`) instead of `intake.claim` plus
  `claim_refusal`; it also runs for an active item with no owner.
- `WorkStore.start` / `FsWorkStore.start` take an active item whose `owner` is
  empty instead of raising `AlreadyClaimed`, whose message now names
  `tcw work tracker claim <slug> --take-over`.
- `tracker create` for work under way binds with a pending record naming `start`
  instead of `catch-up: true`.
- `unsynced_hint` advises `tracker claim` then `tracker sync`.
- `parse_tracker_config` (`tcw/store/base.py`) requires `exclusive-claim-transition`
  when `strict` is true, reported as the new module-level
  `STRICT_NEEDS_EXCLUSIVE_CLAIM` problem. Only an absent key triggers it: a key
  written as `null` or blank keeps its existing single `expected a non-empty
  string` problem. The problem names a key nobody wrote, so under inheritance it is
  attributed to the node being validated even when `strict` came from an ancestor.

### Internal

- Every strict test fixture now sets `exclusive-claim-transition`, so a fixture
  broken on purpose is broken only by what it breaks. `strict_node`
  (`tests/test_tracker_strict.py`) takes it as a required `claim_transition`
  argument with no default.
- Removed `test_strict_is_reported_as_unknown_because_c4_owns_it`
  (`tests/test_tracker_config.py`): `strict` has been an accepted key since strict
  mode shipped, and the test passed only because the word appeared in the
  missing-status problems.

### Removed

- `link --sync-status`: hidden, and refused with the three replacement commands.
  Nothing writes `catch-up: true` (`binding_document` lost `catch_up`); the key is
  still read.
- `claim_refusal`'s lifecycle call sites (it stays for `tracker import`), and
  `_NO_CLAIM_ADVICE`.
