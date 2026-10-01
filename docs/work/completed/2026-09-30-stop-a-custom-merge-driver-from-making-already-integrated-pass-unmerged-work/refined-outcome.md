# Refined outcome

**Accepted by the user on 2026-10-01**, together with its three sibling items.

## The acceptance criteria

All five met (`tests/test_already_integrated_check.py`): a driver named in
`.gitattributes` or only in `.git/info/attributes` cannot make an unmerged
branch pass, and `complete` exits 1 keeping the branch; a squash merge with no
custom drivers still passes; a merge commit passes where a driver exists; the
refusal names the repository's merge drivers.

## Folded in at verify

The release-note order for worktree items and an end-to-end test of the
command (`d61a543f`), recorded in `outcome.md`.

## Deferred, with reasons

- In a repository that uses only git's built-in `union` driver, a refused
  squash gets no explanation of why: the reason text appears only when the
  repository defines drivers of its own. Not required by the criteria.

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
