# Descend through a storeless routing node in delegate and reconcile

A node that keeps no board of its own — a repository root grouping packages that
do — is documented as a routing node that coordination passes through
(`skills/work/references/cross-node-deltas.md`). `escalate` passes through one
going up. `delegate` and `reconcile` do not going down: both walk only direct
children with a board, so the packages behind a routing node are unreachable,
and an epic spanning them has nowhere to live (GitHub #30).

Make the code match the documentation.

## Notes

- From GitHub #30 (filed 2026-09-09; Jira TCW-7). Written during an unattended
  run (2026-09-27); no requester to ask. References: asked; none beyond the
  issue.
- The completion gate already counts slices below a routing node
  (`initiative_children` walks every descendant), so today `reconcile`'s table
  and the gate disagree about the same epic.
- Blocks `2026-09-09-resolve-a-cross-node-external-blocker-against-the-node-that-owns-it`.
- GitHub #30 stays open until the change ships.
