# Accept a project override spelled in other letter case from a linked worktree

## What is being asked for

On a disk that ignores letter case (macOS and Windows by default), a
`TCW_PROJECT_<ID>` override that spells the primary checkout's folder in
different letter case — `.../APP/pkg-b` for `.../app/pkg-b` — should work from a
linked git worktree exactly as the same override spelled as git spells it.
Today `tcw validate` run from the worktree fails with duplicate project ids
(`app-repo`, `pkg-a`) and reciprocity errors.

The failure is loud, so the graph never silently mixes branches; the ask is
that a correct override not fail at all.

## Notes

- From the review of
  `2026-09-29-warn-when-a-project-override-names-the-primary-checkout-s-copy-from-a-linked-worktree`
  (2026-09-29); the problem predates that change.
- The intake's diagnosis: `.resolve()` keeps the spelling it was given, and
  `_worktree_copy` and `_locator_path` (`tcw/store/project.py`) compare path
  text against git's spelling of the worktree roots, so the overridden node's
  `..` locators land on `APP/` and are never mapped back into the worktree.
  The wanted fix: compare folder identity there, as `_canonical` already does
  for the graph's own keys.
- Written without the requester during an autonomous run (the user asked for
  all four open bug items back to back). References: asked; none provided
  beyond the intake's.
