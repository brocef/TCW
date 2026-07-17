# Spec: Web UI multi-select dropdown filter for taxonomy kind and work tags

Frontend-only enhancement to `tcw serve`. Unblocked by
`2026-07-17-add-tags-to-work-items-for-filtering` (its `GET /api/work/tags`
endpoint ships the registered tag set this consumes).

## Capability changes

- **Changed:** `web` (Browse TCW content in a local web app) — the object list
  gains a category filter control (kind for taxonomy, tags for work) alongside
  the existing text filter and work status toggles. Its description is updated at
  completion. Recorded in this item's `capabilities.yaml`.

No new endpoint, model, or store change.

## Problem

The web list has one narrowing control: a free-text `#filter` (substring over
the item JSON), plus work-only status toggles. There is no way to narrow by a
*category* — taxonomy **kind** (Feature / Vocabulary) or work **tag** — which is
the natural axis now that work items carry tags.

## Goal

One **reusable multi-select dropdown** control, used in two places, complementing
(not replacing) the text filter:

1. **Taxonomy view:** filter by **kind** — a dropdown with a checkbox per kind
   (`Feature`, `Vocabulary`).
2. **Work view:** filter by **tag** — a dropdown whose checkboxes are the node's
   registered tags (`state.registeredTags`, already fetched from
   `GET /api/work/tags`). Multiple tags selected ⇒ show items carrying **one or
   more** (OR / match-any).

Empty selection ⇒ no filtering on that axis (everything passes). Capabilities
view gets no facet control (out of scope).

## Proposed behavior

### The control (reusable)

A native `<details class="facet">` disclosure: a `<summary>` button labelled
`Kind ▾` / `Tags ▾` (with a `(N)` count when N options are selected) opening a
`.facet-panel` of checkbox rows. Native `<details>` gives open/close + keyboard
accessibility with no custom dropdown JS. One render helper
`renderFacetDropdown(id, label, options, selected)` builds it; one change handler
updates the selected set. Toggling a checkbox re-prunes the tree via `renderList()`
only (not a full `render()`), so the dropdown stays open across selections.

### State

- `state.kindFilter: string[]` — selected taxonomy kinds (empty = all).
- `state.tagFilter: string[]` — selected work tags (empty = all).
- Both reset to `[]` on load; not persisted (like the text filter, transient).

### Filtering (reuse the existing prune)

Extend `itemVisible(item)`:

- taxonomy: if `kindFilter.length` and `item.kind ∉ kindFilter` → hidden.
- work: if `tagFilter.length` and `(item.tags ∩ tagFilter) = ∅` → hidden (OR).

Extend the `filtering` gate in `renderList()` so a non-empty facet selection
triggers the tree prune (matches + ancestors) exactly as the status toggles do.
Text filter, status toggles, and the facet filter **compose** (AND across
controls; OR within the multi-select).

### Placement

The facet control renders in the existing filter-controls row (`#status-filters`,
generalized to show for taxonomy too): work view shows status toggles **and** the
Tags dropdown; taxonomy view shows the Kind dropdown; capabilities view stays
empty/hidden.

## Affected surfaces

- `tcw/serve/static/app.js` — `state.kindFilter`/`state.tagFilter`;
  `renderFacetDropdown` helper + change handler; `itemVisible` + `renderList`
  `filtering` gate; generalize `renderStatusFilters` (→ filter-controls) to render
  the facet for work + taxonomy.
- `tcw/serve/static/style.css` — `.facet` / `.facet-panel` / `.facet-option`
  styling (a small popover panel).
- `docs/capabilities/web/description.md` — note the filter controls at completion.

## Acceptance criteria

1. Taxonomy view: a **Kind** dropdown with `Feature`/`Vocabulary` checkboxes;
   selecting `Feature` shows only Feature terms (and their ancestor folders);
   clearing shows all. Composes with the text filter.
2. Work view: a **Tags** dropdown whose options are the registered tags; selecting
   two tags shows items carrying either (OR); composes with status toggles + text.
3. The dropdown stays open while toggling multiple checkboxes.
4. No registered tags ⇒ the Tags dropdown shows an empty/hint state, not a broken
   control. Capabilities view shows no facet control.
5. No new endpoint/model/store change; no console errors.

## Non-goals / risks

- No persistence of facet selections across reloads (transient, like text filter).
- No capabilities-view facet (no obvious category axis for it in v1).
- `<details>` doesn't auto-close on outside click — acceptable (native, simplest);
  a click-away handler can be added later if it annoys.
- Reuses `state.registeredTags`, already loaded in `load()`; no new fetch.

## Documentation sync (expected)

- `docs/capabilities/web/description.md` — filter controls (capability body).
- README / release-notes / changelog: the web viewer is described only briefly;
  a one-line release-note ("filter the web list by kind/tag") is warranted.
  Re-evaluate all triggers at completion.
