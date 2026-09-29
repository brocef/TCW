# Spec — Share one descendant walk, and say when delegate names a node with no board

## Capability changes

None.

## Reproduction

`tests/test_routing_nodes.py`'s `node` helper, root (board) → mid (no board) →
pa, pb (boards): `delegate(root, "mid", "x")` raises "no child node 'mid'.
children: pa, pb" (2026-09-29, on `bug-run`).

For the walk: `_tasks_for` builds its rows from `_node_stores` (`[node,
*descendant_nodes(node)]`) and filters `initiative == epic`;
`initiative_children` repeats both steps. Nothing is wrong today; the defect is
that the two can drift again, as they did before the routing-node fix.

## Problem

1. Two walks answer one question — "an epic's slices, here and below" — for two
   callers that must agree (the `reconcile` table and the completion gate).
2. `delegate`'s refusal for a registered node that keeps no board denies the
   node exists.

**Sibling sweep** (`grep -rn "descendant_nodes\|initiative ==" tcw`): the
other readers of `initiative ==` are `resolved_initiative_children` (tombstones,
a different source) and board rendering (one node). Only these two walk
descendants for slices.

## Goals

1. `FsWorkStore.initiative_slices(epic) -> list[tuple[Path, WorkItem]]` — (node
   root, item) for this node and every descendant with a board.
   `initiative_children` returns its items; `_tasks_for` labels its nodes.
2. `delegate` to a registered node with no board says so and names the nodes
   with a board below it (or, if none, those it can delegate to).
3. `delegate` to a registered node whose board is declared but not provisioned
   says the board is not available here, with the provisioning reason.

## Non-goals

- Changing which nodes either walk visits.
- `escalate`'s messages.

## Design

- `fs.py`: `initiative_slices` on `FsWorkStore`; `initiative_children` becomes
  `[item for _node, item in self.initiative_slices(epic)]`.
- `recursion.py`: `_tasks_for(node_root, epic)` maps each node of
  `FsWorkStore.open(node_root).initiative_slices(epic)` to its row label with
  the same labelling `_node_stores` uses (one `_label` helper); its unused
  `stores` parameter goes.
- `delegate`: after the "below a node with a board" check, when
  `registry.get(child_ref)` is registered, open its store:
  `StoreNotProvisioned` → "cannot delegate to '<ref>': its board is not
  available here (<reason>)"; any other `ValueError` → "'<ref>' keeps no board,
  so it has no inbox to delegate to. Nodes with a board below it: <…>" (falling
  back to the nodes this one can delegate to).

## Abstraction litmus test

`initiative_slices` is "items of this epic across this node's graph" — a store
that knows its node graph can answer it; it is FS-adapter code because the node
graph is. The `delegate` wording is CLI-side.

## Acceptance criteria

1. With slices in root, pa and pb (behind `mid`), `initiative_children(epic)`
   and `_tasks_for(root, epic)` return the same items, in the same order.
2. `delegate(root, "mid", …)` raises a message containing "keeps no board" and
   naming `pa` and `pb`, and not "no child node".
3. With `mid` declaring a work `repository` that is not provisioned,
   `delegate(root, "mid", …)` says its board "is not available here".
4. `delegate(root, "nope", …)` still says "no child node 'nope'".
5. The full test suite passes.

## Risks

- Opening a registered node's store to tell the two cases apart runs only on
  the refusal path.
