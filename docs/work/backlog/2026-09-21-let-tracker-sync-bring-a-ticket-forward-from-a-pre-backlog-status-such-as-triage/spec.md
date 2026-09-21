# Spec: Let tracker sync bring a ticket forward from a pre-backlog status such as Triage

Line numbers below were checked against the tree on 2026-09-21. Other items are
being worked in the same checkout, so re-check any citation before relying on it.

## Capability changes

Planned deltas only; nothing is written to the ledger at this stage.

```yaml
changed:
    - work/synchronize-external-tracker-work    # cap-207f2c
    - work/manage-external-tracker-intake       # cap-bd57b7
    - work/inspect-external-tracker-work        # cap-1b0a04
```

- `work/synchronize-external-tracker-work` — `start`, `link --sync-status` and
  `sync` can take a ticket out of a status the project names as coming before
  its backlog, through a transition the project names, before claiming it.
- `work/manage-external-tracker-intake` — `tracker import`, and so
  `inbox accept <ticket>`, can take a ticket waiting in triage, which is exactly
  the set `work.tracker.inbox-query` selects.
- `work/inspect-external-tracker-work` — the capability describes the
  configuration keys a user sets under `work.tracker`, and gains one. `tracker
  show` / `inbox show` also stop calling such a ticket unclaimable without saying
  why (criterion 16).

No new Vocabulary or Feature entry: this is the existing `external-work-tracker`
Feature, and "status" and "transition" are already its terms.

## Problem

A ticket can sit in a Jira status that comes before the backlog — `Triage` is the
common one — and when it does, nothing TCW runs can take it from there.

Every claim goes through `claim` in `tcw/tracker/intake.py:475`, and a claim is
the transition `work.tracker.transitions.start` names (`intake.py:494`, `:518`).
A Triage status does not offer that transition; in the reporter's project and in
this one it offers only `Accept` and `Cancel`. So:

- **The ticket is unassigned.** `claim` refuses at row `1f`
  (`intake.py:524`): "PRPI-147 is in 'Triage', unassigned, and does not offer
  'Start Progress'. It offers: 'Accept', 'Cancel'." `deliver` then advises
  `tcw work tracker claim` (`tcw/tracker/sync.py:613-615`), which only assigns
  (`tcw/tracker/ownership.py`, applies no transition unless
  `exclusive-claim-transition` names one) and so turns this case into the next.
- **The ticket is already assigned to you** — a creator is often its assignee.
  `claim` reports it as held without moving it (row `1e`, `intake.py:521`), and
  `deliver` refuses to go on because it did not land on `statuses.active`
  (`sync.py:625-634`): "claimed PRPI-147, but it is in 'Triage', not 'In
  Progress', so it was not brought forward from there." This is the message the
  reporter saw.

Nothing later can recover it either. `walk()` (`sync.py:439`), which walks a
ticket up rung by rung, is only reached after that refusal is passed
(`sync.py:646`), and its rungs are the statuses mapped under `statuses`, which a
Triage status is not. A plain `sync` finds the same claim still owed and reaches
the same refusal.

The same claim, with the same refusal, sits behind two more commands:

- `tcw work start` under strict mode claims through `_strict_claim`
  (`tcw/work/cli.py:393`, claim at `:416`) before moving the item.
- `tcw work tracker import` claims at `cli.py:2431`, and `tcw work inbox accept
  <ticket>` is that import (`cli.py:725`). `inbox-query` exists to select tickets
  awaiting triage (`docs/guide/jira.md:44`, `:286`), so today every ticket it
  lists is one `inbox accept` refuses. The active epic records this exact case,
  `TCW-1` in `Triage`, in its request.

The reporter worked around it by running `Accept` (id 11) by hand through the Jira
API on all 22 tickets before `link` and `sync` would work.

`tcw work tracker create` does not have this problem, because it moves each new
ticket to `statuses.backlog` itself (`tcw/tracker/create.py:69-78`, `:153-207`).
What remains is a ticket that already exists in Triage.

## Goals

1. A project can name, in `work.tracker`, each status that comes before its
   backlog and the transition that takes a ticket out of it.
