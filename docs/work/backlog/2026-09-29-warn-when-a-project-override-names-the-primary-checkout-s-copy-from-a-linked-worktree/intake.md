# Warn when a project override names the primary checkout's copy from a linked worktree

From `2026-09-27-resolve-project-graph-paths-by-case-and-through-a-symlinked-config`
(2026-09-29), which kept a `TCW_PROJECT_<ID>` override exactly as stated rather
than redirecting it to a linked worktree's copy.

The two advisors split on that. One point that stands whichever way it is
settled: an override set once for an environment and naming the primary
checkout's copy of a sibling node, used from a linked worktree, loads the
primary checkout's copy for that node and the worktree's copies for the rest —
a graph mixing two branches, with no error (the override applies to every
reference to that id, so nothing is loaded twice).

Wanted: `tcw validate` (and the registry's notes) say so when, inside a linked
worktree, an override names a path under the main worktree whose counterpart in
this worktree holds the same node — or decide to redirect after all.
