# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Changed

<changes starting-hash="1c74c50" ending-hash="c3fab23">
- Added repository-wide Prettier scripts/configuration and a bounded ignore
  policy, then applied the initial mechanical formatting pass.
- Split the React client into focused route, state, type, shared-component, and
  content/editor modules while retaining the existing API, route, dirty-state,
  conflict, keyboard, theme, and persistence contracts.
- Standardized all axis tree rows and nesting containers, enlarged disclosure
  controls, added guarded filter clearing, applied full-row Work status tints,
  and replaced reference-result card effects with a real opaque dropdown.
- Added component, route, reference-dropdown, filter-clear, and Playwright
  regressions, refreshed intentional UI screenshots, and rebuilt the committed
  browser/server assets.
</changes>
