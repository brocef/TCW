# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- `claim.NOT_CONFIGURED` (`tcw/tracker/claim.py`): `assess` returns it, with
  `NOT_CLAIMABLE` / `NOT_DETERMINED`, for a claim transition name that is blank.
  One guard in the shared function rather than three in its callers, which are the
  three readers of `config.start_transition` that have no target status to derive
  from: `intake._claim_from`, `_print_ticket` (`tcw/work/cli.py`) and
  `sync.claim_refusal`.
- Row `1d` in `intake._claim_from`: `tracker import` and `inbox accept` refuse a
  ticket when `work.tracker.transitions.start` names nothing, and say which key to
  set. Placed **after** row `1e`, so a ticket the running account already holds is
  still imported — the re-run recovery and the `tracker claim` then `import`
  sequence both depend on that order.
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
- `OwnershipOutcome.assigned`: whether this run's own assignment landed — false up
  to and including the assignment failing, true from the read-back onwards. It is
  what separates *the ticket is unassigned* from *who holds it is unknown*, so the
  sentence above is said only for a failed assignment; a failed read-back keeps
  "Run this again to find out", which is advice that works.
- `authorize(..., ownership=False)` and `_strict_refusal(..., ownership=False)`:
  strict `complete` checks where the ticket is, not who holds it.
- `tcw work tracker sync` prints what its delivery did to take the ticket
  (`Outcome.claimed`) on stderr.

- `STRICT_NEEDS_START_TRANSITION` (`tcw/store/base.py`): `parse_tracker_config`
  reports `work.tracker.transitions.start` as required when `strict` is true and the
  key is absent from the `transitions` mapping (or the mapping is absent). Checked
  after `_parse_tracker_transitions`, absent-only like
  `STRICT_NEEDS_EXCLUSIVE_CLAIM`; attributed to the node being validated by the
  existing prefix match in `attribute_tracker_problems`.
- `OwnershipOutcome.key` (`tcw/tracker/ownership.py`), set by `assert_ownership`
  (now a wrapper over `_assert_ownership`) on every outcome, so `claim_refusal`
  serves an ownership outcome and an `intake.claim` outcome alike.
- `claim_refusal(..., off_active_refuses=True)` (`tcw/tracker/sync.py`): the two
  lifecycle callers pass `False`, so a ticket found off `statuses.active` is a
  question this run cannot answer rather than a refusal — a strict `start` of a
  held ticket in the backlog status goes on to move it there itself.
