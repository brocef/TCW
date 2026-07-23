# Cross-node epic slices cannot link their parent epic (tcw:// resolves downward only)

## Origin

GitHub issue [#7](https://github.com/brocef/TCW/issues/7), filed 2026-07-23.
Hit independently by two completed items in a downstream workspace
(`proposit-app` → `proposit-mobile`).

## Problem

A cross-node epic relation is machine-tracked but unlinkable in prose.

A child node adopts a slice with `tcw work new "<task>" --initiative <epic-slug>`.
Its `state.yaml` then carries a bare slug naming an item that lives in the
**parent** node, and `tcw validate` accepts that. But the `tcw://` locator form
only permits `<project-id>/` for a *registered descendant* (`W`) or explicit axis
inheritance (`T`/`C`) — resolution walks downward only. So the natural link in
the child's `initial-request.md`:

```
Epic: [Home argument sorting](tcw://W/proposit-app/2026-07-22-home-argument-sorting…)
```

fails `tcw validate` with `no such work item: proposit-app/<slug>` — even though
the epic exists, the ID is correct, and the connection is registered and
reciprocal.

Two failures compound: the relation cannot be expressed, and the error message
reads like a typo rather than a direction restriction, so the fix is not
discoverable.

## Product changes

Decide among the three routes the issue proposes (listed weakest-assumption
first); they are alternatives, not a sequence.

1. **Let `<project-id>/<slug>` resolve to any node in the registered graph**, or
   at minimum the reciprocal parent. Project IDs are canonical and connections
   are already required to be reciprocal, so there is no ambiguity to resolve.
   This is the option that actually makes the relation expressible.
2. **If upward links are deliberately out of scope, document that where the
   mistake is made** — `skills/tcw-work/references/cross-node-epic.md` walks
   through precisely this workflow and never says the epic it tells you to point
   at is unlinkable.
3. **Have `validate` name the cause, not the symptom** — "`proposit-app` is an
   ancestor, not a registered descendant; locators resolve downward only"
   instead of "no work item".

Route 3 is worth doing regardless of which of 1 or 2 is chosen.

## Technical changes

Scoped at spec time, once the route is picked. Touches locator resolution and
the `tcw validate` reference check; if route 1 is taken, the graph walk in
project resolution has to admit the upward edge without loosening the
"registered and reciprocal" requirement.

## Meta changes

- Litmus: resolving a reference through canonical project IDs in a registered
  graph is exactly the abstract "reference" vocabulary — no filesystem trick is
  implied by any of the three routes.
- Docs to sync: `README.md` (the `tcw://` locator section), the `tcw-work`
  skill's quick-reference row for locators, `references/cross-node-epic.md`,
  changelog + release notes.

## Open questions for spec

- Does "any node in the registered graph" invite ambiguity when two nodes share a
  slug, and is the project-ID prefix sufficient to prevent it?
- Should upward resolution be unrestricted, or limited to the reciprocal parent?
- Does the same restriction bite the `T` / `C` axes, or only `W`?
