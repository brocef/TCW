---
verdict: accepted
judges: 2
---

# Review round 2 — TCW-115

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-24 in a frozen worktree at `b08252bf`, the head of the item's branch,
against review round 1's items (a) to (c), over `7d7c0c9b..b08252bf`. Round
1's acceptance-criterion results carry forward.

## Checks run

- The full suite as CI runs it, run by the dispatching session on the branch
  at `318c68cd` in two halves by folder: `2078 passed, 2 skipped` and
  `4979 passed, 111 skipped`, recorded in `implement/round-2.md`. `pnpm test`
  `198 passed`; `tsc --noEmit`, `pnpm lint`, `pnpm check:build` clean.
- By the reviewer: `tests/test_project_provision.py`,
  `tests/test_fetch_project.py`, `tests/test_project_registry.py`,
  `tests/test_static_guards.py`, `tests/test_object_folder_sweep.py`,
  `214 passed`. Each of the four mutations, applied in a scratch copy, turns
  exactly its test red: `fetched_here[-1]` put back, the first holder taken
  instead of the deepest, the clone folder matched instead of the project's
  own, and `except OSError` narrowed.
- By hand, through a guarded wrapper with every `TCW_*` variable unset and
  scratch home folders, cloning only local scratch repositories: with parents
  `aa` and `bb` and an unknown key in `aa`'s committed manifest, the refusal
  names `aa` and its folder and never `bb`, also through a symbolic link to
  the project; a later run with the bad `aa` kept gives the general message;
  a target folder with no permissions is refused as "cannot be listed", with
  no traceback, the folder unchanged and no staging folder left.

## Round 1's items

- (a) Met. `require_valid` raises `GraphProblems`, a `ValueError` carrying
  the file each problem is about, with the same message, so every caller that
  catches `ValueError` is unchanged. Both sides of the comparison resolve
  paths the same way. A problem in the active or a kept project gets the
  general text.
- (b) Met (`tcw/provision.py:228-232`, `243-246`).
- (c) Met. Every hash in round 1's commit table is on the branch with the
  matching subject; round 2 describes its commits accurately.

No finding belongs to this change.

## Needs a separate change

Kept on the 4.0 run's list of small follow-ups, decided by the dispatching
session:

- `tcw/provision.py:212-213`: when two fetched projects each have a problem,
  the advice names only the first one's folder, so a person who removes it
  and runs again is refused for the second. Round 2 records this as a choice.
- Seen during setup and not checked: a fetched parent's manifest with an
  unknown top-level key and no `parents:` key was accepted; it may never be
  read. Older than this item.

Round 1's carried concern, the TCW-113 reader opening a descendant's work
store with no locator, is checked once both items are in `v4`.
