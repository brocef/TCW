# Modularize and standardize the TCW web client

## Product changes

Standardize the local web app's taxonomy, capability, and work trees so root
and nested items use the same spacing, row structure, selection treatment, and
metadata presentation. Make expand/collapse controls easier to target, add an
accessible clear action to the filter, tint work-item surfaces by lifecycle
status, and ensure reference-search results remain opaque and unobscured above
the editor and Markdown preview.

## Technical changes

Modularize the React client so `app.tsx` coordinates routing, application state,
and composition rather than owning the entire interface. Extract focused
kebab-case components, hooks, utilities, styles, and shared `T`-prefixed types,
with tests co-located around each subsystem. Preserve all existing routes, API
requests, dirty-draft protection, revision-conflict handling, keyboard
navigation, theme behavior, and persistence.

Adopt Prettier as the web-client formatting foundation, including a bounded
ignore policy that excludes dependencies, generated/build/test/cache output,
logs, worktrees, completed work items, and versioned release archives while
keeping maintained source, configuration, taxonomy, capabilities, active work,
the README, and upcoming notes eligible. Rebuild and verify the committed
`tcw serve` client bundle after the refactor.

## Meta changes

Track the product delta against the existing `web` and `web/editing`
capabilities. No taxonomy, server API, storage interface, URL, or persisted data
format changes are expected. Stop after implementation and automated
verification so the user can visually verify the result before capability
reconciliation, work completion, or release.

