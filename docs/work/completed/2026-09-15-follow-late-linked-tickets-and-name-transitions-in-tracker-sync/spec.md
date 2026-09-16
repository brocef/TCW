# Spec — Let tracker sync name its transitions, bring a late-linked ticket forward, and stop reading ordinary moves as drift

## Capability changes

**Changed — `work/synchronize-external-tracker-work`** (`cap-207f2c`). Three
sentences of the standing entry stop being true and are rewritten, not added to:

- "If someone else holds it, **it is unassigned**, it was moved on in Jira, or its
  workflow does not offer **exactly one transition** to the status I mapped, TCW
  leaves it alone" — an unassigned ticket is now moved by a discard, and a workflow
  with two transitions to the mapped status is served by naming one.
- "`sync` acts only on items I started" — it still acts only on those, but no longer
  reports success when it acted on none.
- The `Limits I accept:` paragraph loses nothing and gains the chaining bound (§ D.2).

No new capability, and none removed. `work/require-tracker-backed-work` is
unchanged: strict mode's rules are untouched by this item (see § Problem 5).

## Reproduction

Every reproduction below was run against this tree at spec time, with the
`tests/tracker_fake.py` fake and the `tests/test_tracker_sync.py` harness
(`make_node`, `bound_item`, `deliver_now`). The quoted text is what the code
actually printed, not what the report recalled.

**1 — two transitions to the same status.** A workflow offering
`("31","Finish","Done")` and `("32","Abandon","Done")` from `In Progress`; item
started, then completed as `done`:

> `SYNC-1 offers more than one transition to 'Done' (ids 31, 32); TCW will not guess which.`

State `conflicting`; `fake.writes() == []`. `complete` can never sync on this
workflow, and no setting changes that.

**2 — an item linked after it was started.** Item created, `start`ed, *then*
`tcw work tracker link`ed; ticket assigned to the caller but still in `To Do`;
`submit`:

> `SYNC-1 is in 'To Do', not 'In Progress'; it was moved in the tracker, or TCW held it there for another part of the ticket whose item is not in this checkout. TCW does not move it back: put it in 'In Progress', or move it on by hand.`

Nobody moved it. The record written is
`{state: conflicting, move: submit, since: 'In Progress', claim: done, …}` — `since`
names a status the ticket was never in, and `claim: done` asserts a claim that never
happened. With the ticket *unassigned* instead, the assignment check fires first and
the message is `SYNC-1 is assigned to nobody, not to you`; the record still says
`claim: done`.

**3 — two failed moves, then a hand move.** `submit` and then `complete` both fail
with the tracker down, leaving
`{state: pending, move: complete, since: 'In Progress', claim: done}`. A person then
moves the ticket by hand to `In Review`. The next sync:

> `SYNC-1 is in 'In Review', not 'In Progress' or 'Done'; it was moved in the tracker, …`

`In Review` is the mapped `review` status — between where the record started and
where it was going — and is reported as drift.

**4 — `sync` on an item owned by someone else.** Item started by
`b@example.test`, claim failed with the tracker down, so
`{state: pending, move: start, claim: owed}`. `a@example.test` then runs
`tcw work tracker sync <slug>`:

> `2026-09-15-bound-item: skipped — started by b@example.test`

Exit code **0**, and the record is still there, still `owed`. Under strict mode
`binding_refusal` (`tcw/tracker/sync.py:343-347`) refuses `submit` while any record
exists and says to run `sync`; `sync` then succeeds having done nothing.

**5 — discarding unstarted work.** A backlog item linked to an unassigned ticket in
`To Do`, completed as `wontfix`:

> `SYNC-1 is assigned to nobody, not to you, so it was not moved from 'To Do' to 'Won't Do'.`

`fake.writes() == []` and the ticket is still `To Do`. It stays open with no
resolution.

## Problem

1. **Ambiguous transitions are refused rather than resolved.** `assess_move`
   (`tcw/tracker/sync.py:115-124`) collects the offered transitions whose
   `to_status` matches the target and refuses when `len(leads) > 1`. The only
   transition a project may name is the claim:
   `TRACKER_TRANSITION_KEYS = frozenset({"claim"})` (`tcw/store/base.py:1086`),
   parsed at `base.py:1150` and `1193` into `TrackerConfig.claim_transition`
   (`base.py:1058`). A `Done` reachable by both a "finished" and an "abandoned"
   transition is the shape the reporter has, and it is unreachable.

