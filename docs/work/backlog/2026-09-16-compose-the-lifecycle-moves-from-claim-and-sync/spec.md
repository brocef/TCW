# Compose the lifecycle moves from claim and sync

**Second draft.** The first was rejected at review: its design answered the
easiest of the seven questions this change actually raises and hand-waved the
rest, and two of its acceptance criteria were unreachable from its own design.
The epic's C4 section has been amended to name all seven, and this spec answers
them in Design. What the review found is recorded in `## Notes`.

## Capability changes

No new capability. Seven existing ones change, all already `Supported`, so none
is seeded and none is flipped:

```yaml
changed:
    - work/start-a-work-item
    - work/submit-a-work-item-for-review
    - work/rework-a-reviewed-work-item
    - work/complete-a-work-item
    - work/discard-a-work-item
    - work/require-tracker-backed-work
    - work/manage-external-tracker-intake
```

## Problem

The five lifecycle moves each carry a private copy of reasoning the epic has
since given names to, and one entanglement sits under all of it: **taking a
ticket and moving it are the same operation.** `intake.claim` applies the
configured transition as part of claiming, so nothing can take a ticket without
moving it, and nothing downstream can tell a ticket that was claimed from a
ticket that merely arrived at the right status.

Everything below follows from that one fact.

**The claim happens twice, in unrelated code.** `_strict_claim`
(`tcw/work/cli.py:379`) takes the ticket before `start` moves the item, but only
under strict mode (`:387-392`). `deliver` claims again on its own terms
(`tcw/tracker/sync.py:590`). Both call `intake.claim`, so both move the ticket.

**`owed` exists only because a claim cannot be read back.** It is three terms
(`tcw/tracker/sync.py:328`): `starting`, `bound.catch_up`, and a record whose
`move` is `start`. All three are ways of remembering that a claim has not
happened, because the ticket itself could not be asked — its status conflates
"claimed" with "someone moved it here by hand".

**`expected` and `since` are set to `statuses.active`**
(`tcw/tracker/sync.py:625-626`) *because the claim transition has just put the
ticket there*. They are consequences of the entanglement, not decisions.

**Strict mode's exclusivity question is asked about the wrong transition.**
`claim_refusal` (`tcw/tracker/sync.py:809-831`) asks whether the workflow still
offers `config.start_transition` from where the claim landed — meaningful only
while the claim *is* that transition.

**A claim gates the wrong verbs.** Strict mode refuses `submit`
(`tcw/work/cli.py:1233`), `rework` (`:1262`), `complete` (`:3107`) and `drop`
(`:3228`). Gating `complete` means somebody who cannot take the ticket cannot
record that the work is finished.

**Outside strict mode a claim gates nothing.** `assess_move` refuses to move a
ticket held by another account (`tcw/tracker/sync.py:224-233`), but the item has
already moved and been committed by then; `_deliver_after` (`tcw/work/cli.py:1027`)
reports and does not undo it.

**An active item with no holder has no answer.** C1's `release` leaves one, and
`FsWorkStore.start` (`tcw/store/base.py:3507`) then raises
`AlreadyClaimed(slug, item.owner, item.started)` at `:3510` with an empty holder
name.

**Two flags take over somebody else's work**, and **`link --sync-status` is a
third way to say "claim this"** (`tcw/work/cli.py:2502`, `:2524-2530`).

## Goals

1. Taking a ticket and moving it become separate operations everywhere, not only
   in C1's verbs.
2. **A claim gates work, not resolution.** `submit` and `rework` require the
   ticket; `complete` and a discard do not.
3. The gate applies whether or not strict mode is set — the requester's decision.
4. `start` on an active item nobody holds takes the claim and succeeds.
5. One way to take over somebody else's work.
6. No fact is remembered that the ticket can be asked.

## Non-goals

- **The web app.** Out of scope for the epic, recorded rather than assumed.
- **Changing what `claim`, `release` or `sync` mean.** This item calls them.
- **`.claiming/`**, the filesystem staging behind the local claim
  (`tcw/store/fs.py:985`, `:3819-3849`, `:3888`). Adapter-private.
- **The catch-up walk's own defect**, which stays
  `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery`.
- **Making the local `owner` a permission.** The gate reads the ticket's
  assignee; an unbound item is not gated.
- **Widening `sync --all`**, a stated non-goal of C2.
- **Retiring `tcw/tracker/claim.py`'s `assess`.** `tracker show`'s claimability
  report and `tracker import` still ask its question. Only the lifecycle stops.

## Design

### 1. The already-yours branch becomes the only branch

`deliver` already contains the shape this item needs. At
`tcw/tracker/sync.py:565-582`, when the ticket is on the ladder and already the
caller's, it makes no claim, asks strict mode's question, sets
`since = ticket.status` and `expected = (ticket.status,)`, and carries on
delivering from where the ticket is.

