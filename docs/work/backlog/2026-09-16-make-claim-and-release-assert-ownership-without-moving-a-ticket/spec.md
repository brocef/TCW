# Spec: Make claim and release assert ownership without moving a ticket

## Capability changes

Planned deltas. No ledger record is written at this stage.

- **new** `work/hold-a-tracker-ticket` — holding a piece of work, and letting go
  of it, becomes something a user does in its own right. Two verbs,
  `tcw work tracker claim <slug>` and `tcw work tracker release <slug>`, that
  say who owns the work and change nothing else.
- **changed** `work/manage-external-tracker-intake` (`cap-bd57b7`) — its text
  says the binding "records what is bound to what and when, never who took the
  ticket", and describes claiming only as something `import` does as part of
  moving a ticket. Ownership becomes assertable on its own, on an item that was
  never imported.
- **changed** `work/synchronize-external-tracker-work` (`cap-207f2c`) — its text
  describes a binding whose "claim is still owed", which is the record key this
  child removes. What is owed is now read from the ticket, not from a file.
- **changed** `work/require-tracker-backed-work` — strict mode's refusals are
  written in terms of the same record key.

`work/start-a-work-item` is **not** changed here. `tcw work start` behaves
exactly as it does today; making the lifecycle moves compose these primitives is
C4.

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

Three consequences, all of them live defects filed elsewhere:

1. **There is no way to say "this is mine" without saying "and it has
   started".** Every verb that needs ownership has to move the ticket to get it.
2. **There is no way to say "this is no longer mine".** The only exits are
   `unlink`, which destroys the binding, and resolving the item.
3. **Ownership is recorded in the wrong place.** Whether a claim is outstanding
   lives inside the sync record as `claim: owed | done`
   (`tcw/tracker/sync.py:338`, `:623`) — a field about ownership inside a record
   about status delivery. `tcw work show` reads it to print "; the claim is still
   owed" (`tcw/work/cli.py:216`), `classify_binding` rejects a record without it
   (`tcw/store/base.py:442`), and the projection schema enumerates it
   (`tcw/work/projection.py:125`).

Locally, the same entanglement holds: an item's `owner` is written only by
`start` (`tcw/store/base.py:3478`, `tcw/store/fs.py:3751-3812`), and the only
way to change it afterwards is `start --take-over`.

## Goals

1. `tcw work tracker claim <slug>` asserts ownership and nothing else: it sets
   the item's `owner` and, where a binding exists, assigns the ticket to the
   caller. It applies no transition by default and changes no status, local or
   remote.
2. `tcw work tracker release <slug>` drops ownership and nothing else: the
   item's status, the ticket's status and the binding are untouched.
3. Ownership is **one fact**. The item's `owner` and the ticket's assignee are
   written together and are required to agree.
4. `claim` is idempotent for whoever holds it, and refuses anyone else by name.
5. Exclusivity has a uniform floor — read-after-write — and an opt-in ceiling
   for a project whose workflow genuinely refuses a second claimant.
6. `claim: owed | done` is gone from the sync record, and what it answered is
   read from the ticket instead.

## Non-goals

- **The other three children.** `sync` moving a ticket in either direction is
  C2. Retiring `transitions.claim` into `transitions.start` is C3. Making
  `start`, `submit`, `rework`, `complete` and `discard` compose these primitives
  — and retiring `link --sync-status` — is C4. This child changes no lifecycle
  move, adds and removes no configuration key other than the optional assertion
  key below, and leaves `tcw work start`'s behaviour byte-for-byte as it is.
- **The web app.** `tcw serve` has its own start path that passes neither an
  owner nor a take-over (`tcw/serve/__init__.py:903` —
  `work.start(slug, force=force)`). This child adds no claim or release action
  to it and changes none of its code. **Recorded rather than assumed:** an item
  started from the web app gets whatever owner `work.start` gives it, and there
  is no way to assert or drop ownership from the browser. Whether that matters
  is a follow-up item's question, raised at this epic's closeout.
- **`.claiming/`.** It is adapter-private filesystem staging behind the local
  claim (`tcw/store/fs.py:921`, `:3799`, `:3851`) and stays exactly what it is.
- **Reading Jira's workflow definition.** The optional assertion below is
  configured by hand, not discovered.
