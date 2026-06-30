# Taxonomy — capabilities

## Add a term
**Status:** Supported
**Subject:** term
**Feature:** taxonomy-feature-registry

As a user, I run `tcw taxonomy add <name>` (with optional `-s <slug>`, `-p <parent>`, `--kind vocabulary|feature`, repeatable `--vocab <ref>`, and an inline or piped description) to register vocabulary or feature entries. The slug is the entry's path identity; adding under a parent nests it.

## Browse the term forest
**Status:** Supported
**Subject:** term
**Feature:** taxonomy-feature-registry

As a user, I run `tcw taxonomy list` to see every entry as an indented forest, each flagged by kind (`Vocabulary` or `Feature`) and origin (`local` or an extends alias). `--local` hides inherited entries.

## Read a term
**Status:** Supported
**Subject:** term
**Feature:** taxonomy-feature-registry

As a user, I run `tcw taxonomy show <path>` (or just `tcw taxonomy <path>`) to read an entry's name, qualified path, kind, feature vocabulary refs, relatesTo links, attachments, and the head of its description.

## Search terms
**Status:** Supported
**Subject:** term

As a user, I run `tcw taxonomy search <query>` to find terms whose name or description matches, across local and inherited taxonomies.

## Remove a local term
**Status:** Supported
**Subject:** term

As a user, I run `tcw taxonomy rm <path>` to delete a local term. The tool refuses to remove an inherited term and warns if other terms still relate to it.

## Validate the taxonomy
**Status:** Supported
**Subject:** reference
**Feature:** taxonomy-feature-registry

As a user, I run `tcw taxonomy check` to validate extends aliases, taxonomy kinds, feature vocabulary refs, and every relatesTo / subject reference — flagging cycles, duplicate aliases, alias/term collisions, dangling or ambiguous refs, and feature refs that do not point at vocabulary.

## Federate shared vocabulary
**Status:** Partial
**Priority:** P2
**Gaps:** remote git/URL sources, version-pinning, and transitive (multi-level) extends are deferred to Phase 6; only local sibling-repo paths resolve today.
**Subject:** namespace

As a user, I run `tcw taxonomy extends add <alias> <repo-path>` (or declare `extends: { <alias>: <repo-path> }` in `docs/taxonomy/config.yaml`) to import another repo's taxonomy under a namespace, so shared nouns mean the same thing everywhere.