The change is to make every path take that shape: **claim through C1's
`assert_ownership` when the ticket is not yours, then proceed exactly as the
already-yours branch does.** `assert_ownership` assigns and reads back without
applying any transition unless `work.tracker.exclusive-claim-transition` names
one, so after it the ticket is still where it was — which is the premise the
already-yours branch is written for.

This answers the epic's questions 2 and 3 together: `expected` and `since` become
the ticket's real status at claim time, for every path, because no path moves it.

### 2. `owed` is deleted, not replaced

Once a claim is an assignment, "has this ticket been held?" is a question the
ticket answers: `ticket.assignee_id == ticket.me_id`. No term of `owed` survives
because none is needed — `starting`, `catch-up: true` and a record naming `start`
were three ways of remembering something that can now be read.

This is why retiring `--sync-status` is safe here and was not safe for C2. C2
removed a *reader* of the fact while the fact was still unreadable, which is why
`owed = starting or bound.catch_up` failed. This item removes the reason the fact
had to be remembered.

`catch-up: true` therefore goes with `--sync-status`, and the binding key is
removed. **`status-synced` stays**: it is written by a plain `link` as well
(`tcw/work/cli.py:2517`), and it records something the ticket cannot answer —
that a binding was made to a ticket already out of step, so the mismatch is not
drift somebody caused. `unsynced_hint` (`tcw/tracker/sync.py:803-806`) is
rewritten to advise `claim` then `sync` instead of the retired flag.

### 3. Lifecycle moves deliver forward; only `sync` reconciles backwards

C2 made delivery bidirectional. That belongs to `sync`, which exists to reconcile
a ticket to its item. A lifecycle move says "this just happened", and dragging a
ticket backwards because an item moved forward is not that.

So a `start` whose ticket is already at or ahead of `statuses.active` takes the
claim and leaves the ticket alone, reporting where it is — exit 0. That is the
epic's criterion 5, and the first draft could not reach it.

This also explains C2's `rework` defect in one rule rather than as a special
case: the "ticket was ahead of its item" note was a `sync` fact leaking into a
lifecycle move, which is the same leak in the other direction.

### 4. Strict mode's exclusivity moves to C1's key

`claim_refusal` asks whether a workflow would refuse a second claimant, by asking
whether `config.start_transition` is still offered. Once a claim applies no
transition, that question is about a transition the claim never makes.

The honest answer is C1's: exclusivity beyond read-after-write requires
`work.tracker.exclusive-claim-transition`, and `assert_ownership` already asserts
through it when set. So **a strict project must set that key**, and `tcw validate`
refuses `strict: true` without it, naming the key — the same migration shape C3
used for `transitions.claim`.

This is a real cost and it is deliberate: the alternative is leaving a strict
project believing it has an exclusivity guarantee that nothing enforces. The
first draft did not notice the guarantee existed.

`claim_refusal`'s lifecycle call sites go; `_tracker_import`'s (`cli.py:2347`)
stays, because `import` still claims through `intake.claim`.

### 5. `transitions.start` becomes optional

C3 kept it required because a start had no status-derived fallback, applying its
transition through the claim rather than through `assess_move`. Design section 1
routes the start through `assess_move`, so the fallback exists and the reason is
gone. The key becomes optional, uniform with its four siblings — which is what
the epic asked C3 for and C3 correctly declined to do early.

The hardcoded branch C3 added to withhold the "or remove it" advice for that one
key (`tcw/tracker/sync.py:247-252`) is deleted with it, and its test changes.

### 6. The gate, and what it does when the tracker cannot answer

`submit` and `rework` refuse before moving the item when the ticket is held by
another account. `complete` and a discard do not consult ownership.

**The gate refuses only on a positive answer.** If the tracker cannot be reached
it cannot say another account holds the ticket, so the move proceeds and the
existing "not updated; run `tcw work tracker sync`" path reports it. Refusing on
silence would make an outage a work stoppage for every project — far larger than
what was asked, and what strict mode already exists to opt into. Strict mode
keeps its stronger behaviour, where an unanswerable tracker is a refusal by
design (`tcw/work/cli.py:404-407`).

### 7. Two retirements, and the unowned active item

`start --take-over` and `link --sync-status` are removed, each failing with a
message naming what replaces it. `FsWorkStore.start` stops raising
`AlreadyClaimed` when the item is active with an empty `owner`: it takes the
claim and returns. Active *and* held by somebody else is still refused, naming
`tcw work tracker claim --take-over`.

### 8. The sweep