2. **A late-linked ticket is judged against a history it never had.** `link` writes
   no sync record (`_BINDING_KEYS`, `tcw/tracker/intake.py:180`, is written by
   `binding_document`; only `deliver` writes `sync`). With no record,
   `expected_statuses` (`sync.py:90-92`) derives the expectation from the item's
   *previous local status* through `_EARLIER` (`sync.py:41`) — so an item linked
   while already `active` is expected to have a ticket in `In Progress`, which was
   never true. The refusal at `sync.py:105-112` then asserts "it was moved in the
   tracker", and `finish` (`sync.py:203-210`) stamps `claim: "owed" if owed else
   "done"` with `owed` false (`sync.py:167`), recording a claim that never occurred.

3. **Expectation is two points, not a path.** With a record, `expected_statuses`
   (`sync.py:76-89`) returns exactly `since` plus the target of the recorded move.
   Any mapped status *between* them — reached by a person doing by hand what TCW
   failed to do — is outside the set and is reported as drift by `sync.py:105-112`.

4. **`sync` reports success for work it did not do.** `_tracker_sync`
   (`tcw/work/cli.py:2236-2239`) prints `skipped — started by …` and `continue`s
   without touching `code`, so the command exits 0 with the record untouched. The
   guide already documents this as "exits 1 while any item **it acted on** is still
   pending" (`docs/guide/jira.md:366-368`), so the code matches the document and
   both are wrong together: combined with `binding_refusal`'s "run sync" advice, a
   strict-mode item whose claim is owed by an absent colleague cannot be moved on by
   anyone present, and nothing reports a failure.

5. **An unassigned ticket is treated as one somebody holds.** `assess_move`
   (`sync.py:101-104`) refuses whenever `assignee_id != me_id`, collapsing "nobody"
   and "somebody else" into one refusal, before it knows which move it is serving.
   The strict-mode path is **not** implicated: `_strict_refusal` is called only when
   `shipping` (`tcw/work/cli.py:2418`, commented "Discards are never refused"), so
   `authorize`'s "discarding the item is always allowed" (`sync.py:378-379`) is
   already true. The defect is confined to delivery.

**Sibling defects found by the sweep** (repo-wide over `tcw/tracker/` and the CLI's
tracker paths):

- `tcw/tracker/progress.py:121-125` repeats the unassigned/held conflation for the
  progress comment: a discard that begins moving an unassigned ticket under § 5
  would move it and then skip its comment, for a reason that is no longer true.
  In scope — it is the same defect in the same feature, reached by the same move.
- `tcw/tracker/intake.py:151` and `tcw/tracker/claim.py:99` also refuse on "more
  than one match", but of *bindings* and of *claim-transition names* respectively.
  Neither is this defect: a ticket bound to two items for one part, and a claim name
  matching two transitions, are genuinely ambiguous inputs with no mapping to
  disambiguate them. Out of scope, deliberately.

## Goals

1. A project may name the transition a move uses, for every move, not only the claim.
2. A ticket linked to work already under way can be brought to where the item is.
3. A hand move to a status between where a record started and where it was going is
   accepted, not reported as drift.
4. `tcw work tracker sync` never exits 0 having left a record it was asked to clear.
5. A discard moves an unassigned ticket; every other move still refuses one.
6. Messages and records say what actually happened: no invented `since`, no
   `claim: done` for a claim nobody made, no "it was moved in the tracker" about a
   ticket nobody moved.

## Non-goals

- Assigning an unassigned ticket to the caller before a move (GitHub #41's other
  option), and moving an unassigned ticket for any move but a discard.
- Moving a ticket assigned to a **different** account, under any move.
- Changing what strict mode refuses (§ Problem 5) or how claims are assessed.
- Checking a workflow against the `statuses` mapping ahead of time — GitHub #44,
  tracked in `2026-09-15-check-the-tracker-s-workflow-against-the-statuses-mapping-in-tcw-validate`.
- Staged records blocking a worktree merge-back — tracked in
  `2026-09-15-harden-tracker-binding-reads-and-writes-and-jira-response-parsing`.
- TCW following the tracker, or pulling a ticket **back** to an earlier status.
  Chaining (§ D.2) only ever moves a ticket forward.
- Any change to `tcw serve`'s transitions, which still deliver nothing.

## Design

`deliver` keeps its shape: one decision from a fresh ticket read, no side effect
until a transition is applied, a record for what did not reach the tracker. The
central change is that **the ordering the module already knows is written down once**.
`_EARLIER` and `_MOVED_FROM` (`tcw/tracker/sync.py:41-45`) are two hand-written
projections of one ladder, and `expected_statuses` reads them as a two-element guess
rather than as a path. One ladder replaces both, and is then used twice: to walk a
ticket forward, and to decide what counts as drift. That shared concept is why
defects 1, 2 and 3 belong in one item rather than three.

### D.0 The ladder

From the configured mapping alone, in local lifecycle order:

| Rung | Mapped status | The move that lands there |
| ---- | ------------- | ------------------------- |
| 1 | `statuses.active` | the claim (`transitions.claim`), or `rework` from above |
| 2 | `statuses.review` | `submit` |
| 3 | `statuses.completed`, or `statuses.discarded` for the resolution | `complete` / `discard` |

A status mapped to nothing has no rung and is skipped. Two local statuses mapped to
the *same* tracker status share a rung, so the walk has one fewer hop — which is
correct. A ticket whose status is on no rung (`To Do`, `Blocked`) is **off the
ladder**; off-the-ladder-below is the ordinary starting point, and the hop onto rung 1
is the claim rather than a ladder hop, because `To Do` appears nowhere in `statuses`
and only `transitions.claim` names the way out of it.

### D.1 A project may name the transition each move uses

`TRACKER_TRANSITION_KEYS` (`tcw/store/base.py:1086`) grows from `{claim}` to
`{claim, submit, rework, complete, discard}`, keyed by **move**, not by status:

```yaml
transitions:
    claim: Start Progress
    complete: Finish
    discard:
        wontfix: Abandon        # sets Jira's "Won't Do" resolution
        duplicate: Mark Duplicate
