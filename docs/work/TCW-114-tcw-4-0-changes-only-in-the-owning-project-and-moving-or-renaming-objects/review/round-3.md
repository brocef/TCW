---
verdict: rejected
judges: 3
---

# Review round 3 — TCW-114

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `ed05f719`, against the qa rejection that
implement round 3 answers, over `d1a86554..ed05f719`. The earlier rounds'
results carry forward. The dispatching session checked the finding against
the code before writing this round.

The reviewer recommended accepting, with one cosmetic finding that belongs
to this change. The user's rule for the TCW-99 children is that an item is
accepted only when the review finds no open finding belonging to the change,
so this round is recorded as rejected.

## Checks run

- The full suite as CI runs it, run by the dispatching session at `b1668d0c`
  in two halves by folder: `2076 passed, 2 skipped` and `4750 passed,
  111 skipped`, recorded in `implement/round-3.md`.
- By the reviewer: `tests/work/test_removed_options.py` and
  `tests/work/test_cli_items.py`, `48 passed`.
- By hand through the guarded wrapper, with `app` and `core` side by side:
  the refusal advised `tcw -C …/core work edit core.work/<x> --blocked-by
  app.work/<a>`; run as advised it exits 0, `core`'s item holds the blocker,
  and `app`'s files are unchanged. The address form also works.

## The qa rejection

Met. A full identifier or address is kept as typed; a folder id-path or a
bare tracker key gets this project's ID in front, and the other project reads
such a key by opening this one (`tcw/work/open.py:200-205`), so it finds the
same item. Building the advice opens no backend. A target in this project
gets no `-C` and the item as typed. Every part is shell-quoted. The tests run
the advised command and see it succeed.

## Findings

1. `tcw/work/cli.py:211`: the placeholder for an item that cannot be
   resolved, `<this item's full id>`, holds an apostrophe, so a person who
   pastes the advised line into a shell is left inside an open quote.

## What implement must do

- (a) A placeholder with no quote character, such as `<full id>`, with the
  test that reads it (`tests/work/test_removed_options.py:156`).
- (b) `implement/round-4.md`.