2. With that named, every command that claims a ticket takes it out of such a
   status first, then claims it as it does today: `start` (strict or not),
   `link --sync-status`, `sync`, `tracker import` and `inbox accept`.
3. Without it, nothing moves a ticket out of such a status — the refusal stays —
   but the refusal names the setting that would resolve it.
4. Taking a ticket out of triage happens only where a claim is made, and nowhere
   else: not on a `submit`, `rework`, `complete` or discard **with no claim
   owed**, not on a discard at all, not on a part-bound `sync` that only reports,
   not from `tcw work tracker claim`, and not on a ticket another account holds.
   A `submit`, `rework` or `complete` that finds a claim still owed — a
   `catch-up: true` binding, or a sync record whose move is `start`
   (`owed`, `tcw/tracker/sync.py:341-342`) — reaches `claim` today
   (`sync.py:537`, `:601-603`), and that is the same debt `sync` settles, so it
   takes the ticket out of triage the same way.

## Non-goals

- **Walking forward from any unmapped status with no configuration.** The
  requester considered and rejected it on 2026-09-21: accepting a ticket out of
  triage can be a team's deliberate decision, so TCW does it only where the
  project said so.
- **`tcw work tracker claim`.** Since C1 of the active epic it asserts ownership
  and moves no status (`ownership.py`). Making it take a ticket out of triage
  would make it move status again, reversing that epic's central decision. That
  holds even with `exclusive-claim-transition` set, whose transition is an
  exclusivity check rather than a status move; a Triage ticket that does not
  offer it is refused, as today.
- **`tcw work tracker create`.** It already places new tickets by destination
  (`create.py:153`). Changing it to read the new key is not needed to fix this.
- **`tracker import` of a ticket that is already bound here.** Import answers
  before claiming (`tcw/work/cli.py:2407-2430`): already yours exits 0, and
  unassigned or held by someone else is refused. That short-circuit is kept as
  it is, so an already-bound Triage ticket is not moved by `import`.
- **Checking the named transition against the real workflow in `tcw validate`.**
  That is `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`;
  see Notes for what it should add.
- **A ticket somebody moved back into triage after TCW had held it.** On a
  `submit`, `rework` or `complete` that ticket is outside the expected window and
  is refused as drift (`assess_move`, `sync.py:235-242`). This item leaves that
  alone.
- **The rewrite of claim-within-delivery.** That belongs to
  `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync` (C4). This item
  must fit it, not do it; see "Sequencing" below.

## Design

### The setting

One new optional key, `work.tracker.pre-backlog`: a mapping from a tracker status
name to the name of the transition that takes a ticket from that status to the
configured backlog status (`statuses.backlog`). That is how the guide and the
configure reference document it: "tracker status → transition name to the
configured backlog".

```yaml
work:
    tracker:
        transitions:
            start: Start Progress
        statuses:
            backlog: To Do       # required when pre-backlog is set
            active: In Progress
        pre-backlog:
            Triage: Accept
```

A mapping rather than two parallel keys (a `statuses.triage` plus a
`transitions.accept`), because a workflow may have more than one such status,
each with its own way out, and because `statuses` maps *local* statuses to
tracker ones — a Triage status is not a local status and has no place there. The
reporter suggested `statuses.triage`; this is the same idea without bending what
`statuses` means.

It is parsed with the rest of `work.tracker` and **fails closed** like every other
key in that block (`tcw/store/base.py:1498`): any problem leaves no tracker
configuration at all, and `tcw validate` reports it. Problems:

- not a mapping; a key or value that is not a non-empty string;
- two keys that are the same status once compared as TCW compares statuses
  (trimmed, case-folded, `tcw/tracker/claim.py` `_normalize`);
- a key that is also a status mapped anywhere under `statuses`, including a
  per-resolution `discarded` entry — a status cannot be both before the backlog
  and on it;
- the key is set and `statuses.backlog` is not.

It inherits from parent nodes key by key, as `statuses` does
(`merge_tracker_blocks`, `base.py:1661`), with no extra code.

### What it does

Whenever TCW is about to claim a ticket, and the ticket's **current status**, read
fresh from the tracker, is a key under `pre-backlog` (compared as TCW compares
statuses, trimmed and case-folded by `_normalize`), TCW first applies the
transition named for that status, reads the ticket back, and then claims it
exactly as it would a ticket in the backlog status. From `statuses.backlog` the
existing rules take over unchanged: the claim applies `transitions.start`, and a
`link --sync-status` catch-up walks on up the ladder with `walk()`.

