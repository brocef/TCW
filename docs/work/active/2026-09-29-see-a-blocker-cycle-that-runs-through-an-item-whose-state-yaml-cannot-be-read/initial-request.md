# See a blocker cycle that runs through an item whose state.yaml cannot be read

## What is being asked for

When a blocker edit is checked for a cycle, and the check has to pass through an
item whose `state.yaml` cannot be read, the edit should say so rather than be
accepted silently.

Today the board reads a damaged `state.yaml` as empty (`FsWorkStore._safe_yaml`),
so the damaged item appears to have no blockers. The cycle check therefore
cannot follow edges through it, and a cycle that runs through it is accepted
without a word. Nothing resolves wrongly — `start` refuses the damaged item
itself — but the cycle only becomes visible once the file is fixed, by which
time the edit that made it is long past.

## Constraints

- Found in the combined review of branch `bug-run` (2026-09-29); left out of
  `2026-09-29-keep-a-child-whose-state-yaml-cannot-be-read-visible-to-its-parent-s-completion-gate`.
- Runs directly after
  `2026-09-29-detect-a-blocker-cycle-that-runs-across-nodes`, which made the
  cycle walk cross nodes and, deliberately, left any item it cannot read as
  "not followed", silently — this item is where that silence is addressed.

## Notes

- Written without the requester during an autonomous run (the user asked for
  all four open bug items back to back); this restates the intake, which asks
  for the edit to "say so" without choosing between refusing and warning.
  That choice is the spec's.
- References: asked; none provided beyond those below.

## References

- `tcw/store/base.py` `_reaches`, `_check_new_blocker` — the walk.
- `tcw/store/fs.py` `_state_damage`, `_require_readable_state` — how a damaged
  `state.yaml` is already detected and refused for moves.
- `tcw/store/base.py` `require_readable_slices`, `_unreadable_refusal` — the
  precedent: completing an epic is refused while an item that might be its
  slice cannot be read.
