# Spec — Hierarchical tree view for the web UI object list

## Capability changes

- **Changed:** `web` — "Browse TCW content in a local web app". The left-column
  object picker changes from a flat list to a **collapsible hierarchy tree**
  across all three axes. Recorded as a work→capability back-pointer in
  `capabilities.yaml`. No new capability; `web` stays `Supported`. At completion,
  the capability body gains a sentence about hierarchical navigation.
- No taxonomy Vocabulary/Feature change is needed — the existing `local-web-app`
  Feature and the axis terms already cover the concepts. (Aside: `web` currently
  lacks a `Feature` link that `web/editing` has; fixing that is out of scope.)

## Problem

The left column lists Taxonomy, Capabilities, and Work as a flat sequence of
rows. But taxonomy terms and capabilities are genuinely hierarchical (their
identity is a `/`-delimited path — `store/adapter`, `work/complete-a-work-item`),
and work items have parent/child relations. The flat list hides that structure:
sibling and parent/child relationships are invisible, and long paths repeat
their prefixes on every row.

## Goals

- Render each axis's left column as a **collapsible tree** reflecting its
  hierarchy.
- **Content is selectable; empty folders are not.** A node backed by a real item
  selects it (unchanged selection/deep-link behavior). An intermediate path
  segment with no item of its own is a non-selectable folder that only
  expands/collapses.
- A node may be **both** selectable and a parent (e.g. `web`).
- Preserve all existing behavior: detail view, editor, create button,
  copy-slug (work), status-filter toggles, deep-link routing, browser history.

## Non-goals

- No backend / store / API / route changes.
- No change to what "hierarchy" means per axis — only its display.
- No localStorage persistence of expand state in v1 (session-memory only, like
  the existing markdown-editor split which also does not persist per session).

## Current-state findings

- **Left column rendering** is entirely in `tcw/serve/static/app.js`:
  `renderList()` (`app.js:1408`) builds rows via `itemRowHtml()` (`:1379`); work
  uses `groupedWorkHtml()` (`:1393`) to group by status. `currentItems()`
  (`:1318`) applies the status filter (work) and the text filter.
- **Selection identity** is `itemKey(item)` (`:1358`): work → `slug`;
  taxonomy → `qualified || slug`; capabilities → `qualified || path`. Selecting
  sets `state.selected = key` and calls `pushRoute()`; routing
  (`pathFor`/`applyRoute`, `:2800`+) keys entirely off `itemKey`. **A tree only
  changes row layout — the selection key is unchanged, so routing/deep-links keep
  working with no change.**
- **Hierarchy is already in the data the client holds:**
  - taxonomy `list_all` → `Term.slug` is the root-relative path (`base.py:99`);
  - capabilities `list_all` → `Capability.path` (`base.py:260`);
  - work board → `WorkItem.parent` is the parent slug, `""` = top-level
    (`base.py:436`).
  Grounding (`tcw capabilities list`): `capabilities/`, `cli/`, `plugin/`,
  `taxonomy/`, `work/` appear only as prefixes (content-less folders), while
  `web` is a real capability that also parents `web/editing`. This is exactly the
  "selectable node with children" + "non-selectable folder" split.
- **Federation:** inherited items carry `qualified = <alias>/<path>`. Splitting
  `qualified` on `/` naturally nests them under an `<alias>` root folder, which
  no item matches → a non-selectable origin folder. Desirable and free.
- **CSS** touch points: `.item`, `.item.active`, `.item-title`, `.item-meta`,
  `.item-row`, `.copy-slug`, `.status-group` (`style.css:181`+).

## Proposed behavior

### Tree derivation (shared)

Build a nested node model from the flat item list for the current axis:

- **Path axes (taxonomy, capabilities):** split each item's `itemKey` on `/`
  into segments; insert into a trie. Each trie node has a full path; it is
  **selectable** iff that exact path is a real item in the list, otherwise it is
  a **folder**. A node can be selectable *and* have children. Federated/inherited
  items nest under their `<alias>` origin folder for free (their `itemKey` is
  `qualified = <alias>/<path>`, and no item matches the bare `<alias>` prefix →
  non-selectable origin folder). **Path-splitting nesting is a path-axis behavior
  only** — the Work axis never splits its key (see below); this removes the
  apparent contradiction a reviewer flagged.
- **Work (parent relation):** every work item is a real (selectable) node — the
  work tree has **no empty folders**. Build a parent index keyed by
  `itemKey(item)` (the work `slug`); each item's children are the items whose
  `parent` resolves to that key. Roots are items whose `parent` is `""` **or
  whose resolved parent is not in the current set** (a missing/out-of-set parent
  → promote the child to root; never synthesize a folder). Ordering within a
  level keeps the board's existing order (priority/topological, applied
  server-side).
  - **Qualified descendant slugs (correctness — caught in review):** under
    `serve --include-descendants`, `_board()` (`tcw/serve/__init__.py:373-379`)
    prefixes each descendant item's `slug` to `sub/proj/<slug>` **but leaves
    `parent` bare**. So a descendant child has `itemKey = "sub/proj/C"` while its
    `parent = "P"`, and its parent's `itemKey = "sub/proj/P"`. Resolve `parent`
    **within the child's own namespace prefix**: if `itemKey` is
    `<prefix>/<slug>`, look the parent up as `<prefix>/<parent>`, not bare
    `parent`. A bare-key item (anchor node) resolves `parent` bare. Without this,
    every cross-node child mis-nests to the root. The `sub/proj/<slug>` key is a
    work **identity**, never split on `/` like a path.

