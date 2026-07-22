## Objective

Establish Radix Themes, first-paint theme resolution, robust browser-local
preference state, and the Settings appearance chooser without changing routes or
editor state.

## Pre-stage checks

- Confirm the Fastify/React prerequisite work item is completed.
- Run `tcw work start` and commit that transition before product edits.
- Run the existing client unit tests and relevant Playwright parity tests to
  establish a behavioral baseline.
- Inspect the exact current package versions, CSP, HTML/build entry handling,
  asset packaging, top-bar ordering, and dirty-editor state ownership.

## Implementation

- Add exactly pinned `@radix-ui/themes` and `@radix-ui/react-icons` dependencies,
  update the lockfile, and import the Radix stylesheet.
- Introduce a `TThemePreference = "light" | "dark" | "system"` internal type
  and small testable helpers for defensive parsing, storage access, resolution,
  document-root class cleanup/application, media-query updates, and storage
  events. Use `tcw.theme`; default all missing, invalid, or inaccessible states
  to System.
- Wrap the client in Radix `Theme` with teal accent, gray neutrals, solid panels,
  small radius, 90% scaling, and the resolved appearance.
- Add a same-origin blocking `theme-init.js` entry before the client paint path.
  Ensure it is deterministic and packaged, and preserve the current CSP without
  inline-script allowances.
- Add a Settings gear `IconButton` immediately after Work with a Settings
  tooltip and accessible name. Its end-aligned `Popover` contains an Appearance
  heading and controlled Light/Dark/System `RadioGroup`.
- Apply and persist choices immediately. Do not navigate, reload project data,
  replace editor drafts, or touch dirty state.
- Add unit/component tests for parsing, System default, storage failures,
  invalid values, root cleanup, OS/storage events, ordering/naming, radio
  semantics, focus and dismissal, persistence, immediate application, and
  unchanged dirty editor state.

## Post-stage checks

- Run typecheck, lint, the theme helper/component tests, and focused Playwright
  coverage for first paint, the three choices, OS changes, cross-tab events, and
  keyboard-only Settings operation.
- Confirm the initializer executes by `DOMContentLoaded` before the React shell,
  and that explicit modes ignore later OS changes.
- Run deterministic build checking and confirm the strict CSP remains unchanged.
- Inspect the diff for domain, route, or dirty-state changes; commit the complete
  foundation stage before continuing.
