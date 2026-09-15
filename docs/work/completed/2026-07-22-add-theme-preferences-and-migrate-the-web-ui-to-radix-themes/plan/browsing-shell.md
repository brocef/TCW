## Objective

Hard-convert every browsing-shell surface to Radix components and tokens while
preserving the existing three-pane information architecture and interaction
contracts.

## Pre-stage checks

- Confirm the theme-foundation stage is verified and committed.
- Run browsing, routing, filtering, tree-keyboard, resizing, Markdown-link, and
  responsive parity tests.
- Inventory native and bespoke shell controls in `app.tsx`,
  `reference-input.tsx`, and `style.css`, separating visual styling from custom
  behavior that Radix does not replace.

## Implementation

- Convert the top bar, axis navigation, panes, filters, object rows, detail
  headers, metadata, badges, cards, tooltips, scroll regions, and Markdown
  presentation to Radix Themes components and tokens.
- Replace native facet `details` elements with Radix popovers and controlled
  checkboxes, preserving the filter state and match behavior.
- Preserve three-pane layout, route/deep-link/history behavior, resizers, tree
  roles and keyboard model, text/status/kind/tag filtering, selected-object
  behavior, responsive single-column layout, copy actions, and object viewing.
- Retain custom tree semantics, resizers, reference-combobox logic, and Markdown
  link handling. Express their presentation solely through Radix color, spacing,
  radius, and shadow tokens.
- Add/update component tests around converted controls and deterministic
  light/dark Playwright screenshots for the shell and filter popovers at desktop
  and responsive widths.

## Post-stage checks

- Run typecheck, lint, Vitest, focused browsing/filter/tree/routing Playwright
  tests, and light/dark screenshot assertions.
- Exercise pane resizing, keyboard tree navigation, filter focus/dismissal,
  deep links, Back/Forward, and responsive transitions in a live browser.
- Inspect remaining raw controls and hard-coded visual values; commit the whole
  browsing-shell stage before editing mutation and feedback surfaces.