- **Closing any of the six subsumed problems**, including GitHub #41 and #42.
  They are evidence; the epic closes them after publication.

### Why the sweep is narrowed

The epic swept claim-and-status coupling through `tcw/tracker/` and
`tcw/work/cli.py` and found `tcw/serve/` to be the one other place with its own
start path. That sweep is inherited here and was re-run for this child against
`tcw/` for the two things this child actually moves: writers of an item's
`owner` (`tcw/store/base.py:3478`, `:3497`, `tcw/store/fs.py:3779`, `:3805` —
all inside `start`) and readers of the sync record's `claim` key
(`tcw/tracker/sync.py:293`, `:307`, `:338`, `:623`, `tcw/work/cli.py:216`,
`:2509`, `tcw/store/base.py:442`, `tcw/work/projection.py:125`). Those eight
sites are the whole of it; nothing else in the tree reads either.

## Design

### The two verbs

```
tcw work tracker claim <slug> [--part <name>] [--owner <identity>] [--take-over]
tcw work tracker release <slug> [--part <name>] [--owner <identity>] [--force]
```

`--owner` resolves through `_local_owner` (`tcw/work/cli.py:1005-1017`) exactly
as `start`'s does: the flag, then `TCW_WORK_OWNER`, then the Git email, then the
Git name. This is deliberately the same identity ladder, because the local owner
and the Jira assignee are being made into one fact and two ladders would make
them two.

**Claim, step by step.** Both halves are attempted; neither is skipped because
the other is already true.

1. Resolve the item and the caller's identity. No identity is a refusal, worded
   as `start`'s is (`tcw/work/cli.py:1122`).
2. Read the binding (`binding_of`). **An unbound item is claimable** — claiming
   is a statement about the work, and the tracker is where that statement is
   also published when there is one to publish. An unbound claim writes the
   local owner and says the ticket half was skipped because there is no ticket.
3. Where bound, read the ticket (`read_ticket`). A resolved ticket is refused:
   ownership of finished work means nothing, and today's `claim` refuses one
   too (`tcw/tracker/intake.py:344`, row `1a`).
4. If the ticket is assigned to someone else, refuse and name them, unless
   `--take-over` was passed. This is row `1b`'s refusal, kept.
5. **Assign** the ticket to the caller. No transition is applied.
6. **Read the ticket back** and confirm the assignee is still the caller. If it
   is not, the claim failed: report who won and exit non-zero, leaving the local
   owner unwritten.
7. Write the item's `owner` with `set_field(slug, "owner", owner)` — the
   abstract operation that already exists (`tcw/store/base.py:3006`) and that
   `start` itself uses for exactly this field (`:3478`). The local write comes
   **after** the read-back, so an item is never marked owned by someone who lost
   the race.

Idempotence falls out of this without a special case: a holder re-running it
assigns the same account to itself, reads back its own name, and rewrites the
same owner. The ticket's status is not consulted and no transition is applied,
so the ticket cannot move on either pass.

**Release, step by step.** The mirror image.

1. Resolve the item and the identity as above.
2. Where bound, read the ticket. If the assignee is neither empty nor the
   caller, refuse and name the holder — unless `--force`.
3. Unassign the ticket. No transition; the status is not read and not changed.
4. Clear the item's `owner` (`set_field(slug, "owner", "")`).

`--force` exists for one reason, and the help text says so: recovering a ticket
held by an account that has gone away. It is the release-side counterpart of
`start --take-over`, and **the two are reconciled rather than duplicated** —
`claim --take-over` and `start --take-over` mean the same thing and share the
refusal wording; `release --force` is the only new escape hatch.

`started` is left alone by both verbs. It records when work began, which is a
statement about the lifecycle, not about ownership, and C4 owns the lifecycle.

### Exclusivity: a uniform floor and an opt-in ceiling

**The floor is read-after-write**, steps 5 and 6 above. It is weaker than
today's transition-first rule and that is the trade this epic makes: today's
guarantee costs a status move on every claim.

**The window is real and is not closed.** Two claims can both succeed if they
interleave as: A assigns, A reads back, B assigns, B reads back. Nothing in this
design prevents that, and the spec says so rather than implying atomicity. What
it does prevent is the much more likely interleaving — A assigns, B assigns, A
reads and sees B — where today's assignment would simply be overwritten with no
one told.

**The ceiling is opt-in**, under a new configuration key:

