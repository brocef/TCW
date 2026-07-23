# Implementation outcome — modular TCW web client

## Implemented

- Added repository-wide Prettier configuration and a bounded ignore policy,
  retained the prepared package/lockfile changes, and committed the initial
  formatting pass separately.
- Reduced `app.tsx` from roughly 2,700 formatted lines to about 1,100 lines by
  extracting shared `T`-prefixed contracts, route utilities, persisted UI state,
  reusable presentation, and detail/editor/lifecycle views into kebab-case
  modules.
- Standardized taxonomy, capability, and work trees around shared root/nested
  containers and row classes; enlarged disclosure controls to 32 by 32 pixels;
  added accessible guarded filter clearing; and applied full-row status tints
  with status retained as ordinary metadata.
- Replaced the reference result `Card` with a real opaque, bordered, absolutely
  positioned scrolling surface above the editor and Markdown preview.
- Added route, tree, filter-clear, status-surface, disclosure-control,
  reference-dropdown, and long scrolling Playwright regressions and refreshed
  intentional screenshots.
- Rebuilt deterministic packaged client/server assets and synchronized README,
  release notes, and the developer changelog. Driving skills remain unchanged
  because no CLI, lifecycle, storage, or agent-workflow contract changed.
- Corrected the plan-stage/artifact Open POST contract to send a valid empty JSON
  object through Fastify, and scoped the root Theme height rule so portaled copy
  tooltips and Settings/filter popovers keep their intrinsic dimensions.
- Consolidated the Work backlog, active, and completed filters into a single
  `Status` checkbox facet that shares the `Tags` interaction and selected-count
  treatment.
- Added a single Work tree sort selection for name or bounded-resource modified
  time with an ascending/descending toggle, while retaining active, backlog,
  completed grouping ahead of the selected sort.
- Removed the nested tree scroll-area root/viewport pair so the list has one
  independently scrolling surface instead of two synchronized scrollbars.
- Updated the `tcw-work` driving skill for the read-only adapter-provided
  `WorkItem.modified` presentation field; it remains non-editable metadata.
- Added consistent `Modified at` subtext to every Taxonomy, Capability, and Work
  tree row and detail header. Taxonomy and Capability timestamps use bounded
  object resources, including declared composed documents and effective
  inherited-capability overrides.
- Updated all three driving skills to identify their axis's `modified` value as
  read-only, adapter-provided presentation metadata.

## Verification evidence

- Prettier check: passed for every file changed by this implementation. The
  repository-wide check separately reports formatting in the independently
  created eval-harness backlog item and `tcw-config.yaml`; those files remain
  untouched here. The pinned local binaries were invoked directly for
  Prettier, TypeScript, ESLint, Vitest, Playwright, and build checks.
- TypeScript and ESLint: passed with zero errors/warnings.
- Vitest: 10 files, 42 tests passed.
- Playwright: 12 scenarios passed using the already-installed compatible local
  Chromium executable, including timestamps in all axis trees/details,
  sort-key/direction controls, a single Work tree scroll container, the long
  opaque scrolling reference list, and a visible, horizontally sized copy-slug
  tooltip.
- Production build and deterministic `check_web_build`: passed. Vite retains
  its existing advisory that the single client chunk exceeds 500 kB.
- Pytest: 683 tests passed. The first sandboxed run could not bind loopback
  sockets; the approved unsandboxed rerun passed completely.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check`: passed.

## Deviations and retained state

- The architecture and tree/editor source changes were committed together
  because the shared row components were the extraction boundary as well as the
  presentation boundary; formatting and generated/docs stages remained
  isolated commits.
- The pre-existing blue theme selection and corresponding generated bundle were
  preserved and incorporated when rebuilding final assets.
- `.pnpm-store/` remains untracked and untouched.

## Pending user gate

Automated implementation verification is complete. Capability descriptions
remain unreconciled and the work item remains active pending user visual
verification. Do not write `refined-outcome.md`, complete the item, or cut a
release until the user approves the interface.