Repo-wide, and by **reader** rather than by name — the rule C3's failure taught
and the first draft then broke twice. The readers to trace: `owed`, `catch_up`,
`status_synced`, `expected`, `since`, `claim_refusal`, `start_transition`,
`MOVE_STATUS` (`tcw/tracker/sync.py:67`), `unsynced_and_out_of_step` (`:408-415`),
`walk()`, `unsynced_hint` (`:803`), `_strict_claim`, `_strict_refusal`,
`_deliver_after`, `intake.claim`, `FsWorkStore.start`, and every test naming any
of them. `tcw serve` and `web/` are read for callers, not changed.

## Acceptance criteria

1. `tcw work start` on a backlog item whose bound ticket is in the review status
   exits 0 and leaves the ticket in that status.
2. The same `start` assigns the ticket to the running account.
3. `tcw work start` on an item already active with an empty `owner` exits 0 and
   sets `owner` to the running identity.
4. `tcw work start` on an item active and held by another account exits non-zero
   and names `tcw work tracker claim --take-over`.
5. `start --take-over` and `link --sync-status` each exit non-zero naming their
   replacement, and neither appears in any help text.
6. With strict mode off, `tcw work submit` on an item whose ticket is held by
   another account exits non-zero **and the item is still `active`**.
7. `tcw work rework` behaves the same way from `review`.
8. `tcw work complete <slug> --resolution done --confirm` on an item whose ticket
   is held by another account exits 0 and the item is `completed`.
9. `tcw work complete <slug> --resolution wontfix --confirm` on a bound,
   never-started, unassigned ticket moves the ticket to the discarded status and
   exits 0.
10. With the tracker unreachable and strict mode off, `tcw work submit` moves the
    item to `review` and exits non-zero naming `tcw work tracker sync`.
11. With strict mode on, the same case exits non-zero and the item is still
    `active`.
12. `tcw work tracker link <slug> <key>` on an active item, then
    `tcw work tracker claim <slug>`, then `tcw work tracker sync <slug>`, leaves
    the ticket at `statuses.active` and exits 0.
13. No `catch-up` key is written to any binding, and one already on disk does not
    break the binding.
14. With `exclusive-claim-transition` unset, a `tcw work start` posts exactly one
    workflow transition — the one `transitions.start` names — or none when that
    key is unset too.
15. `tcw validate` refuses `work.tracker.strict: true` without
    `exclusive-claim-transition`, naming the key.
16. A configuration with no `transitions.start` validates.
17. A sync record written by a failed `start`, on an item since moved to
    `review`, does not make a later `tcw work tracker sync` serve the `start`
    move.
18. No lifecycle move moves a ticket backwards: with the item in `review` and the
    ticket ahead of it, `tcw work rework` does not pull the ticket back and prints
    no note saying it did.

Criteria 6 and 10 are the pair the first draft conflated: 6 is a refusal *before*
the local move, 10 is a non-zero exit *after* one. They are different contracts
and both are wanted.

## Risks

1. **Strict projects must add a configuration key** (criterion 15). It is the
   only way to keep a guarantee they already believe they have, but it is a
   breaking change and the release notes must lead with it.
2. **The gate is a reversal.** Until now a tracker problem never stopped a local
   move outside strict mode. Mitigated by refusing only on a positive answer.
3. **Six coupled changes in one item.** Kept together because they answer one
   fact jointly; the epic records why. If it grows past one item during planning,
   the plan says so rather than absorbing it.
4. **Every child of this epic shipped a defect its full suite did not see**, and
   four tests across them were caught asserting something other than what they
   claimed. Mutation-check every new assertion; distrust any test reading a value
   through a parser or through a later writer.
5. **`deliver` serves both the lifecycle and `sync`.** A change made for one
   reaches the other — C2's `rework` note was exactly that, and Design section 3
   is the rule meant to stop it recurring.

## Notes

Four decisions are the requester's, recorded in `initial-request.md`: `start` on
an unowned active item claims and carries on; `start --take-over` is retired; the
gate applies always; the gate reads the ticket's assignee only.

Two are this spec's own and are argued above rather than assumed: an unreachable
tracker does not refuse outside strict mode (section 6), and strict mode now
requires `exclusive-claim-transition` (section 4). Both have criteria so a reader
can check them.

**What the first draft got wrong**, kept because the pattern matters more than
the errors. It specced from the epic's summary and read the code afterwards, so
it missed that removing one transition cascades into six other changes. It then
broke, twice, the rule it had itself written down — audit every reader of a
shared thing, not every mention of its name — by retiring `--sync-status` without
tracing `catch_up`, `status_synced`, `walk()` and `unsynced_hint`, and by
removing the claim transition without tracing `claim_refusal` and `owed`. Two of
its own criteria were unreachable from its own design. The adversarial review
caught all of it before any code was written.
