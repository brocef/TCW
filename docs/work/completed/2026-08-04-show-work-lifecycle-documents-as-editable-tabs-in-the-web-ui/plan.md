# Implementation plan: first-class lifecycle document tabs

## 1. Add a focused work-document tab component

Create a focused kebab-case component under `web/client/src/ui/` for the work
content tabs rather than expanding the already broad `DetailView`. Define the
three bounded tab descriptors in one place, mapping the requested labels to
`initial-request`, `spec`, and `plan`.

The component will:

- render an accessible Radix tab list in the required order;
- render Initial Request from the already-loaded work body;
- load a present Spec or Implementation Plan through the existing artifact GET
  route when selected, with explicit loading, error/retry, and per-item cached
  content states;
- show a not-yet-present panel without Edit for missing later documents;
- route Initial Request editing to the existing core work editor and Spec/Plan
  editing to the existing artifact editor; and
- reset to Initial Request when the selected work slug changes, ensuring stale
  content or selection cannot carry between items.

Add focused component tests for the labels and order, default/reset selection,
present-document loading and rendering, missing states, error/retry behavior,
and the correct edit callback for each document. Verify with
`pnpm test -- web/client/src/ui/work-document-tabs.test.tsx` and
`pnpm typecheck`.

## 2. Integrate tabs into the work detail without duplicating artifacts

Wire the component through `web/client/src/ui/content-views.tsx` and
`web/client/src/ui/app.tsx`, exposing the narrow artifact-read callback it
needs while reusing the current `enterResource` and `enterCore` edit flows.
Keep the server routes and `WorkStore` interface unchanged.

Replace the standalone initial-request Markdown body with the tabbed content
area. Filter Initial Request, Spec, and Implementation Plan out of the generic
artifact action row while leaving other lifecycle artifacts, plan stages, and
sidecars in their existing surfaces. Add only the CSS needed for the tab panel,
document actions, and loading/empty/error states, including narrow-screen
behavior consistent with the detail pane.

Update `web/client/src/ui/content-views.test.tsx` and any app-level tests needed
to prove callback wiring and preservation of the surrounding work detail.
Verify with `pnpm test`, `pnpm typecheck`, and `pnpm lint`.

## 3. Cover the complete browser interaction

Update the lifecycle-artifact flow in `web/e2e/parity.spec.ts` to assert that:

- the three tabs are visible in order and Initial Request starts selected;
- Spec and Implementation Plan render in the browser after selection;
- editing Spec from its selected tab persists through the existing API;
- choosing another work item restores Initial Request selection; and
- the existing sidecar and stale-write scenarios still work.

Use accessible role/name locators for the Radix tabs and document actions.
Verify with `pnpm test:e2e`; if the environment cannot launch Chromium or bind
the fixture server, record that environmental limitation and run the component
coverage plus all other web checks rather than weakening the assertions.

## 4. Reconcile the capability and Documentation Sync entries

After the implementation is stable, update the following as one final
documentation block:

- `docs/capabilities/web/editing/description.md` — describe the first-class
  Initial Request, Spec, and Implementation Plan tab behavior while keeping the
  capability `Supported`.
- `README.md` [Public-API] — update the local web-app editing overview to explain
  that the three planning documents are viewed and edited in tabs.
- `docs/release-notes/upcoming.md` [Public-API] — add a plain-language note about
  viewing and editing work planning documents without leaving the browser.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — record the tab component,
  artifact loading integration, and regression coverage under the appropriate
  technical headings.
- `skills/tcw-work/SKILL.md` [Skill-Driven-Component] — update the web-editing
  note so agents know the core planning documents are first-class web tabs,
  while lifecycle gates and hooks remain CLI/skill responsibilities.

Run `tcw capabilities check` after the capability reconciliation and inspect
the final code diff before writing these entries so their wording describes the
landed behavior.

## 5. Build and run repository checks

Build the maintained web client and commit the deterministic packaged assets
under `tcw/serve/dist/client`. Run:

- `pnpm prettify:check`
- `pnpm typecheck`
- `pnpm lint`
- `pnpm test`
- `pnpm build`
- `pnpm check:build`
- `pnpm test:e2e`
- the focused Python serve tests if the existing API contract is touched during
  implementation
- `tcw capabilities check`
- `tcw taxonomy check`
- `tcw validate`
- `git diff --check`

## Verification

In addition to automated checks, inspect the work detail at desktop and narrow
viewport widths with work items representing all three planning states:

- Initial Request only;
- Initial Request plus Spec; and
- Initial Request, Spec, and Implementation Plan.

Confirm that tab order, selection treatment, Markdown rendering, missing-state
copy, and Edit availability are unambiguous; switching between items never
shows the prior item's tab or content; no tab click launches an external
application; and other lifecycle artifacts, plan stages, and sidecars remain
reachable. Verify keyboard tab selection and visible focus treatment as part of
the accessible Radix interaction.