```yaml
work:
  tracker:
    exclusive-claim-transition: "Start Progress"
```

When set, `claim` applies that transition before assigning, in today's order and
for today's reason, and a refusal from the workflow is a refusal to claim. When
unset — the default, and what every existing config has — no transition is ever
applied.

**Opting in costs a status move, and the documentation must say so.** A workflow
transition moves the ticket; that is what a transition is. A project that names
one is choosing today's behaviour deliberately for the stronger guarantee, on
the understanding that its claims move the ticket. The key is named for the
guarantee rather than for the move so that nobody reaches for it expecting a
free lunch.

This is a **new** key, not a rename of `transitions.claim`. The two answer
different questions — `transitions.claim` is the transition that a `start`
applies, which C3 renames to `transitions.start` — and collapsing them is what
this epic exists to undo. C3 is unaffected by this key and does not touch it.

### Removing `claim: owed | done`

The key answers one question: *has TCW ever taken this ticket?* With ownership
its own fact, that is answered by the ticket's assignee, which `deliver` already
reads fresh every time and already trusts over the binding
(`tcw/tracker/sync.py:15-18`: "the binding is never proof of anything").

- **Stop writing it.** The two writers (`tcw/tracker/sync.py:338`, `:623`) and
  the one in `link --sync-status` (`tcw/work/cli.py:2509`) drop the key.
- **Accept it on records already on disk.** `_sync_record`
  (`tcw/store/base.py:425-443`) currently makes a record without `claim` into
  `{"problem": ...}`, which would turn every existing binding into a broken one
  the moment this ships, and every new binding into a broken one on an older
  `tcw`. The field moves out of the required set and a value already present is
  ignored. The projection schema (`tcw/work/projection.py:125`) keeps accepting
  it and stops requiring it, for the same reason.
- **Derive what it drove.** `owed` (`tcw/tracker/sync.py:293`) becomes
  `starting or bound.catch_up` for the decisions taken before the ticket is
  read, and the ticket's own assignee for those taken after. `catch-up` is
  already a separate binding note written by the only path that creates an owed
  claim (`tcw/tracker/intake.py:184`, `tcw/work/cli.py:2505`), so the
  information is not being invented.
- **Drop the display.** `tcw work show`'s "; the claim is still owed"
  (`tcw/work/cli.py:216`) goes; a ticket nobody holds is visible from the ticket.

This is the one part of this child that reaches into code C2 and C4 rewrite.
It is here because the epic put it here — the answer moves to where the answer
now lives — and because leaving a required key behind would make C2's work start
by removing it anyway.

### Abstraction litmus test

**Passes.** `claim` is: read a sidecar, read a record from a tracker, write one
field on that record, read it back, write one field on an item. `release` is the
same minus one read. Both are expressed in item, field and reference; neither
needs a folder. The one operation added to the item is `set_field`, which is
already on the abstract `WorkStore` and already implemented by the filesystem
adapter. `.claiming/` is untouched and stays adapter-private.

### Harness compatibility

**Unaffected.** Both verbs are `tcw` CLI subcommands, which behave identically
under Claude and Codex. No skill, hook or injected context carries any guarantee
here. The skill documents change to describe the new verbs; they teach, they do
not enforce.

## Acceptance criteria

Each is runnable against the fake tracker (`tests/tracker_fake.py`) unless
marked otherwise. The fake already holds accounts, a workflow and `before(...)`
hooks for deterministic interleaving, which is what makes 3 checkable at all.

1. `tcw work tracker claim <slug>` run twice by the same account exits 0 both
   times, and the ticket's status — read from the fake after each run — is the
   same string before and after each.
2. After a successful `claim`, the item's `state.yaml` has `owner` set to the
   caller's identity and the ticket's assignee is that same account, on an item
   that is still in `backlog`.
3. `tcw work tracker claim <slug>` against a ticket assigned to another account
   exits non-zero, prints that account's display name, and leaves the item's
   `owner` unchanged.
4. On the fake's `GLOBAL` workflow, where the claim transition is offered from
   every status, two claims from different accounts interleaved as *A assigns,
   B assigns, A reads back* produce exactly one exit-0 run; A's run exits
   non-zero and names B.
5. `tcw work tracker claim <slug>` on an item with no binding exits 0, sets the
   item's `owner`, and says no ticket was assigned because the item is not bound.