- `_unclaimable_on_active` (`tcw/work/cli.py`): the refusal for an unassigned
  ticket on `statuses.active` whose workflow does not offer
  `exclusive-claim-transition` there (a released item's ticket), shared by
  `_strict_claim` and `_tracker_claim` so the three retake commands agree. It names
  the state and both ways forward.
- `ONE_MUTEX_ONE_NOT` (`tests/tracker_fake.py`): a workflow with two routes into
  `In Progress`, one exclusive and one not — the only fixture on which
  `transitions.start` and `exclusive-claim-transition` can be told apart.

### Changed

- `work.tracker.transitions` and `work.tracker.transitions.start` are both
  optional. `parse_tracker_config` (`tcw/store/base.py`) loses both required checks:
  the shared `nested` call for the mapping, and `if "start" not in transitions`.
  An absent mapping yields `{}`; `transitions: null` is now reported as
  `work.tracker.transitions: expected a mapping, got NoneType` rather than as a
  missing required key, the shape `inbox-query` and `exclusive-claim-transition`
  already use. A start with no configured name reaches `assess_move`'s
  status-derived tail, which it has done since the lifecycle moves were composed
  from claim and sync; the parser's requirement was the only thing preventing the
  configuration.
- `assess_move`'s "offers no transition named" refusal offers removal for all five
  moves. The `start` special case existed because the parser then refused a
  configuration without the key.
- `REASON_LIMIT` (`tcw/tracker/sync.py`) 300 → 400. The uniform removal advice
  added 50 characters to a refusal that then measured 331, and the cut took the
  `pre-backlog` hint — the part that says what to do — off the recorded reason.
  The limit caps how much of a reason the binding stores; it is not a size the
  message is known to fit under, since the transition names and status names the
  message quotes come from the project's configuration and from the tracker.
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
- A recorded start is owed only while the **item** is unresolved (`start_owed` in
  `deliver`), never decided from the move: `sync` has none of its own and reads the
  record's, so a resolved item carrying a start record used to read as a start. It
  gates `takes_ticket`, the `leave_pre_backlog` step and the recorded-start hop, so
  a `sync` of a finished item claims nothing and climbs nothing; and `sync` falls
  back to `MOVE_ONTO[local]` rather than the recorded start, without which
  `MOVES_NEEDING_NO_CLAIM` would not exempt the resolution and a ticket nobody
  holds could not be closed. A `complete` on a `catch-up: true` binding no longer
  leaves a `pre-backlog` status either.
- **On that path `work.tracker.transitions.complete` / `.discard` is now enforced.**
  `assess_move`'s `named_transition` is only passed when the move's own mapped status
  is the one being moved to, and the recorded `start` never satisfied that, so the
  transition used to be derived from the target status whatever the project had
  named. With the move now naming the resolution, a project that configured one gets
  it — and a name the workflow does not offer is refused, naming the key, where it
  was silently bypassed before.
- A `sync` delivering a resolution takes `since` and its window from the ticket it
  has just read: no local move just happened, and a resolution moves a ticket from
  wherever it sits, so there is no status it was supposed to have been left in.
  Without it a completion `sync` never managed to send recorded an empty `since`,
  which sends `expected_statuses` to `_MOVED_FROM["complete"]` and produced a window
  beginning at `statuses.review` — so the next run read an untouched ticket as drift
  and refused with "TCW does not move it back". A discard never showed it, because
  `_MOVED_FROM["discard"]` is empty.
- While `start_owed` holds, `finish` writes `start` as the record's move whatever
  move is being delivered, and `record_unsent` does the same — replacing the three
  assignments that covered the recorded-start hop alone. Taking the ticket out of a
  `pre-backlog` status and taking the ticket itself are done on the start's behalf
  too, and naming the later move there lost the start for good. The flag is cleared
  the moment the start's hop has landed and been read back.
- The catch-up walk runs for any binding carrying `catch-up: true`, not only when
  a claim was owed, and looks for a shortcut before every hop. `resolving` is false
  for a `complete` on such a binding, so that completion still needs the ticket
  held — the walk climbs working statuses, which is work. Documented rather than
  changed; only bindings written before `--sync-status` was retired are affected.
  Leaving a `pre-backlog` status is now gated on the item instead, so that
  completion no longer takes its ticket out of triage.
- The delivery says "{key} is already held by you." only for a `start`, not for
  every move that takes the ticket, and `_deliver_after` takes `say_claim=False`
  from a strict `start` — `_strict_claim` now prints the claim's own message, since
  under strict mode the ticket was taken by that same command, not "already".
- `Outcome.already_held` (`tcw/tracker/sync.py`) marks a claim message that only
  reports the ticket as *already* this account's, and `_deliver_after`'s
  `say_claim=False` now withholds that alone: a claim `deliver` itself had to make —
  the ticket was let go between `_strict_claim` and the delivery — is printed. The
  `TransitionCommitError` recovery in `_cmd_start` passes `say_claim` too, so a
  strict start that trips it no longer prints a claim line twice.
- `_strict_claim`'s past-the-claim refusal says the transition "would move {key}
  back" only where the workflow offers it from the ticket's status; where it does
  not, the refusal stands but gives that as the reason.
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

### Fixed

- **A recordless `tcw work tracker sync` wrote an unreadable record**
  (`deliver`, `tcw/tracker/sync.py`). With no sync record, `move` stayed `None`, and
  a pending or conflicting run wrote `move: null`, which `classify_binding` rejects.
  Under strict mode `binding_refusal` then blocked the next move. `deliver` now keeps
  two values: `assessed = move or MOVE_ONTO.get(local)` feeds `resolving` and
  `assess_move(move=...)` only, and the recorded move is unchanged — so a failure
  with nothing owed writes no record at all. The derived move never reaches the
  configured-transition lookup (that broke `sync`'s both-ways reconciliation when
  tried), and is never written (a recorded `start` would re-arm the claim on the
  next run). An earlier version's `move: null` record is cleared by the next
  successful sync; no migration.
- **A reopened ticket on a completed or discarded item could not be closed by
  `sync`** without a claim, for the same reason: `None` is not in
  `MOVES_NEEDING_NO_CLAIM`. Fixed by the same derived move. A catch-up binding
  heading for a completion still requires the ticket held.
- **Strict mode stopped checking claim exclusivity — a regression.** Three
  children of the tracker-verbs epic combined to cause it: the one that made
  `exclusive-claim-transition` required under strict mode (so the promise rested on
  that key alone), the one that composed the lifecycle moves out of claim and sync
  (which removed `claim_refusal`'s lifecycle call sites), and the one that made
  `transitions.start` optional (which broke the one surviving check, since it asked
  about that key). Each was correct alone and reviewed alone; the invariant spanning
  all three — *strict mode checks that the transition carrying its promise is a
  mutex* — had no owner, and only a review of the combined change found it.
  `claim_refusal` now asks `assess(config.exclusive_claim_transition, ...)` and
  names that key, and is called from `_strict_claim` and `_tracker_claim` (under
  `config.strict`) after a settled `assert_ownership`, including on the
  already-held early return. Measured against the pre-epic tree `bfb2ff33`: a strict
  start on a workflow offering the claim from its own destination is refused again
  for an unassigned ticket and for one the caller holds on the active status. One
  path stays unprovable: a ticket the caller holds in the backlog status, on such a
  workflow, is accepted — what it offers from there says nothing about the active
  status, and re-applying the transition is what the idempotent claim must avoid.
  Deciding that needs the workflow definition
  (`2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`).
- Found at verify: a strict `tracker claim --take-over` (and `start --take-over`) on
  a workflow offering the claim transition from `statuses.active` applied it, took
  the holder's ticket, then refused — leaving the item owned by the holder and the
  ticket by the caller. `_unclaimable_on_active(..., take_over=)` now refuses before
  `assert_ownership` whenever the ticket is on `statuses.active` and the transition
  is offered there, and `claim_refusal` asks the question at `outcome.status` when an
  applied claim transition landed off `statuses.active` rather than skipping it.
  `not_exclusive_advice` (`tcw/tracker/sync.py`) gives both refusals a next step.
- `_print_ticket` (`tracker show`, `inbox show`) answered its `workflow:` line from
  the `transitions.start` assessment; it now assesses
  `exclusive_claim_transition or start_transition` with `statuses.active` as the
  landing status. `claimable:` and `note:` stay about `transitions.start`.
- The strict binding refusal read "first; It is held by … . if that cannot …"; now
  ordinary sentences.

### Internal

- Tests: `test_strict_import_of_a_held_ticket_needs_no_start_transition` deleted —
  its node is invalid under strict mode now, and its premise (`claim_refusal` reads
  `transitions.start`) is false. Its held-ticket-succeeds-and-sends-nothing
  properties are held by `test_a_strict_claim_of_a_ticket_you_already_hold_sends_nothing`;
  the unset-key half survives only outside strict mode, in
  `test_tracker_import.py::test_import_of_a_ticket_already_held_needs_no_start_transition`.
  Five strict tests ran a strict start on `GLOBAL`, which excludes nobody, and
  encoded the regression: four now run on `SYNC`, the on-its-own-rung case asserts
  the refusal, and `test_a_strict_start_reports_a_claim_the_delivery_had_to_make_again`
  is replaced — its re-claim is unreachable on an exclusive workflow. Each
  successor was mutation-checked. The fixture `global_claim_node` is now
  `claim_node` with a required `workflow`.
- The comments in `tcw/store/base.py` (above `TRACKER_TRANSITION_KEYS`, in
  `_parse_tracker_transitions` and in `attribute_tracker_problems`) and in
  `tcw/tracker/sync.py` that stated `start` had no status-derived fallback. That
  stopped being true when the lifecycle moves were composed from claim and sync.
  `attribute_tracker_problems`' docstring used `transitions.start: required` as its
  worked example of a problem about a key nobody set; the parser can no longer
  produce that message, so the example is now `credentials.token-env: required`.
- `make_node` and `ladder_node` (`tests/test_tracker_sync.py`) and `strict_node`
  (`tests/test_tracker_strict.py`) take a `transitions` argument, where `None`
  leaves the mapping out of the block. `TWO_ROUTES_IN` (`tests/tracker_fake.py`) is
  `SYNC` with a second route out of the backlog status into `In Progress`: two
  routes into `statuses.active` is what makes a configured name load-bearing, since
  on `SYNC` the named and the derived answers are the same transition id.
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
