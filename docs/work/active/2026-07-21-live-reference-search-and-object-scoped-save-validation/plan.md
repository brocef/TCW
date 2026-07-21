# Implementation plan

## 1. Establish object-scoped validation

- Add `ValidationTarget` and selector exclusivity to `tcw/validate.py` while preserving full-node/path behavior and CLI calls.
- Extend the three abstract store `check()` contracts and filesystem adapters with optional object identifiers.
- Extract per-object semantic checks and private filesystem target-resource resolution for Taxonomy, Capabilities, and Work.
- Cover graph prerequisites, missing targets, local authored YAML/links, axis semantics, qualified/inherited references, bounded attachments, Work lifecycle artifacts/sidecars, and isolation from unrelated broken objects.

## 2. Wire post-save validation into the web server

- Centralize safe targeted validation and warning conversion in `web/server/src/server.ts`/the Python runtime boundary as appropriate.
- Invoke it after all create, structured edit, artifact, and sidecar mutations using canonical returned/resolved identities and descendant node roots.
- Remove component-wide warning checks and preserve successful mutation responses when validation reports findings or unexpectedly raises.
- Server-test all mutation categories, warning/clean responses, exceptions after committed writes, and descendant Work addressing.

## 3. Add reusable reference search and controls

- Add internal `T`-prefixed option, ranking-result, field-configuration, and mutation-response types; expose Work's optional `type`.
- Implement pure matching/ranking/highlighting utilities with deterministic ties, 10-result limit, and duplicate filtering.
- Centralize candidate scopes for every Work, Taxonomy, and Capability reference field, including descendant exclusion, epic/type filtering, kind/path filtering, and current-object exclusion.
- Build accessible single/multi combobox controls with keyboard and pointer selection, chips, free-form commits, focus retention, and negated Capability `When` handling.
- Integrate warning banners/toasts and clear stale warnings after clean saves while keeping conflicts and pre-save errors separate.

## 4. Verify UI behavior and browser integration

- Add Vitest unit/component coverage for ranking, highlighting, restrictions, ARIA, keyboard/mouse updates, free text, negation, and warning transitions.
- Add Playwright coverage for the `use` ranking example, bold matches, keyboard/pointer selection, canonical stored identifiers, and targeted validation alert.
- Rebuild committed client/server assets and verify deterministic output.

## 5. Reconcile product and documentation surfaces

- Update `README.md` web-editor guidance and `docs/capabilities/web/editing/description.md` while retaining `Supported` and the existing Feature.
- Update `docs/release-notes/upcoming.md` for the user-visible behavior and `docs/changelogs/upcoming.md` with the implementation commit range.
- Re-run documentation-sync; no driving-skill update is expected because CLI workflows and guardrails do not change.

## 6. Final verification

- Run Python tests, TypeScript typecheck, ESLint, Vitest, Playwright, build verification, `tcw taxonomy check`, `tcw capabilities check`, `tcw validate`, and `git diff --check`.
- Record results and any deviations in `outcome.md`, checkpoint the outcome, and stop for explicit user verification before refinement/completion.

## Dependencies and parallelism

The pure client search utilities can be developed independently of Python target validation, but server wiring depends on the target contract and UI integration depends on stable mutation warning types. Documentation follows verified behavior.
