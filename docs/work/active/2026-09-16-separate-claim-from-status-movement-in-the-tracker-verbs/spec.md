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
   in the tracker; the local owner and the Jira assignee are required to agree,
   and a disagreement is drift `sync` reports.
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

*Blocked by C1.* Parallel with C2.

### C4 — The lifecycle moves compose claim and sync

`start`, `submit`, `rework`, `complete` and `discard` stop implementing claim and
status logic and call the primitives. The rule the requester settled:
**a claim gates work, not resolution** — `submit` and `rework` verify the claim is
held; `complete` and `discard` require none. Retires `link --sync-status`
(`tcw/work/cli.py:2341`), which becomes `link` then `claim` then `sync`.

*Blocked by C2 and C3.*

```
C1 ──┬── C2 ──┐
     └── C3 ──┴── C4
```

## Acceptance criteria

1. `tcw work tracker claim <slug>` run twice by the same account succeeds both
   times, and the ticket's status is unchanged after each.
2. `tcw work tracker claim <slug>` against a ticket assigned to another account
   exits non-zero and names the holder.
3. On a workflow that offers the claim transition from every status, two claims
   from different accounts do not both report success.
4. `tcw work tracker release <slug>` leaves the item's status, the ticket's
   status and the binding unchanged, and a subsequent `claim` from another
   account succeeds.
5. `tcw work start` on a backlog item whose ticket is in the review status leaves
   the ticket in that status.
6. `tcw work complete <slug> --resolution wontfix --confirm` on a bound,
   never-started, unassigned ticket moves the ticket to the discarded status and
   exits 0.
7. `tcw work tracker link <slug> <key>` on an active item, followed by
   `tcw work tracker sync <slug>`, leaves the ticket at `statuses.active`; no
   `--sync-status` flag is accepted.
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
