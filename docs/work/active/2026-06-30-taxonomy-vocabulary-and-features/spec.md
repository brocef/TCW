# Taxonomy vocabulary and features spec

## Capability changes

Changed existing capabilities:

- `taxonomy#add-a-term`: add can create vocabulary or feature entries, with vocabulary as the compatibility default.
- `taxonomy#browse-the-term-forest`: listing should expose enough kind signal to distinguish vocabulary from features.
- `taxonomy#read-a-term`: showing an entry should include its kind and, for features, the vocabulary it involves.
- `taxonomy#validate-the-taxonomy`: validation should check feature vocabulary references in addition to existing `relatesTo` and federation checks.
- `capabilities#validate-capabilities`: validation should accept and check a `Feature` metadata field that resolves to a taxonomy feature.

## Problem

Taxonomy currently models all entries as generic terms. That is enough for project language, but it cannot express the difference between a conceptual vocabulary item like `User` and an interaction-oriented feature like `User Authentication`. Capabilities can only point to a `Subject`, so they cannot strongly bind to the feature whose behavior they describe.

## Goals

- Add first-class taxonomy entry kinds: `Vocabulary` and `Feature`.
- Keep existing taxonomy entries valid by treating missing kind metadata as `Vocabulary`.
- Let feature entries declare the vocabulary terms they operate on or involve.
- Let capabilities declare a `Feature` metadata field and validate that it points to a registered taxonomy feature.
- Update CLI output, tests, docs, release notes, changelog, and the driving skills.

## Non-goals

- No migration command for existing repositories in this change.
- No removal of `Subject`; it remains compatible and continues to validate against taxonomy entries.
- No new filesystem-only tree layout for features. Kind and relationships remain abstract entry metadata.

## Current-state findings

- Taxonomy entries are `Term` objects backed by `docs/taxonomy/<slug>/meta.yaml` plus `description.md` in `tcw/store/base.py` and `tcw/store/fs.py`.
- Existing `meta.yaml` supports `name` and `relatesTo`; `tcw taxonomy check` validates `relatesTo` references and federation.
- Capability metadata fields are locked by `CAP_FIELDS` in `tcw/store/base.py`; `tcw capabilities check` validates `Subject` references through the taxonomy store.
- Public behavior is documented in `README.md`, `docs/capabilities/*`, and the `skills/tcw-taxonomy` and `skills/tcw-capabilities` routers.

## Proposed behavior

- Extend taxonomy entries with:
  - `kind`: `Vocabulary` or `Feature`, defaulting to `Vocabulary` when absent.
  - `vocabulary`: a list of taxonomy refs used by `Feature` entries.
- Extend `tcw taxonomy add` with:
  - `--kind vocabulary|feature` with `vocabulary` as the default.
  - repeatable `--vocab <ref>` values used when creating feature entries.
- Print taxonomy kind in `list` and `show`; print feature vocabulary refs in `show`.
- Validate:
  - unknown taxonomy kinds;
  - feature `vocabulary` refs that are dangling or ambiguous;
  - feature `vocabulary` refs that resolve to another feature instead of vocabulary.
- Extend capability metadata with `Feature`. Validate that it resolves to a taxonomy entry whose kind is `Feature`.

## Acceptance criteria

- Existing tests and current repository data continue to pass without adding kind metadata to every existing term.
- New tests cover adding/showing/listing features, feature vocabulary validation, and capability `Feature` validation.
- `tcw taxonomy --help` and `tcw capabilities check` behavior reflect the new fields.
- Documentation sync files and relevant skills are updated.

## Risks

- Existing test helpers that write bare metadata must remain valid through default-kind behavior.
- The `Subject` and `Feature` fields must be clearly documented so the new stronger association does not appear to silently replace subject references.

