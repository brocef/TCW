# Spec: Make claim and release assert ownership without moving a ticket

## Capability changes

Planned deltas. No ledger record is written at this stage.

- **new** `work/hold-a-tracker-ticket` — holding a piece of work, and letting go
  of it, becomes something a user does in its own right. Two verbs,
  `tcw work tracker claim <slug>` and `tcw work tracker release <slug>`, that say
  who owns the work and change nothing else.

**And nothing else.** This is the whole capability delta, and it is a signal
worth reading: as scoped below, this child adds two verbs and one optional
configuration key and changes the behaviour of no existing verb. The epic's
planned deltas to `work/manage-external-tracker-intake` (`cap-bd57b7`),
`work/synchronize-external-tracker-work` (`cap-207f2c`) and
`work/require-tracker-backed-work` all describe behaviour that C2, C3 and C4
change, not this child.

## Problem

Claiming a ticket and moving a ticket are one act.

`claim` (`tcw/tracker/intake.py:310-360`) applies the configured claim transition
first and assigns only after an applied transition. Its docstring says why:

> **Transition first; assign only after an applied transition.** On a workflow
> that refuses the claim from its own destination, a second claimant's transition
> is refused, so it never reaches the assign and cannot overwrite the first
> claimant's assignment.

That is a sound way to get exclusivity out of a workflow, and it is exactly why
ownership cannot be expressed without moving the ticket. The transition it
applies is also the one that carries the ticket to the active status —
`MOVE_STATUS` maps `start → active` (`tcw/tracker/sync.py:50`), and the comment
on `MOVE_ONTO` (`:53-55`) says so outright: "`active` is the claim's move, not
`rework`: reaching it from nothing is claiming".

Two consequences, both of them live defects filed elsewhere:

1. **There is no way to say "this is mine" without saying "and it has
   started".** Every verb that needs ownership has to move the ticket to get it.
2. **There is no way to say "this is no longer mine".** The only exits are
   `unlink`, which destroys the binding, and resolving the item.

Locally the same entanglement holds: an item's `owner` is written only by `start`
(`tcw/store/base.py:3478`, `tcw/store/fs.py:3751-3812`), and the only way to
change it afterwards is `start --take-over`.

A third consequence — that whether a claim is outstanding lives inside the sync
record as `claim: owed | done` (`tcw/tracker/sync.py:338`, `:623`) rather than
being its own answer — is **C2's**, not this child's. See the Non-goals.

## Goals

1. `tcw work tracker claim <slug>` asserts ownership and nothing else: it sets
   the item's `owner` and, where a binding exists, assigns the ticket to the
   caller. It applies no transition by default and changes no status, local or
   remote.
2. `tcw work tracker release <slug>` drops ownership and nothing else: the item's
   status, the ticket's status and the binding are untouched.
3. Ownership is **one fact**. The item's `owner` and the ticket's assignee are
   written together, and neither is overwritten while somebody else holds it.
4. `claim` is idempotent for whoever holds it, and refuses anyone else by name.
5. Exclusivity has a uniform floor — read-after-write — and an opt-in ceiling for
   a project whose workflow genuinely refuses a second claimant.

## Non-goals

- **Removing `claim: owed | done` from the sync record.** The epic originally put
  this here. Its own spec review showed the replacement rule proposed for it was
  wrong — `deliver` writes `claim: owed` itself whenever a `start` fails to reach
  the tracker (`tcw/tracker/sync.py:338`), and `record_unsent` writes it with no
  client at all (`:623`), and neither writes the `catch-up` note the replacement
  depended on. Replacing the key means rewriting which tickets `deliver` claims
  and walks forward, which is C2's subject, and two existing tests pin today's
  behaviour (`tests/test_tracker_sync.py:1710` and `:983`). **The epic's spec has
  been changed to put it in C2**, and the requester approved the move. Leaving
  the key alone for one child is safe: `deliver` already reconciles a stale
  `owed` against the ticket's real assignee (`tcw/tracker/sync.py:456-461`,
  `:504-517`), so a ticket this child's `claim` took is not claimed again.
- **Any edit to `deliver`, `record_unsent`, `binding_refusal` or `authorize`.**
  This child adds code; it changes none of the existing delivery path. That is
  what keeps it out of the way of C2, C4 and
  `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`,
  all three of which edit those functions.
- **The other three children.** `sync` moving a ticket in either direction is C2.
  Retiring `transitions.claim` into `transitions.start` is C3. Making `start`,
  `submit`, `rework`, `complete` and `discard` compose these primitives — and
  retiring `link --sync-status` — is C4. `tcw work start`'s behaviour is
  unchanged by this child, byte for byte.