```

**Keyed by move, departing from the reporter's suggestion of status keys.** `active`
is reached by two different moves from two different places — `MOVE_STATUS`
(`sync.py:38-39`) maps both `start` and `rework` to it — and they are normally
different transitions ("Start Progress" from `To Do`; "Back to Progress" from
`In Review`). A single `transitions.active:` cannot name both, so status keys are not
expressive enough for the ambiguity the feature exists to resolve. Move keys also
name exactly what a walk hop needs (D.2).

**There is no `start` key, deliberately.** A `start` sets `starting`/`owed`
(`sync.py:166-167`) and returns from the claim path at `sync.py:266` without reaching
`assess_move`; `transitions.claim` already names it. Said here so the absence does not
read as a gap.

`TrackerConfig` gains `move_transitions: dict`, read through a
`transition_name(…, move, resolution)` accessor shaped like the existing
`target_status`. `tcw validate` checks shape only: a non-empty string, or for
`discard` a mapping whose keys are known resolutions. **Unlike `statuses.discarded`
under strict mode (`base.py:1176-1182`), a partial `discard` mapping is allowed** —
`transitions` is an optional override that exists to disambiguate, so naming only the
ambiguous resolutions must work. `nested()` already reports an unknown key.

Selection inside `assess_move`:

- **A name is configured** → matched against `ticket.offered` by the existing
  `_normalize`. Exactly one match **that leads to the target** is applied. No match,
  two matches, or a match leading elsewhere is **conflicting**, naming what was
  configured and what the ticket offers; `claim.py:100-110`'s `AMBIGUOUS` handling is
  reused for the two-match case. A named transition is never applied toward a status
  other than the mapped one: the module's whole model is that the ticket's status is
  compared with the mapped status to tell delivered from undelivered, so a transition
  landing elsewhere yields a ticket that never reads as delivered — the bug class
  under repair. Refusing before applying beats reading back afterwards, because
  applying a transition you already believe is wrong is irreversible.
- **No name configured** → today's rule verbatim: exactly one offered transition to
  the target, and `len(leads) > 1` stays conflicting with today's message. This is the
  request's explicit constraint, and it keeps
  `test_no_transition_or_two_to_the_target_is_conflicting` passing untouched.

A configured name that is simply never offered is **refused, not ignored**: silently
falling back would make a typo'd transition name invisible for ever, which is the
failure `base.py:1084-1085` already argues against.

### D.2 Bringing a ticket forward — triggered by the owed claim, not by position

**The trigger is `claim == "owed"`, not "the ticket is behind".** Direction alone is
not enough, and `sync.py:82-83` already says why: a wider rule "would let a ticket
someone sent back to active be carried forward". A ticket TCW claimed and moved to
`In Review` that someone then pushed back to `To Do` is *behind*, and must stay
refused. A ticket TCW has never held is a different thing, and the record already
carries that distinction — `claim: owed` means exactly "TCW has not observed a
successful claim for this binding". No new field, and no new value in a validated
enum (see Risks).

So: when the claim is owed and the ticket is below the target, TCW walks it forward —
the claim onto rung 1, then one hop per rung, each hop's transition selected by D.1
using the move that lands on that rung. Each hop re-reads the ticket, because what a
workflow offers depends on where the ticket is. This is a generalisation of the
two-phase shape `deliver` already runs for an owed claim (`sync.py:234-274`: claim,
reset expectation to `active`, re-read, then assess), not a new mechanism.

- **Bounded by construction.** Three rungs, so at most three hops, each strictly
  higher. It terminates with no depth counter.
- **Forward only.** A ticket at or above the target is never walked; TCW still never
  pulls a ticket back.
- **Only through mapped statuses.** A workflow's `Blocked` or `Cancelled` is never
  entered by TCW guessing a route.
- **A hop that fails stops the walk** and reports conflicting, naming the hop, where
  the ticket now is, and how far it got. The partial walk is not undone — the ticket
  is nearer where it belongs — and because every resting place is a *mapped* status,
  the record describes it in today's fields (`since` = the status actually read,
  `move` = the item's move, `claim` = `done` once the claim hop landed) and a later
  `sync` resumes from there.

**Why not a bounded search over the transition graph.** It would traverse a workflow
with a mandatory unmapped intermediate, which the ladder cannot (see Risks). It is
rejected anyway because it is non-deterministic — the same configuration yields
different transition sequences on different tickets, chosen by graph shape — and
every step is irreversible. A rung is a value that fits the existing record; a search
frontier is not, so a half-finished search could not be described in the fields a
non-filesystem store has.

**`link` writes a local record when it binds an item past `backlog`.** Without it the
repair is unreachable from the command the reporter actually ran: `sync --all` selects
only items that already carry a `sync` or `comment` record (`tcw/work/cli.py:2221-2223`),
and `sync <slug>` on a recordless item runs with `check_only=True` (`cli.py:2249`) and
refuses at `sync.py:279-282`. The record is
`{state: pending, move: <the move that lands on the item's own status>, since: "",
claim: owed}` — valid under today's `_sync_record` (`base.py:417-435`), and literally
true: the ticket is not where the item is, and no claim has been observed. It is a
**local** write, so `link`'s promise that the ticket is unchanged in the tracker — kept
by `2026-09-14-make-tracker-link-record-a-cross-reference-without-claiming-the-ticket`,
completed the day before — survives intact. Linking an item still in `backlog` writes
nothing, so the ordinary case is unchanged.

`since` is never fabricated. The `_MOVED_FROM` fallback that invents a starting status
(`sync.py:84-85`) is not consulted while the claim is owed, which is behaviour-preserving
today: the only existing `claim: owed` record with an empty `since` comes from
`record_unsent` (`sync.py:313-316`), and there `deliver` overwrites the expectation in
the owed path (`sync.py:267-268`) before the fallback is ever read.

### D.3 Drift is judged against the path, not two points

The acceptance window becomes **the statuses TCW's own walk would pass through going
from the record's `since` forward to the move's target** — one function, two callers,
so every status the window admits is one the engine can actually advance from.
Direction is load-bearing: the window is anchored at `since` and runs *forward* only,
which is what keeps `sync.py:82-83`'s hole closed.

Problem 3 dissolves: a hand move to `In Review` while a record was heading for `Done`
lands on rung 2 with a target of rung 3 — inside the window — so TCW finishes the
journey instead of calling it drift.

A discard has no intermediates: `_MOVED_FROM["discard"] = ()` (`sync.py:45`) already
records that a discard can start anywhere, so for `move == "discard"` the window is
`{since, target}`.

Where two local statuses map to one tracker status — `completed: Done` and
`discarded: Done`, which is GitHub #40's own configuration — a status name cannot be
inverted to a single rung. The window is therefore computed by walking the path from
`since` toward the target and collecting what it passes, never by inverting the
mapping.

### D.4 An unassigned ticket, and only a discard

`assess_move` takes the move it is serving — which it needs anyway for D.1 and D.2 —
and the policy is a named constant, `MOVES_ALLOWING_UNASSIGNED = frozenset({"discard"})`:

- assigned to the caller → proceed, as today;
- **unassigned** → proceed **only** for `discard`; otherwise conflicting, with a
  message that says the ticket is unassigned and that claiming it is the way forward,
  rather than implying somebody holds it;
- **assigned to another account** → conflicting for every move, `discard` included,
  unchanged.

**Two downstream sites re-apply the assignment rule and would undo the fix.**

1. **The post-transition read-back.** `sync.py:292` accepts the result only when
   `again.status == target and again.assignee_id == again.me_id`. A ticket that was
   never assigned still is not, so a *successful* discard falls through to
   `sync.py:296-297` and reports `"… did not reach 'Won't Do': it is in 'Won't Do'."` —
   a self-contradicting message and a `conflicting` record that can never clear. The
   clause is relaxed exactly as the owed short-circuit at `sync.py:236` already relaxes
   it, to `local in RESOLVED_STATUSES or again.assignee_id == again.me_id`, so the shape
   is one the module already uses rather than a new exception.
2. **The progress comment.** `tcw/tracker/progress.py:121-125` skips the comment for an
   unassigned ticket *and clears the owed record*, so without this the reporter's 115
   tickets would close with no note saying why. The same discard exception applies in
   `_send`.

Strict mode is untouched, and deliberately so: `_strict_refusal` is never called for a
discard (`tcw/work/cli.py:2416-2418`, "Discards are never refused — abandoning work
authorizes none"), so `authorize`'s "discarding the item is always allowed"
(`sync.py:378-379`) is already a true statement about the CLI rather than a promise
`authorize` keeps itself. Adding an `allow_unassigned` there would be dead code. Said
explicitly so a later reviewer does not "fix" it back.

### D.5 `sync` stops reporting success for work it did not do

The skip in `_tracker_sync` (`tcw/work/cli.py:2236-2239`) keeps its message, adds the
record's state and that it is still owed, and sets `code = 1` — **for an explicitly
named slug only.** `--all` is a sweep and stays exit-0 over other people's items;
making a team-wide sweep fail because a colleague owns something would be noise, and
the deadlock in Problem 4 is a user asking about *one* item and being told it
succeeded. The single loop at `cli.py:2234-2238` is split so the two cases can differ.

`binding_refusal`'s "Run `tcw work tracker sync <slug>` first" (`sync.py:345-347`)
names `TCW_WORK_OWNER=<owner>` alongside it, which it can do because it already takes
the store and can read the item's owner. That closes the loop the deadlock runs in.

Delivery is still **not** attempted for another owner's item: `sync` acts as whoever
runs it, and taking a colleague's ticket is not a side effect a retry should have.
No new flag — `TCW_WORK_OWNER` and `tcw work start --take-over` already exist and are
documented.

### D.6 Records and messages say what happened

- `claim` is `owed` whenever TCW has not observed a successful claim for the binding,
  rather than defaulting to `done` when there is no record (`sync.py:167`, `206-207`).
- `since` holds a status actually observed, or is empty. Never a computed one.
- The "it was moved in the tracker" explanation survives only for the ahead-or-elsewhere
  case, where it is true. A ticket that is merely behind is no longer reported — it is
  moved.

### D.7 Two statements that stop being true

Both are specification in this repo, and are work rather than cleanup:

- the module docstring `sync.py:10-14` — "A ticket is moved only when it is assigned to
  the account the credentials authenticate as and sits where the item's previous status
  left it";
- the comment at `base.py:1082-1085`, which is the standing rationale for `claim` being
  the only named transition.

## Abstraction litmus test

| Operation | Verdict |
| --------- | ------- |
| Name a transition per move in node configuration | **Model.** Node configuration, exactly as `transitions.claim` and `statuses` already are. |
| Order mapped statuses into a ladder (D.0) | **Model.** A pure function of the configured mapping and the local status order. |
| Walk a ticket forward hop by hop (D.2) | **Model.** Reads and transitions against the tracker — itself the non-filesystem store this test protects. |
| Decide the acceptance window from the path (D.3) | **Model.** Pure, over the ladder and one ticket read. |
| Serve the move to the assignment check (D.4) | **Model.** The move is already a parameter of delivery (`MOVE_STATUS`, `sync.py:38`). |
| `link` writing a record for an item past `backlog` (D.2) | **Model.** A named field on the binding, written through `write_sidecar` as every binding write already is. |
| `sync`'s exit code for a named slug (D.5) | **Model.** A command result derived from outcomes the store already returns. |

**No new store operation and no new persisted field.** The record keeps its shape
(`state/move/since/claim/reason/at`); only which values are written changes.

Four ways an implementation could still fail the test, named so the plan can avoid
them:

1. **Inferring "linked late" from history or timestamps** — reading git for when
   `tracker.yaml` appeared, or comparing the binding's `bound:` date with the item's.
   The first is the violation `abstraction.md` names outright ("state is the status;
   git is archive"); the others are inference a tracker-backed store has no analogue
   for. The state is a field, and `claim: owed` is that field (D.2).
2. **Deciding "is the ticket behind?" from anything but item status, mapped statuses
   and the record** — anything that enumerates the item's folder, or knows items live
   in status directories, fails. `_siblings` (`sync.py:131-147`) is the model to copy:
   it queries and compares fields.
3. **Pushing owner resolution downward.** `_local_owner` (`cli.py:884-896`) shells out
   to `git config` — a git leak correctly confined to the CLI. D.5 must not move owner
   logic into `tcw/tracker/`; pass a string if `binding_refusal` needs to name it.
4. **A walk whose partial state is not expressible as fields.** D.2 rests on every
   resting place being a mapped status, so "halfway" is a value.

## Acceptance criteria

Each is checkable against `tests/tracker_fake.py` with the `tests/test_tracker_sync.py`
harness, except where it names a file to read.

**Naming a transition (D.1)**

1. With a workflow offering `("31","Finish","Done")` and `("32","Abandon","Done")` from
   `In Progress`, and `transitions.complete: Finish`, `tcw work complete --resolution
   done` on a bound item leaves the ticket in `Done`, applies transition `31` and no
   other, and writes no record. Reproduction 1 is the same scenario without the
   configured name and must still be conflicting.
2. With the same workflow and `transitions.discard: {wontfix: Abandon}`, a
   `--resolution wontfix` discard applies transition `32` and no other.
3. A `discard` mapping naming only `wontfix` parses without problems, and a
   `superseded` discard on it falls back to the unnamed rule. `tcw validate` reports no
   problem for that config, and reports one for `transitions.submit: 5` and for
   `transitions.discard: {nonsense: X}`.
4. `transitions.complete: Nonexistent` produces a **conflicting** outcome naming the
   configured transition and what the ticket offers, with `fake.writes() == []` — not a
   silent fall back to the unnamed rule.
5. `transitions.submit: Finish` where `Finish` leads to `Done` and `statuses.review` is
   `In Review` produces a conflicting outcome **before** any transition is applied
   (`fake.writes() == []`).
6. `test_no_transition_or_two_to_the_target_is_conflicting` passes unmodified.

**Bringing a ticket forward (D.2)**

7. Reproduction 2 — an item created, started, then linked, ticket assigned to the
   caller and still in `To Do` — reaches `In Review` after `tcw work submit`, and the
   item's binding carries no record afterwards.
8. The same with the ticket **unassigned**: `submit` claims it, walks it to
   `In Review`, and leaves no record.
9. `tcw work tracker link` on an item in `active` writes
   `{state: pending, move: start, since: "", claim: owed}`, and the same command on an
   item in `backlog` writes no record at all.
10. `tcw work tracker sync <slug>` on the item from criterion 9 brings the ticket
    forward and clears the record — i.e. the repair is reachable from `sync`, not only
    from a lifecycle move.
11. A ticket TCW claimed and moved to `In Review` that is then moved **back** to
    `To Do` by hand, with a record whose `claim` is `done`, is still **conflicting** on
    the next move, and `fake.writes() == []`.
    `test_a_ticket_moved_elsewhere_in_the_tracker_is_not_pulled_back` passes unmodified.
12. A walk whose second hop has no usable transition leaves the ticket at the rung it
    reached, reports conflicting naming that rung, and writes a record whose `since` is
    the status actually read.

**Drift as a path (D.3)**

13. Reproduction 3 — `submit` then `complete` both failed, then a hand move to
    `In Review` — ends `current` with the ticket in `Done` and no record.
14. With `completed: Done` and `discarded: Done` both mapped, criterion 13 still holds
    and no window is computed by inverting the mapping.

**Unassigned and discard (D.4)**

15. Reproduction 5 — a backlog item linked to an unassigned ticket, discarded as
    `wontfix` — leaves the ticket in `Won't Do` and writes no record. In particular the
    outcome is `current`, not `"… did not reach 'Won't Do': it is in 'Won't Do'."`
