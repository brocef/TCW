## Objective

Give every axis one consistent tree-row model and improve the accessibility and
layering of filtering, expansion, work status, and reference results.

## Pre-stage checks

- Confirm the architecture stage is verified and committed.
- Run focused tree, filter, editor, reference-input, and keyboard tests.
- Inspect current root/nested markup, item classes, theme tokens, hit targets,
  status badges, navigation guards, and editor/preview stacking contexts.

## Implementation

- Render root and nested children through the same explicit grid/list container
  using the current capability-row spacing at every depth.
- Standardize taxonomy, capability, and work items around a shared structure,
  sizing, metadata, hover, selected, and dimmed-ancestor treatment.
- Increase toggle icons and hit targets to at least 32 by 32 pixels while
  preserving `aria-expanded` and keyboard behavior.
- Add a conditional right-side `Clear filter` button and clear via the existing
  filter navigation/dirty-change path.
- Render work status as metadata text and tint the complete item surface amber,
  blue, or gray for backlog, active, or completed with theme-aware states.
- Replace the reference-results pseudo-background with a real opaque bordered
  surface, positioned above both editor and preview with internal scrolling.
- Add component and Playwright regressions for all new behavior, including a
  long scrolling reference result list over Markdown preview.

## Post-stage checks

- Run focused component tests, `pnpm typecheck`, `pnpm lint`, `pnpm test`, and
  the relevant Playwright scenarios.
- Exercise filter clearing, dirty navigation, keyboard expansion, all status
  rows, and reference scrolling in a live browser.
- Commit the experience stage before generated assets or release docs.
