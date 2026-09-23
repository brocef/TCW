# Make `transitions.start` optional now that a start goes through `assess_move`

## Request

`work.tracker.transitions.start` must stop being a required setting. A tracker
configuration that does not set it must pass `tcw validate`, and a start must then
find its transition the same way the other four moves do — from the status the
move is heading for.

**Why.** The key was required for one reason, stated in the code itself
(`tcw/store/base.py:1263-1266` and `:1503-1508`): a start applied its transition
through the claim rather than through `assess_move`, so it had no rule to fall
back on when the key was absent. C4
(`2026-09-16-compose-the-lifecycle-moves-from-claim-and-sync`, completed
2026-09-22) removed that reason. A start now goes through `assess_move` like
every other move, and `assess_move` derives the transition from the target status
when no name is configured.

Leaving the key required after its reason is gone forces every tracker-backed
project to name a transition TCW can work out for itself, and makes three comments
in the code say something that is no longer true.

**Scope, as the requester confirmed it on 2026-09-22: drop the requirement, and
nothing more.**

- Remove the parser check that reports `work.tracker.transitions.start: required`
  (`tcw/store/base.py:1507-1508`).
- Remove the special case in `assess_move` (`tcw/tracker/sync.py:276-281`) that
  withholds the ", or remove it to let TCW find the transition itself" advice for
  `start` alone. Its stated reason — that removing the key is something `tcw
  validate` refuses — stops being true with the check gone.
- Correct the three comments that assert the key is required: `base.py:1263-1266`,
  `base.py:1503-1506`, and `_parse_tracker_transitions`' docstring at
  `base.py:1693-1695`.
- Update the test C3 added for the required check, and the documentation.

**Not** in scope: `tcw validate` suggesting that a project remove the key. The
requester ruled that out — a permitted setting should not be one TCW nudges people
away from.

## Constraints

- **This is not a breaking change and must not become one.** A configuration that
  sets `transitions.start` keeps working exactly as it does now, with the named
  transition applied. Only the absence of the key changes meaning, from "refused"
  to "derive it from the target status".
- `work.tracker.exclusive-claim-transition` is a different setting and is not
  affected. Strict mode still requires it
  (`2026-09-18-require-an-exclusive-claim-transition-under-strict-tracker-mode`).
- The other half of C4's acceptance criterion 14 lands here. C4 proved that a
  start with the key set posts exactly the one transition the key names; it could
  not prove the other half, that a start with the key unset posts none, because
  the key could not be unset. This item makes that testable, so test it.

## Out of scope

- Any change to what a start does when the key *is* set.
- Anything about `exclusive-claim-transition`, strict mode, or the claim.

## Notes

- Requester asked for reference material: asked; none provided beyond the
  references below.
- This repository's own `tcw-config.yaml` sets `transitions.start: Start` and will
  keep it. That makes it a live example of the setting still being honored, not a
  migration.
- This is the last open child of the epic
  `2026-09-16-separate-claim-from-status-movement-in-the-tracker-verbs`. The
  version cut covering the whole epic follows it.

## References

- C4's `spec.md`, Design section 5 and acceptance criterion 16 — the argument for
  this change, written when it was still part of C4. Retained in commit
  `8e9937b4`.
- `tcw/tracker/sync.py`, `assess_move` — the status-derived rule a start now falls
  back to, and the one place that still treats `start` as the exception.
- C3, `2026-09-16-retire-the-claim-transition-key-into-a-named-start-transition`
  (completed in `a2b72dac`) — it created this key and the test that asserts it is
  required, which is the test to update.
