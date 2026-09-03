# Spec — The epic owner walk stops at a parent that has no work store

## Capability changes

- **changed** — `work/escalate-a-request-to-the-parent-node`. Its body says the
  command refuses at the root of the graph with *"no parent node to escalate
  to (this is the root)"*. Today it says that at any work-less ancestor too,
  which is a different situation wearing the same words.
- **changed** — `work/inspect-the-node-topology`. It states that a node with no
  parent prints `parent: (none — root)`. A node whose parent has no work store
  prints the same thing and is not the root.

`work/coordinate-a-cross-node-epic` is deliberately **not** listed: the epic
relation it describes is what this item restores, not what it changes. If the
implementation finds its body asserts the broken behavior, add it then.

## Problem

`parent_node` returns a parent only when that parent has a usable work store
(`tcw/store/fs.py:231-238`):

    def parent_node(root: Path) -> Path | None:
        """Direct registered parent that contains a work store."""
        ...
        return path if _has_work_store(path) else None

Four call sites treat `None` as "there is nothing above here", and each fails a
different way:

1. **`FsWorkStore.initiative_epic` (`tcw/store/fs.py:4057-4063`).** The loop
   `parent = parent_node(parent)` walks up looking for the epic. A work-less
   ancestor ends it and the method returns `None` — the item reads as having no
   initiative epic. This is the failure the request names: a rollup that stops
   listing its slices, with no error anywhere.
2. **`_render_descendant_boards` (`tcw/work/cli.py:405-420`).** The same walk
   decides ownership for row indentation on `tcw work list -i`, so a slice is
   rendered as unowned rather than nested.
3. **`escalate` (`tcw/work/recursion.py:302-305`).** Refuses with "no parent node
   to escalate to (this is the root)" at a work-less parent. The node is not the
   root and there is a store above it.
4. **`_nodes` (`tcw/work/cli.py:164`).** Prints `parent: (none — root)` for a node
   whose parent is merely storeless.

A fifth site fails in the downward direction for the same reason.
`FsWorkStore.initiative_children` (`tcw/store/fs.py:4066-4070`) uses `child_nodes`,
which is *direct* children with a work store (`tcw/store/fs.py:221-228`), so an
epic in a grandparent cannot see slices below a storeless child. Note that
`descendant_nodes` (`:241-247`) does **not** have this defect — it filters
`registry.descendants()`, which walks the registry rather than hopping
store-to-store — so the two directions are already inconsistent with each other.

`_has_work_store` itself is correct and should not change: its docstring
(`tcw/store/fs.py:251-262`) explains that it answers `False` rather than raising
precisely so one unprovisioned child cannot fail a parent's listing. The defect
is that its answer is being used to mean "there is nothing above here".

## Goals

- The upward walks find the nearest ancestor that has a work store, passing
  through any number of storeless ones.
- `initiative_children` sees slices below a storeless intermediate node.
- `escalate` targets the nearest work-bearing ancestor, and refuses only when
  there genuinely is none.
- `tcw work nodes` distinguishes "no parent registered" from "the registered
  parent keeps no board".
- No relation resolves to a smaller answer without saying so.

## Non-goals

- Changing `_has_work_store`, or what counts as a usable store.
- Making a storeless node able to *hold* work. It is a routing node; boards stay
  where they are.
- The `proposit-app` root node itself.
- Cross-node addressing (`<project-id>/<slug>`), which resolves through the
  registry by id (`tcw/store/fs.py:381`) and never had this defect.

## Design

Keep `parent_node` as it is — a direct-parent question with a store filter, which
is what `_nodes` wants — and add a second, explicitly named helper for the walk:
the nearest ancestor with a work store, using the registry's `ancestors()` rather
than repeated single hops. Using `ancestors()` is the substantive part: it is one
graph traversal that cannot be terminated early by a filter, so the fix cannot
regress by a caller forgetting to loop.

`initiative_children` moves from `child_nodes` to the descendant walk that
already crosses storeless nodes, bounded the same way the registry bounds it.
This also removes the existing asymmetry between the two directions, which is
worth doing on its own.

`escalate` uses the new helper and refuses only when the walk finds nothing,
with a message that distinguishes the two cases. `_nodes` keeps using
`parent_node` for the direct answer and gains wording for a registered parent
that keeps no board.

**Litmus test.** "The nearest ancestor that can hold work" is a node-relation
query, expressible in the abstract vocabulary and answerable by any adapter: a
tracker asks the same question of its project hierarchy when a board is not
enabled on an intermediate project. Nothing here reads a directory or infers a
relation from nesting — the registry answers, as it already does for
`descendants()`.

**Harness.** CLI and adapter only; identical under both.

## Acceptance criteria

1. Given nodes A → B → C where B has no work store, an item in C whose
   `initiative` names an epic in A resolves that epic via `initiative_epic`.
2. In the same graph, `tcw work reconcile <epic>` run in A lists the slice in C.
3. In the same graph, `tcw work list -i` in A renders the C slice nested under
   its epic rather than as an unowned row.
4. In the same graph, `tcw work escalate` in C writes into A's inbox.
5. Where no ancestor has a work store, `escalate` still refuses, and its message
   says so without claiming the node is the root.
6. `tcw work nodes` in C names B as its parent and says B keeps no work store;
   in a node with no registered parent it still prints `parent: (none — root)`.
7. A graph with no storeless nodes behaves exactly as it does today, asserted by
   the existing tests passing unchanged.

## Risks

- **A longer reach is a wider blast radius.** A walk that used to stop early now
  reads stores further away, so a malformed store two levels up can surface in a
  command that previously never opened it. `_has_work_store` already swallows
  `ValueError` for exactly this reason, so the exposure is bounded to stores that
  open and then misbehave.
- **`escalate` changes where a request lands.** On a graph with a storeless
  parent it used to refuse; now it writes. That is the intended fix, but it is a
  behavior change to a command that writes into someone else's repository, and
  the capability wording must move with it rather than after it.
- **Only one shape is exercised.** No node in this repository or in `proposit-app`
  is storeless today, so every acceptance criterion above is a fixture. The first
  real use will be the `proposit-app` root node, and it is not in this item's
  scope — the plan should say plainly that this ships unproven against a real
  graph.

## Notes

Found while designing the consumer-side fix, not by a user hitting it — no
existing graph has a storeless intermediate node, which is why an epic rollup has
never quietly dropped a slice in practice. It would the first time someone built
one, and the symptom gives no hint of the cause.
