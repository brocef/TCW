# Hierarchical tree view for the web UI object list

## Requested outcome

The left-hand column of the `tcw serve` web app (where you pick a TCW object)
should present items as a **collapsible tree** that reflects the hierarchy of
each axis, replacing the current flat list.

- **Content is selectable; empty folders are not.** A tree node that
  corresponds to an actual item (a real capability / term / work item) is
  clickable and selects that item. An intermediate path segment with no item of
  its own (e.g. the `capabilities/`, `cli/`, `plugin/` prefixes that never
  appear as capabilities themselves) renders as a non-selectable folder label.
- A node can be **both** selectable and a parent — e.g. `web` is a real
  capability *and* the parent of `web/editing`.
- Folders **expand/collapse**, and the expanded/collapsed state is remembered
  across re-renders within a session.

## Scope

All three axes get the tree, per the user's decision:

- **Taxonomy** — hierarchy is the term `slug` path (`store` → `store/adapter`,
  `work-item` → `work-item/transition`). In practice every taxonomy node is a
  real term, so "empty folder" is rare here but the same rule applies.
- **Capabilities** — hierarchy is the capability `path`
  (`work/complete-a-work-item`); intermediate segments are frequently
  content-less folders.
- **Work** — hierarchy is the `parent` slug relation (parent/child items), not a
  path. This axis currently groups rows by status (active/backlog/completed) and
  has status-filter toggles; how status grouping/filtering coexists with parent
  nesting is the main open question for the spec.

## Key finding (feasibility)

The change is **frontend-only**. The server already sends everything needed:

- taxonomy `list_all` / capabilities `list_all` return each item's full
  `/`-delimited path (`slug` / `path`), so the tree — including which segments
  are content-less folders — is fully derivable client-side by splitting paths
  and checking membership in the flat item set.
- the work board returns each item's `parent` slug, so the work tree is
  derivable client-side by grouping on `parent`.

No new API routes or store methods are required. This keeps the change inside
the filesystem-agnostic client and passes the abstraction litmus test trivially
(nothing new touches the store interface).

## Constraints and non-goals

- No backend/store/API changes (unless the spec surfaces a real gap).
- Preserve existing behavior otherwise: detail view, editor, create button,
  copy-slug, deep-link routing, status-filter toggles.
- Not changing what "hierarchy" means for any axis (paths for taxonomy/
  capabilities, `parent` for work) — only how it is displayed.

## Decisions already made

- Tree is **collapsible** (expand/collapse toggles + remembered state), not
  merely indented.
- **Work is in scope** (tree by parent/child), alongside taxonomy and
  capabilities.

## Open questions for spec

- Work axis: how do the existing status groups and status-filter toggles
  interact with parent/child nesting? (e.g. keep status as top-level grouping
  with nesting inside, vs. a single parent/child tree that keeps the status
  badge per row and hides filtered nodes while retaining ancestors of visible
  ones.)
- Filter/search behavior: when the text filter is active, does the tree stay a
  tree (matches shown with their ancestor folders) or flatten to a filtered
  list?
- Federated/inherited items (origin alias prefix in `qualified`, e.g.
  `shared/...`): do they nest under an origin-named root, and are those roots
  selectable? (Expected: non-selectable origin folder.)
- Default expansion state on first load (all expanded, top level only, or
  remember last).
- Capability delta: is this a *change* to the existing `web` capability
  ("Browse TCW content in a local web app") or a new capability? (Resolve at the
  tcw-capabilities planning gate in the spec stage.)