16. The same item submitted rather than discarded is still conflicting, and its message
    says the ticket is unassigned and names claiming it — it does not say somebody else
    holds it.
17. A ticket assigned to **another** account is still conflicting for `discard` as for
    every other move.
18. With `comments: true`, the discard in criterion 15 posts its progress comment
    rather than skipping it.
19. `test_a_ticket_not_assigned_to_you_is_never_moved` is narrowed: its
    `(assignee=None, move="discard")` case is removed from the parametrisation and
    replaced by criterion 15; the `assignee=B` cases and the non-discard `assignee=None`
    cases pass unmodified.

**`sync`'s exit code (D.5)**

20. Reproduction 4 — an item owned by `b@example.test` with a record, `sync <slug>` run
    by `a@example.test` — exits **1**, and the message names the record's state and
    `TCW_WORK_OWNER`.
21. `sync --all` over a board containing that item and one clean item of the caller's
    exits **0**.
22. `binding_refusal`'s refusal text names `TCW_WORK_OWNER` and the item's owner.

**Everything else**

23. `pytest tests/` passes with no test deleted except as criterion 19 describes, from a
    baseline of 3367 passed / 2 skipped.
24. `docs/guide/jira.md` no longer says a ticket is moved only when it offers exactly
    one transition to the target, no longer says `sync` "exits 1 while any item it acted
    on is still pending" without the named-slug rule, and documents the new
    `transitions` keys and the catch-up.
