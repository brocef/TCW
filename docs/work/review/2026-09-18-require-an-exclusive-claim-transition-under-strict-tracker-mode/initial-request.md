# Require an exclusive claim transition under strict tracker mode

## Request

Under `work.tracker.strict: true`, `tcw validate` must refuse a configuration
that does not set `work.tracker.exclusive-claim-transition`, and the refusal must
name that key.

**Why.** A strict project today believes that starting an item takes its ticket
exclusively. That belief is enforced by `claim_refusal`
(`tcw/tracker/sync.py`), which checks whether the workflow still offers
`transitions.start` after the claim. C4
(`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`) stops the claim
from moving the ticket, and so removes that check from the lifecycle. After C4
the only thing that can still make a claim exclusive is C1's opt-in assertion
through `exclusive-claim-transition`. A strict project that has not set that key
would keep believing in a guarantee that nothing enforces. Making the key
required under strict mode turns that silent loss into a message the project
sees.

That is why this item blocks C4: it has to land first, so no build on `main`
has C4's behaviour without this requirement.

**Scope, as the requester confirmed it: validation only.**

- The new requirement sits alongside the keys strict mode already requires
  (`statuses.active`, `statuses.completed`, `statuses.discarded`). It is a
  configuration problem like theirs, so the result is also the same. `tcw
  validate` reports the problem, and every strict move refuses because the
  tracker configuration is broken, until the key is set. Strict mode already
  handles a broken configuration by refusing, never by turning its gates off.
  This item keeps that behaviour and does not invent another.
- The message should tell an upgrading project what to do, as C3's
  `transitions.claim` retirement did: name the key and say why strict mode now
  needs it.
- Today's strict `start` (`_strict_claim` → `intake.claim` → `claim_refusal`) is
  **not** rewired to use the key here. C4 deletes that path and routes a strict
  start through `assert_ownership`, which already asserts through the key when it
  is set. So between this item and C4, the key is required but not yet used. That
  window never reaches a user, because the whole epic ships in one version cut.

## Constraints

- It is a breaking change for every strict project, and a deliberate one: C4's
  spec, Design section 4 and Risk 1, argues that the alternative is a guarantee
  nothing enforces. The release notes lead with it. C4's plan already says its
  own release-note entry leads with this, so the two entries must not
  contradict each other or say the same thing twice.
- The documentation this changes, per the epic's Documentation Sync map:
  `skills/configure/references/tracker.md` (Configuration-Key-Change),
  `docs/guide/jira.md` (Tracker-Change), and both `upcoming.md` files.

## Out of scope

- Wiring strict `start` to the key (C4 does it).
- Removing `claim_refusal`'s lifecycle call sites, and deleting `_strict_claim`.
  These were once part of this item's brief (C4's plan, old Task 8). C4's plan
  now keeps them in its own Task 4, because they belong to the claim change and
  not to a configuration key.
- Making `transitions.start` optional
  (`2026-09-18-make-transitions-start-optional-now-that-a-start-goes-through-assess-move`).
- Checking the named transition against the live Jira workflow. `validate` works
  offline.

## Notes

- Requester asked for reference material: asked; none provided beyond the ones
  listed below.
- No project on this machine sets `strict: true` today, including this
  repository's own `tcw-config.yaml`, so nothing here needs migrating.
- **Corrected at `spec` (2026-09-22).** The Request above says the window between
  this item and C4 never reaches a user because the whole epic ships in one
  version cut. That is wrong: C1 and C3 shipped in v2.4.0, and v2.5.0 and v2.5.1
  were cut after them without C4. The spec treats a release between this item and
  C4 as possible (its Risk 2) and keeps every sentence this item writes true in
  that state.

## References

- `docs/work/backlog/2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync/spec.md`:
  Design section 4 and acceptance criterion 15. This item takes that criterion
  over, and the section argues why.
- C3, `2026-09-16-retire-the-claim-transition-key-into-a-named-start-transition`
  (completed in `a2b72dac`), and `TRACKER_RENAMED_KEYS` in
  `tcw/store/base.py`: the migration shape to copy, which says what changed and
  what to set instead.
- C1, `2026-09-16-make-claim-and-release-assert-ownership-without-moving-a-ticket`
  (completed in `ee59c22a`), and `tcw/tracker/ownership.py`'s module docstring:
  what `exclusive-claim-transition` means and what it costs.
