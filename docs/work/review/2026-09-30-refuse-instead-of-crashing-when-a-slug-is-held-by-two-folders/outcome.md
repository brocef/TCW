# Outcome: Refuse instead of crashing when a slug is held by two folders

## What shipped

- **Code and tests** — `b0856977`:
  - `_find` (`tcw/store/fs.py`) names every folder and points at `tcw validate`;
  - `main` (`tcw/cli.py`) catches `MultipleMatch`;
  - `_render_board_item` marks the row (`!`, `held by N folders — see tcw
    validate`); `unresolved_blockers` counts a blocker held twice as still
    blocking; `epic_completable` reads a duplicated epic as not ready; the
    descendant board treats a duplicated initiative holder as none;
  - the blocker-cycle remedy points at `tcw validate`;
  - `tests/test_duplicate_slug_refusals.py` (8 tests); two existing tests
    updated from the old "resolves to 2 items" wording to assert the new text
    and the old text's absence.
- **Docs** — `bdc49ab0` (changelog, release notes).

## Test result

- Full suite under bare `pytest` at `d6e98814`: 1 failed, 5219 passed, 3
  skipped; the one failure belongs to the detached-worktree item, not this one.
- Mutation checks: removing each of the three new catches turns a test red.
- Hand sweep over every `tcw work` verb taking a slug: no traceback.

## What the plan or spec got wrong

- **The request's `validate` crash was already fixed** by #58 (`eddfa41e`); the
  item was renamed at spec to the crashes that remained.
- **The first design caught too little.** Three more board calls reached the
  duplicated slug (a blocked item's row, an epic, the descendant board); the
  spec review reproduced it and the spec was amended before coding.
- **My first grep for tests pinning the old wording was too narrow** ("slug
  resolves to"), so two tests using "resolves to 2 items" only failed in the
  related-tests run.

## Notes

- `tcw serve` was not changed: its handlers turn unexpected errors into a 500
  response rather than crashing the server. Not verified by running it.
- The board prints one row for the slug (it keys rows on the slug), showing
  whichever folder's status it read first.

## Folded in at verify

- `e2364c76`: a blocker held twice is labelled `(held by more than one folder)`
  in the board and in `start`'s refusal. The web app answered a duplicated slug
  with a 500 and **one duplicate emptied its whole board** (checked by a new
  test, `tests/test_serve_duplicate_slug.py`); item routes now refuse with 409
  naming the folders, and the board lists the row with no artifacts. This
  corrects the Notes above, which guessed the web app was merely returning an
  error page for the one item.
- Tests: `tests/test_serve*.py`, `test_duplicate_slug_refusals.py`,
  `test_work.py`, `test_retention.py` — 466 passed.