6. `tcw work tracker release <slug>` leaves the item's status, the ticket's
   status and the binding sidecar's binding keys unchanged, clears the item's
   `owner`, and leaves the ticket unassigned.
7. After that release, `tcw work tracker claim <slug>` from a second account
   exits 0.
8. `tcw work tracker release <slug>` on a ticket assigned to another account
   exits non-zero and names them; the same command with `--force` exits 0 and
   leaves the ticket unassigned.
9. With `work.tracker.exclusive-claim-transition` unset, no `POST` to a
   transitions endpoint is made by any `claim` run — asserted against the fake's
   recorded requests, not inferred from the resulting status.
10. With `work.tracker.exclusive-claim-transition` set to a transition the
    ticket offers, a second account's claim exits non-zero because the workflow
    refused the transition, on a workflow that does not offer it from its own
    destination.
11. No `claim` key appears in a `tracker.yaml` written by any command, including
    `link --sync-status`; a `tracker.yaml` on disk that still carries one is read
    without becoming `{"problem": ...}`, and `tcw work show` on it exits 0.
12. `tcw work start` on a bound item produces the same ticket status, the same
    assignee and the same exit code as it does on `main` today — checked by the
    existing `tests/test_tracker_sync.py` and `tests/test_tracker_strict.py`
    suites passing unchanged.

**Not checkable by the suite**, and stated here so a green run is not mistaken
for proof:

- **Criterion 4 proves the logic, not Jira.** The fake interleaves a read and a
  write deterministically; it does not establish that Jira's own read-after-write
  consistency behaves the way this design assumes. One real two-account attempt
  against a live project is what would, and the epic's verification list already
  carries it.
- **Whether the floor is acceptable in practice.** The window in the Design
  section is a judgment about a trade, not a fact a test can settle.

## Risks

1. **The race window is the whole point of the trade, and it is real.**
   Read-after-write narrows it; it does not close it. If the requester decides
   at verification that the floor is too weak, the answer is to make the
   assertion transition the recommended configuration rather than to redesign —
   but that decision belongs to a person, not to this spec.
2. **The opt-in ceiling moves the ticket.** A project that sets
   `exclusive-claim-transition` gets a claim that changes the ticket's status,
   which is the behaviour this epic exists to separate. That is a deliberate,
   documented, opt-in exception, and the risk is that it reads as a
   contradiction to someone who meets the key before the reasoning.
3. **Removing a required record key breaks old and new both ways.** A binding
   written by this version and read by an older `tcw` gets a record with no
   `claim`, which the older `_sync_record` turns into a problem record. Nothing
   can be done about the old direction, but the new one must be forgiving, which
   is why acceptance criterion 11 exists in both halves.
4. **`owed` carries more than one meaning.** It is "the ticket was never
   claimed" and, through `walk`, "a catch-up was asked for". Splitting it onto
   `catch_up` and the ticket's assignee is a behaviour change inside `deliver`,
   which C2 then rewrites and C4 then calls differently. If the split turns out
   to need `deliver`'s direction rules changed first, this child stops at the
   record removal and says so, and C2 finishes it.
5. **Strict mode is contended.** `binding_refusal` (`tcw/tracker/sync.py:637`)
   and `authorize` (`:668`) read the claim record, and
   `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`
   also edits them. Whichever lands second rebases.
6. **Two identity ladders could reappear.** `_local_owner` is deliberately
   reused so the local owner and the Jira assignee are derived from one place.
   A Git email is not a Jira account id, and the two are *compared* nowhere —
   the item's `owner` is the local string and the ticket's assignee is the
   account the credentials authenticate as. They are written together and are
   one fact by construction, not by comparison. Anything that starts comparing
   them will find they never match.

## Notes

- **The command sits under `tcw work tracker` but works without a tracker.**
  Criterion 5 makes an unbound claim legal, which puts a tracker-free operation
  under a tracker-named group. The epic's spec names the surface, so it stands;
  it is recorded here because it is the kind of wart that gets re-litigated.
- **`--part` is accepted by both verbs** for the same reason `link` accepts it:
  one ticket can back several items, and the claim is on the item.
- Asked for reference material at the request stage; the requester's answer was
  that the epic's spec, the code it cites, and GitHub #41 and #42 are the whole
  of it.
