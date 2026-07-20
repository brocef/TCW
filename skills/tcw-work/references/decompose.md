# Keep items small: decompose into child items

**No single work item should be too large.** When planning reveals that one item
has several pieces which will be worked and transitioned together, break it into
**child items nested under it**. This is the coupled decomposition path: one
item, one repo, broken into smaller pieces that travel with the parent.

```
tcw work new "<sub-item title>" --parent <parent-slug>
```

- The child's folder is created **inside** the parent's folder; `tcw work list`
  shows children indented under their parent.
- A child inherits the parent's status by living inside it. `tcw work start`/
  `complete` on the **parent** carries its children along; transitioning a
  **child** on its own promotes it to a top-level item (it de-nests).
- Decompose at *planning* time (in the parent's `plan.md`, list the children you
  intend to spin off), then create them. Each child gets its own
  `initial-request.md`/`spec.md`/`plan.md` as it's planned — the parent stays a thin
  umbrella.

Reach for this **before** a coupled item grows unwieldy. A parent with three
focused nested pieces beats one item whose `plan.md` has fifteen tasks.

**Which path?** Choose by scheduling behavior:

- Pieces worked together and transitioned as a unit → `--parent` children (this
  doc). This relation is local because its filesystem adapter realizes nesting,
  but locality alone is not a reason to choose it.
- Epic tasks worked independently over time → `--initiative`, even when every
  task is in the same repo. `reconcile` follows these initiative children; see
  [`epic-lifecycle.md`](epic-lifecycle.md).
- Independently scheduled tasks in multiple sub-project repos → the same
  `--initiative` relation plus `delegate`/`reconcile`; see
  [`cross-node-epic.md`](cross-node-epic.md).
