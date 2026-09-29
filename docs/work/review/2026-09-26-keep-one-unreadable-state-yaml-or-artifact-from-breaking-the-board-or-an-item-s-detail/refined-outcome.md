# Refined outcome — Keep one unreadable state.yaml or artifact from breaking the board or an item's detail

## Decision

**Accepted**, 2026-09-29, during an unattended run: the decision is the
implementing agent's, taken in place of the user's at the user's request, on the
evidence below.

## Evidence

- `tcw:verifier` assessment: criteria 1–5 met; criterion 6 met as narrowed
  below. Full suite at its run: 4779 passed.
- Full suite on this branch with `bug-run` (which holds the claim-recovery fix)
  merged in and the combined fix added (971e2259), from the item worktree with
  its private virtual environment: **4789 passed, 3 skipped** (exit 0).
- Hands-on (mine), in a scratch node: with one item's `state.yaml` and
  `intake.md` not UTF-8, `tcw work list` exits 0 and lists both items;
  `tcw work show` of an item whose `intake.md` is damaged prints it with a
  replacement character; `tcw work start` of the damaged item is refused with
  "state.yaml cannot be read (it is not valid UTF-8)" and the folder stays in
  `backlog/`; the web detail endpoint answers 200 for both items.

## Accepted deviations from the spec

- Criterion 6 said a state file that vanishes mid-read still raises. `_safe_yaml`
  answers `{}` for a path that is already gone before the read (no regular file
  to read), and raises `FileNotFoundError` only when it disappears during the
  read. The test simulates the latter; the callers that tell a moved folder
  from a damaged one check existence first, so the narrower reading is what
  they need.
- `_present` now counts an artifact that is not UTF-8 as present, so a stage
  gate sees the file the author wrote rather than treating it as missing.
- Beyond the spec: `start`, the transitions and interrupted-claim recovery all
  refuse a damaged item before moving anything (`_require_readable_state`).
  The recovery check was found only by testing this change combined with the
  claim-recovery item already on `bug-run`.

## Closeout

- Capability reconciliation: none declared; nothing to reconcile.
- Documentation: changelog and release-note entry files.
- Not from a GitHub issue.
- Merge route: `tcw work complete` from the `bug-run` integration worktree,
  merging into `bug-run`; `main` is left for the user to merge.
- Follow-ups: `2026-09-29-keep-a-child-whose-state-yaml-cannot-be-read-visible-to-its-parent-s-completion-gate`.
