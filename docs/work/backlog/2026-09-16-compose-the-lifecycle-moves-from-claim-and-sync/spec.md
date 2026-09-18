# Compose the lifecycle moves from claim and sync

## Capability changes

No new capability. Seven existing ones change, and all seven are already
`Supported`, so none is seeded and none is flipped:

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

`work/hold-a-tracker-ticket` (C1's) and `work/synchronize-external-tracker-work`
(C2's) are **read** by this item but not changed: what `claim` and `sync` mean
stays as those children left it, and this item makes the lifecycle call them.

## Problem

Each of the five lifecycle moves carries its own copy of the reasoning the epic
has since given names to.

**The claim happens in two unrelated places.** `_strict_claim`
(`tcw/work/cli.py:379`) takes the ticket before `start` moves the item, but only
under strict mode — it returns early for every other project (`:387-392`). The
delivery path claims again on its own terms inside `deliver`
(`tcw/tracker/sync.py:590`). Both go through `intake.claim`, which reads the
transition name from the configuration directly, so both apply a status move as
part of taking a ticket. That coupling is the epic's subject, and C1 built
`assert_ownership` (`tcw/tracker/ownership.py`) precisely so a claim need not
move anything.

**A claim gates the wrong set of verbs.** Strict mode refuses `submit`
(`tcw/work/cli.py:1233`), `rework` (`:1262`), `complete` (`:3107`) and `drop`
(`:3228`) through `_strict_refusal` (`:355`) → `authorize`
(`tcw/tracker/sync.py:757`). Gating `complete` means somebody who cannot take the
ticket cannot record that the work is finished — the tracker's opinion about
ownership outliving the work itself.

**Outside strict mode a claim gates nothing at all.** `assess_move` refuses to
*move a ticket* held by another account (`tcw/tracker/sync.py:224-233`), but by
then the item has already moved and been committed; `_deliver_after`
(`tcw/work/cli.py:1027`) reports the failure and explicitly does not undo it.
Two people can therefore drive one item's lifecycle from different checkouts and
only find out afterwards.

**An active item with no holder has no answer.** C1's `release` may be run on an
active item — that is the verb's purpose — leaving the item active with an empty
`owner`. `FsWorkStore.start` (`tcw/store/base.py:3507`) then raises
`AlreadyClaimed(slug, item.owner, item.started)` at `:3510` with an empty holder
name, so the refusal names nobody. No earlier version of TCW could produce that
state, which is why nothing answers for it.

**Two flags take over somebody else's work.** `start --take-over`
(`tcw/store/base.py:3511-3516`) predates C1's `tcw work tracker claim
--take-over`, and after this item `start` is composed from that primitive.

**`link --sync-status` is a third way to say the same thing.** It writes a
binding and a sync record in one command (`tcw/work/cli.py:2502`, `:2524-2530`)
and guards itself with its own ownership check at `:2503`, because it "acts as
you". With `claim` and `sync` as verbs, it is `link`, then `claim`, then `sync`.

**A record's `move` is read as a statement about the present.** `deliver` serves
the recorded move when its caller names none, while its target comes from the
item's *current* status, so the two disagree whenever a record outlives the
status it was written under. C2 deferred this here by name; C3 reached it
independently and added a guard (`tcw/tracker/sync.py:648`) so a stale record
strands nobody in the meantime. The guard is a floor, not the fix.

## Goals

1. The five moves obtain ownership through C1's `assert_ownership` and status
   through C2's delivery, rather than through private copies.
2. **A claim gates work, not resolution.** `submit` and `rework` require the
   ticket; `complete` and a discard do not.
3. The gate applies whether or not strict mode is set — the requester's
   decision, recorded in `initial-request.md`, and a reversal of the rule that a
   tracker problem never stops a local move.
4. `start` on an active item nobody holds takes the claim and succeeds.
5. One way to take over somebody else's work, not two.
6. A sync record says what was last attempted, not what to do now.

## Non-goals

- **The web app.** Out of scope for the epic, recorded rather than assumed.
- **Changing what `claim`, `release` or `sync` mean.** This item calls them.
- **`.claiming/`**, the filesystem staging behind the local claim
  (`tcw/store/fs.py:985`, `:3819-3849`, `:3888`). Adapter-private, and the epic
  says so. The epic's own spec cites `fs.py:921` and `:3799` for this; neither
  line resolves to claiming code on `main` today, so the lines above are the ones
  this item checked.
- **The catch-up walk's own defect**, which stays
  `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery`.
- **Making the local `owner` a permission.** The requester decided the gate reads
  the ticket's assignee only; an unbound item is not gated, and `owner` stays a
  record of who holds the work.
- **Widening `sync --all`**, a stated non-goal of C2.

## Design

### 1. One claim, through C1's primitive

`_strict_claim` and `deliver`'s own claim are replaced by calls to
`assert_ownership`, which assigns and reads back without applying a transition
unless `work.tracker.exclusive-claim-transition` names one. The status move that
`intake.claim` performed as part of claiming becomes an ordinary delivery through
`transitions.start`, which is what C3 renamed the key to mean.

This is the change that makes criterion 5 of the epic true: a `start` on a
backlog item whose ticket sits in the review status no longer drags the ticket to
the claim transition's destination as a side effect of being claimed.

### 2. The gate, and what it does when the tracker cannot answer

`submit` and `rework` refuse before moving the item when the ticket is held by
another account. `complete` and a discard do not consult ownership at all.

**The gate refuses only on a positive answer.** If the tracker cannot be reached,
it cannot say that another account holds the ticket, so the move proceeds and the
existing "the ticket was not updated; run `tcw work tracker sync`" path reports
it, exactly as today. The alternative — refusing whenever the tracker is silent —
would make an outage a work stoppage for every project, which is a far larger
change than the one asked for, and it is what strict mode already exists to opt
into. Strict mode keeps its stronger behaviour: there, an unanswerable tracker is
a refusal by design (`tcw/work/cli.py:404-407`).

So the gate has three answers, and only the first refuses outside strict mode:
another account holds it; nobody or you hold it; the tracker did not say.

### 3. An active item nobody holds

`FsWorkStore.start` stops raising `AlreadyClaimed` when the item is active and
`owner` is empty. It takes the claim and returns the item, and the CLI reports
both halves. An item active *and* held by somebody else is still refused, and the
remedy named is `tcw work tracker claim --take-over`.

The store-level change is the smaller half: `AlreadyClaimed` carrying an empty
holder is the symptom, and an item with no holder is not a claimed item.

### 4. Two retirements

`start --take-over` and `link --sync-status` are removed, not deprecated — the
epic's own rule is that a false alternative is worse than none, and the requester
has said not to plan around old versions. Each leaves a message naming the
commands that replace it, because a removed flag that fails with "unrecognized
arguments" teaches nobody anything.

### 5. The record says what was attempted

`deliver` stops treating a record's `move` as an instruction. C3's guard
(`tcw/tracker/sync.py:648`) is kept as the floor while the shape changes, and
removed only once the new reading makes it dead — and a test proves it dead
rather than an argument.

### 6. The sweep

Repo-wide, and it is the sweep C3's failure teaches: every **reader** of the
things this item changes, not every mention of their names. That means each
caller of `_strict_refusal`, `_strict_claim`, `_deliver_after`, `authorize`,
`intake.claim`, `FsWorkStore.start` and `MOVE_STATUS` (`tcw/tracker/sync.py:67`),
and the tests that name them. `tcw serve` and `web/` are read for callers but not changed.

## Acceptance criteria

1. `tcw work start` on a backlog item whose bound ticket is in the review status
   leaves the ticket in that status and exits 0.
2. `tcw work start` on an item that is already active with an empty `owner`
   exits 0, sets `owner` to the running identity, and leaves the item active.
3. `tcw work start` on an item active and held by another account exits non-zero,
   names the holder, and names `tcw work tracker claim --take-over`.
4. `tcw work start --take-over` exits non-zero with a message naming
   `tcw work tracker claim --take-over`, and `--take-over` appears in no `start`
   help text.
5. `tcw work submit` on an item whose ticket is held by another account exits
   non-zero **and the item is still `active`** — with strict mode off.
6. `tcw work rework` behaves the same way from `review`.
7. `tcw work complete <slug> --resolution done --confirm` on an item whose ticket
   is held by another account exits 0 and the item is `completed`.
8. `tcw work complete <slug> --resolution wontfix --confirm` on a bound,
   never-started, unassigned ticket moves the ticket to the discarded status and
   exits 0. (The epic's criterion 6, unchanged.)
9. With the tracker unreachable and strict mode off, `tcw work submit` moves the
   item, exits non-zero, and names `tcw work tracker sync`.
10. With strict mode on, the same case refuses and the item does not move.
11. `tcw work tracker link <slug> <key>` on an active item, followed by
    `tcw work tracker claim` and `tcw work tracker sync`, leaves the ticket at
    `statuses.active`; `--sync-status` is accepted by no command.
12. No lifecycle move applies a workflow transition as part of taking a ticket:
    with `exclusive-claim-transition` unset, a `start` posts exactly one
    transition, the one `transitions.start` names.
13. A sync record written by a failed `start`, on an item that has since moved to
    `review`, does not make a later `tcw work tracker sync` serve the `start`
    move.
14. `tests/test_tracker_strict.py`, `test_tracker_sync.py`, `test_tracker_hold.py`
    and `test_tracker_ownership.py` pass. Where one changes, the change is named
    in `outcome.md` with the reason — this criterion is not a promise that they
    are untouched, which is the mistake C3's criterion 16 made.

## Risks

1. **The gate is a reversal, and reversals surprise people.** Until now a tracker
   problem never stopped a local move. Projects that are not strict have never
   had `submit` refuse. The mitigation is that it refuses only on a positive
   answer that somebody else holds the ticket — never on silence — and that the
   release notes say so in those words.
2. **Composing the moves touches the most heavily tested area in the
   repository.** Every one of C1, C2 and C3 shipped a defect the full suite did
   not see, and three tests across them were caught asserting something other
   than what they claimed. Mutation-check every new assertion, and distrust any
   test that reads a value through a parser or through a later writer.
3. **This item is `effort: high` and the last of four.** If it grows past one
   item, the spec says so and decomposes rather than absorbing.
4. **`deliver` is called from both the lifecycle and `sync`.** A change made for
   one caller reaches the other; C2's `rework` note was exactly that mistake.

## Notes

Four decisions came from the requester rather than from the code, and all four
are in `initial-request.md`: `start` on an unowned active item claims and carries
on; `start --take-over` is retired; the gate applies always; the gate reads the
ticket's assignee only.

One decision is the spec's own and is argued in Design section 2: an unreachable
tracker does not refuse outside strict mode. It follows from the requester's
choice rather than being part of it, and it has its own criteria (9 and 10) so a
reader can check it rather than take it on trust.