25. The capability entry `work/synchronize-external-tracker-work` matches the shipped
    behaviour on the three sentences named under **Capability changes**.
26. `sync.py`'s module docstring and `base.py:1082-1085`'s comment no longer assert what
    D.7 says becomes false.

## Risks

- **Chaining applies transitions the user did not individually ask for, to a shared
  system.** Each hop can fire notifications, automations and SLA clocks in a tracker
  other people watch. It is bounded to three hops through statuses the project itself
  mapped, and gated on an owed claim so it only ever runs on a ticket TCW has never
  held — but this is the part of the item with real blast radius, and it lifts a
  non-goal a shipped spec set deliberately. It should be the last thing implemented and
  the most heavily verified.
- **The ladder cannot traverse a mandatory unmapped intermediate status.**
  `In Progress → Code Review → In Review`, with `Code Review` absent from `statuses`, is
  an ordinary Jira shape, and the walk refuses it where a graph search would not. The
  remedy is to map the status or move the ticket by hand once, and the guide must say
  so. This is a deliberate trade of reach for predictability.
- **`link` on an active item starts writing a record, which strict mode then blocks on.**
  `binding_refusal` (`sync.py:343-347`) refuses `submit` while any record exists, so a
  freshly linked active item under strict mode must be synced before it can be
  submitted. That is arguably correct — strict mode means no work without a claimed
  ticket, and it is not claimed — but it is a behaviour change, and criterion 9 plus the
  guide have to state it.
