# Accepted

The user accepted this child and its sibling together, and chose the closeout
route in the same message: "1. Accept both 2. Merge to main locally 3. C4 now."

## What was accepted

Ten commits. Eight were written at the `implement` stage; two more answered the
verify assessment (`639890e5`, `4eb95c15`).

The item does what its title says: `work.tracker.transitions.claim` becomes
`transitions.start`, the transition the `start` move applies, parsed uniformly
with `submit`, `rework`, `complete` and `discard`. `transitions.start` stays
**required**, as `claim` was — the only move with no status-derived fallback,
because a start applies its transition through the claim rather than through
`assess_move`. Making it optional would have been a behaviour change smuggled in
under a rename, and would let a configuration parse while a start could not run.

A configuration still carrying the old key fails closed with two problems, one
naming the exact replacement:

    work.tracker.transitions.claim: renamed to work.tracker.transitions.start,
    the transition the start move applies, alongside submit, rework, complete
    and discard
    work.tracker.transitions.start: required

That is the migration the epic asked for. This repository's own
`tcw-config.yaml` was migrated in the same commit.

## What the verify stage found

**The item's headline claim — that it changes no runtime behaviour — was false,
and the difference stranded work.** `TRACKER_MOVE_TRANSITION_KEYS` gained
`start`, so `move_transitions` now holds it, and `transition_name` has a third
call site at the end of `deliver` that the implementation never examined. `move`
there is not the caller's move: it falls back to the sync record's. So a record
written by a failed `start`, outliving a local status change, reached
`assess_move`'s named branch and refused:

    conflicting — SYNC-1 in 'In Progress' offers no transition named
    'Start Progress'. It offers: 'Ready for Review' to 'In Review'.
    Fix work.tracker.transitions.start, or remove it to let TCW find the
    transition itself.

On `main` that lookup returned `""` and the status-derived rule found
`Ready for Review` by itself. The item was stuck, and the repair the message
offered was impossible, because this change made `transitions.start` required.

The fix is one guard at the shared site, and it is **not** `start`-shaped:

```python
named = (transition_name(config.move_transitions, move, item.resolution)
         if move and MOVE_STATUS.get(move) == local else "")
```

`deliver` serves a recorded move while `target` comes from the item's current
status, so the two disagree whenever a record outlives the status it was written
under — and a transition configured for a move leads where *that* move lands,
not to `target`. A record naming `complete` under an item back in `review` was
broken the same way before this branch existed, reaching a dead end through the
other refusal branch. One guard covers both; a `start`-only patch would have left
the sibling defect in place. Every move a caller passes agrees with the item's
status by construction, so nothing any caller asked for is narrowed.

The removal advice is now offered only for a key that can actually be removed.

**Why the original sweep missed it**, which is the lasting part: the sweep
searched for the key's own spelling, and the site that broke never names the key
— it reads `config.move_transitions` through `transition_name`. Adding a key to a
shared mapping means auditing every reader of that mapping, not every mention of
the key. That is now written into the spec.

**A second lesson, recorded rather than smoothed over.** The implementation
concluded the call was unreachable because a probe fired zero times across four
test modules. That proves no test exercises the call, not that nothing reaches
it. The same mistake in a different form appeared twice more in this epic.

## Definition of Done

- **tests pass** — the full suite on the branch: **3750 passed**. On `main` with
  this child and its sibling merged: **3767 passed, 0 failed** (13m48s), with
  `tcw validate` clean. A further full run on merged `main` is recorded below.
- **docs synced** — `docs/guide/jira.md` (the configuration table row and a new
  "Renaming the start transition" section), `README.md`,
  `skills/configure/references/tracker.md`, `skills/work/references/commands.md`,
  `docs/release-notes/upcoming.md`, `docs/changelogs/upcoming.md`, and this
  repository's own `tcw-config.yaml`. `Configuration-Key-Change`,
  `Tracker-Change`, `Any-Code-Change` and `Skill-Driven-Component` all fired.
- **capabilities reconciled** — no delta, and the item carries no
  `capabilities.yaml`. No ledger entry names the transition key:
  `work/manage-external-tracker-intake` says "the configured claim transition"
  without naming it. The reasoning is in the spec's "Capability changes" section.
- **reviewed** — the finished change by the `tcw-verifier` agent, which found
  the regression above; every one of its findings was reproduced independently
  before being acted on. There was no separate adversarial review of the spec,
  and the regression is the kind a spec review might have caught.
- **version offered** — the version stays where it is. `CLAUDE.md` asks for the
  cut to be batched across a run of items, and C4 is still to come. The entries
  are in `docs/changelogs/upcoming.md` and `docs/release-notes/upcoming.md`.
- **originating GitHub issue answered and closed** — not applicable. The item
  came from the epic, not an issue, and carries no tracker binding.

## Closeout route

Merged into `main` in the primary checkout locally. Not pushed, no version cut.

## Deliberately left for someone else

- **The real defect belongs to C4.** `deliver` treats a record's `move` as a
  statement about what to do now rather than what was last attempted. The guard
  above stops that stranding anyone; the coupling itself is what C4 rewrites.
- **Acceptance criterion 8 is falsified as written.** It says no file under
  `docs/guide/`, `skills/` or `README.md` mentions `transitions.claim`; five
  lines do, all of them the migration documentation the same item requires. Its
  intent — that nothing tells a reader to use the old key — holds exactly. The
  criterion was wrong the moment the plan also required a migration section, and
  it is recorded rather than rewritten after the fact.
- **`tcw/tracker/claim.py`'s `assess(claim_transition=…)` parameter keeps its
  name.** That module answers "can this ticket be claimed", which is still a real
  question until C4 retires the concept. Only the message naming the
  configuration key changed.
- **Released changelogs and release notes keep `transitions.claim`** — that is
  what shipped in them.
- **This item was started before its artifacts existed**, so the `request`,
  `spec` and `plan` gates all refused: they run from `backlog` and the item was
  already `active`. The stage prompts were read and the artifacts written in
  order, but those gates did not run. The hole is already known —
  `2026-09-16-stop-an-item-reaching-implement-without-a-spec-and-plan-and-say-how-to-plan-an-item-started-too-early`.
