# `tcw://` link resolution never applies on a work item's document tab

## Origin

Found at the `implement` stage of
`2026-08-19-render-an-unhosted-tcw-reference-as-a-visibly-distinct-non-link-naming-its-project`,
while doing that item's manual visual check. **It predates that change** — the
same failure reproduces on the pre-change bundle (`index-BZcG-A9f.js`, verified
by checking out `5ecdb9a` and reloading), so it is not a regression from it.

## Problem

In `tcw serve`, a work item's **Initial Request** tab renders every `tcw://`
reference as a plain, unstyled Markdown link. No anchor receives `data-nav-key`,
`tcw-inert`, or a `title` — so a resolvable reference is not clickable in-app,
and an unresolvable one is not marked at all.

The same document content rendered from a **capability** page resolves correctly:
`data-nav-key` is set on live references, `tcw-inert` plus the failure reason on
dead ones. Both call sites use the same component with the same prop
(`web/client/src/ui/shared-components.tsx` `Markdown`, `resolveLinks`), so the
component is not the difference.

That makes the README's claim — a `tcw://` reference "renders as a **clickable
in-app link**" — false for the surface where work items are actually read.

## What was measured

On a fresh load of a work item whose body holds six `tcw://` links
(`performance.getEntriesByType("resource")`):

```
work@35  capabilities@35  taxonomy@35  work/tags@35
work/<slug>@69
resolve@95
```

- `/api/resolve` is requested **exactly once**, at ~95ms, and returns `200` with
  a correct body (verified by replaying the same payload by hand from the page).
- After it settles, all six anchors still have `className === ""`, no
  `data-nav-key`, and no `title`.
- A `MutationObserver` over `document.body` (`attributes` on `class` / `title` /
  `href` / `aria-describedby`) records **zero** anchor attribute mutations,
  while recording the article's children being replaced (8 removed, 8 added)
  when switching between items.

One fetch plus zero mutations means the effect's `.then` wrote to anchors that
were no longer in the document by the time it ran — the article's content was
replaced after the request started, and the effect did not re-run because its
deps (`[html, resolveLinks]`) were unchanged.

## Where to look

`web/client/src/ui/work-document-tabs.tsx` is the difference from the working
capability path. Its

```ts
useEffect(() => {
    setSelectedDocument("initial-request")
    setArtifactStates({})
}, [item.slug])
```

runs _after_ the child `Markdown` effect (children commit first) and sets a
fresh `{}` object every time, forcing a parent re-render immediately after the
resolve request is issued. That is the first thing to rule in or out; the root
cause was not confirmed, and the fix should not be guessed at.

## Why it matters beyond cosmetics

The `web` capability asserts that "unknown, unregistered, or dangling foreign
targets remain inert", and `README.md` asserts in-app navigation. Neither holds
on the work-item tab today. A fix belongs with a test that would have caught it —
the existing `Markdown` unit tests pass because they render the component
directly, so no test exercises it through `WorkDocumentTabs`.
