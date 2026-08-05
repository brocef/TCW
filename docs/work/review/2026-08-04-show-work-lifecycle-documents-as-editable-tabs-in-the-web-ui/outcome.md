# Outcome: first-class lifecycle document tabs

## What shipped

### Work-document tabs and integration

Commit `10f5503` added a focused `WorkDocumentTabs` React component and wired it
into the work detail. Initial Request, Spec, and Implementation Plan now appear
as accessible tabs in the requested order, with Initial Request selected by
default. Present Spec and Plan artifacts load through the existing bounded API
and render in the browser; missing documents show explicit not-yet-present
states. Each present document routes to the existing revision-aware editor.

The work detail no longer duplicates those three documents in its generic
artifact actions. Other lifecycle artifacts, plan-stage documents, and sidecars
retain their existing controls. The tab cache is keyed by core and artifact
revisions so returning from a save cannot display stale content. The same
commit added component and Playwright regression coverage and rebuilt the
deterministic packaged client assets.

### Capability and documentation reconciliation

Commit `69eeb0a` updated `web/editing`, the README, upcoming user release notes,
the developer changelog, and the `tcw-work` skill's web-editing guidance.

### Browser regression hardening

Following review feedback, commit `259d84c` expanded the Playwright coverage
with a dedicated missing-document and cross-item-reset scenario and additional
editing assertions. The browser suite now directly protects Initial Request
editing, Implementation Plan editing, missing Spec/Plan states without edit
actions, and resetting to Initial Request without stale content when a different
work item is selected. The existing Spec edit, sidecar edit, and stale-write
coverage remains in place.

## Verification

- Vitest: 11 files, 50 tests passed.
- TypeScript: `pnpm tsc --noEmit` passed.
- ESLint: `pnpm lint` passed with zero warnings.
- Production client: `pnpm build` passed; `pnpm check:build` passed after the
  generated assets were committed.
- Two focused Playwright lifecycle-document scenarios passed. Together they
  cover tab order and default selection; missing Spec/Plan states; Initial
  Request, Spec, and Implementation Plan editing and persistence; cross-item
  reset without stale content; sidecar editing; and stale-write behavior.
- `tcw capabilities check`, `tcw taxonomy check`, `tcw validate`, and
  `git diff --check` passed.

## Plan corrections and environmental findings

- The first component-test pass exposed that an effect-driven loader cancelled
  its own request when it set the loading state. Loading was moved directly to
  tab selection and retry, and the regression tests now pass.
- The repository-wide `pnpm typecheck` wrapper remains blocked by the checkout's
  pre-existing Prettier baseline (59 unrelated files); the underlying TypeScript
  compiler passed, and every maintained source file changed by this work was
  formatted directly.
- The full Playwright suite starts successfully outside the sandbox but stops in
  the pre-existing taxonomy reference-search fixture before reaching this
  feature's serial test. The focused lifecycle-artifact Playwright test passes
  independently. The initial sandbox run also could not bind TCW's private API
  sidecar, as expected in the restricted environment.
