# Taxonomy vocabulary and features plan

## Phase 1: Model and store

- Add taxonomy kind constants and a `vocabulary` field to `Term`.
- Update `TaxonomyStore.add` and `FsTaxonomyStore.add` to accept `kind` and `vocabulary`.
- Persist `kind` and `vocabulary` in `meta.yaml`; default missing kind to `Vocabulary`.
- Add validation for unknown kinds and feature vocabulary refs.

## Phase 2: CLI

- Add `tcw taxonomy add --kind vocabulary|feature --vocab <ref>`.
- Show kind and feature vocabulary in `tcw taxonomy show`.
- Add kind markers to `tcw taxonomy list`.

## Phase 3: Capability association

- Add `Feature` to the locked capability field vocabulary.
- Validate `Feature` refs against the taxonomy store and require the target taxonomy entry to be kind `Feature`.
- Preserve existing `Subject` behavior.

## Phase 4: Tests

- Add focused taxonomy tests for feature creation, listing, show output, and validation.
- Add capability tests for valid feature refs, dangling refs, and refs to vocabulary terms.
- Run the taxonomy/capabilities test subset and the full suite if practical.

## Phase 5: Documentation sync

- Update `README.md` for taxonomy vocabulary/features and capability `Feature` validation.
- Update `docs/capabilities/taxonomy/capabilities.md` and `docs/capabilities/capabilities/capabilities.md`.
- Update `docs/release-notes/upcoming.md` and `docs/changelogs/upcoming.md`.
- Update `skills/tcw-taxonomy/SKILL.md` and `skills/tcw-capabilities/SKILL.md`.
- Write `outcome.md` after implementation with verification evidence.
