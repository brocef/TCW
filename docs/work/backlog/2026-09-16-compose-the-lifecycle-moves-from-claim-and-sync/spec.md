# Compose the lifecycle moves from claim and sync

**Third draft.** The first two were rejected at review. The first answered the
easiest of the seven questions this change raises and hand-waved the rest. The
second answered them, but its central claim — that `owed` could be deleted rather
than replaced — was broken by the reviewer and the break was confirmed against
the code. What each draft got wrong is in `## Notes`, because the pattern is more
useful than the errors.

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

**A claim gates the wrong verb.** Strict mode refuses `submit`
(`tcw/work/cli.py:1233`), `rework` (`:1262`) and `complete` (`:3107`). Gating
`complete` means somebody who cannot take the ticket cannot record that the work
is finished. Half of the epic's rule is **already true**: `_complete` calls
`_strict_refusal` only under `if shipping` (`:3105`), with the comment "Discards
are never refused — abandoning work authorizes none", so a discard has never been
gated there. `drop` is **not** one of the five moves and is out of scope: it
erases an item outright, and its strict refusal is `ever_bound()` (`:3225-3229`),
which refuses because dropping would erase a tracker record — nothing to do with
a claim. The first two drafts cited it wrongly.

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

### 1. `assert_ownership` replaces `intake.claim`, and the ticket stops moving

The claim inside `deliver` (`tcw/tracker/sync.py:590`) and `_strict_claim`
(`tcw/work/cli.py:379`) both call `intake.claim`, which applies the configured
transition. Both call C1's `assert_ownership` instead, which assigns and reads
back and applies no transition unless `work.tracker.exclusive-claim-transition`
names one.

Everything after the claim then has to change, because it was written on the
premise that the claim had just moved the ticket onto `statuses.active`:

- **The "claimed, but it is in X, not active" refusal (`:613-620`) goes.** It
  exists because a claim that landed off the ladder left a ticket nothing could
  reason about. With the transition applied through `assess_move` instead, a
  ticket at an unmapped status is exactly what `transitions.start` is for. **This
  is the hole C2 named and handed here**: "a ticket in a status the project maps
  to nothing could not be walked onto the ladder at all, because the claim
  transition was the only thing that ever put it there."
- **`if starting: return finish(CURRENT)` (`:621`) goes.** A start's ticket has
  not arrived anywhere yet; it still has to be delivered.
- **`since` becomes the ticket's status at claim time**, not `statuses.active`.
- **`expected` is left exactly as `expected_statuses` computed it** (`:367-368`),
  including its `shared` widening. It is not overwritten. See the warning below.

**`expected` is the drift window, not bookkeeping.** Its docstring
(`tcw/tracker/sync.py:170`) is "Where the ticket may be before this move without
it counting as drift", and `assess_move` refuses on it at `:234`. The second
draft proposed setting it to the ticket's own status on every path; that makes
the refusal unreachable by construction, discards the `shared` widening that C2's
`--part` hold depends on, and disables the resolved-ticket check at `:221`, which
only fires when `expected` is empty. The one place it may be set that way is the
already-yours branch (`:585`), and only because that branch has already
established the ticket is on the ladder and is where a claim would have left it.
That premise does not generalise, and any later change proposing to widen it
should be read against this paragraph.

### 2. `owed` becomes a question the ticket answers

`owed` is three remembered facts today (`:328`): `starting`, `bound.catch_up`,
and a record whose `move` is `start`. All three remember that a claim has not
happened, because the ticket could not be asked — its status conflated "TCW
claimed this" with "somebody moved it here by hand".

Once a claim is an assignment, the ticket answers directly:
`ticket.assignee_id != ticket.me_id`.

**But `owed` is not deleted, and the block it gates is not left alone.** `if owed:`
(`:524`) hosts six guards that have nothing to do with assignment, and two of
them test the assignee *again* — `at_target and (… or assignee == me)` at `:526`,
and `rung > 0 or assignee == me` at `:545`. Those inner tests exist precisely
because the remembered `owed` was not trustworthy. Once `owed` **is** the
assignee question they are unreachable, and they are removed rather than left as
dead conditions. Each remaining guard is restated under the new definition:

| Guard | Under the new `owed` |
| --- | --- |
| `at_target and local in RESOLVED_STATUSES` → CURRENT (`:526`) | Kept. A finished item whose ticket is already at the target is not claimed, whoever holds it. Its `assignee == me` half is removed as unreachable. |
| `move == "discard"` claims nothing (`:533`) | Kept verbatim. Abandoning work is not a statement that you are doing it. |
| `check_only` → CONFLICTING (`:543`) | Kept, reworded: "the claim of X is still owed" becomes "X is not held", which is what is now being reported. |
| the past-the-claim branch (`:545-585`) | Its `rung > 0` half is kept; its `assignee == me` half is removed as unreachable. |
| the resolved refusal inside it (`:554-561`) | Kept. Its comment says it exists because skipping the claim would lose the claim's own resolved refusal; that reason survives. |
| strict mode's `claim_refusal` at `rung == 0` (`:569`) | Replaced — see section 4. |

**`owed` is two questions, and only one of them is about the ticket.** It asks
*is this a move that takes a ticket* — the `starting`, `bound.catch_up` and
`record["move"] == "start"` terms — and *is the ticket already taken*, which
nothing answers today. That second question is why the first has to be
remembered at all: with no way to read whether a ticket was ever held, TCW has to
keep a note of every route that would have held it.

So the conjunction is split rather than collapsed:

```python
takes_ticket = starting or bound.catch_up or (record is not None
                                              and record["move"] == "start")
...                                   # after the ticket is read
owed = takes_ticket and ticket.assignee_id != ticket.me_id
```

`takes_ticket` is a property of the move, needs no ticket, and is computed at
`:328` exactly where `owed` is today — so the early exit at `:497`, which decides
without a ticket in hand, keeps working unchanged and no extra tracker request is
made. Only the second half waits for the read at `:505`.

**Collapsing the two into one read would be a defect, and a subtle one.** With
`owed = assignee != me` alone, `owed` is true for every move on an unassigned
ticket: a `submit` on a ticket in `statuses.active` that nobody holds enters the
block at `:524`, is not at target, is not a discard, is not `check_only`, fails
both halves of `rung > 0 or assignee == me` at `:545`, and reaches the claim.
`submit`, `rework` and `complete` would all start assigning tickets — which is
exactly what `MOVES_ALLOWING_UNASSIGNED`'s comment (`:75-78`) exists to forbid,
"marching a ticket through a workflow on behalf of a person who never took it",
and what Goal 2 forbids for `complete`. The second draft proposed that collapse;
it was caught at review, and the reasoning is recorded here so it is not retried.

`catch-up: true` stops being written with `--sync-status`, and the field is
dropped from `Bound`. A binding on disk that still carries the key parses as
`Bound` either way, because `classify_binding` reads it with `data.get`
(`tcw/store/base.py:419`) — verified, not assumed. Whether `_BINDING_KEYS`
(`tcw/tracker/intake.py:189`) keeps carrying it forward on a rewrite is a
decision for the plan; dropping it is the tidier answer and loses nothing.

**`status-synced` stays.** It is written by a plain `link` as well
(`tcw/work/cli.py:2517`) and records something the ticket cannot answer — that a
binding was made to a ticket already out of step. `unsynced_hint` (`:803-806`) is
rewritten to advise `claim` then `sync` rather than the retired flag.

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

**For a bound item, `submit` and `rework` require the ticket to be assigned to
you.** Held by another account refuses and names them; unassigned refuses and
names `tcw work tracker claim`. Requiring the assignment, rather than merely the
absence of a rival, is what makes the epic's own sentence true — "`submit` on
[an active item with no holder] is refused, and the way back is
`tcw work tracker claim`" — because C1's `release` unassigns the ticket
(`tcw/tracker/ownership.py:180`), so a released item has no rival to detect. The
first two drafts refused only "held by another account" and therefore did not
refuse the case the epic exists to answer.

