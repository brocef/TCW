# Request: Make claim and release assert ownership without moving a ticket

This is the first child of
`2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`, and the
one the other three wait on. The epic's spec section **C1** is the brief; this
request records it in the requester's terms and settles the two points that spec
deliberately left open.

## What is being asked for

Today, claiming a ticket and moving a ticket are the same act. The claim applies
a workflow transition and only then assigns the ticket
(`tcw/tracker/intake.py:310-360`), and that same transition is what carries the
ticket to the active status. Because ownership only ever happens as a side
effect of moving, there is no way to say "this is mine" without also saying
"and it has started", and no way to say "this is no longer mine" without
unlinking it or resolving the item.

Make ownership its own fact, with its own two verbs:

- **`tcw work tracker claim <slug>`** asserts that the caller owns this work. It
  sets the item's owner, and where a tracker binding exists it assigns the
  ticket to the caller. It applies no transition and changes no status —
  neither the item's nor the ticket's.
- **`tcw work tracker release <slug>`** drops both. The item's status, the
  ticket's status and the binding are all left exactly as they were.

Ownership is **one fact**, not two. The item's owner and the ticket's assignee
are required to agree; where they disagree, that is drift for `sync` to report,
not something `claim` papers over.

Claiming must be **idempotent for whoever already holds it** — running it twice
succeeds twice and the ticket does not move either time — and must **refuse a
second holder**, naming who holds it.

Exclusivity is established by **read-after-write**: assign, re-read the ticket,
confirm the assignee is still the caller. The loser of a race sees the winner
and backs off. A project whose workflow genuinely refuses a second claim may
additionally name a transition to assert through, keeping today's stronger
guarantee where it exists. **The race window is real and must be written down
rather than implied away** — two claims whose reads interleave exactly can both
report success, and the optional transition assertion is the answer for anyone
who cannot accept that.

This child also carries the removal of **`claim: owed | done` from the sync
record** (`tcw/tracker/sync.py:338`, `:623`), because this is where the answer
to "who holds this" moves to. It stops being a field inside a record about
something else.

## Decisions taken at this stage

Both were left to C1 by the epic's spec, and both were put to the requester:

1. **`release` is self-release, plus a `--force`.** It refuses by default when
   the holder is not the caller, naming them; `--force` releases a ticket held
   by another account, which is what recovers work from a departed colleague.
   This mirrors what `--take-over` already does for the local half of the claim
   (`tcw/store/fs.py:3751`), and reconciling the two is part of this child's
   job rather than a later one's.

2. **The web app is out of scope, and that is recorded rather than assumed.**
   `tcw serve` has its own start path that passes neither an owner nor a
   take-over (`tcw/serve/__init__.py:905` — `work.start(slug, force=force)`).
   C1 changes no web-app code; its spec must state plainly that the web app has
   no claim or release action, so ownership asserted there remains whatever
   `work.start` does on its own. A follow-up item can add it if that turns out
   to matter in use.

## Constraints

- **No transition, no status change.** A claim that moves a ticket is the bug
  this whole epic exists to remove. Neither verb may apply a workflow
  transition as part of asserting or dropping ownership — the only exception is
  the *optional* assertion transition a project opts into, which exists to make
  the claim refuse, not to move the ticket somewhere new.
- **`.claiming/` is not in scope.** It is adapter-private filesystem staging
  behind the local claim (`tcw/store/fs.py:921`, `:3799`) and stays exactly what
  it is. Only what ownership *means* is being changed.
- **The abstraction litmus test governs.** Ownership is an item field plus an
  assignment on a tracker record; read-after-write is two reads and a write.
  Nothing here may require a filesystem.
- **Do not read Jira's workflow definition.**
  `2026-09-15-decide-claim-exclusivity-from-a-jira-project-s-workflow-definition`
  stays parked. This child makes that read optional rather than prerequisite;
  whether the optional assertion covers what that item was parked on is
  answered at the epic's closeout, not here.
- **Strict mode is contended.**
  `2026-09-15-make-the-strict-tracker-gate-refuse-unfollowable-moves-and-allow-child-items`
  also edits `binding_refusal` and `authorize` (`tcw/tracker/sync.py:637`,
  `:668`), which read the claim record this child removes. Whichever lands
  second rebases.

## Out of scope

- The other three children. `sync` moving a ticket either way is C2;
  `transitions.claim` retiring into `transitions.start` is C3; the lifecycle
  moves composing these primitives is C4. This child changes no lifecycle move
  and no config key.
- Closing GitHub #41 and #42, or any of the six subsumed problems. They stay
  open as independent evidence and are resolved at the epic's closeout, after
  the version carrying the work is cut and pushed.
- `tracker create` (GitHub #43) and tracker field writes (GitHub #37).

## Verification the suite cannot do

The concurrent-claim race (the epic's acceptance criterion 3) cannot be driven
from the test suite against real Jira. The fake tracker can interleave the read
and the write deterministically, and that proves the *logic*; it does not prove
Jira's own consistency behaves as this design assumes. This child's spec must
keep that distinction explicit rather than let a green fake stand in for it.

## Notes

- Asked for reference material; the requester's answer was that the epic's
  `spec.md`, the code it cites, and GitHub #41 and #42 are the whole of it.
  Nothing further was provided.
- The epic's spec was amended after its verb table was agreed: the rule that
  survived is **a claim gates work, not resolution**. That rule is C4's to
  implement, but it is the reason this child must not make the claim a
  precondition of anything — it only has to make ownership assertable and
  droppable.

## References

- `docs/work/active/2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs/spec.md`
  — section **C1** is this child's brief, and the acceptance criteria 1 through
  4 and 11 are the ones this child is answerable for.
- `tcw/tracker/intake.py:310-360` — the current `claim`, where transition-first
  and assign-after are entangled; the docstring explains why it is ordered that
  way, and that reasoning is what changes.
- `tcw/tracker/claim.py` — the pure claimability/exclusivity assessment, and the
  written record of why the workflow definition is not read. Its two words held
  apart, *claimable* and *exclusive*, are the vocabulary this child inherits.
- `tcw/tracker/sync.py:338`, `:623` — the `claim: owed | done` writes this child
  removes.
- `tcw/store/fs.py:3751` — `start`'s `owner` and `take_over`, the local half of
  ownership that `claim` and `release` have to reconcile with.
- GitHub #41 and #42 — the two issues whose mechanism is this entanglement; they
  are evidence, not this child's to close.
