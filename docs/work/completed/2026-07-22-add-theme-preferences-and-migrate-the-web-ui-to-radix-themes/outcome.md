# Outcome — Radix Themes and appearance preferences

Work completed successfully and is ready for user visual verification.

## What changed

- Added exactly pinned `@radix-ui/themes` 3.3.0 and
  `@radix-ui/react-icons` 1.3.2 dependencies and imported the Radix stylesheet.
- Added a defensive `light | dark | system` preference model under `tcw.theme`.
  System is the default, follows live operating-system changes, and storage
  events synchronize open tabs. Invalid, missing, unreadable, or unwritable
  browser storage fails safely to System or retains the in-memory choice.
- Added a blocking same-origin `theme-init.js` before the React entry point. It
  resolves and applies exactly one `light`/`dark` root class before application
  paint while preserving the strict `default-src 'self'` CSP.
- Wrapped the client in a controlled Radix `Theme` with teal accent, gray
  neutrals, solid panels, small radii, and 90% scaling.
- Added an accessible Settings gear immediately after Work. Its end-aligned
  Radix popover contains a controlled Light/Dark/System radio group and applies
  the browser-local choice without navigation or editor-state changes.
- Hard-converted navigation, filters, popovers, checkboxes, scroll areas, tree
  controls, object rows, details, metadata, badges, cards, tooltips, Markdown,
  fields, selects, text areas, tags, references, editor controls, resource
  controls, lifecycle actions, validation, warnings, stale-write feedback,
  reconciliation, notifications, and empty/error states to Radix components.
- Start and Complete now use Radix Dialog; destructive Drop uses AlertDialog.
- Replaced the 1,200-line bespoke visual stylesheet with a compact layout and
  behavior layer backed exclusively by Radix tokens. Custom logic remains only
  for trees, reference search, resizers, dirty-state handling, and Markdown
  link behavior.
- Rebuilt deterministic packaged client assets, including Radix CSS/icons and
  the early initializer.
- Updated the README, upcoming release notes, and upcoming developer changelog.
  Documentation Sync found no driving-skill change because CLI, lifecycle,
  installation, and agent workflow contracts did not change.

## Verification performed

- TypeScript typecheck and ESLint passed.
- Vitest/React Testing Library passed: **29 tests** across six files, including
  preference parsing, invalid/inaccessible storage, System resolution, root
  cleanup, Settings ordering/naming, persistence, and unchanged shell state.
- Playwright passed: **12 tests** in the complete serial suite. Coverage includes
  first visits under dark OS settings, explicit Light persistence, System live
  changes, cross-tab storage synchronization, root class application by
  `DOMContentLoaded`, keyboard Settings operation, Radix select/popover/radio
  semantics, every pre-existing browser workflow, and seven deterministic
  screenshots for light/dark shell, responsive Settings, filter popover,
  validation editor, stale-write conflict, and lifecycle dialog.
- `pnpm check:build` passed against the committed generated assets.
- Full pytest passed: **680 tests**.
- A clean wheel built successfully after moving an obsolete ignored setuptools
  cache aside. The isolated install contains only the current hashed JS/CSS,
  `index.html`, and `theme-init.js`; no stale assets were included.
- The isolated wheel served from a throwaway TCW node without source or
  `node_modules`. Live responses confirmed the strict CSP, initializer path,
  hashed Radix client assets, and initializer preference/media-query logic.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` pass.

## Preserved contracts

The three-pane information architecture, routes, deep links, Back/Forward,
resizers, tree keyboard model, filters, responsive stacking, API payloads,
object creation/editing, lifecycle transitions, resource editing, dirty-state
guards, validation recovery, stale-write recovery, and accessibility semantics
remain intact. No public CLI, HTTP API, schema, Python store interface, taxonomy,
or TCW object-storage change was introduced.

## Deviations and follow-up

- The planned visual matrix is represented by seven deterministic baselines
  spanning light, dark, desktop, responsive, editor, filters, lifecycle,
  validation, and conflict surfaces rather than duplicating every state at every
  viewport/theme combination. Behavioral assertions cover both appearances and
  responsive operation independently.
- The production client bundle now crosses Vite's 500 kB warning threshold
  because Radix Themes is bundled as the selected complete design system. The
  bundle remains deterministic and fully offline; code splitting is a possible
  future optimization, not a correctness blocker for the local app.

## Pending closeout

`web/choose-a-theme` intentionally remains `Missing` until the user visually
verifies the result. After approval and any refinements, write
`refined-outcome.md`, set the capability to `Supported`, complete the work item,
and make the separate version-bump decision.