### Rendering

- A folder row shows a disclosure triangle (▸ collapsed / ▾ expanded) and the
  segment name; clicking it toggles expansion. It is not selectable and carries
  no route.
- A selectable row reuses the existing `.item` button (title + `itemMeta`) so
  detail/edit/routing are untouched; when it also has children it additionally
  gets a disclosure triangle.
- Depth is shown by indentation (padding-left ∝ depth). Since the tree already
  conveys hierarchy, the row title shows the **leaf segment name** (already
  `itemTitle`) and the redundant full path may be dropped from `itemMeta` in tree
  view (keeps the "prefixes repeat on every row" motivation actually solved). The
  status/kind/origin parts of the meta line stay.
- Work rows keep the copy-slug button.
- **Accessibility:** disclosure toggles are real `<button>`s with
  `aria-expanded`, so folders are keyboard-focusable and operable (Enter/Space)
  like the existing item buttons. Full ARIA `tree`/`treeitem` roles with
  roving-tabindex arrow navigation are **deferred** (out of scope for v1) — the
  basics (focusable, operable, labeled) are covered.

### Expand/collapse state

- Kept in `state` as a per-axis set of expanded folder/parent paths (session
  memory; no localStorage in v1).
- **Default: everything expanded on first load**, so initial visibility matches
  today's flat list (no content hidden by default); collapsing is opt-in.
- Selecting an item or landing on a deep link **auto-expands the ancestors** of
  the selected node so it is visible.

### Work: status grouping and filtering (user-decided)

- **Drop the status *group headers*** (`status-group`); the parent/child tree is
  the single structure. **Keep the status-filter toggle bar and the per-row
  status badge** — status is still visible and filterable, just not the grouping
  axis. (User confirmed this over a status-first grouping.)
- **Build the work tree from the unfiltered board** (`state.data.work`), not from
  `currentItems()`. `currentItems()` (`app.js:1322`) *hard-removes* status-toggled
  items, which would delete a filtered-out parent needed to reach a visible child.
  The status filter is instead applied as a **tree prune**: keep a node if it
  matches the active statuses **or** has a visible descendant.
- **A status-filtered-out ancestor kept only to reach a visible child renders
  dimmed** ("ancestor-only" style — like a folder label, still selectable), so
  it reads as context rather than as a match. (User-decided.)

### Text filter/search (user-decided)

- **Keep the tree while filtering:** prune to nodes matching the query plus their
  ancestors, and auto-expand those ancestors so matches are visible. Clearing the
  filter keeps the current expand/collapse state (the filter is a transient
  overlay, not a state reset).
- Note: the existing text filter matches `JSON.stringify(item)` — content-less
  folders have no item, so a query that matches *only* a folder-segment name
  surfaces nothing unless a descendant item also matches. Accepted behavior.

## Acceptance criteria

1. Capabilities column shows `capabilities/`, `cli/`, `plugin/`, `taxonomy/`,
   `work/` as non-selectable folders; their leaves are selectable; `web` is
   selectable **and** expands to reveal `web/editing`.
2. Taxonomy column nests `store/adapter` under `store`, and
   `work-item/{definition-of-done,transition}` under `work-item`.
3. Work column nests child items under their parent; a top-level item with no
   parent sits at the root; the copy-slug button still works.
4. Clicking a folder toggles expand/collapse; clicking a content node selects it
   and updates the detail pane and URL exactly as before.
5. Deep-linking to a nested item (`/capabilities/web/editing`) selects it and its
   ancestor folders are expanded so it is visible.
6. Status toggles still filter the work tree; a parent hidden by the filter but
   with a matching child stays visible **dimmed**; the text filter prunes the
   tree to matches + ancestors; create button and editor flows are unregressed.
7. Federated/inherited items (if any) appear under a non-selectable origin folder.
8. Under `serve --include-descendants`, a descendant child item
   (`sub/proj/<slug>`) nests under its descendant parent, not at the root.

## Risks / dependencies

- **Work status UX shift:** removing status group headers is a visible change to
  the work board. Mitigated by keeping toggles + badges; flagged for review.
- **Filter-prune correctness:** the "match or has-visible-descendant" rule is the
  one piece of non-trivial logic. Extract the tree build + prune as **pure
  functions** so they carry focused checks without a browser. Cases to cover:
  match-or-visible-descendant reachability; the qualified `sub/proj/<slug>`
  parent-in-namespace resolution (identity treated atomically, never split);
  deep-link ancestor auto-expansion; a work item whose parent is absent from the
  set (promote to root, no synthetic folder).
- No store/interface risk — abstraction litmus test passes trivially (no new
  store operation; the client derives structure from data it already receives).

## Related work items

- `2026-07-01-local-read-only-web-viewer-tcw-serve` (introduced the viewer)
- `2026-07-02-interactive-local-web-editor-for-tcw-objects` (`web/editing`)
- `2026-07-04-subproject-qualified-slugs-for-descendant-work-items` (qualified
  work slugs; the tree must treat a `sub/proj/<slug>` work key correctly — it is
  a work identity, not a path to split; work nests by `parent`, not by `/`).
