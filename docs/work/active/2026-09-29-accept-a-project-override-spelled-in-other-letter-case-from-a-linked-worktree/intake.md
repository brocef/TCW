# Accept a project override spelled in other letter case from a linked worktree

From the review of
`2026-09-29-warn-when-a-project-override-names-the-primary-checkout-s-copy-from-a-linked-worktree`
(2026-09-29). This problem predates that change.

On a disk that ignores letter case (macOS, Windows), set a `TCW_PROJECT_<ID>`
override that spells the primary checkout's folder in different letter case
(for example `.../APP/pkg-b` for `.../app/pkg-b`), then run from a linked
worktree. `tcw validate` then fails with duplicate `app-repo`/`pkg-a` and
reciprocity errors.

The cause: `.resolve()` keeps the spelling it was given, and `_worktree_copy`
and `_locator_path` (tcw/store/project.py) compare path text against git's
spelling of the worktree roots. So the `..` locators of the overridden node
land on `APP/` and are never mapped back into the worktree.

The failure is loud, so the graph does not silently mix branches.

Wanted: compare folder identity rather than path text there, as `_canonical`
does for the graph's own keys.
