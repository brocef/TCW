# Outcome: web UI multi-select dropdown filter

Work completed successfully. Frontend-only enhancement to `tcw serve`; verified
in-browser; dual-reviewed. Full test suite green (629 passed — no backend change,
so coverage is unchanged).

## What changed

`tcw/serve/static/app.js` + `style.css`:

- **Reusable facet dropdown** — `renderFacetDropdown(id, label, options, selected)`
  builds a native `<details class="facet">` disclosure (summary + `(N)` count) over
  a checkbox panel. Native `<details>` gives open/close + keyboard access with no
  custom dropdown JS.
- **Two uses** — `renderStatusFilters()` was generalized to
  `renderFilterControls()`: work view shows the status toggles **+** a `Tags`
  dropdown (options from `state.registeredTags`, already fetched via
  `GET /api/work/tags`); taxonomy view shows a `Kind` dropdown
  (`Feature`/`Vocabulary`); capabilities view shows none. `#status-filters` now
  renders for taxonomy too.
- **State + filtering** — `state.kindFilter[]` / `state.tagFilter[]` (empty = all;
  multiple = OR/match-any). `itemVisible()` gained kind/tag checks; the
  `renderList()` `filtering` gate ORs in a non-empty facet so the tree prunes.
  Facets compose (AND) with the text filter and status toggles.
- **Open-across-selections** — the checkbox `change` handler flips the value in the
  selected array, updates the summary count in place, and re-prunes via
  `renderList()` **only** (not full `render()`), so the `<details>` stays open.
- CSS: `.facet` / `.facet-panel` (absolute popover) / `.facet-option` / `.facet-empty`.

No new endpoint, model, or store change (the `GET /api/work/tags` endpoint shipped
with the tags item).

## Verification performed

In-browser (`tcw serve`), both facets:

- **Taxonomy Kind:** selecting `Feature` pruned the tree to Feature terms only;
  summary read `Kind (1)`; dropdown stayed open. ✓
- **Work Tags** (throwaway repo, tags `bug`/`urgent`/`chore` + 5 items): selecting
  `bug` + `urgent` showed exactly the three items carrying either (`Bug and urgent`,
  `Only bug`, `Only urgent`); `Only chore` and the untagged item were excluded —
  OR/match-any confirmed; summary read `Tags (2)`; dropdown stayed open across both
  selections. ✓
- Empty registered tags → `Tags` dropdown shows a `none available` hint. ✓
- Capabilities view shows no facet control. ✓
- Popover renders un-clipped over the (independently-scrolling) list. No console
  errors. ✓
- `pytest` — 629 passed; `tcw validate` clean.

## Review (dual)

1. **Subagent (targeted-code-reviewer)** — traced state → `itemVisible` →
   `pruneTree` → `renderList`, the handler, `esc`, server-side `kind`
   normalization, and the CSS clip chain. **No correctness, state, or XSS bugs.**
   All six high-risk areas verified sound (no stale array refs; `renderList`-only
   re-render keeps `<details>` open; correct AND/OR composition; `renderStatusFilters`
   fully removed; no cross-view leakage; option values HTML-escaped and round-trip).
   Two judgment/minor findings (below).
2. **`bllm-review-many` (qwen25)** — nothing actionable: `esc` is defined elsewhere
   and option values are escaped; `state.registeredTags` is initialized and guarded;
   the "duplicate selected" case can't occur (handler only pushes when absent);
   `indexOf`-vs-`includes` is style; app.js has no unit-test harness by design.

### Findings triaged

- **[Low–Medium] Facets don't force-expand ancestors** — when a facet is the only
  active filter and a user has *manually collapsed* a parent, matching items under
  it stay pruned-in-but-hidden (unlike the text filter, which force-expands to
  reveal matches; **like** the status toggles, which deliberately don't override a
  manual collapse). **Kept as-is** because the spec explicitly scoped facets to
  "trigger the tree prune … exactly as the status toggles do," and on a fresh load
  (parents default-expanded) acceptance criterion 1 holds — verified. **Surfaced to
  the user** as a deliberate, spec-aligned choice: if facets should instead *reveal*
  matches like the text search, it's a one-line change to OR the facet-active
  condition into the force-expand gate (+ skip manual toggles while a facet is
  active). Awaiting the user's call; not blocking.
- **[Low] Popover clip in short/narrow windows** — `.facet-panel` (absolute) can be
  clipped by `.list-pane { overflow: hidden }` only if the pane is shorter than the
  panel or narrower than its 160px min-width. In practice the list column's grid
  min-width is 260px (> 160px) and the pane is `100vh`-tall, so it doesn't manifest
  on desktop; the mobile breakpoint flips to `overflow: visible`. Verified un-clipped
  in-browser. Accepted (the plan already noted this risk).

No code changes were required from the review.

## Deviations from plan

None material. The changelog entry bundles this item with the sibling
tree-scroll change (both are `tcw/serve/static/` layout/UX shipping together).

## Follow-up notes (closeout decision)

- Optional: adopt the facet force-expand behavior (finding 1) if preferred.
- No capabilities-view facet and no persistence of facet selections across reloads
  — explicit non-goals for v1.