- **The web app.** `tcw serve` has its own start path that passes neither an
  owner nor a take-over (`tcw/serve/__init__.py:903` —
  `work.start(slug, force=force)`). This child adds no claim or release action to
  it and changes none of its code. **Recorded rather than assumed:** an item
  started from the web app gets whatever owner `work.start` gives it, and there
  is no way to assert or drop ownership from the browser. Whether that matters is
  a follow-up item's question, raised at this epic's closeout.
- **`.claiming/`.** It is adapter-private filesystem staging behind the local
  claim (`tcw/store/fs.py:921`, `:3799`, `:3851`) and stays exactly what it is.
- **Reading Jira's workflow definition.** The optional assertion below is
  configured by hand, not discovered.
- **Closing any of the six subsumed problems**, including GitHub #41 and #42.
  They are evidence; the epic closes them after publication.

### Why the sweep is narrowed

The epic swept claim-and-status coupling through `tcw/tracker/` and
`tcw/work/cli.py` and found `tcw/serve/` to be the one other place with its own
start path. That sweep is inherited. It was re-run for this child against `tcw/`
for the one thing this child actually writes — an item's `owner`. Every writer is
inside `start`: `tcw/store/base.py:3478` and `:3497`, `tcw/store/fs.py:3779` and
`:3805`. There is no other writer and no standalone reader-and-writer pair to
collide with.

## Design

### The two verbs

```
tcw work tracker claim   <slug> [--part <name>] [--owner <identity>] [--take-over]
tcw work tracker release <slug> [--part <name>] [--owner <identity>] [--force]
```

`--owner` resolves through `_local_owner` (`tcw/work/cli.py:1005-1017`) exactly
as `start`'s does: the flag, then `TCW_WORK_OWNER`, then the Git email, then the
Git name. Deliberately the same ladder, because the local owner and the Jira
assignee are being made into one fact and two ladders would make them two.

**Claim, step by step.**

1. Resolve the item and the caller's identity. No identity is a refusal, worded
   as `start`'s is (`tcw/work/cli.py:1122`).
2. **Check the local holder first.** If the item's `owner` is set and is not the
   caller, refuse and name them — unless `--take-over`. This check is what makes
   goal 3 true on an item with no ticket behind it, where there is no assignee to
   check instead. It is the same question `FsWorkStore.start` asks before raising
   `AlreadyClaimed` (`tcw/store/fs.py:3802-3806`), asked here without the status
   move that exception is bound to; the refusal reuses that wording so the two
   verbs do not disagree about what "already claimed" sounds like.
3. Read the binding (`binding_of`). **An unbound item is claimable** — claiming
   is a statement about the work, and the tracker is where that statement is also
   published when there is one to publish. An unbound claim writes the local
   owner and says the ticket half was skipped because there is no ticket.
4. Where bound, read the ticket (`read_ticket`). A resolved ticket is refused:
   ownership of finished work means nothing, and today's `claim` refuses one too
   (`tcw/tracker/intake.py:344`, row `1a`).
5. If the ticket is assigned to someone else, refuse and name them, unless
   `--take-over`. This is row `1b`'s refusal, kept.
6. **Assign** the ticket to the caller. No transition is applied.
7. **Read the ticket back** and confirm the assignee is still the caller. If it
   is not, the claim failed: report who won and exit non-zero, leaving the local
   owner unwritten.
8. Write the item's `owner` with `set_field(slug, "owner", owner)` — the abstract
   operation that already exists (`tcw/store/base.py:3006`) and that `start`
   itself uses for exactly this field (`:3478`). The local write comes **after**
   the read-back, so an item is never marked owned by someone who lost the race.

Idempotence falls out without a special case: a holder re-running it passes its
own name at step 2, assigns the same account to itself, reads back its own name,
and rewrites the same owner. The ticket's status is not consulted and no
transition is applied, so the ticket cannot move on either pass.

**Release, step by step.** The mirror image.

1. Resolve the item and the identity as above.
2. **Check the local holder.** If the item's `owner` is set and is not the
   caller, refuse and name them — unless `--force`.
3. Where bound, read the ticket. If the assignee is neither empty nor the caller,
   refuse and name the holder — unless `--force`.
4. Unassign the ticket. No transition; its status is neither read for a decision
   nor changed.
5. Clear the item's `owner` (`set_field(slug, "owner", "")`).

`--force` exists for one reason, and the help text says so: recovering a ticket
held by an account that has gone away. It is the release-side counterpart of
`start --take-over`, and **the two are reconciled rather than duplicated** —
`claim --take-over` and `start --take-over` mean the same thing and share the
refusal wording; `release --force` is the only new escape hatch.

`started` is left alone by both verbs. It records when work began, which is a
statement about the lifecycle, not about ownership, and C4 owns the lifecycle.

