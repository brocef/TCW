# Keep items small: decompose into child items

**This page holds only the part of this procedure a project cannot replace.**
For the rest, run `tcw work procedure prompt decompose` and follow what it
prints: this project's text if it configured one, TCW's own otherwise. The rules
on this page hold whatever it prints. If the command fails, say so rather than
working from memory.

What nesting a child with `--parent` does:

- The child's folder is created **inside** the parent's folder; `tcw work list`
  shows children indented under their parent.
- A child inherits the parent's status by living inside it. `tcw work start`/
  `complete` on the **parent** carries its children along; transitioning a
  **child** on its own promotes it to a top-level item (it de-nests).

**Which path?** Choose by scheduling behavior:

- Pieces worked together and transitioned as a unit → `--parent` children (this
  doc). This relation is local because its filesystem adapter realizes nesting,
  but locality alone is not a reason to choose it.
- Epic tasks worked independently over time → `--initiative`, even when every
  task is in the same repo. `reconcile` follows these initiative children; see
  [`epic-deltas.md`](../epic-deltas.md).
- Independently scheduled tasks in multiple sub-project repos → the same
  `--initiative` relation plus `delegate`/`reconcile`; see
  [`cross-node-deltas.md`](../cross-node-deltas.md).
