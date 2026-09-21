# Keep items small: decompose into child items

**No single work item should be too large.** When planning reveals that one item
has several separable pieces, break it into **child items** under it. This is the
local decomposition path: one item, one repository, broken into smaller items
that each go through the lifecycle on their own.

```
tcw work new "<sub-item title>" --parent <parent-slug>
```

- Decompose at _planning_ time: list the children you intend to create in the
  parent's `plan.md`, then create them. It does not matter whether the parent has
  been started yet — a child always starts in `backlog`.
- Each child gets its own `initial-request.md`/`spec.md`/`plan.md` as it's
  planned, and is started, submitted and completed on its own. The parent stays a
  thin umbrella.
- The parent cannot be completed or discarded while any child beneath it is
  still open, so finish or discard the children first. It cannot be dropped
  while any child names it at all, even a finished one.

Reach for this **before** an item grows unwieldy. A parent with three focused
children beats one item whose `plan.md` has fifteen tasks.
