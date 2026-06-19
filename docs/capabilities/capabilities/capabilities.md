# Capabilities — capabilities

## Add a capability
**Status:** Supported
**Subject:** capability

As a user, I run `tcw capabilities add <namespace/path> [name]` (with `-s <status>`, `--folder`, and a piped body) to scaffold a capability as a flat file or a promoted folder. The tool refuses a flat/folder collision.

## Browse capabilities by status
**Status:** Supported
**Subject:** capability/status

As a user, I run `tcw capabilities list` to see every capability flagged by its status, filterable with `--status` and `--namespace`.

## Read a capability
**Status:** Supported
**Subject:** capability

As a user, I run `tcw capabilities show <id>` (or just `tcw capabilities <id>`) to read a capability file or a single `#heading`, printing its metadata block and body.

## Search capabilities
**Status:** Supported
**Subject:** capability

As a user, I run `tcw capabilities search <query>` to find capabilities whose name or body matches.

## Validate capabilities
**Status:** Supported
**Subject:** capability/subject

As a user, I run `tcw capabilities check` to validate cross-reference identifiers, the locked metadata vocabulary and required-when fields, role/condition slugs, and every `Subject:` ref against the taxonomy store.