Whether the step runs is decided **only** by the ticket's current status. It is
never decided by whether a transition with the configured name happens to be
offered: a ticket in some other status that also offers `Accept` does not get the
step.

### Where it lives

The step is **its own small status-movement function**, separate from the
ownership part of claiming. For now `claim` in `tcw/tracker/intake.py` calls it,
because `claim` is the one function all three claim callers go through today —
`deliver` (`sync.py:603`), `_strict_claim` (`cli.py:416`) and `_tracker_import`
(`cli.py:2431`) — so one call covers them all. `claim` is also already the
function that moves a ticket, since it applies `transitions.start`. Keeping the
step in its own function keeps the ownership primitive, `assert_ownership`
(`tcw/tracker/ownership.py`), free of status movement. It also lets C4 call the
step from its new path (see "Sequencing").

### The rules it keeps

The step runs after the claim's own first checks, and keeps them:

- A resolved ticket, or one assigned to another account, is refused exactly as
  today (rows `1a`, `1b`, `intake.py:509-513`), and nothing is sent.
- It runs for a ticket that is unassigned or assigned to you. Taking an
  unassigned ticket out of triage is part of claiming it, and the claim that
  follows assigns it.
- **Checked before anything is sent.** The named transition must be offered by
  the ticket exactly once, and must lead to `statuses.backlog`. If it is not
  offered, is offered more than once, or leads anywhere else, nothing is sent.
  The refusal names `work.tracker.pre-backlog.<status>` and lists what the
  ticket offers, or both ids when it is offered twice. That is the same shape as
  `assess_move`'s refusal for a named transition (`sync.py:243-268`). A
  transition leading elsewhere is refused rather than applied for the reason
  `assess_move` gives: the ticket would land somewhere no later run can reason
  about, and a transition cannot be taken back.
- **Checked again after.** The ticket is re-read with `read_ticket`, and one
  that is not in `statuses.backlog` is refused, naming where it is.
- **Everything after the step uses the fresh read.** The claim that follows
  never reuses the snapshot taken before the step. It re-checks rows `1a` and
  `1b` against the fresh read, because somebody may have resolved the ticket or
  taken it in between. It takes the offered transitions, and so where the claim
  leads, from the fresh read, because what a workflow offers depends on where
  the ticket is.

### Failures, and pending versus conflicting

The split `deliver` already makes is kept: **pending** means the tracker could
not be reached or could not answer, so running the command again may clear it.
**Conflicting** means the tracker answered, and the answer stops the move. A
claim's own read-back failure is already pending (`sync.py:607`, rows `3-read`
and `3f`). For the step:

| What happened | Outcome |
| --- | --- |
| Tracker unreachable, rate-limited, or refusing the credentials before or while applying the transition | pending; nothing is known to have moved |
| The transition request's response does not say whether it applied | the read-back decides; if the read-back also fails, pending |
| Transition applied, read-back failed | pending, and the message says the transition was sent |
| Read back and not in `statuses.backlog` | conflicting, naming where it is |
| Named transition not offered, offered twice, or leading elsewhere | conflicting; nothing sent |

Authentication, permission, rate-limit and not-found errors keep propagating out
of `claim` as they do today (`intake.py:536-538`). The callers already classify
them (`classify_error`, `sync.py:161-166`).

### Saying that the ticket was moved

A ticket taken out of triage has left the `inbox-query` list, so every command
that did it says so, **whether or not the claim afterwards succeeded**.
`ClaimOutcome` (`intake.py:431`) gains a field recording the status the ticket
was taken out of (for example `left_status`). All three callers print
"moved {key} out of 'Triage'" from it: `deliver` in its reason, `_strict_claim`
in its refusal or success line, and `_tracker_import` in its output.

This includes partial success. If the step applied and the claim then raises
`TrackerError` — for example the tracker stops answering between `Accept` and
`Start Progress` — the caller still reports that the ticket was moved out of
triage. So the fact has to survive the exception, not only a returned
`ClaimOutcome`. How it survives is the plan's to choose.

