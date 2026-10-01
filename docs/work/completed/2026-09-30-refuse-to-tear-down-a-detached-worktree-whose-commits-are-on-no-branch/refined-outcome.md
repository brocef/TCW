# Refined outcome

**Accepted by the user on 2026-10-01**, together with its three sibling items.

## The acceptance criteria

All seven met (`tests/test_detached_worktree_teardown.py`, 10 passed): a
shipping completion refuses and changes nothing, `--force` and
`--already-integrated` included; a discard keeps the worktree and warns; a
worktree detached at the branch tip completes as before; saving the commits on
a branch lets completion through; `remove_worktree` refuses on its own; a plain
folder is never answered for by the primary checkout.

## Deferred, with reasons

- No test drives the ten-hash cap through the CLI, and none checks that a
  discard on a folder git cannot inspect keeps the folder. The code does both
  (the cap was called directly at verify). Too small to hold the item for.
- The check steps aside when the primary checkout has no repository
  (`d49c4fee`); not in the spec, recorded in `outcome.md`.

## Evidence

- Full suite under bare `pytest` at `d61a543f`, clean tree: **5231 passed, 3 skipped**. This is
  the first full run after `d49c4fee`, which `outcome.md` noted had not had one;
  an earlier run at `0080da55` gave 5228 passed, 3 skipped.
- Each item was assessed against its spec by a separate read-only verifier that
  ran the item's targeted tests and reproduced the behaviour by hand in a
  throwaway project. Every acceptance criterion was met.

## Closeout

- The four items were built, reviewed and tested together and are accepted
  together. The code is already on `main`; there is no merge-back.
- The item was moved to `review` by hand in the session that built it (that
  session was editing `tcw/`); it is completed with `tcw work complete`, run
  against a clean, committed tree.
- No originating GitHub issue. The version cut that ships these four is the
  user's call; nothing is pushed or published by this closeout.
