## Objective

Replace the monolithic client source with focused components and non-visual
modules without changing user or server contracts.

## Pre-stage checks

- Confirm the formatting stage is verified and committed.
- Run the existing unit/component tests and inspect `app.tsx`, current support
  modules, tests, and styles to map ownership and behavioral seams.
- Record route, persistence, dirty-draft, conflict, keyboard, and API contracts
  that must remain stable.

## Implementation

- Reduce `app.tsx` to top-level routing, application-state coordination, and
  composition.
- Extract browsing, detail, editing, Markdown, settings, lifecycle-dialog, and
  shared-form concerns into kebab-case files; give reusable functional
  components their own modules.
- Extract route parsing, draft/payload conversion, and tree-view state into
  focused utilities or hooks with unit coverage; avoid one oversized hook.
- Move shared UI contracts into a dedicated type module with `T`-prefixed names.
- Split/co-locate subsystem styles while keeping tokens and shell rules central.
- Preserve and relocate existing tests beside their extracted owners.

## Post-stage checks

- Run `pnpm typecheck`, `pnpm lint`, and `pnpm test`.
- Verify all routes, API payloads, navigation guards, revision conflicts,
  keyboard behavior, settings, and persistence remain covered.
- Inspect module size/ownership and commit the architecture stage before visual
  behavior changes.