**An unbound item is not gated**, on the requester's decision that the gate reads
the ticket only. The epic's sentence is therefore satisfied for bound items and
knowingly not for unbound ones; that is recorded rather than quietly dropped.

**`complete` and a discard do not consult ownership — and neither does their
delivery.** `assess_move` refuses a ticket held by another account for every move
(`tcw/tracker/sync.py:224-233`), so "requires no claim" has to reach that check
too, or the verb succeeds locally and still exits non-zero. Those two moves join
`discard` in `MOVES_ALLOWING_UNASSIGNED` (`:78`), which becomes the set of moves
that need no claim. Without this, criteria 8 and 10 demand opposite exit codes
from one code path — `_deliver_after` returns 1 for `PENDING` and `CONFLICTING`
alike (`tcw/work/cli.py:1071-1076`) — which is what the first two drafts did.

**The gate refuses only on a positive answer.** If the tracker cannot be reached
it cannot say another account holds the ticket, so the move proceeds and the
existing "not updated; run `tcw work tracker sync`" path reports it. Refusing on
silence would make an outage a work stoppage for every project — far larger than
what was asked, and what strict mode already exists to opt into. Strict mode
keeps its stronger behaviour, where an unanswerable tracker is a refusal by
design (`tcw/work/cli.py:404-407`).

### 7. One retirement, and the unowned active item

**`link --sync-status` is retired**, failing with a message naming `link`, then
`claim`, then `sync`.

**`start --take-over` stays.** The requester reversed an earlier decision to
retire it once the premise turned out to be false, and the reason belongs here so
nobody retires it again on the same reasoning: it is not a duplicate of
`claim --take-over`. It is the only code that republishes an interrupted
`.claiming/` staging directory (`tcw/store/fs.py:3817-3830`, whose own comment
calls it "the documented remedy for an interrupted claim"), it refreshes
`started` (`tcw/store/base.py:3516`), and it accepts `--owner`.
`claim --take-over` does none of those, and on an item with an interrupted claim
it cannot even be attempted: it resolves the item through `st.get`, which raises
"`{slug}` has an interrupted claim; use `--take-over --owner <identity>`"
(`tcw/store/fs.py:5172`) before any ownership code runs. Two messages advise the
flag by name, and
`2026-09-15-make-start-take-over-recover-an-interrupted-claim-from-the-cli-and-the-web-app`
is an open item aimed at the same path.

`FsWorkStore.start` stops raising `AlreadyClaimed` when the item is active with
an empty `owner`: it takes the claim and returns. Active *and* held by somebody
else is still refused, naming `tcw work tracker claim --take-over`.

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
5. `link --sync-status` exits non-zero naming its replacement and appears in no
   help text. `start --take-over` still works, and still recovers an interrupted
   claim.
6. With strict mode off, `tcw work submit` on an item whose ticket is held by
   another account exits non-zero **and the item is still `active`**.
6b. With strict mode off, `tcw work submit` on an item that is `active` with an
    empty `owner` and an unassigned ticket exits non-zero, the item is still
    `active`, and the message names `tcw work tracker claim`.
6c. `tcw work submit` on an item with no binding is not gated: it moves.
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
13. No `catch-up` key is written to any binding; one already on disk still
    parses as a bound binding.
13b. `tcw work tracker sync` on a `--part` binding whose sibling is open still
     reports the hold and moves nothing — C2's criterion 9, re-checked here
     because this item rewrites the block that decides it.
14. With `exclusive-claim-transition` unset, a `tcw work start` posts exactly one
    workflow transition — the one `transitions.start` names — or none when that
    key is unset too.
15. `tcw validate` refuses `work.tracker.strict: true` without
    `exclusive-claim-transition`, naming the key.
16. A configuration with no `transitions.start` validates.
17. A sync record written by a failed `start`, on an item since moved to
    `review`, does not make a later `tcw work tracker sync` serve the `start`
    move.
17b. A bound item whose local status maps to no tracker status is delivered with
     no tracker request at all, exactly as today — the early exit at `:497`
     decides before any read and keeps deciding.
17c. `tcw work submit`, `rework` and `complete` on a bound item whose ticket is
     unassigned assign nothing in the tracker.
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
