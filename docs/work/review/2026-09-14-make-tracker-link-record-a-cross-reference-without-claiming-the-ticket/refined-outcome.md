# Refined outcome — Make `tracker link` record a cross-reference without claiming the ticket

**Accepted.** The user directed closeout after reading the implementation
assessment, having already had the change presented as
[PR #38](https://github.com/brocef/TCW/pull/38).

## Assessment against the spec

All 18 acceptance criteria are met. Evidence, from commands run at verification
rather than during implementation:

| Criteria | Evidence |
| --- | --- |
| 1–3, 6–10, 12, 13 | `tests/test_tracker_link.py` — 19 passed |
| 4, 5 | `grep -rn "claimed-by" tcw/` → 0 |
| 11 | `tests/test_tracker_claim.py` unedited (`git diff origin/main` → 0 lines) and the two pinning tests pass |
| 14, 15 | `tests/test_tracker_help.py`; `tcw work tracker link --help \| grep -ci 'claim\|assign'` → 0, `import` → 6 |
| 16 | The parser walk reports 0 positionals with no `help=` |
| 17 | The four fired documentation entries are in `f5fef3e` |
| 18 | `pytest`: **3113 passed, 1 skipped**. `tcw validate` OK, `tcw capabilities check` OK |

## What verification found

**One criterion had no end-to-end test.** Criterion 12 names an invalid `--part`
among the refusals `link` must still make, and `tests/test_tracker_link.py` never
mentioned `part` at all — on `main` either, so the gap predates this item rather
than being introduced by it. The behaviour was right (`validate_part` is
unit-tested in `tests/test_tracker_binding.py`, and the guard is the first thing
`_tracker_link` does), but nothing pinned it through the command. Closed at
verification in `9b09636`, mutation-checked by removing the guard, rather than
recorded as a gap: it sits inside this item's own criteria, and this repository
prefers the fix to the follow-up.

That is the only finding. No post-mortem is warranted — one criterion missing a
test it shares with an untouched unit test is a coverage gap, not a process
failure, and the coverage table in `spec.md` did point at it. Nothing about the
implementation was rejected or reworked.

## Capability ledger

Reconciled before closeout. `work/manage-external-tracker-intake` (`cap-bd57b7`,
Supported) is rewritten to match what shipped, and the item's `capabilities.yaml`
records it as `changed:`. `tcw capabilities check` passes against `main`'s
reworked ledger, which deleted nine capabilities in the interim but not this one.
No capability was added or removed.

## Deferred, with what each is blocked on

- **The version cut**, deliberately. This repository's guide says to batch the
  cut across a run of items rather than cutting one per item, so
  `docs/{release-notes,changelogs}/upcoming.md` are left un-rotated and both
  carry this item's entries. Offered to the user at closeout; blocked on their
  choice of when the run is over, not on anything technical.

- **Claiming a ticket an item is already linked to.** A non-goal here by
  decision, and the gap it leaves is named in the release note. It belongs to
  `2026-09-12-synchronize-the-work-lifecycle-outward-to-the-tracker`, which is
  blocked on this item and whose `initial-request.md` records the hand-off.

- **`find_binding` still skips resolved items**, so a ticket held by a finished
  item can be bound to a second, open one with no refusal. Not deferred work but
  an accepted limit: fixing it would re-break the discarded case the skip exists
  for. Documented in the docstring, the README, the skill reference and the
  capability.

The DoD's "originating GitHub issue answered and closed" does not apply — this
item came from a `docs/work/inbox/` entry, not from an issue.

## Notes

- **This item completes while PR #38 is unmerged.** The completion transition is
  a commit on the same branch, so the board and the code land on `main`
  together when it merges. Until then `main`'s board does not show this item as
  completed, which is accurate: nothing has shipped there yet.