### Unassigning is a tracker operation that does not exist yet

`JiraClient.assign` (`tcw/tracker/jira.py:268`) takes `account_id: str` and PUTs
`{"accountId": account_id}`. Release needs `{"accountId": null}`, which is Jira's
documented way to unassign, so the signature widens to `str | None`.

**Two things the fake tracker cannot tell us**, and the spec says so rather than
letting a green suite imply otherwise:

- The fake assigns whatever it is handed —
  `self._find(match[1]).assignee = body["accountId"]` (`tests/tracker_fake.py:206`),
  returning 204 unconditionally. It will accept `null` whether or not real Jira
  would.
- **A Jira project can forbid unassigned issues.** Where a project has that
  setting off, the real endpoint answers 400 and `release` cannot unassign. The
  fake will never produce that answer.

So `release` must treat a refused unassignment as a refusal it reports, not as a
crash, and must not clear the local `owner` when the ticket half failed —
otherwise the one fact splits in two, which is what goal 3 forbids. The failure
path is real and untestable against the fake; it is listed under verification
below.

### Exclusivity: a uniform floor and an opt-in ceiling

**The floor is read-after-write**, steps 6 and 7 above. It is weaker than today's
transition-first rule, and that is the trade this epic makes: today's guarantee
costs a status move on every claim.

**The window is real and is not closed.** Two claims can both succeed if they
interleave as: A assigns, A reads back, B assigns, B reads back. Nothing here
prevents that, and this spec says so rather than implying atomicity. What it does
prevent is the much more likely interleaving — A assigns, B assigns, A reads and
sees B — where today's assignment would simply be overwritten with nobody told.

**The ceiling is opt-in**, under a new configuration key:

```yaml
work:
  tracker:
    exclusive-claim-transition: "Start Progress"
```

When set, `claim` applies that transition before assigning, in today's order and
for today's reason, and a refusal from the workflow is a refusal to claim. When
unset — the default, and what every existing config has — no transition is ever
applied. It is a top-level `work.tracker` key, so it joins `TRACKER_KEYS`
(`tcw/store/base.py:1106`) and merges through `merge_tracker_blocks` (`:1408`)
like every other one.

**Opting in costs a status move, and the documentation must say so.** A workflow
transition moves the ticket; that is what a transition is. A project that names
one is choosing today's behaviour deliberately for the stronger guarantee, on the
understanding that its claims move the ticket. The key is named for the guarantee
rather than for the move so nobody reaches for it expecting a free lunch.

This is a **new** key, not a rename of `transitions.claim`. The two answer
different questions — `transitions.claim` is the transition a `start` applies,
which C3 renames to `transitions.start` — and collapsing them is what this epic
exists to undo. C3 is unaffected by this key and does not touch it.

### Abstraction litmus test

**Passes.** `claim` is: read one item field, read a sidecar, read a record from a
tracker, write one field on that record, read it back, write one field on the
item. `release` is the same minus one read. Both are expressed in item, field and
reference; neither needs a folder. The one operation added to the item is
`set_field`, already on the abstract `WorkStore` and already implemented by the
filesystem adapter. `.claiming/` is untouched and stays adapter-private.

### Harness compatibility

**Unaffected.** Both verbs are `tcw` CLI subcommands, which behave identically
under Claude and Codex. No skill, hook or injected context carries any guarantee
here. The skill documents change to describe the new verbs; they teach, they do
not enforce.

## Acceptance criteria

Each is runnable against the fake tracker (`tests/tracker_fake.py`) unless marked
otherwise. The fake already holds accounts, a workflow and `before(...)` hooks for
deterministic interleaving, which is what makes criterion 4 checkable at all.

1. `tcw work tracker claim <slug>` run twice by the same account exits 0 both
   times, and the ticket's status — read from the fake after each run — is the
   same string before and after each.
2. After a successful `claim`, the item's `state.yaml` has `owner` set to the
   caller's identity and the ticket's assignee is that same account, on an item
   still in `backlog`.
3. `tcw work tracker claim <slug>` against a ticket assigned to another account
   exits non-zero, prints that account's display name, and leaves the item's
   `owner` unchanged.
4. On the fake's `GLOBAL` workflow, where the claim transition is offered from
   every status, two claims from different accounts interleaved as *A assigns, B
   assigns, A reads back* produce exactly one exit-0 run; A's exits non-zero and
   names B.
5. `tcw work tracker claim <slug>` on an item with no binding exits 0, sets the
   item's `owner`, and says no ticket was assigned because the item is not bound.
6. `tcw work tracker claim <slug>` on an **unbound** item whose `owner` is
   another identity exits non-zero and names them; the same command with
   `--take-over` exits 0 and sets `owner` to the caller. This is the criterion
   that would pass vacuously if the guard were only on the ticket.
