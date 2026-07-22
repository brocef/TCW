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

<changes starting-hash="facb747" ending-hash="facb747">
- Replaced the three independent Work status toggle buttons with a reusable
  `Status` facet popover using the same checkbox/count interaction as `Tags`.
- Added component and Playwright coverage for default status selections and the
  consolidated popover, refreshed screenshots, and rebuilt packaged assets.
</changes>

<changes starting-hash="84d55c1" ending-hash="84d55c1">
- Added a mutually exclusive Work tree sort selector for name or bounded
  resource modification time, plus a single ascending/descending toggle while
  preserving active, backlog, completed status grouping.
- Added the adapter-provided `WorkItem.modified` presentation field and
  filesystem derivation from state, lifecycle, sidecar, and plan-stage
  resources; arbitrary attachments remain excluded.
- Replaced the nested Radix tree scroll area with one native scroll container,
  added unit/API/Playwright regressions, refreshed UI snapshots, and rebuilt the
  packaged client assets.
- Marked hashed generated client assets as non-text diffs so dependency-emitted
  whitespace does not break repository whitespace validation.
</changes>

## Fixed

<changes starting-hash="eb2e019" ending-hash="9f97140">
- Moved work-resource opening into a tested client module and send `{}` with
  JSON POST requests so Fastify accepts plan-stage and artifact Open actions.
- Scoped the application `min-height` rule to the root Radix Theme wrapper so
  portaled tooltips and popovers retain their intrinsic size; added a browser
  assertion for visible, horizontally sized copy-slug tooltip content.
- Rebuilt the packaged client assets and refreshed affected portal screenshots.
</changes>
