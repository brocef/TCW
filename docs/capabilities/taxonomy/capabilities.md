# Taxonomy — capabilities

## Add a term
**Status:** Supported
**Subject:** term

As a user, I run `tcw taxonomy add <name>` (with optional `-s <slug>`, `-p <parent>`, and an inline or piped description) to register a domain noun. The slug is the term's path identity; adding under a parent nests it.

## Browse the term forest
**Status:** Supported
**Subject:** term

As a user, I run `tcw taxonomy list` to see every term as an indented forest, each flagged by origin (`local` or an extends alias). `--local` hides inherited terms.

## Read a term
**Status:** Supported
**Subject:** term

As a user, I run `tcw taxonomy show <path>` (or just `tcw taxonomy <path>`) to read a term's name, qualified path, relatesTo links, attachments, and the head of its description.

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

As a user, I run `tcw taxonomy check` to validate extends aliases and every relatesTo / subject reference — flagging cycles, duplicate aliases, alias/term collisions, and dangling or ambiguous refs.

## Federate shared vocabulary
**Status:** Partial
**Priority:** P2
**Gaps:** remote git/URL sources, version-pinning, and transitive (multi-level) extends are deferred to Phase 6; only local sibling-repo paths resolve today.
**Subject:** namespace

As a user, I run `tcw taxonomy extends add <alias> <repo-path>` (or declare `extends: { <alias>: <repo-path> }` in `docs/taxonomy/config.yaml`) to import another repo's taxonomy under a namespace, so shared nouns mean the same thing everywhere.
