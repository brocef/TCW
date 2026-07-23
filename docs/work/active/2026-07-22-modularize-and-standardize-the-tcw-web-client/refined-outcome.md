# Refined outcome — modular and standardized TCW web client

The user visually verified and accepted the implemented web-client
modularization and interface standardization on 2026-07-23. No visual or
behavioral refinements were requested.

## Accepted result

- `app.tsx` is reduced from roughly 2,700 formatted lines to about 1,100, with
  shared contracts, route utilities, persisted UI state, reusable presentation,
  and detail/editor/lifecycle views extracted into kebab-case modules under a
  repository-wide Prettier configuration.
- Taxonomy, capability, and work trees share the same root and nested
  containers, row classes, selection treatment, and metadata presentation at
  every depth; disclosure controls are 32 by 32 pixels; work rows carry
  full-row lifecycle status tints with status retained as ordinary metadata.
- The Work tree exposes a single `Status` checkbox facet matching the `Tags`
  interaction, a name or modified-time sort with an ascending/descending
  toggle, and one independently scrolling surface.
- Every tree row and detail header shows an `Modified at` timestamp sourced
  from bounded object resources.
- Reference search results render on a real opaque, bordered, absolutely
  positioned scrolling surface above the editor and Markdown preview.

## Final verification

- Prettier, TypeScript, ESLint, 42 Vitest tests, and 12 Playwright scenarios
  passed, including refreshed intentional screenshots.
- The production build and deterministic `check_web_build` passed; the Vite
  chunk-size advisory is unchanged and pre-existing.
- 683 pytest tests passed, along with `tcw capabilities check`,
  `tcw taxonomy check`, `tcw validate`, and `git diff --check`.

## Closeout decisions

- Capability `web` is reconciled: its description now records the shared tree
  presentation, modified timestamps, status tinting, and the Work status/tag
  filtering and sorting. `web/editing` needs no wording change — the reference
  dropdown fix is already covered by its accessible live-search sentence.
  Both capabilities remain `Supported`.
- Documentation Sync is complete: README, user-facing release notes, and the
  developer changelog describe the change, and all three driving skills record
  `modified` as read-only adapter-provided presentation metadata.
- No follow-up work item is required. The client bundle-size advisory remains a
  possible optimization, not an acceptance issue.
- The release version remains unchanged pending the user's separate explicit
  major, minor, patch, or no-bump decision.
