# Refined outcome

## Verification decision

**Accepted.** Approved for closeout as part of a decision to drive the whole
epic to completion, use the resulting lifecycle for a while, and refine it later
under a fresh work item rather than polishing each child in isolation.

The reasoning is worth recording, because it sets the standard the remaining
children are held to: the epic exists because the lifecycle was never defined
once and drifted across six documents. A definition cannot be evaluated before
it is run. Child 1 already produced two corrections that only implementation
could surface, which is the argument against more up-front analysis per child.

## Evidence

- 767 Python tests pass (from 733); 44 web tests pass; `tcw validate` OK.
- A full end-to-end run in a scratch repo with `docs/work/review/` deleted
  first, standing in for a node that predates the status:
  `new → start → submit → rework (refused) → rework → submit → complete`.
- The parity guard broken by hand in both directions and confirmed red each way.

## Open questions resolved at closeout

- **Keep the `pr` field.** Two reviewers flagged it as speculative and were
  correct in isolation — nothing in this child reads it. Kept because child 2's
  `complete --already-integrated` consumes it, and reverting a field we re-add
  two commits later is churn under a ship-then-refine plan.
- **Accept the parity test's regex brittleness.** The alternative is requiring
  Node.js in the Python suite. The `assert m, "declaration not found"` guard
  means a reformat reads as a broken test rather than silently passing, which is
  the only failure mode worse than having no guard.
- **No version cut here.** `docs/{changelogs,release-notes}/upcoming.md`
  accumulate across all five children and the version is cut once at epic close,
  so the release note describes a whole lifecycle rather than a half-built state
  machine.

## Capability reconciliation

- **New, both `Supported`:** `work/submit-a-work-item-for-review`,
  `work/rework-a-reviewed-work-item`.
- **Changed:** `work/complete-a-work-item` (two legal source statuses, plus the
  advisory verify-skipped note), `work/view-the-board` (`review` is live work
  and stays on the default board).
- `work/start-a-work-item` was listed as changed in the spec but is not — this
  child added no gate and changed no behavior on that path. Left untouched.

## Deferred to the remaining children

Nothing from this child's scope is outstanding. Two notes carried forward:

- **Child 2 must not add a `submit` gate.** `submit` deliberately carries none,
  even though the epic spec lists `outcome.md` as a soft check — soft means
  judgment, and per the terminology rule the CLI must not refuse on it. If the
  hook layer makes a `pre` binding tempting there, that is a user's choice to
  configure, not a default to ship.
- **Child 4 describes what shipped, not what the plan predicted.** Two spec
  claims were wrong before implementation corrected them.

## Notes

Process observation worth keeping: the per-child cycle for children 3 and 5 is
being compressed to `plan → implement → verify` with no separate spec, because
the epic plan already specifies both at spec-level detail. Children 2 and 4 keep
the full cycle — 2 has the largest design surface, 4 the most judgment. That is
a deliberate departure from uniform ceremony, and if it turns out to be the
wrong call, this is the line to point at.
