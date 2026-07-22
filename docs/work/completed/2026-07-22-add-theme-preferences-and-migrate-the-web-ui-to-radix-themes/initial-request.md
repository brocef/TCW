# Add theme preferences and migrate the web UI to Radix Themes

## Product changes

- Let users choose Light, Dark, or System appearance from a Settings control in
  the local web app. System is the default and follows live operating-system
  changes; the preference is stored only in the current browser.
- Replace the entire existing client visual layer with Radix Themes using a
  dense graphite treatment, teal emphasis, small radii, solid panels, and 90%
  scaling.
- Preserve the current three-pane information architecture, routes, object
  workflows, editor state and conflict handling, responsive layout, keyboard
  behavior, and accessibility contracts.

## Technical changes

- Add exactly pinned `@radix-ui/themes` and `@radix-ui/react-icons`
  dependencies and use Radix components and tokens throughout browsing,
  editing, dialogs, filters, feedback, and Markdown presentation.
- Store the preference under `tcw.theme`, resolve missing, invalid, or
  inaccessible storage to System, follow `prefers-color-scheme`, and synchronize
  cross-tab changes.
- Add a same-origin blocking `theme-init.js` entry so the resolved root class is
  applied before React and CSS paint without weakening the existing CSP.
- Remove the legacy visual variables and bespoke component styling, retaining
  only layout and behavior-specific CSS expressed with Radix tokens.
- Rebuild deterministic packaged web assets and verify an installed wheel can
  serve them offline.

## Meta changes

- Add `web/choose-a-theme` as a planned Missing capability associated with the
  existing `local-web-app` Feature; no taxonomy change is needed.
- Update the README, upcoming release notes, and upcoming developer changelog.
- This work introduces no public CLI, HTTP API, schema, Python store interface,
  or TCW object-storage change.
- The item remains blocked until
  `2026-07-21-upgrade-tcw-serve-to-fastify-and-react` is verified and closed.
  Do not begin implementation while that blocker remains active.
- After implementation and automated verification, stop for user visual
  verification and refinement before capability reconciliation, completion,
  and any separate version-bump decision.
