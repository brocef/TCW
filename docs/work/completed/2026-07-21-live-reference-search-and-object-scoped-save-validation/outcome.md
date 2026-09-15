Work completed successfully.

## What changed

- Added typed, reusable reference option scoping, weighted ranking, deterministic sorting, highlighting, and accessible single/multi combobox controls for structured Work, Taxonomy, and Capability references.
- Preserved free-form entry, canonical identifier persistence, duplicate filtering, focus retention, and negated Capability conditions.
- Added storage-neutral `ValidationTarget` selection and optional per-object store checks while preserving full-node, path-scoped, and CLI validation behavior.
- Scoped target scans to each object's metadata, body, bounded attachments, Work lifecycle artifacts, and sidecars; project-graph validation remains the prerequisite.
- Added safe targeted validation warnings after every web create, structured edit, artifact save, and sidecar save, including successful responses when validation itself unexpectedly raises.
- Added persistent accessible validation notices, warning-count toasts, and clean-save warning clearing.
- Rebuilt the committed browser assets and updated the README, `web/editing` capability description, release notes, and changelog.

## Verification

- `python -m pytest -q` — 672 passed.
- TypeScript `tsc --noEmit` — passed.
- ESLint over `web` with zero warnings — passed.
- Vitest — 18 passed.
- Playwright — 11 passed using the installed local Chromium executable.
- Deterministic browser build verification — passed.
- `tcw taxonomy check`, `tcw capabilities check`, and `tcw validate` — passed.
- `git diff --check` — passed.

## Deviations and notes

- The pnpm launcher could not verify its registry signature in the restricted environment, so the installed project-local TypeScript, ESLint, Vitest, and Playwright binaries were used directly. The pinned build script and deterministic build check both passed.
- No taxonomy or driving-skill update was needed: `local-web-app` already models the Feature, and public CLI workflows and guardrails did not change.
- The work item remains active pending the required user verification/refinement decision before closeout.