It never loops. It runs at most once per claim, and only from a `pre-backlog`
status. Its only permitted landing is `statuses.backlog`, which the parser
guarantees is not a `pre-backlog` status. A claim that itself lands in a Triage
status — the shape `test_a_claim_landing_off_the_ladder_stops_the_catch_up`
(`tests/test_tracker_sync.py:1612`) pins — is still refused as today.

### If the claim fails after the ticket was taken out of triage

The step and the claim are two tracker writes, and TCW cannot make them one. If
the claim then fails — somebody else assigns the ticket in between, or the
workflow refuses `transitions.start` — the ticket stays in the backlog status.
That is a forward, mapped status, and how each command resumes from it differs:

- **`deliver`** (`start` outside strict mode, `link --sync-status`, `sync`, and
  a move with a claim still owed) records the claim as still owed, and the next
  `tcw work tracker sync` claims from the backlog status with no second step.
- **Strict `start`** refuses before the item moves (`_strict_claim`,
  `cli.py:393-427`). The item stays in `backlog`, and **no sync record is
  written**, so `sync` has nothing to resume. The recovery is to run
  `tcw work start` again, which claims from the backlog status. The refusal says
  so.
- **`tracker import` / `inbox accept`** create no item. Running the same
  command again by key claims the ticket from the backlog status. Its refusal
  says the ticket has left triage, because `inbox list` will no longer show it.

### Without the setting

Nothing moves. The places a Triage ticket reaches today gain one sentence naming
the setting. It is worded as a condition, because TCW cannot tell a pre-backlog
status from a status the project simply forgot to map:

> If 'Triage' is where tickets wait before your backlog, name it and the
> transition out of it under work.tracker.pre-backlog.

It is added only when the ticket's status is mapped nowhere under `statuses` and
the ticket is not resolved, and:

- to the claim's row-`1f` refusal (`intake.py:524`), which reaches `deliver`,
  strict `start`, `tracker import` and `inbox accept` alike;
- to `deliver`'s "claimed …, but it is in …, not …" refusal
  (`sync.py:631-634`), only when the claim applied no transition, meaning the
  ticket was already in that status. When the claim transition itself led
  there, naming `pre-backlog` would be wrong advice;
- as a **warning line** from `tracker import` / `inbox accept` when the claim
  succeeds at row `1e` (`intake.py:521`) — a Triage ticket already assigned to
  you. Today that import succeeds and creates a backlog item while the ticket
  stays in Triage. That behaviour is kept, pinned by a test, and gains the
  warning.

### `tracker show` and `inbox show`

Both print a claimability report from `assess` (`cli.py:2319`), which today says
"not claimable" for a Triage ticket, with a note that `transitions.start` is not
offered. With the ticket's status named under `pre-backlog`, the report adds one
`note:` line saying that a claim will first take it out through the named
transition. The two-word claimable/exclusive report itself is unchanged.

### Sequencing with the active epic

`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs` is
separating "take the ticket" from "move the ticket". Its remaining children are
`2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode` (no
spec yet), C4 `2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`
(specced and planned, blocked by the former), and
`2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`
(blocked by C4).

**C4 does not fix this.** It deletes the refusal at `sync.py:625-634` and routes
a start through `assess_move` instead (C4 spec, Design section 1; C4 plan Task 4).
Traced through that design, a Triage ticket still fails. The claim becomes an
assignment only. Then `assess_move` looks for a transition from Triage to
`statuses.active`, either by `transitions.start`'s name or, if that key is
unset, by destination, and Triage offers neither. Two hops are needed and
`assess_move` makes one. C4 also keeps `_tracker_import` on `intake.claim` (C4
plan Task 4). So `inbox accept` on a Triage ticket would stay broken, even though
the epic's request expected an ownership-only claim to fix it.

**This item lands first, and is recorded as a blocker of C4.** v2.5.1 is held
until it is accepted (`initial-request.md`), and C4 is two items away from
starting. So it changes today's code, putting the step in its own function that
`intake.claim` calls. The team lead is recording the blocker and amending C4's
plan; this spec only states what C4 has to carry.

