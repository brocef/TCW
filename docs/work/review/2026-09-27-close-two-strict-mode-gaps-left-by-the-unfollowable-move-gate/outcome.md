# Outcome — Close two strict-mode gaps left by the unfollowable-move gate

## What shipped

| Task | Commit | What |
| ---- | ------ | ---- |
| 1–2 | `4c4ac39a` | Tests, then `sync.needs_claim` (one rule for `deliver` and the gate), ownership forced on in `authorize` where it says so, and a refusal for a catch-up walk of more than one rung. |
| docs | `fe54a481` | `docs/guide/jira.md` (strict `complete` row), changelog and release-note entry files. |
| review | `6be604ef` | The refusal's advice fits the item's status (no `submit` for an item already in review) and always offers moving the ticket one status by hand; three comments name the catch-up exception. |

## Tests

- In `tests/test_tracker_strict_gate.py`: `test_a_catch_up_binding_is_walked_not_refused`
  is replaced (its expectation is what this item changes) by five tests —
  refused then taken one step at a time; broken part-way, refused before
  anything moves; held by someone else, refused; one step away and held,
  passes; and at review, an item already in review gets no `submit` advice and
  the tracker step works.
- Against the code before the fix: the first three failed; the held-and-one-
  step test passed (a guard). The reviewer mutation-checked the ownership line
  and the refusal (each turns its tests red); I checked the review advice test
  against advice that always names `submit` (red).
- Full suite after the review fix: 4809 passed, 3 skipped.

## What the plan or spec got wrong

- **The advice assumed the item was active.** A shared part lets a review
  item's ticket lag two statuses, where "submit first" is impossible. Found by
  review.
- **Three comments** said a completion is never asked who holds the ticket;
  each now names the exception.

## Autonomous decisions

- **Gap 2 — how the gate handles a multi-rung catch-up walk (spec).** Codex:
  refuse and ask the user to bring the ticket along first (option A); checking
  only the first rung leaves the bug, and checking configured transition names
  cannot see the live workflow. Opus: A too, but advising `tcw work tracker
  sync` would loop forever for a named-part binding, and a colleague-held ticket
  would then fail the claim. Chose A in the form "one step at a time" (submit
  first, or move the ticket one status in the tracker), which works for every
  binding and needs no `sync`.
- Review (adversarial-code-reviewer, "merge after the one fix"): accepted the
  advice finding and the three comments. Nothing rejected.