- **The record schema is a closed validator shared across checkouts.** `_sync_record`
  (`base.py:417-435`) turns an unrecognised `state`, `move` or `claim` into
  `{"problem": …}`, so a record written by a newer `tcw` would read as broken to an
  older one against the same store. Every decision above is built to need no schema
  change; if one becomes unavoidable it must be additive and ignored, never a new value
  in a validated enum.
- **Five defects in one item is a wide blast radius for one review.** 1, 2 and 3 share
  the ladder and would otherwise be written three times, which justifies bundling them;
  4 and 5 are small and independent. The plan must sequence them so the shape shows —
  4 and 5 first (no new configuration, independently verifiable), then 1 (schema,
  validation, docs, no chaining), then 2+3 (the ladder). If anything slips, 2+3 is what
  should slip, and an interleaved plan makes that impossible.
- **Two transitions landing in one status cannot be told apart after the fact.** With
  `completed: Done` and `discarded: Done`, a ticket in `Done` reads as delivered for
  either, so a mis-sent `complete` cannot be detected by re-reading. Naming the
  transitions is what prevents it being sent wrongly in the first place; nothing
  detects it afterwards, and the guide should not imply otherwise.

## Notes

**Alternatives considered and rejected.**

- *A bounded search over the transition graph*, instead of the ladder walk. Rejected in
  D.2: non-deterministic across tickets, irreversible at every step, and its partial
  state is not expressible in the record's fields. It would, however, handle the
  unmapped-intermediate workflow the ladder refuses — that is the trade, stated.
