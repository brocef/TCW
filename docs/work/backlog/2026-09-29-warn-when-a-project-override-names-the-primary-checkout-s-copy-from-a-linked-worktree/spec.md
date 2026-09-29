# Spec — Warn when a project override names the primary checkout's copy from a linked worktree

## Capability changes

None. This adds a warning to an existing report.

## Reproduction

1. A repository `app` holds nodes `app-repo`, `pkg-a` and `pkg-b`, and has a
   linked worktree `app/.worktrees/feature`.
2. The environment sets `TCW_PROJECT_PKG_B=<app>/pkg-b`: the primary
   checkout's copy, set once for the machine.
3. Run `tcw validate` from `app/.worktrees/feature/pkg-a`.

What happens: `pkg-b` is read from the primary checkout (the override wins,
`_target_path`, tcw/store/project.py:551), and every other node is read from
the worktree (`_worktree_copy`, project.py:662). The graph mixes two branches.
`validate` prints only "connected project 'pkg-b' is overridden by
TCW_PROJECT_PKG_B to …" (tcw/cli.py:406) and passes.

## Problem

Item `2026-09-27-resolve-project-graph-paths-by-case-and-through-a-symlinked-config`
decided to keep an override exactly as stated, because it is documented as the
final word on where a project is. The case where that silently mixes branches
was left unflagged. The user uses both overrides and linked worktrees.

## Goals

1. When the registry is opened inside a linked worktree, it adds a warning to
   an override that:
   - names a folder under the main worktree, and not under this worktree;
   - whose counterpart in this worktree, in the same repository, holds a
     config with the **same project id**.

   The warning names both paths and says the project is read from another
   branch than the rest of the graph.
2. The override is still followed exactly as stated. The warning never
   counts as a problem and never fails a command.
3. `tcw validate` prints the warning under the existing "is overridden by"
   line.

## Non-goals

- **Redirecting the override.** The earlier item decided against it.
- **Warning outside a linked worktree**, or for an override whose
  counterpart holds a different project or none. There is nothing mixed then.
- **Other commands.** They already say nothing about overrides, and
  `validate` is where overrides are reported.

## Design

- `ProjectOverride` (tcw/store/base.py:153) gains `warning: str | None = None`.
  It is storage-neutral: an override can take effect and still not be what
  the user meant.
- `FsProjectRegistry._reconcile_overrides` (project.py:812) already runs
  after the graph walk. For an override with no `problem`, it takes
  `self._worktree_copy(where)`.
  - When that differs from `where`, and the copy's config holds the same
    `id`, it fills in `warning`.
  - `_worktree_copy` already applies every condition in Goal 1: under main,
    not under this worktree, the counterpart exists, and the same repository.
- `tcw validate` (tcw/cli.py:406) prints `  warning: <text>` after the
  override line.

## Abstraction litmus test

"This statement from the environment took effect but disagrees with the rest
of the graph" is a question any registry could answer. The field lives on
the storage-neutral record. How the disagreement is detected (git worktrees)
stays in the filesystem adapter.

## Acceptance criteria

1. **The reproduction.** `validate` exits 0 and prints a warning naming
   `TCW_PROJECT_PKG_B`, the primary checkout's path, and the worktree's copy.
2. **No warning outside a linked worktree.** The same override, with
   `validate` run from the primary checkout, prints no warning.
3. **No warning when the override points into the worktree.** An override
   naming the worktree's own copy prints no warning.
4. **The full suite passes.**

## Risks

- **Reading the copy's id costs one YAML read** per override, and only
  inside a linked worktree.
