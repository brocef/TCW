# Taxonomy vocabulary and features

## Product changes

Upgrade TCW taxonomy so it can represent two object types:

- Vocabulary: the current taxonomy usage, meaning the fundamental language and conceptual terms of a project.
- Features: named manifestations of vocabulary in terms of how users or applications interact with those concepts. A feature operates on or involves one or more vocabulary terms.

Capabilities should be able to strongly associate with registered taxonomy features. This closes the loop: features operate on vocabulary, capabilities describe user-observable details of those operations, and work items describe changes to vocabulary, features, and capabilities.

The storage judgment should distinguish conceptual terms from interaction-oriented manifestations. Users do not interact with vocabulary directly; they interact with those concepts through features.

## Technical changes

Keep the taxonomy model storage-abstracted. Represent object kind and feature-to-vocabulary references as named fields on taxonomy entries, not filesystem-specific conventions. Preserve existing taxonomy terms as vocabulary by default so current repositories continue to validate.

## Meta changes

Update the TCW work item artifacts, public docs, changelog/release notes, and driving skills for taxonomy and capabilities.

