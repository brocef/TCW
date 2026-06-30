Work completed successfully.

## What changed

- Added taxonomy entry kinds: `Vocabulary` and `Feature`.
- Existing taxonomy metadata without `kind` now defaults to `Vocabulary`.
- Feature taxonomy entries can carry `vocabulary` refs, created through `tcw taxonomy add --kind feature --vocab <ref>`.
- `tcw taxonomy list` now marks entries as `[V]` or `[F]`, and `tcw taxonomy show` prints kind plus feature vocabulary refs.
- `tcw taxonomy check` validates taxonomy kinds and feature vocabulary refs.
- Capabilities can now use `Feature:` metadata, and `tcw capabilities check` verifies that it resolves to a taxonomy entry whose kind is `Feature`.
- The repo now dogfoods the new model with vocabulary entries for `Vocabulary` and `Feature`, plus feature entries for taxonomy feature registration and capability feature association.
- Updated README, capability ledgers, release notes, changelog, and the `tcw-taxonomy` / `tcw-capabilities` skills.

## Verification

- `pytest tests/test_taxonomy.py tests/test_capabilities.py` -> 49 passed.
- `tcw taxonomy check` -> taxonomy OK.
- `tcw capabilities check` -> capabilities OK.
- `pytest` -> 212 passed.
- `tcw taxonomy add --help` shows `--kind {vocabulary,feature}` and `--vocab REF`.
- `tcw taxonomy show taxonomy-feature-registry` prints `kind: Feature` and its vocabulary refs.
- Local `bllm-review` over `b6f02e7^..HEAD` saved to `logs/taxonomy-vocabulary-feature-review.md`.
- Addressed the local review's concrete follow-up: unknown taxonomy kinds now show `?` in list output instead of looking like vocabulary, and focused tests now cover missing feature vocabulary refs, ambiguous capability feature refs, repeatable `--vocab`, and mixed `[V]` / `[F]` list output.
- `pytest tests/test_taxonomy.py tests/test_capabilities.py` after local-review follow-up -> 52 passed.
- `pytest` after local-review follow-up -> 215 passed.

## Deviations

- `Subject` remains supported and unchanged. `Feature` is added as the stronger association instead of replacing the loose subject pointer.

## Follow-up notes

- No migration command was added. Existing entries remain valid through the default `Vocabulary` behavior.
