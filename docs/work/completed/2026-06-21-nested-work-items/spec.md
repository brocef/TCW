# Spec — Nested work items

## Goal

Let a work item hold **child work items**, so a large item can be decomposed
into smaller ones that travel with it. Two surfaces:

1. `tcw work new "<title>" --parent <slug>` — create a child nested inside the
   parent item's folder.
2. `tcw work list` — render children indented under their parents.

Plus a skill change: teach agents to break a large item into children.

## Model (abstract — passes the litmus test)

A parent/child link is a **node relation**: any store (Jira sub-tasks, a graph
DB) can express "item X is a child of item Y". So it lives in the model:

- `WorkItem.parent: str` — the parent's slug (`""` = top-level).
- `WorkStore.create(..., parent: str | None = None)` — create under a parent.

The FS adapter *derives* the relation from directory nesting (AGENTS.md:
"Parent/child as literal directory ancestry … express the relation abstractly").

## FS realization

- **Discovery is `state.yaml`-keyed and depth-agnostic.** An item folder is any
  dir containing `state.yaml`. `_find` and `query` walk the tree (`rglob
  state.yaml`) instead of assuming `root/{status}/{slug}` one level deep.
- **Status = the first path component** under `docs/work/` (`backlog/p/c` →
  `backlog`). No longer `dir.parent.name` (which for a child is the parent slug).
- **Parent = the nearest `state.yaml`-bearing ancestor's name** (`""` if the
  nearest ancestor is a status folder).
- **`create(parent=…)`** places the child folder *inside* the parent's current
  folder; the child inherits the parent's status by location.
- **Transitions** still `git mv` the item's own folder to `{to_status}/{slug}`:
  - a **parent** carries its nested children along (they ride inside the dir);
  - a **child** that moves to a status different from its parent **de-nests** to
    top level. This is *forced* by the model (status is the top-level folder; a
    child can't sit under a parent that lives in a different status folder), not
    a separate design choice. The derived parent link ends when nesting ends —
    acceptable adapter-local behavior (a remote store would keep a stored link).

## CLI

- `new`: `--parent <slug>`; errors if the parent doesn't resolve.
- `list`: depth-first render, children indented two spaces per level, board
  order within each sibling group. A child whose parent is filtered out of the
  view renders at the top level.
- `show`: print a `parent:` line when set.

## Out of scope

- Reparenting / moving a child between parents.
- Guarding child creation under a `completed` parent (allowed; rare; the child
  just materializes in `completed/`).
- Roll-up of child status into the parent (cross-node `reconcile` already
  covers the epic case; intra-node rollup is not requested).

## Definition of done

- Create-nested, list-nesting, depth-agnostic find/query/get, parent carries
  children on transition, child de-nests on independent transition — all tested.
- `docs/capabilities/work` gains the decomposition capability (Supported on
  completion).
- README, changelog, release-notes, and `skills/tcw-work/SKILL.md` updated; the
  skill gains decomposition guidance.
