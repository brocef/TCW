# Spec: resolve sibling nodes to their worktree copies

## Capability changes

None to the ledger: a graph that already worked from the primary checkout now
also works from a linked worktree.

## Problem

`ProjectRegistry._locator_path` (`tcw/store/project.py`) resolves each locator.
Inside a linked worktree (`top`, whose main worktree is `main`), Rule 1
re-anchors a relative locator that escapes the worktree onto the main
checkout. Rule 2 then aliases exactly one path back onto the worktree: the main
checkout's spelling of the *current* node. Any other node of the same
repository reached through the main checkout — the repository's root, a sibling
package — loads a second time from the main checkout, so its id is a duplicate
and reciprocity fails.

## Goals

1. Rule 2 aliases any resolved config path under `main` (and not already under
   `top`) onto `top / <same relative path>` when a config exists there: that is
   the same node on the checked-out branch.
2. A path under `main` with no counterpart under `top` (a node the branch does
   not have) keeps its main-checkout path; ids that really repeat across
   different repositories are still reported.
3. The current node's aliasing keeps working (it is the special case of 1).

## Acceptance criteria

1. The issue's layout: `tcw validate` and `tcw work list` from
   `app-wt/pkg-a` report no graph problems; the graph holds `app-repo`,
   `pkg-a`, `pkg-b` at their `app-wt` paths and `workspace` at its own.
2. A worktree placed inside its own primary checkout (TCW's `.worktrees/<slug>`
   layout) behaves the same, and a path already inside the worktree is not
   re-aliased.
3. A node present only in the main checkout's tree still resolves there.
4. Two different repositories using one id are still a duplicate.
5. Existing registry tests pass; full suite passes.

## Notes

- The issue's own remediation, with the guard for a path already under `top`
  added because TCW's worktrees live inside the primary checkout.
- The closing of GitHub #39 waits for publication (repository rule).
