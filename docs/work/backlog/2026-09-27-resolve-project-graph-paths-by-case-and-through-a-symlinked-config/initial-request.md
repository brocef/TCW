# Resolve project-graph paths regardless of letter case and through a symlinked config

Four ways the project graph loads a node twice or reads it from the wrong place,
each predating `2026-09-15-resolve-sibling-nodes-to-their-worktree-copies`:

1. An absolute locator spelled with different letter case on a case-insensitive
   disk (macOS) loads a node twice: "duplicate project id", and reciprocity
   fails.
2. A node whose own `tcw-config.yaml` is a symlink reads its relative locators
   from the symlink target's folder, not its own.
3. Running from a submodule node inside a linked worktree (`app-wt/lib`) still
   reports duplicates: `worktree_anchors` answers `None` for the submodule's
   own directory.
4. When the repository is itself a submodule of an outer repository,
   `worktree_anchors` answers `None` (its git directory is
   `.git/modules/app`), so the worktree fix does not apply at all.

And one question: should a `TCW_PROJECT_<ID>` override naming the main
checkout's copy of a sibling be redirected to the worktree copy?

## Notes

- Unattended run (2026-09-29); from `intake.md`. Reference material: asked; none
  beyond the intake's.
- Reproduced 2026-09-29: (1) root spelled `Root`, child locator spelled
  `.../ROOT/kid` → "duplicate project id 'root'" and "parent locator … does not
  point back"; (2) the intake's "no tcw-config.yaml here" did not reproduce in
  a node with no children, but with a child `kid` declared as `kid`, validate
  reports "'kid' is declared but not reachable" at `<symlink target>/kid`.

## References

- `intake.md` in this folder.
