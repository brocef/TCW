# Specification — Radix Themes and appearance preferences

## Capability changes

- Add `web/choose-a-theme` — **Choose the web interface theme** — as
  `Missing`, with `Feature=local-web-app` and this work item as its
  `Planning doc`.
- Record the capability under `new:` in this item's `capabilities.yaml`.
- A user can choose Light, Dark, or System for the local web app. The current
  browser stores the preference; it is not node data and does not cross
  browsers.
- No taxonomy change is required because `local-web-app` already describes the
  affected feature.
- Before completion, change the capability to `Supported` and validate it.

## Problem

The React client currently owns a bespoke light-only visual system in
`web/client/src/style.css`. Controls, dialogs, status feedback, filters, cards,
and navigation use custom classes and hard-coded light colors. Users cannot
choose an appearance, System preference is not respected, and the visual layer
does not have a shared accessible component foundation.

## Goals

- Adopt Radix Themes as the single visual component and token system across the
  complete client.
- Add a Settings control immediately after Work that offers Light, Dark, and
  System appearance choices.
- Apply the resolved appearance before first paint and keep it synchronized with
  operating-system and same-origin browser preference changes.
- Preserve all established information architecture, navigation, editor,
  conflict-recovery, responsive, keyboard, and accessibility behavior.
- Keep generated assets deterministic and usable from an installed wheel with
  no network access.

## Non-goals

- No public CLI, HTTP API, schema, Python store interface, or object-storage
  change.
- No server-side, project-level, account-level, or cross-browser preference.
- No compatibility flag or gradual coexistence with the legacy visual system.
- No domain redesign of TCW objects or workflows.
- No taxonomy addition or driving-skill update.

## Dependency and implementation gate

This item is blocked by
`2026-07-21-upgrade-tcw-serve-to-fastify-and-react`. That item has implemented
the source client and deterministic asset pipeline but remains active pending
user verification and closeout. Do not run `tcw work start` or edit product
code until the prerequisite is completed.

## Current-state findings

- `web/client/src/ui/app.tsx` contains the three-axis shell, object trees,
  filters, editors, lifecycle modals, feedback, Markdown rendering, routing, and
  dirty-state behavior in one React surface.
- `web/client/src/ui/reference-input.tsx` owns the behavior-specific reference
  combobox that must retain its interaction contract.
- `web/client/src/style.css` defines the light-only variables and bespoke
  component styling to remove. Layout-specific rules for panes, resizers, trees,
  and the split Markdown editor remain necessary but must consume Radix tokens.
- `web/client/index.html` currently loads only the React module entry, so an
  external blocking initializer must be inserted before the stylesheet/module
  path without weakening the strict server CSP.
- `package.json` pins every runtime dependency exactly; Radix packages must
  follow that convention. `scripts/build_web.mjs` and
  `scripts/check_web_build.mjs` own the deterministic generated-asset contract.
- Vitest/Testing Library tests cover client behavior, while
  `web/e2e/parity.spec.ts` and `playwright.config.ts` provide browser parity
  coverage against a live TCW node.

## Theme behavior

Define the internal preference type as `"light" | "dark" | "system"` and use
the key `tcw.theme`. Missing, invalid, or inaccessible local storage resolves to
System. Explicit Light or Dark always overrides the operating-system setting.

The document root has exactly one resolved Radix appearance class, `light` or
`dark`; switching removes the obsolete class. While System is selected, a live
`prefers-color-scheme: dark` listener updates the resolved class. A browser
`storage` event for `tcw.theme` re-reads, validates, applies, and reflects the
new preference without writing it back.

A same-origin blocking `theme-init.js` runs before React and CSS paint. It reads
the same key defensively, resolves System through `matchMedia`, cleans both root
classes, and adds the resolved class. It is an external packaged asset so the
existing CSP remains strict and does not gain an inline-script allowance.

The Radix `Theme` root uses `accentColor="teal"`, `grayColor="gray"`,
`panelBackground="solid"`, `radius="small"`, and `scaling="90%"`, with its
appearance controlled by the resolved choice.

## Settings interaction

Place a Radix `IconButton` with a gear icon immediately after Work. Its
accessible name and tooltip are both Settings. It does not navigate.