- *Chaining behind an opt-in flag* (`--catch-up`). Rejected: GitHub #42's reported path
  is a plain `tcw work submit`, so a flag leaves it broken, and nothing would tell a
  user the flag exists.
- *Using a configured transition name only to break a tie*, leaving the unnamed rule in
  charge otherwise. Rejected in D.1: it makes a typo'd name invisible for ever.
- *Attempting delivery on another owner's item* in `sync`, instead of exiting 1. There
  is a real argument for it — the local owner check protects nothing the tracker does
  not protect better, since `assess_move` would refuse a ticket assigned to somebody
  else with a message naming them, and `sync --all` already writes sidecars into other
  owners' items. It is recorded here rather than adopted because the folded-in review
  entry asked for the exit code, the exit code is reversible, and taking a colleague's
  ticket as a side effect of a retry is not. A later reviewer should not have to
  rediscover the argument.
- *Adding a third `claim` value* (`never`) to distinguish never-claimed from
  claim-failed. Rejected: `_sync_record` is a closed validator and the store is shared,
  so a new enum value breaks older readers. `owed` already carries the meaning.

**On the sibling sweep.** `tcw/tracker/intake.py:151` and `tcw/tracker/claim.py:99` also
refuse on "more than one match", and are deliberately left alone: a ticket bound to two
items for one part, and a claim name matching two transitions, are ambiguous *inputs*
with no mapping available to disambiguate them, not the ambiguous *workflow* this item
is about.

