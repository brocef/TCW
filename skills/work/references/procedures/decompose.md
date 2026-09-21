# Keep items small: decompose into child items

**This page holds only the part of this procedure a project cannot replace.**
For the rest, run `tcw work procedure prompt decompose` and follow what it
prints: this project's text if it configured one, TCW's own otherwise. The rules
on this page hold whatever it prints. If the command fails, say so rather than
working from memory.

What creating a child with `--parent` does:

- The child records its parent (a `parent:` field in its `state.yaml`) and has a
  status of its own. It starts in `backlog` whatever the parent's status, so its
  `request`, `spec` and `plan` stages are available even under an active parent.
- Starting or completing the parent does not move the child, and the child keeps
  its parent through every one of its own transitions. `tcw work list` shows it
  indented under the parent.
- `tcw work complete` refuses to close the parent — even with `--force` — while
  anything beneath it is open, naming each open item; `tcw work drop` refuses
  while any child names it. A child cannot be created under a completed or
  discarded item.
- Children made before TCW gave children their own status sit inside the
  parent's folder and still move with it. Leave them be; one that is moved on its
  own is given its own status from then on.

**Which path?** `--parent` and `--initiative` both group items; they differ in
reach and in what they enforce:

- `--parent` → a child in the **same** work store, under any item. No epic is
  needed and nothing gates the child's `start`; the relation's rule is that the
  parent cannot close over an open child.
- `--initiative` → a slice pointing at a `type: epic` item, which may live in
  **another** node. A slice cannot start until its epic is active, and
  `reconcile` rolls the slices up into the epic; see
  [`epic-deltas.md`](../epic-deltas.md). Across sub-project repositories, add
  `delegate`; see [`cross-node-deltas.md`](../cross-node-deltas.md).
