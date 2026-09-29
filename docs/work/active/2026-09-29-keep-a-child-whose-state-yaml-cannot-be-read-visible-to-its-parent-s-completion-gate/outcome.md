# Outcome — Keep a child whose state.yaml cannot be read visible to its parent's completion gate

Taken up during the autonomous bug run because the combined review of
`bug-run` found a regression. After
`2026-09-26-keep-one-unreadable-state-yaml-or-artifact-from-breaking-the-board-or-an-item-s-detail`,
an epic could complete over a slice whose `state.yaml` was not UTF-8. On
`main` that case failed closed. The scope was widened from the parent gate
to include the epic gate.

## What shipped

| Commit | What |
| ------ | ---- |
| `886c0102` | `unreadable_open_items` / `unreadable_slice_candidates` (the abstract store's default is `[]`; the filesystem store implements both); `_state_damage` pulled out of `_require_readable_state`; refusals added to `require_nothing_open_beneath` and to the epic branch of `complete`; tests; guide, skill reference, changelog and release note. |
| `62b6cc86` | Review fold-in: `tcw work complete` runs the store's checks **before** merging a worktree branch, replacing its own copy of the open-children check; `drop` refuses over a damaged open item; the damaged item is left out of its own refusal; `require_readable_slices` added; docs and spec corrected on where `--force` applies. |

## Tests

`tests/test_unreadable_state_gates.py`, 11 tests:

- **Criteria 1 to 5**, which now assert the epic gate's own wording.
- **`--force` on the epic's own board:** still refused, because the parent
  gate catches the item there.
- **The damaged item's own refusal:** it is refused by the move's own
  message, not listed in its own refusal.
- **`drop`:** refused over a damaged child, and allowed for the damaged item
  itself.
- **The CLI refuses before the worktree merge:** checked with
  `refused_before_merge`.

Against the code before the fix, 6 of the first 7 tests failed with "did not
raise". The damaged-resolved-item test passes before and after, which is its
job: it guards against the fix going too far.

Each refusal was also removed on purpose to confirm its test goes red:

| Removed | Test that went red |
| ------- | ------------------ |
| Parent refusal | The 3 parent tests |
| Epic refusal | The child-node test (now also the same-board wording asserts) |
| The CLI's new check order | The CLI test |
| The `drop` guard | The `drop` test |

Hands-on with the real CLI on a scratch board:

- A discard or `drop` of the parent over a non-UTF-8 child is refused, and
  the refusal names the file.
- `tcw validate` reports the file.
- Dropping the damaged child is allowed, and the parent then discards.

## What the spec got wrong

- **The CLI route.** The spec did not see that `tcw work complete` had its
  own copy of the open-children check, run before the merge, so the store's
  new refusal would have arrived after the merge.
- **`drop`.** It was left out, although it is irreversible.
- **`--force`.** The spec said `--force` bypasses the epic refusal. It does
  so only for items in nodes below.

All three were amended at review.

## Autonomous decisions

- **Advisors.** None consulted: the item's intake already named the direction
  ("refuse while any item's state could not be read, naming it").
- **Widening the scope and taking the item up now.** I made that choice
  myself, because it closes a regression that the batch introduced.
- **Review (adversarial-code-reviewer, NOT DONE).**
  - Accepted all five findings. Finding 3 (`drop`) was folded in rather
    than filed, since it has the same root cause and is a one-line guard.
  - Left for a separate change: the CLI's existing epic open-children check
    still runs after the merge, as it already did on `main`.
- **The reviewer's open question, answered by me.** Is it acceptable that
  one item with malformed YAML now blocks every complete, discard and drop
  on its board, where `main` blocked nothing for that case? I kept it:
  - It fails closed.
  - The message names the file.
  - The damaged item can still be dropped.
  - This is the direction the intake asked for.

  **I would have asked the user about this.**