**It is not a child of the epic.** The epic's goal is separating claim from
status movement. This item adds a configured status move in front of the claim,
and would be needed whether or not the epic existed. Its release deadline is
also different.

**What C4 must carry:**

- **C4 deletes `_strict_claim`** (C4 plan Task 4: "delete `_strict_claim`
  (`cli.py:379`) with its call"). After C4, strict `start` is delivered through
  `deliver`, so there are two paths to keep, not three: `deliver` and `import`.
- **In `deliver`**, C4's path is to assert ownership, then run `assess_move`. C4
  must call the step on that path before `assess_move`, and **independently of
  `owed`**. C4 redefines `owed` as `takes_ticket and ticket.assignee_id !=
  me_id` (C4 spec, Design section 2). The reporter's ticket is already assigned
  to them, so under C4 `owed` is false for it. A step placed inside `if owed:`
  would never run for exactly the case this item exists for.
- **In `import`**, C4 keeps `intake.claim`, and so keeps the step with no change.
- **C4's replacement for the deleted refusal** must still carry the
  `pre-backlog` sentence.
- **C4 Task 8 retires `link --sync-status`** in favour of `link`, then `claim`,
  then `sync`. The tests for criteria 2-4 below then move to that flow rather
  than being deleted with the flag: the same Triage ticket, the same ending in
  `In Progress`, and the same `Accept` then `Start Progress`.

`2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode` is
unaffected in substance, with one interaction C4 inherits. With
`exclusive-claim-transition` set, an ownership claim asserts through that
transition, and a Triage status will not offer it either. So once C4 routes
strict `start` through `deliver`, the step has to run before that assertion too.

### Sweep for sibling defects

Repo-wide, by caller rather than by name. Every call of `intake.claim` is covered
(`grep -rn "claim(client" tcw/` finds three: `sync.py:603`, `cli.py:416`,
`cli.py:2431`). `deliver`'s call is reached by `start` and `sync`, and also by
`submit`, `rework` and `complete` whenever a claim is still owed (Goal 4). The
other places that consult where a claim can start from:

- `claim_refusal` (`sync.py:822`) runs after a successful claim and is
  unaffected.
- `tracker show` and `inbox show` are covered above.
- `tracker claim` and `tracker create` are non-goals, with reasons.
- `walk()` and the "already yours and on the ladder" branch (`sync.py:558`) only
  act on mapped statuses, so a Triage ticket never reaches them before the
  claim.

No other code reads a ticket's status to decide whether it can be taken.

### The abstraction litmus test and harness compatibility

**Passes.** "A status tickets wait in, and the named transition out of it" is
expressed in the model's own terms — status and transition — and any tracker
with a workflow can implement it. Nothing depends on the filesystem.

**Harness: unaffected.** Everything is in the `tcw` CLI and its configuration, so
Claude and Codex users get the same behaviour; no skill, hook or injected context
carries any of it.

## Acceptance criteria

Criteria 1-16 can be checked against the fake Jira the tracker tests already use
(`tests/test_tracker_sync.py`, `tests/test_tracker_cli.py`). Unless a criterion
says otherwise, they use:

- the workflow `Triage --Accept--> To Do --Start Progress--> In Progress --> …`;
- `statuses.backlog: To Do` and `statuses.active: In Progress`;
- `pre-backlog: {Triage: Accept}`.

"Applies no transition" means the fake records no applied transition.

1. `tcw validate` reports a problem, naming the key, for each of:
   - `pre-backlog` not a mapping;
   - an empty or non-string status or transition name;
   - two keys equal after trimming and case-folding;
   - a key equal to a status mapped under `statuses`, including a
     per-resolution `discarded` entry;
   - `pre-backlog` set with no `statuses.backlog`.

   In each case the node has no tracker configuration, as for any other
   `work.tracker` problem. A valid `pre-backlog` validates, and a child node
   inherits a parent's entries.
2. `tcw work tracker link <slug> <KEY> --sync-status` on an active item whose
   ticket is unassigned in `Triage` exits 0. The ticket ends in `In Progress`,
   assigned to the running account, and the transitions applied are `Accept`
   then `Start Progress`, in that order. The output says the ticket was moved out
   of `Triage`.
3. The same, with the ticket already assigned to the running account in
   `Triage` — the reporter's case — ends the same way.
4. `tcw work tracker sync <slug>` on a binding left with a catch-up owed and the
   ticket in `Triage` ends the same way. On an item in `review` whose workflow
   has no shortcut, the ticket is walked on to the review status.
5. `tcw work start <slug>` on a backlog item whose ticket is in `Triage` exits 0
   and leaves the ticket in `In Progress`. The same holds with
   `work.tracker.strict: true`.
6. `tcw work inbox accept <KEY>` and `tcw work tracker import <KEY>` on an
   unassigned ticket in `Triage` create the bound backlog item and exit 0, the
   ticket having gone through `Accept` then `Start Progress`.
7. **A Triage ticket already assigned to you, through import.**
   - (a) With `pre-backlog` set, `tcw work tracker import <KEY>` applies
     `Accept` then `Start Progress` and creates the item.
   - (b) With it unset, today's behaviour is pinned: row `1e`, the item is
     created, the ticket stays in `Triage`, and no transition is applied. Output
     also carries a warning line containing `work.tracker.pre-backlog`.
8. **Another holder, or a resolved ticket.** With the ticket in `Triage`:
   - assigned to another account: each of criteria 2, 5 and 6 applies no
     transition and reports who holds it;
   - resolved: each of them applies no transition and reports it resolved.
9. **Somebody else takes it in between.** The fake assigns the ticket to another
   account after `Accept` is applied and before the claim. Then:
   - `Start Progress` is not applied;
   - the claim is refused naming that account, which shows the re-check of row
     `1b` used the fresh read;
   - the ticket is left in `To Do`;
   - the output says it was moved out of `Triage`.

   Likewise, if the fake resolves the ticket in between, the claim is refused as
   resolved.
10. **Misconfigured or wrong destination.** Each of these applies no transition,
    and its refusal names `work.tracker.pre-backlog.Triage`:
    - `pre-backlog: {Triage: Approve}`, not offered: the refusal lists what the
      ticket offers;
    - `Accept` leading to a status other than `statuses.backlog`;
    - `Accept` offered twice: the refusal names both ids.
11. **The step is chosen by status, not by transition name.** A ticket in a
    status that is not a `pre-backlog` key, but that also offers a transition
    named `Accept`, does not have `Accept` applied. The claim proceeds, or
    refuses, exactly as it does today. The same key written as `triage` still
    matches a ticket in `Triage`.
12. **Failures keep pending and conflicting apart**, checked through `deliver`'s
    recorded `state`:
    - tracker unavailable before or during `Accept`: pending;
    - `Accept`'s response does not say whether it applied, and the read-back
      shows `To Do`: the claim proceeds;
    - `Accept` applied, then the read-back fails: pending, and the reason says
      `Accept` was sent;
    - read back and not in `To Do`: conflicting, naming where it is.
13. **Partial success is reported.** `Accept` is applied and then the claim
    raises `TrackerError`, for example the tracker becomes unreachable. The
    output of `deliver`, strict `start` and `import` each still says the ticket
    was moved out of `Triage`.
14. **Resuming after the claim fails.** With `Accept` applied and `Start
    Progress` then refused by the tracker, the ticket is left in `To Do` and the
    output says it was moved out of `Triage`. Then:
    - for criteria 2-4 and non-strict `start`, a following `tcw work tracker
      sync` finishes the claim with no second `Accept`;
    - for strict `start`, the item is still in `backlog` and no sync record is
      written. Running `tcw work start` again finishes it with no second
      `Accept`;
    - for `import`, running the same `import` again finishes it with no second
      `Accept`.
15. **Only where a claim is made.** With `pre-backlog` set and the ticket in
    `Triage`:
    - (a) `submit`, `rework` and `complete` of an item with **no claim owed**
      apply no `Accept`. This holds with no sync record, and with a record
      whose move is not `start`;
    - (b) a `submit` of an item with a claim **owed** — a `catch-up: true`
      binding, and separately a sync record whose move is `start` — applies
      `Accept` then `Start Progress`, as the claim it owes;
    - (c) a discard applies no `Accept`;
    - (d) a part-bound `tcw work tracker sync` that only reports applies no
      transition at all;
    - (e) `tcw work tracker claim <slug>` applies no transition. It assigns
      only, and leaves the ticket in `Triage`;
    - (f) `tcw work tracker import <KEY>` of a ticket already bound here takes
      its existing short-circuit (`cli.py:2407-2430`) and applies no transition.
16. **Without the setting**, every case below applies no transition:
    - the reporter's case (criterion 3's setup) still refuses, and its message
      contains `work.tracker.pre-backlog`;
    - criterion 6's setup still refuses, and its message contains
      `work.tracker.pre-backlog`;
    - a claim transition that itself leads to an unmapped status (the workflow
      in `test_a_claim_landing_off_the_ladder_stops_the_catch_up`) is refused
      **without** that sentence.

    With `pre-backlog` set, `tcw work tracker show <KEY>` on a ticket in
    `Triage` prints a `note:` line naming `Accept`.
