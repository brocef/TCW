# Resolve project-graph paths regardless of letter case and through a symlinked config

From the review of `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies`, each
reproduced in a scratch layout and predating it:

1. An absolute locator spelled with different letter case on a case-insensitive
   disk (macOS) loads a node twice — even outside any worktree.
2. Running `tcw` from a directory whose own `tcw-config.yaml` is a symlink fails
   ("no tcw-config.yaml here") even in the primary checkout.
3. Question, not reproduced: should a `TCW_PROJECT_<ID>` override (rule 0) that
   names the main checkout's copy of a sibling be redirected to the worktree copy
   like a locator is? Today an explicit statement wins.
4. From verify of `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies`:
   running from a submodule node inside a linked worktree (`app-wt/lib`) still
   reports duplicates — `worktree_anchors` returns `None` for the submodule's own
   directory — so validate from the worktree root also fails in that layout.
5. The same: when the repository is itself a submodule of an outer repository,
   `worktree_anchors` returns `None` (its git directory is `.git/modules/app`),
   so #39's fix does not apply at all.