7. `tcw work tracker release <slug>` leaves the item's status, the ticket's
   status and the binding sidecar's binding keys unchanged, clears the item's
   `owner`, and leaves the ticket unassigned.
8. After that release, `tcw work tracker claim <slug>` from a second account
   exits 0.
9. `tcw work tracker release <slug>` on a ticket assigned to another account
   exits non-zero and names them; the same command with `--force` exits 0 and
   leaves the ticket unassigned.
10. When the unassignment is refused by the tracker — driven with the fake's
    `fail(...)` hook on the assignee endpoint — `release` exits non-zero, says
    the ticket was not released, and the item's `owner` is **unchanged**.
11. With `work.tracker.exclusive-claim-transition` unset, no `POST` to a
    transitions endpoint is made by any `claim` run — asserted against the fake's
    recorded requests, not inferred from the resulting status.
12. With `work.tracker.exclusive-claim-transition` set to a transition the ticket
    offers, a second account's claim exits non-zero because the workflow refused
    the transition, on a workflow that does not offer it from its own
    destination.
13. `tcw validate` accepts a `work.tracker` block without
    `exclusive-claim-transition` and one with it, and reports an unknown key for
    a misspelling of it.
14. The existing `tests/test_tracker_sync.py`, `tests/test_tracker_strict.py`,
    `tests/test_tracker_link.py` and `tests/test_tracker_import.py` suites pass
    **unchanged** — this child edits none of the code they cover.

**Not checkable by the suite**, stated here so a green run is not mistaken for
proof:

- **Criterion 4 proves the logic, not Jira.** The fake interleaves a read and a
  write deterministically; it does not establish that Jira's own read-after-write
  consistency behaves as this design assumes. One real two-account attempt
  against a live project is what would, and the epic's verification list already
  carries it.
- **Criterion 10 proves the handling, not the trigger.** Whether real Jira
  refuses an unassignment on a project that forbids unassigned issues — and with
  what status code and message — has to be tried against a live project. The fake
  is made to fail on demand; it does not know when Jira would.
- **Whether the floor is acceptable in practice.** The window in the Design
  section is a judgment about a trade, not a fact a test can settle.

## Risks

1. **The race window is the whole point of the trade, and it is real.**
   Read-after-write narrows it; it does not close it. If the requester decides at
   verification that the floor is too weak, the answer is to make the assertion
   transition the recommended configuration rather than to redesign — but that
   decision belongs to a person, not to this spec.
2. **The opt-in ceiling moves the ticket.** A project that sets
   `exclusive-claim-transition` gets a claim that changes the ticket's status,
   which is the behaviour this epic exists to separate. That is a deliberate,
   documented, opt-in exception, and the risk is that it reads as a contradiction
   to somebody who meets the key before the reasoning.
3. **Release can be refused by a project that forbids unassigned issues**, and no
   test will ever show it. The handling is specified (criterion 10) and the
   trigger is not reproducible here. A user on such a project has no way to
   release a ticket at all; if that turns out to be common, the answer is
   probably to assign it to a configured default rather than to nobody, which
   would be a follow-up item, not a redesign of this one.
4. **Two identity ladders could reappear.** `_local_owner` is deliberately reused
   so the local owner and the Jira assignee come from one place. A Git email is
   not a Jira account id, and the two are *compared* nowhere — the item's `owner`
   is the local string, the ticket's assignee is the account the credentials
   authenticate as. They are written together and are one fact by construction,
   not by comparison. Anything that starts comparing them will find they never
   match.
5. **The claim can half-succeed.** Steps 6 to 8 are three tracker-and-store
   operations with no transaction across them. A crash between the assignment and
   the local write leaves the ticket assigned and the item unowned. Re-running
   `claim` fixes it, because every step is idempotent for the holder — but that
   is a property the implementation has to keep, not one the design guarantees on
   its own.

## Notes

- **This child got smaller during its own spec review**, and the epic's spec was
  changed rather than worked around. What left was the `claim: owed | done`
  removal; where it went and why is in the Non-goals and in the epic's C1 and C2
  sections.
- **The command sits under `tcw work tracker` but works without a tracker.**
  Criterion 5 makes an unbound claim legal, which puts a tracker-free operation
  under a tracker-named group. The epic's spec names the surface, so it stands;
  it is recorded here because it is the kind of wart that gets re-litigated.
- **`--part` is accepted by both verbs** for the same reason `link` accepts it:
  one ticket can back several items, and the claim is on the item.
- Asked for reference material at the request stage; the requester's answer was
  that the epic's spec, the code it cites, and GitHub #41 and #42 are the whole
  of it.
