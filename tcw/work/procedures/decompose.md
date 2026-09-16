# Keep items small: decompose into child items

**No single work item should be too large.** When planning reveals that one item
has several pieces which will be worked and transitioned together, break it into
**child items nested under it**. This is the coupled decomposition path: one
item, one repo, broken into smaller pieces that travel with the parent.

```
tcw work new "<sub-item title>" --parent <parent-slug>
```

- Decompose at _planning_ time (in the parent's `plan.md`, list the children you
  intend to spin off), then create them. Each child gets its own
  `initial-request.md`/`spec.md`/`plan.md` as it's planned — the parent stays a thin
  umbrella.

Reach for this **before** a coupled item grows unwieldy. A parent with three
focused nested pieces beats one item whose `plan.md` has fifteen tasks.
