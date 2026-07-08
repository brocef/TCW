# Web viewer improvements — initial request

A batch of changes to the `tcw serve` local web app (`tcw/serve/`).

## Requested changes (verbatim intent)

1. **Resizable list/detail divider** — drag the divider between the left item-list
   column and the right content area to adjust the left column width.
2. **Fix 500 on inherited taxonomy item** — when serving a project that extends
   another project's taxonomy, selecting an inherited term returns a 500 from
   `GET /api/taxonomy/<ref>`.
3. **Reorder top-right nav** — buttons should read **Taxonomy · Capabilities ·
   Work** (matching the "TCW" order), not "Work · Taxonomy · Capabilities".
4. **Auto-include descendant nodes** — serving at a root that contains further TCW
   roots (orchestrator/subproject) should show the same items as
   `tcw work list --include-descendants`.
5. **URL reflects UI state** — viewing work item `work-slug-123` → path
   `/work/work-slug-123`; taxonomy list → `/taxonomy`; etc.
6. **Namespace descendant objects in the URL** — a descendant item shows its
   subproject path in the URL, e.g. `/subproject/work/subproject-work-slug-456`.
7. **URL pattern** — `{namespace}/[taxonomy|capabilities|work]/{identifier}`
   (discussion item; resolved below).
8. **Resizable markdown editor divider** — the split between the editable textarea
   and the rendered preview should drag like item (1).
9. **Copy-slug button** on each work-list entry — quick copy of the slug to the
   clipboard.
10. **Group the work list by status** — order top→bottom: active → backlog →
    inbox → completed.
11. **Reorder + relabel the summary counts** — under "TCW", show counts in order
    taxonomy · capabilities · work, and say "{N} work items" (not "{N} work").

## Design decisions (confirmed with user)

- **URL namespace:** the local (anchor) project carries **no** sigil —
  `/work/slug`, `/taxonomy`. Descendants use their subproject path as the prefix
  — `/sub/proj/work/slug`. The axis keyword (`work|taxonomy|capabilities`)
  separates the namespace from the identifier, so the leading component is not
  required to be a namespace. (One accepted edge case: a subproject path segment
  that equals an axis keyword would be ambiguous — see spec.)
- **Routing mechanism:** real paths via the History API. The server serves
  `index.html` for app routes; `app.js` reads `location.pathname` on load and
  calls `history.pushState` on navigation. Deep-linkable.
- **Descendants:** auto-included by default in `tcw serve` (the
  `--include-descendants` flag becomes redundant).

See `spec.md` for the resolved behavior and `plan.md` for the implementation.
