# Spec: Separate claim from status movement in the tracker verbs

## Capability changes

Planned deltas only; each child declares and writes its own.

- **new** `work/hold-a-tracker-ticket` — holding and releasing a ticket becomes a
  thing a user does in its own right, with its own verbs, rather than something
  that happens as a side effect of starting work.
- **changed** `work/manage-external-tracker-intake` (`cap-bd57b7`) — its text
  describes the claim as moving the ticket through the claim transition, which
  stops being true; `link`'s `--sync-status` exception goes away.
- **changed** `work/synchronize-external-tracker-work` (`cap-207f2c`) — "It never
  follows Jira and never pulls a ticket back" is reversed by the requester's
  decision that the item is the source of truth.
- **changed** `work/require-tracker-backed-work` — strict mode's refusals are
  written in terms of the claim record this epic removes.

## Problem

Claiming a ticket and moving a ticket's status are one operation today. The claim
applies a workflow transition (`tcw/tracker/intake.py:310-330`) and only then
assigns, and the transition it applies is also what carries the ticket to
`statuses.active` — `MOVE_STATUS` maps `start → active`
(`tcw/tracker/sync.py:50`). One act, two jobs.

Six open problems follow from that entanglement, and each was filed where it
surfaced rather than where it comes from:

| Problem | Mechanism |
| ------- | --------- |
| GitHub #42 — linking an active item strands its ticket | `link` cannot move the ticket; `sync` reads "ticket behind item" as drift it must not undo |
| GitHub #41 — discarding unstarted work is refused | every move requires the ticket assigned to the caller, because assignment is a claim side effect (`sync.py:205`) |
| `…-close-three-gaps-…` §1 — `start` moves a ticket backwards | `deliver` skips the "already past the claim's status" check when the move is `start` (`sync.py:297`), so the claim transition fires from wherever the ticket sits |
| that item's §3 — strict mode never asks exclusivity for a ticket already held | `claim_refusal` (`sync.py:714`) runs only for a ticket sitting on the claim's own status |
| `2026-09-15-decide-claim-exclusivity-…` | the workflow definition must be read to learn whether a claim was exclusive, because the claim rides the workflow |
| the `claim: owed \| done` state | claim state lives inside the sync record (`sync.py:338`, `:623`), not as its own answer |

Fixing them one at a time means six changes to the same coupling.

## Goals

1. Four verbs, each doing one thing: `link` associates, `claim` asserts ownership,
   `sync` reconciles status, and the lifecycle moves compose them.
2. Ownership is one fact. `claim` asserts it locally and, where a binding exists,
   in the tracker, **writing both together in one command** so they cannot come
   apart. They are not *compared*: an item's `owner` is a local identity
   (`--owner`, `TCW_WORK_OWNER`, then Git), and a ticket's assignee is the
   account the tracker credentials authenticate as, and the two are unrelated
   strings that would rarely match even when they name the same person. One fact
   by construction, not by reconciliation. **Amended** after C1's spec review,
   which found the original wording — "required to agree, and a disagreement is
   drift `sync` reports" — asked for a comparison nothing can make.
3. `claim` is idempotent for its holder and refuses a second holder.
4. `release` exists, so stepping away or handing off has a name that is neither
   `unlink` nor resolving the item.
5. The item is the source of truth for status; `sync` moves the ticket to match,
   in either direction.
6. The six problems above stop being reachable.

## Non-goals