The control opens an end-aligned Radix `Popover` with an Appearance heading and
a controlled `RadioGroup` containing Light, Dark, and System. Selection applies
and persists immediately without replacing the route, reloading data, closing
an editor, or changing dirty state. Radix owns focus placement, Escape/outside
dismissal, and radio semantics.

## Visual-system migration

Hard-convert the browsing shell: top bar, axis navigation, panes, filters,
rows, headers, metadata, badges, cards, tooltips, scroll regions, and Markdown
presentation. Replace native facet `details` controls with Radix popovers and
checkboxes.

Hard-convert editing and feedback: text fields, selects, text areas,
checkboxes, buttons, tags, editor headers, lifecycle actions, artifact controls,
reference-input presentation, errors, warnings, conflicts, reminders, empty
states, and notifications. Start and Complete use Radix `Dialog`; destructive
Drop confirmation uses `AlertDialog`. Validation and operational feedback use
`Callout`, `Badge`, and themed surfaces.

Custom behavior remains only where Radix has no equivalent: tree semantics,
reference-combobox logic, resizers, and Markdown link handling. Custom CSS is
limited to layout or those behaviors and exclusively consumes Radix color,
spacing, radius, and shadow tokens. Remove old theme variables, hard-coded light
colors, and bespoke visual button/form/modal rules.

## Acceptance criteria

- The first visit follows a light or dark OS setting with no flash of the wrong
  theme, and the resolved class exists by `DOMContentLoaded` before the React
  shell renders.
- Light, Dark, and System are keyboard-operable, semantically exposed as radios,
  applied immediately, persisted across reloads, and synchronized across tabs.
- System follows live OS changes; explicit modes do not.
- Storage read/write failures and invalid stored values safely behave as System.
- The Settings gear follows Work and its popover has correct focus, Escape, and
  outside-dismissal behavior.
- Switching appearance leaves the URL, selected object, editor contents, and
  dirty-state protections unchanged.
- All browsing, filtering, editing, lifecycle, validation, warning, stale-write,
  reconciliation, empty/error, and notification surfaces use Radix components
  and tokens with deterministic light and dark presentation.
- Existing desktop/responsive layout, pane resizing, tree keyboard navigation,
  API contracts, routes, and workflows remain behaviorally equivalent.
- Source and committed generated assets are deterministic; an isolated installed
  wheel serves the initializer, Radix CSS, and icons offline.

## Documentation and release evidence

- Update `README.md` with the gear location, three choices, System default, and
  browser-local persistence.
- Add plain-language coverage to `docs/release-notes/upcoming.md`.
- Add dependency, theme, initializer, migration, and build details plus the
  implementation hash range to `docs/changelogs/upcoming.md`.
- Re-run Documentation Sync after implementation. No `skills/*/SKILL.md` change
  is expected because CLI behavior, lifecycle, installation requirements, and
  agent workflow are unchanged.

## Verification requirements

Unit and component coverage must include parsing/defaulting, storage failures,
invalid values, explicit overrides, OS and storage events, root cleanup, gear
order and naming, popover focus/dismissal, radio semantics, immediate switching,
persistence, and unchanged dirty editor state.

Playwright must cover first visits under both OS schemes; all choices and reload
persistence; explicit override and live System changes; pre-React theme timing;
keyboard-only Settings operation; and deterministic light/dark screenshots for
the shell, editor, filter popovers, lifecycle dialog, validation warning, and
conflict state at desktop and responsive widths.

Run typecheck, lint, Vitest, Playwright, deterministic build checking, full
pytest, `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`,
`git diff --check`, a live `tcw serve` smoke, and an isolated-wheel offline
smoke.

## Risks

- An initializer and React preference logic can drift; keep parsing/resolution
  behavior small, explicit, and tested against the same cases.
- Radix portal/focus behavior can expose regressions in existing modal and
  filter flows; cover keyboard and dismissal behavior in components and a real
  browser.
- A hard conversion can accidentally alter domain behavior hidden in visual
  markup; preserve behavioral tests before changing structure and expand them
  around affected workflows.
- Generated asset ordering or package CSS can break reproducibility or wheel
  inclusion; extend deterministic and isolated-install checks rather than
  relying on the development server.
