# Specification — modular TCW web client

## Outcome

The `tcw serve` web client is organized into focused, testable modules and uses
one consistent, accessible presentation for taxonomy, capability, and work
trees. Maintainers can format the supported source surface deterministically,
and users retain every existing browsing and editing behavior while gaining
clearer tree controls, filter clearing, work-status treatment, and unobscured
reference search.

## Functional requirements

- `app.tsx` owns only top-level routing, application-state coordination, and
  composition. Browsing, details, editing, Markdown, settings, lifecycle
  dialogs, shared forms, and reusable components live in focused kebab-case
  modules.
- Shared UI type aliases and interfaces use the project's `T` prefix and live
  in a dedicated module. Route parsing, draft/payload conversion, and tree-view
  state are separated into coherent utilities or hooks rather than one large
  replacement hook.
- Root and nested tree children render through the same explicit list/grid
  container. Taxonomy, capability, and work rows share structure, sizing,
  metadata, hover, selected, and dimmed-ancestor treatments.
- Expand/collapse controls expose `aria-expanded`, preserve keyboard behavior,
  and provide a hit target of at least 32 by 32 CSS pixels.
- A `Clear filter` action appears at the right of the Filter field only while
  the query is non-empty. Clearing follows the same routing and unsaved-change
  protection as changing the query.
- Work status is ordinary metadata text. The whole work-item surface is tinted
  amber for backlog, blue for active, and gray for completed, with readable
  theme-aware hover and selection states.
- Reference results use a real opaque, bordered dropdown surface, remain
  absolutely positioned above both editor and Markdown preview, and keep their
  background while a long result list scrolls.
- Existing routes, API requests, persistence, keyboard navigation, dirty-draft
  protection, revision-conflict recovery, settings, and lifecycle behavior are
  unchanged.

## Formatting and generated assets

- Keep the existing Prettier configuration, package scripts, dependency, and
  lockfile changes.
- Add `.prettierignore` entries for dependencies, package-manager artifacts,
  generated web bundles, build/test/cache output, logs, worktrees, completed
  work, and versioned changelog/release-note archives.
- Keep maintained source/configuration, taxonomy, capabilities, backlog/active
  work, `README.md`, and upcoming changelog/release-note files format-eligible.
- Make the initial repository formatting pass a standalone mechanical commit.
- Rebuild and commit the deterministic `tcw serve` browser bundle.

## Internal interfaces

Add typed internal contracts for list-pane state, editor sessions, detail
rendering, and lifecycle-modal actions. Do not change server APIs, abstract
stores, URLs, or persisted data formats.

## Capability and taxonomy impact

- Change `web` to describe consistent, accessible tree presentation.
- Change `web/editing` to describe unobscured reference search.
- No taxonomy change is required.

## Verification

- Component coverage proves uniform root/nested structure, shared item classes,
  work status text/surface classes, enlarged toggles, and conditional filter
  clearing.
- Existing shell, settings, reference-input, tree-keyboard, and editor tests
  remain green after relocation.
- A reference-input regression and Playwright scenario cover an opaque,
  scrolling result list above Markdown preview.
- Final checks: `pnpm prettify:check`, `pnpm typecheck`, `pnpm lint`,
  `pnpm test`, `pnpm test:e2e`, `pnpm build`, `pnpm check:build`,
  `python -m pytest`, `tcw capabilities check`, `tcw taxonomy check`,
  `tcw validate`, and `git diff --check`.

## Completion boundary

After implementation, documentation, generated assets, and automated checks are
recorded, stop for user visual verification. Do not reconcile capability text,
complete the item, or cut a release until the user approves the result.