- **Not fixing the six problems individually.** They stay open as independent
  evidence and are closed as the children land (the requester's decision). This
  epic does not touch their items.
- **Not reading Jira's workflow definition.**
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  stays parked; this epic makes it optional rather than prerequisite.
- **Not `tracker create` (GitHub #43) or tracker field writes (GitHub #37).**
  Both are additions to a surface this epic is reshaping; they follow it.
- **Not changing `.claiming/`**, the filesystem staging behind the local claim
  (`tcw/store/fs.py:921`, `:3799`). It is adapter-private and stays so; only what
  ownership *means* is in scope.
- **Not the catch-up walk's own defect**, which is
  `2026-09-16-close-three-gaps-the-pr-45-review-left-in-tracker-delivery` and
  survives this change unaltered.

## Child boundaries and ordering

Four children, each with its own spec and plan. All in this node; all use
`--initiative`, since each starts and completes independently.

### C1 — Ownership as its own fact: `claim` and `release`

`tcw work tracker claim <slug>` and `tcw work tracker release <slug>`. Claim
asserts ownership: it sets the item's owner and, where a binding exists, assigns
the ticket. It applies no transition and changes no status. It is idempotent for
its holder and refuses a holder who is not the caller, naming them. Release drops
both, leaving status and binding alone.

**Exclusivity is read-after-write, with an optional transition assertion**
(the requester's decision). Assign, re-read the ticket, confirm the assignee is
still the caller; the loser of a race sees the winner and backs off. A project
whose workflow genuinely refuses a second claim may additionally name a
transition to assert through, keeping today's strong guarantee where it exists.
The floor is uniform; the ceiling is opt-in.

**The `claim: owed | done` removal moved to C2** after C1's own spec review. The
reasoning that put it here — this is where the answer moves to — held, but the
replacement rule did not: `deliver` writes `claim: owed` itself whenever a
`start` fails to reach the tracker (`tcw/tracker/sync.py:338`), and
`record_unsent` writes it with no client at all (`:623`). Neither path writes the
`catch-up` note, so the record cannot be replaced by reading that note, and two
tests pin the behaviour —
`test_an_owed_claim_without_sync_status_is_followed_by_one_transition_only`
(`tests/test_tracker_sync.py:1710`) and
`test_open_work_with_no_mapping_keeps_its_owed_claim` (`:983`). Replacing the key
means changing `deliver`'s own rules, which is C2's subject. Leaving it in place
for one child is safe: `deliver` already reconciles a stale `owed` against the
ticket's real assignee (`:456-461`, `:504-517`), so a ticket the new verb claimed
is not claimed again.

*No blockers.*

### C2 — `sync` makes the ticket match the item, in either direction

Removes the forward-only rule. A ticket ahead of its item is brought back; one
behind is brought forward. Must not break the `--part` hold, where a ticket
legitimately lags its item because another part is still open.

**Also carries the `claim: owed | done` removal**, moved here from C1 for the
reason recorded there. It belongs with the direction rules because what `owed`
actually drives is which tickets `deliver` claims and walks forward, and that is
what this child rewrites. `SYNC_FIELDS` (`tcw/store/base.py:423`), the record's
validation (`:442`), the projection schema (`tcw/work/projection.py:125`) and
`tcw work show`'s "; the claim is still owed" (`tcw/work/cli.py:216`) come with
it, and a `tracker.yaml` already on disk that still carries the key must stay
readable.

*Blocked by C1* — it reads ownership rather than the claim record.

### C3 — `transitions.claim` retires into `transitions.start`

Once the claim does not transition, the key is no longer special: it becomes the
transition for the `start` move, uniform with the `submit`/`rework`/`complete`/
`discard` keys added by pull request #45. Covers the config surface, `tcw
validate`'s checks, and the migration for configs carrying the old key.

*No blockers.* **Amended** after C1's spec review. C3 was blocked by C1 on the
premise that "once the claim does not transition, the key is no longer special" —
but C1 as scoped edits no delivery code, so `deliver` goes on applying
`transitions.claim` through `intake.claim` (`tcw/tracker/sync.py:522`,
`tcw/tracker/intake.py:329`) for every `start` until **C4**. The premise is
satisfied by C4, not by C1. Re-pointing the blocker at C4 would make a cycle,
since C4 is blocked by C3; and the work itself — renaming a configuration key,
validating it, and migrating configs that carry the old one — needs nothing from
any sibling. So the blocker goes rather than moves, and this plan's own rule
applies: a false blocker is a lie the tool enforces.

### C4 — The lifecycle moves compose claim and sync

`start`, `submit`, `rework`, `complete` and `discard` stop implementing claim and
status logic and call the primitives. The rule the requester settled:
**a claim gates work, not resolution** — `submit` and `rework` verify the claim is
held; `complete` and `discard` require none.

**An active item with no holder is a state C1 creates, and this rule has to
answer for it.** C1's `release` may be run on an `active` item — that is the
point of the verb, per goal 4 — which leaves the item active with an empty
`owner`. Under this rule `submit` on such an item is refused, and the way back is
`tcw work tracker claim`, not `start --take-over`. C4 states that explicitly and
gives it a criterion; it should also decide what `tcw work start` says about an
unowned active item, which today renders `AlreadyClaimed(slug, "", started)` with
an empty holder name (`tcw/store/base.py:3510` — the line moved; this section said
`:3475`). Raised by C1's spec review. Retires `link --sync-status`
(`tcw/work/cli.py:2502`), which becomes `link` then `claim` then `sync`.

**Amended after C4's spec review. This section reads as a list of independent
jobs, and it is not one.** Removing the transition a claim applies is a single
change that pulls six others in behind it, and a spec written from the list above
without tracing them produced a design with a one-sentence answer to the hardest
part. Whoever plans C4 must answer all seven together:

1. **What replaces `owed`.** It is three terms today
   (`tcw/tracker/sync.py:328`): `starting`, `bound.catch_up`, and a record whose
   `move` is `start`. Retiring `--sync-status` deletes the only writer of
   `catch-up: true` (`tcw/tracker/intake.py:185`), and reading a record's `move`
   as an instruction is the coupling C2 and C3 both deferred here — so two of
   the three terms go, leaving `owed = starting`, which **C2 built and reverted**
   because it does not work. The replacement fact has to be named.
2. **What `expected` and `since` become.** Both are set to `statuses.active`
   (`tcw/tracker/sync.py:625-626`) *because the claim transition has just put the
   ticket there*. With no transition the ticket has not moved.
3. **What a `start` delivers when its ticket is at or ahead of the target.**
   C2 made delivery bidirectional, so "an ordinary delivery" would drag a ticket
   backwards out of the review status — which is the epic's own criterion 5 and
   one of the six problems it exists to fix.
4. **What happens to strict mode's exclusivity.** `claim_refusal`
   (`tcw/tracker/sync.py:809`) reads `config.start_transition` and is what tells
   a strict project a second person could claim the same ticket. Its lifecycle
   call sites all disappear with the claim transition; C1's replacement key,
   `work.tracker.exclusive-claim-transition`, is **opt-in**. A strict project
   that never set it loses a guarantee unless C4 says otherwise.
5. **Whether `transitions.start` stays required.** C3 kept it required precisely
   because a start applies it through the claim rather than through `assess_move`
   and so has no status-derived fallback. Route the start through `assess_move`
   and that reason is gone, along with the hardcoded branch C3 added to withhold
   the "or remove it" advice for that one key (`tcw/tracker/sync.py:247-252`).
6. **The machinery behind `--sync-status`.** `status-synced`, `catch-up`,
   `unsynced_and_out_of_step` (`tcw/tracker/sync.py:408-415`), `walk()` and
   `unsynced_hint` (`:803`) are its readers. `unsynced_hint` advises the very
   flag being retired.
7. **The five verbs and the claim gate**, which is the only part of this list
   that could stand as its own item.

Kept as one item rather than split, on the requester's rule that a split is worth
it only when the parts can run in parallel. They cannot: items 1 and 6 must
jointly answer one fact, and items 1, 3 and 7 all edit `_start`
(`tcw/work/cli.py:1103`).

*Blocked by C2 and C3.*

```
C1 ───── C2 ──┐
              ├── C4
C3 ───────────┘
```

C3 starts whenever; C2 waits for C1; C4 waits for both.

## Acceptance criteria

1. `tcw work tracker claim <slug>` run twice by the same account succeeds both
   times, and the ticket's status is unchanged after each.
2. `tcw work tracker claim <slug>` against a ticket assigned to another account
   exits non-zero and names the holder.
3. Where two accounts claim the same ticket and the second assigns before the
   first reads back, the first reports failure and names the second. **Amended**
   after C1's spec review. The original — "two claims from different accounts do
   not both report success" — is not what read-after-write guarantees: two claims
   whose reads interleave exactly (A assigns, A reads, B assigns, B reads) can
   both succeed, and C1's design says so. The unconditional guarantee returns
   only where a project sets `work.tracker.exclusive-claim-transition`, which is
   opt-in, so it cannot be the criterion for the default.
4. `tcw work tracker release <slug>` leaves the item's status, the ticket's
   status and the binding unchanged, and a subsequent `claim` from another
   account succeeds.
5. `tcw work start` on a backlog item whose ticket is in the review status leaves
   the ticket in that status.
6. `tcw work complete <slug> --resolution wontfix --confirm` on a bound,
   never-started, unassigned ticket moves the ticket to the discarded status and
   exits 0.
7. `tcw work tracker link <slug> <key>` on an active item, followed by
   `tcw work tracker claim <slug>` and `tcw work tracker sync <slug>`, leaves the
   ticket at `statuses.active`; no `--sync-status` flag is accepted. **Amended**
   at the epic's verify (2026-09-24, requester's decision). The original read
   "`link`, followed by `sync`". The design the children shipped keeps `link` from
   taking the ticket, so a bare `sync` of a ticket linked without its status holds
   it and names `tracker claim`; link, claim, sync reaches the end state, in the
   suite and against real Jira (`walkthrough.md`).
8. A ticket moved by hand to a status ahead of its item is returned to the item's
   mapped status by `sync`.
9. A ticket held back because another `--part` item is open is not moved by
   `sync`, and the hold is reported.
10. `transitions.claim` is not accepted; `transitions.start` names the start
    move's transition; a config carrying only `transitions.claim` is reported by
    `tcw validate` with the replacement named.
11. No `claim` key appears in `tracker.yaml`'s sync record, and one already on
    disk is still read without breaking the binding. **C2's**, moved from C1.
12. `tcw work submit` on an item whose ticket is held by another account is
    refused; `tcw work complete` and a discard on the same item are not.

## Risks

1. **The race window is real.** Read-after-write narrows it; it does not close
   it. Two claims whose reads interleave exactly can both report success. C1's
   spec must state the window rather than imply atomicity, and the optional
   transition assertion is the answer for anyone who cannot accept it.
2. **"The item is truth" silently undoes deliberate Jira moves.** A person who
   moves a ticket on purpose finds the next `sync` putting it back. Whether that
   warrants a warning, a confirmation or a record is C2's to decide; shipping it
   silent is the risk.
3. **The `--part` hold looks exactly like drift.** A ticket behind its item
   because a sibling part is open is indistinguishable, from the item alone, from
   one that fell behind. C2 must reach `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`
   before deciding, or it will re-break the hold.
4. **Config migration touches every `work.tracker` block in existence.**
   `transitions.claim` is required today, so every configured node carries it.
5. **Strict mode is defined in terms of what is being removed.**
   `binding_refusal` (`sync.py:637`) and `authorize` (`:668`) read the claim
   record. `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`
   also edits them; whichever lands second rebases.
6. **`deliver` is contended.** C4 and the catch-up-walk item both change it.
7. **The sweep is narrowed, deliberately.** Claim-and-status coupling was swept
   through `tcw/tracker/` and `tcw/work/cli.py`. `tcw/serve/` has its own start
   path that never passes `take_over` (`tcw/serve/__init__.py:905` — `work.start(slug, force=force)`, no owner and no `take_over`); whether the
   web app grows `claim`/`release` actions is left to C1 to decide and record,
   rather than assumed either way here.

## Notes

- **Abstraction litmus test: passes.** Ownership is an item field and an
  assignment on a tracker record — both are ordinary field writes any store can
  make. Read-after-write is two reads and a write. Nothing in the model requires
  a filesystem; `.claiming/` stays what it already is, adapter-private staging
  behind an abstract fact.
- **Harness compatibility: unaffected.** Every guarantee lands in the `tcw` CLI,
  which behaves identically under Claude and Codex. No skill, hook or injected
  context carries any of it.
- **The approved verb table was amended after it was agreed.** It gave `complete`
  "verify still held"; the requester then chose "no claim, same as discard". The
  resulting rule — a claim gates work, not resolution — is what C4 implements, and
  it is cleaner than the table it replaces.
- **What `release` does about a ticket someone else holds** is left to C1: whether
  releasing is only ever self-release, or whether a `--force` exists for recovering
  a ticket held by a departed account. The local claim already has `--take-over`
  for its half of this (`tcw/store/fs.py:3698`), which C1 must reconcile with.
