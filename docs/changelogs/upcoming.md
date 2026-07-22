# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Fixed

<changes starting-hash="c0974d1" ending-hash="2e59173">
- Refreshed the deterministic packaged React assets so installed distributions
  include the current staged-plan interface.
- Restored the declared plan-stage resource contract: writes to an undeclared
  stage return HTTP 400 while stale revisions continue to return HTTP 409.
</changes>

## Added

<changes starting-hash="89c0710" ending-hash="d2676c1">
- Added exactly pinned `@radix-ui/themes` 3.3.0 and
  `@radix-ui/react-icons` 1.3.2 dependencies, with a controlled
  Light/Dark/System preference stored under `tcw.theme`.
- Added a same-origin blocking `theme-init.js` packaged asset that resolves and
  applies the root appearance before the React entry point without changing the
  strict `default-src 'self'` CSP.
- Added live operating-system and cross-tab synchronization, defensive storage
  handling, Radix Settings popover/radio semantics, unit and component coverage,
  and six deterministic browser screenshot baselines.
</changes>

## Changed

<changes starting-hash="89c0710" ending-hash="d2676c1">
- Replaced the legacy light-only client presentation with Radix Themes
  components and tokens across navigation, trees, filters, details, editors,
  lifecycle dialogs, destructive confirmation, validation, warnings, stale
  writes, references, Markdown, and notifications.
- Reduced client CSS to layout and behavior rules backed exclusively by Radix
  tokens while preserving routes, API payloads, three-pane/responsive layout,
  resizers, tree keyboard behavior, dirty-state guards, and conflict recovery.
- Rebuilt the deterministic packaged web assets with the Radix stylesheet,
  icons, client code, and early initializer.
</changes>
