# Accepted

The user accepted this child and its sibling together, and chose the closeout
route in the same message: "1. Accept both 2. Merge to main locally 3. C4 now."

## What was accepted

Twelve commits. Eight were written at the `implement` stage; one strengthened two
tests immediately after (`c2ce6813`); three answered the verify assessment.

Two pieces of work the epic deliberately put together:

**`sync` reconciles a ticket to its item in either direction.** The forward-only
rule is gone. A ticket ahead of its item is brought back, one behind is brought
forward. The `--part` hold survives: a binding for a named part is reported on
rather than reconciled, because several items share that ticket and a hold leaves
no evidence outside the checkout it happened in.

**`claim: owed | done` is gone from the sync record.** What `owed` actually drove
was which tickets `deliver` claims and walks forward, which is what this child
rewrites. A `tracker.yaml` already on disk carrying either value still reads: the
key is ignored, and a test pins both values end to end.

## What the implementation found that the spec had wrong

**The spec's replacement for `owed` did not work, and building it is what showed
that.** The design was `owed = starting or bound.catch_up`, dropping the retry of
a failed `start` claim and sending users to `tcw work tracker claim`. After that
verb takes the ticket, `sync` still could not deliver — the record's window
refuses a ticket below it — and a ticket in a status the project maps to nothing,
where a never-claimed ticket usually sits, could not be walked onto the ladder at
all, because the claim transition was the only thing that ever put it there. That
coupling is C3's and C4's to remove.

The shipped answer is smaller than the spec: the record's own `move` field
already says a start's delivery never finished, so `record["move"] == "start"`
carries the fact with no new state. The epic's premise that both pinned tests
would have to change turned out half right — `tests/test_tracker_sync.py:1710`
behaves identically and only its name and one assertion changed; `:983` genuinely
changed.

## What the verify stage found

Four findings, all addressed:

- **A second lost corner the outcome did not admit.** Dropping the
  `record["claim"] != "owed"` term from `stale` means a sibling-part hold now
  discards a record that still names the `start`. See the disagreement below.
- **`tcw work rework` misdescribed the user's own action.** `deliver` set the
  "ticket was ahead of its item" note for any caller, not only `sync`, and
  `rework` moves an item from review back to active every time it runs — so every
  `rework` of a bound item announced the user's deliberate move as drift somebody
  else caused. Fixed at the source: the note is set only when syncing, and both
  prints that can no longer fire are deleted.
- **Two of acceptance criterion 9's four legs were not pinned.** `record_unsent`
  and `link --sync-status` could each still write `claim` to disk with the suite
  green. The second was the same masked-read the implementation had already
  fixed once, a level up: the test asserted on the record, but `deliver`'s
  `finish` overwrote it between the link's write and the assertion, so the test
  observed `finish` and never the function it named. Both are now pinned by tests
  that read the file at the moment the named writer wrote it.
- **Three dead terms**, deleted rather than tested.

**A test that was not earned, caught by its own author.** The first version of
the `rework` test observed only the command output that the deleted print had
already silenced, so dropping the `syncing` term left it green. Assertions
against `deliver` itself are what make it red.

## The one instruction that was pushed back on, and rightly

The verify assessment asked for the `owed` guard in `stale` to be restored in
terms of the new rule. Building it showed that it breaks
`tests/test_tracker_strict.py:762`, a test that exists to stop strict mode
locking a user out of their own lifecycle: with the record kept,
`binding_refusal` refuses every local move on the held item, so somebody whose
`start` never reached the tracker cannot submit finished work until an unrelated
part closes.

So the real trade is **one extra recovery command, whose name the refusal
prints**, against **a user unable to move their own work until somebody else's
item closes**. The cheaper failure was the right one to take. The principled
argument is better still: while another part holds the ticket this item owes the
tracker nothing, which is exactly why the record is dropped — the claim was a
different fact riding on that record, and keeping the record alive to carry it is
`claim: owed | done` returning under another name, which is the thing this item
removes.

The cost is now stated where it happens, admitted as a second corner in
`outcome.md`, the guide, the release notes, the changelog and the capability
text, and pinned by two tests that fail in opposite directions.

## Definition of Done

- **tests pass** — the full suite on the branch: **3756 passed**. On `main` with
  this child and its sibling merged: **3767 passed, 0 failed** (13m48s). Also
  `pnpm test` 64 passed, `npx tsc --noEmit` clean, `tcw validate` OK.
  `npx prettier --check` rejects five documents this item edited — it rejects the
  same five with the change stashed, so that is
  `2026-09-15-make-pnpm-prettify-check-pass-on-a-clean-checkout`, not this item.
- **docs synced** — `docs/guide/jira.md`, `README.md`,
  `skills/work/references/commands.md`, `docs/release-notes/upcoming.md`,
  `docs/changelogs/upcoming.md`, and the descriptions of the two capabilities
  this item changes. `Tracker-Change`, `Any-Code-Change`, `Public-CLI-API` and
  `Skill-Driven-Component` fired.
- **capabilities reconciled** — `capabilities.yaml` declares
  `work/synchronize-external-tracker-work` and `work/require-tracker-backed-work`
  as `changed:`. Both resolve and both are already `Supported`, so nothing is
  flipped; their descriptions were rewritten to match what shipped. There is no
  new capability.
- **reviewed** — the finished change by the `tcw-verifier` agent, which produced
  the four findings above from twenty-four mutations, nineteen of which went red.
  Every finding was reproduced independently before being acted on, and one
  instruction was argued down on the evidence. There was no separate adversarial
  review of the spec.
- **version offered** — the version stays where it is, batched for after C4 as
  `CLAUDE.md` asks.
- **originating GitHub issue answered and closed** — not applicable. The item
  came from the epic, not an issue.

## Closeout route

Merged into `main` in the primary checkout locally. Not pushed, no version cut.

## Deliberately left for someone else

- **The record's `move` as a statement about the present** belongs to C4, which
  both children reached independently. `deliver` serves a recorded move while
  `target` comes from the item's current status; C3 added a guard so a stale
  record strands nobody, and C4 is where that coupling is rewritten.
- **`--all` still sweeps only items with a record or an owed comment.** Widening
  it to every bound item costs one tracker read per item per sweep. Reconciling
  drift stays something asked for by naming an item. A stated non-goal.
- **Durable evidence of a `--part` hold** stays
  `2026-09-15-record-lasting-evidence-of-a-tracker-hold-on-a-shared-ticket`. This
  item worked around its absence rather than supplying it.
- **`intake.claim` is untouched.** Its refusal now has a way out appended at the
  call site in `sync.py`, named only when the ticket is unassigned or already
  yours, because sending somebody to claim a ticket another account holds only
  a second refusal naming the same person. The message and the coupling behind it
  belong to C3 and C4.
- **This item was started before its artifacts existed**, so the `request`,
  `spec` and `plan` gates refused — they run from `backlog` and the item was
  already `active`. The stage prompts were read and the artifacts written in
  order, but those gates did not run. Already tracked as
  `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`.
