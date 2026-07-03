# Keep items small: decompose into child items

**No single work item should be too large.** When planning reveals an item is
big — it would touch many subsystems, span several sessions, or bundle loosely
related concerns — break it into **child items nested under it**, and whenever
the user asks you to split an item, do so the same way. This is the *intra-node*
decomposition path: one item, one repo, broken into smaller pieces that travel
with the parent.

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

Reach for this **before** an item grows unwieldy. A parent with three focused
children beats one item whose `plan.md` has fifteen tasks.

**Which path?** Same repo, one big item → `--parent` children (this doc).
Multiple sub-project repos → an `--epic` + `delegate`/`--initiative`/`reconcile`
(see [`cross-node-epic.md`](cross-node-epic.md)).
