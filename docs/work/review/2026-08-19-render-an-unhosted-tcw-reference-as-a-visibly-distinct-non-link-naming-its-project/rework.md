# Rework: the presentation must actually reach the surface work is read on

**Verdict: rejected at `verify`.** Not because anything in the diff is wrong —
every acceptance criterion in `spec.md` is met, and the gates are green at the
review tip (`pytest` 1959, `pnpm test` 58, `tsc` 0, `eslint` 0, `check:build` 0,
`tcw capabilities check` OK). Rejected because the user decided the item should
**absorb** the defect that makes its result invisible where work items are
actually read, rather than ship around it.

## What changed about the scope

`docs/work/inbox/2026-08-24-tcw-link-resolution-never-applies-on-a-work-items-document-tab.md`
recorded, as a separate finding, that a work item's **Initial Request** tab
applies no link treatment at all — not the new off-board rendering, and not the
pre-existing `tcw-inert` one. It is pre-existing (reproduced against `5ecdb9a`'s
bundle) and it was filed rather than fixed, on the reasoning that it is a
different subject with an unconfirmed root cause.

The user overrode that: the item ships a reader-facing behavior, and a
reader-facing behavior that does not appear on the surface readers use has not
shipped. That inbox document is therefore **absorbed into this item** and deleted
in the same commit as this file; its measurements are reproduced below so nothing
is lost with it.

## What the implementation still has to do

**1. Find the root cause. Do not guess it.** The hypothesis in the inbox note
(`work-document-tabs.tsx`'s `useEffect(..., [item.slug])` setting a fresh `{}`
and forcing a re-render right after the child's resolve request goes out) is
where to start looking, not a diagnosis. Round 1 of the review found that the
first thing shipped here was a defect precisely because a plausible-sounding
mechanism went unchecked; the same discipline applies harder to a fix.

Reproduce it under test first, if that is possible at all — a `WorkDocumentTabs`
test that mounts the real component with a body containing a `tcw://` link and
asserts the anchor ends up marked. **A test that reproduces this is worth more
than the fix**, because the existing `Markdown` unit tests pass through the
defect: they render the component directly and never exercise it through the tab.

**2. Fix it where every caller routes through.** The failure is not specific to
the off-board rendering — the pre-existing `tcw-inert` and `data-nav-key` paths
are equally dead on that tab. Whatever the mechanism is, the fix belongs where
all three appearances route through it, not in a branch that only rescues the new
one.

**3. Re-run the visual check on the work-item tab.** Task 4 was satisfied on a
capability page, which is a real surface but not the one this rework is about.
The fixture already exists (three connected nodes, `platform` → `orchestrator` →
`webapp`); the webapp node's item body already holds all four situations.

**4. Update the record.** `spec.md` needs the scope expansion and the acceptance
criteria that come with it — the current criteria 8-11 are all satisfiable
without the tab ever working, which is how this got through. `plan.md` is
superseded for this slice; this file carries the tasks.

## The measurements, carried over

On a fresh load of a work item whose body holds six `tcw://` links, via
`performance.getEntriesByType("resource")`:

```
work@35  capabilities@35  taxonomy@35  work/tags@35
work/<slug>@69
resolve@95
```

- `/api/resolve` is requested **exactly once**, at ~95ms, `200`, with a correct
  body (verified by replaying the same payload by hand from the page).
- After it settles, all six anchors still have `className === ""`, no
  `data-nav-key`, no `title`.
- A `MutationObserver` on `document.body` watching `class` / `title` / `href` /
  `aria-describedby` records **zero** anchor attribute mutations, while recording
  the article's children being replaced (8 removed, 8 added) when switching
  items.
- The same content on a capability page resolves correctly, so the component and
  the endpoint are not the difference.

One request plus zero mutations means the effect's `.then` wrote to anchors that
had left the document — the article's content was replaced after the request went
out, and the effect did not re-run because `[html, resolveLinks]` was unchanged.

## Not reopened

Everything already accepted stays accepted. The `/api/resolve` contract, the
three appearances, the unclickability fix, the lazy hosted-projects snapshot, the
corrected spec claims, and the documentation are not in question here; this
rework adds a surface, it does not revisit the design.

A second adversarial review round over `5ecdb9a..HEAD` was running when this was
written, at the user's instruction that a fixed round is not a passed round. Its
findings land on top of this rework, not instead of it.