**Deferred with a stated reason.** The originating GitHub issues #40, #41 and #42 stay
open until the fix is published, per `CLAUDE.md` ("Closing the originating GitHub issue
waits for publication"); the completion criterion in `docs/work/dod.yaml` is recorded as
deferred in `refined-outcome.md` when this item completes.

## Revision after review (2026-09-16)

Recorded by hand while TCW's own code was being changed, so no lifecycle command ran.
Review of pull request #45 — an adversarial code review and a Codex review — found
that the walk could pull a ticket back, could move an already-closed ticket to a
different closed status, and could not resume when more than one step remained. The
user then decided the direction of D.2, overriding this spec in two places:

- **Changing the ticket is opt-in.** In the user's words: "Relink should just create
  the TCW item <-> Jira ticket association by default, Jira ticket status changes are
  opt-in", and for a finished item, "Don't move it by default, but warn the user that
  the statuses are out of sync. Offer an optional capability to also update the Jira
  ticket status which will move it straight to the desired status, if possible, else
  do the full walk." This reverses the Notes' rejection of *chaining behind an opt-in
  flag*. The flag is `tcw work tracker link --sync-status`; it acts at link time by
  writing the D.2 record and delivering it at once, and whatever does not arrive
  stays recorded for `sync`.
- **`link` without the flag writes no record.** It notes `status-synced: false` on the
  binding — an additive key older versions ignore, as the Risks section requires — and
  warns when the ticket's status does not match. While that note stands, a later move
  that cannot follow is `held`, says the ticket was linked without its status synced,
  names the repair, and records nothing. That is what keeps GitHub #42's false
  "someone moved it" conflict gone without moving the ticket. Whether ordinary moves
  should catch such a ticket up on their own is left open for the user; they do not.
- **D.2's walk tries the direct transition first**, per the user's "straight to the
  desired status, if possible", and aims at the item's current status rather than
  the recorded move's.
- **D.2's "forward only" is now enforced before the claim**: a ticket already past its
  item is refused instead of claimed, and a resolved ticket is never walked.
- **D.5**: a named slug somebody else started exits 1 only when a record is owed.
- **D.6**: records written for bindings made by earlier versions are not rewritten.
  The documented repair is `unlink`, then `link --sync-status`.
