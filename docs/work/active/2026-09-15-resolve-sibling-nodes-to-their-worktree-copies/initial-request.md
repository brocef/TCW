# Resolve sibling nodes to their worktree copies

In a linked worktree of a repository that holds several TCW nodes, running `tcw`
from any node but the worktree's root reports every other node in that
repository as a duplicate project id, plus reciprocity failures, and refuses
(GitHub #39). The project graph should resolve against the worktree's copy of
each node, as it does in the primary checkout.

## Notes

- From GitHub #39 (filed 2026-09-15; Jira TCW-12). Reproduced on main
  2026-09-26 with the issue's layout: `tcw validate` from `app-wt/pkg-a` lists
  the issue's four problems.
- Written during an unattended run; no requester to ask. References: asked;
  none beyond the issue.