17. The full test suite passes, run as CI runs it (bare `pytest`).

Every new assertion is mutation-checked before it is trusted. Each of these must
turn its criterion's test red, for the reason the test claims:

- removing the step;
- moving it after the claim;
- having the claim reuse the snapshot from before the step;
- deciding the step by transition name instead of by status.

## Risks

1. **Two writes, not one.** Taking a ticket out of triage and claiming it cannot
   be atomic. A claim that fails in between leaves the ticket in the backlog
   status. That is resumable and reported (criteria 13 and 14), but the ticket
   has still left the triage list. Accepted: the alternative is no way out of
   triage at all.
2. **An unassigned ticket is moved before anyone holds it.** On a workflow where
   two people race for a Triage ticket, both may apply `Accept`. The second
   finds it already in `To Do` and carries on, and the existing claim rules,
   run against a fresh read, decide who ends up holding it (criterion 9). No
   worse than two people accepting it by hand.
3. **C4 can silently undo this.** It deletes one of the three callers and moves
   another off the function this item changes. Its new `owed` is also false for
   the reporter's case. Criteria 2-5 and 7 are the tests that go red if it
   does. The blocker the team lead is recording is the lasting protection.
4. **A misconfigured status name does nothing.** A `pre-backlog` key that
   matches no real status is simply never matched, and TCW cannot tell that
   without the workflow definition. The row-`1f` refusal still carries the hint,
   so the user is pointed back at the key.
