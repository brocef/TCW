# Plan: web UI multi-select dropdown filter

Frontend-only, single-threaded. Derived from `spec.md`. Verified in-browser (no
unit tests — the store/endpoint is unchanged and already covered).

## Phase 1 — state + predicate (`tcw/serve/static/app.js`)

1. `state`: add `kindFilter: []` and `tagFilter: []` (next to `filter`/`statusFilter`).
2. `itemVisible(item)`: after the existing text/status checks, add:
   - taxonomy: `if (state.kindFilter.length && state.kindFilter.indexOf(item.kind) === -1) return false;`
   - work: `if (state.tagFilter.length && !state.tagFilter.some(t => (item.tags||[]).indexOf(t) !== -1)) return false;`
3. `renderList()` `filtering` gate: OR-in `state.kindFilter.length` (taxonomy) and
   `state.tagFilter.length` (work) so the prune runs when a facet is active.

## Phase 2 — the reusable control (`app.js`)

1. `renderFacetDropdown(id, label, options, selected)` → a `<details class="facet">`
   with a `<summary>` (label + `(N)` count) and a `.facet-panel` of
   `.facet-option` checkbox rows (value = option, checked if in `selected`). Empty
   `options` → a `.facet-empty` hint row.
2. Generalize `renderStatusFilters()` → `renderFilterControls()`:
   - work: existing status toggles **+** `renderFacetDropdown("facet-tags", "Tags",
     state.registeredTags, state.tagFilter)`.
   - taxonomy: `renderFacetDropdown("facet-kind", "Kind", ["Feature","Vocabulary"],
     state.kindFilter)`.
   - capabilities: hidden (as today).
   Show `#status-filters` for work **and** taxonomy (currently work-only).
3. Wire `.facet-toggle` change events: flip the value in the matching selected
   array (`kindFilter` for `#facet-kind`, `tagFilter` for `#facet-tags`), update the
   summary count text in place, then call `renderList()` only (keep the `<details>`
   open). Keep the existing status-toggle wiring intact.
4. Call site: `render()` already calls `renderStatusFilters()` — rename to
   `renderFilterControls()`.

## Phase 3 — styling (`tcw/serve/static/style.css`)

`.facet` (inline-block, relative), `.facet > summary` (button-like, reuse the
status-toggle look), `.facet-panel` (absolute popover: border, background,
shadow, small padding, `z-index`, scroll if long), `.facet-option` (flex checkbox
row), `.facet-empty` (muted hint). Ensure the panel escapes the filter row
(`overflow: visible` on the container as needed) — note the list column now has
`overflow-y: auto` from the prior item, so the panel may need to render above the
scroll region; if clipping occurs, anchor the panel with enough `z-index` and, if
needed, keep the controls row outside the scroll container (it already is —
`#status-filters` sits above `#list`).

## Phase 4 — docs (documentation-sync)

- `docs/capabilities/web/description.md` — add the kind/tag filter controls to the
  browse-capability body (at completion, via edit; `check`/`validate` after).
- `docs/release-notes/upcoming.md` — one-line "filter the web list by kind/tag".
- `docs/changelogs/upcoming.md` — Added: web facet filter (app.js/style.css).
- README: the `tcw serve` section lists viewer features — add filter-by-kind/tag
  if it fits; re-evaluate at completion.

## Verification

- `tcw serve` on this repo: taxonomy Kind filter (Feature-only, compose with text);
  work Tags filter (multi-select OR, compose with status + text); dropdown stays
  open across toggles; empty-tags hint; capabilities view has no facet; no console
  errors. Screenshot the two filtered states.
- Dual review (subagent + `bllm-review-many`) before the verification stop.