5. **Line numbers are moving.** Other items are editing `tcw/tracker/` and
   `tcw/work/cli.py` in this checkout, so the plan should re-derive every
   citation.

## Settled after review

Codex and an Opus reviewer both read the first draft and recommended
proceeding, with changes. These four were open questions, and are now decided:

1. **Scope: all five entry points** — `start`, `link --sync-status`, `sync`,
   `tracker import` and `inbox accept`. They share one claim and one defect.
   Three carve-outs are explicit:
   - `tracker claim` stays ownership-only;
   - `tracker create` is unaffected;
   - `import`'s short-circuit for an already-bound ticket is kept.
2. **The step lands exactly on `statuses.backlog`.** This gives TCW something to
   check before sending and again after. It makes `statuses.backlog` required
   with the key, and costs only a workflow whose way out of triage skips the
   backlog, which can map its backlog accordingly.
3. **The key is `pre-backlog`**, documented as "tracker status → transition
   name to the configured backlog".
4. **A separate status-movement function, called by `intake.claim` for now.**
   This keeps the ownership primitive free of status movement, and fits the
   fact that `claim` already applies `transitions.start`. The item lands first
   and is recorded as a blocker of C4, which the team lead is doing, together
   with the C4 plan amendment.

## Open questions

None outstanding.

## Notes

- `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`
  lists the moves `tcw validate` should check against the real workflow. It
  should add one per `pre-backlog` entry: the named transition is offered from
  that status and leads to `statuses.backlog`.
- GitHub #40 asked for `work.tracker` to name the transition for a status move,
  and shipped as `transitions.submit`/`rework`/`complete`/`discard`. This item is
  its sibling: a named transition, but for a hop *out of* a status that no local
  move maps to, which is why it is keyed by status rather than by move.
- The stage instructions ask for `spec.md` to be committed on its own. The team
  lead's instructions for this run forbid committing, so it is left uncommitted
  for the lead to commit.
