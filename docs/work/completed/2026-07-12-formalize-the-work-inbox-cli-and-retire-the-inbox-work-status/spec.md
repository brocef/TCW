# Formalize the work inbox CLI and retire the inbox work status

## Capability changes

- Add `work/manage-the-work-inbox` as a Missing capability linked to the new
  `work-inbox` Feature. Flip it to Supported after implementation verifies.
- Update the existing board, start, and drop capability descriptions so formal
  work begins in backlog and has only backlog, active, and completed statuses.

## Problem

`docs/work/inbox/` currently serves two incompatible roles: a permissive raw
intake channel and a formal `WorkItem` status directory. Raw requests need not
contain TCW metadata, so treating them as work items leaks filesystem structure
into the abstract lifecycle and leaves no supported CLI ingestion path.

## Goals

- Expose `tcw work inbox list|show|accept` over abstract inbox entries and named
  resources.
- Accept standalone files and folder packages into backlog atomically.
- Preserve readable intake bodies and bounded attachment hierarchies without
  emitting binary data.
- Remove `inbox` from the formal work status vocabulary and transitions.
- Keep delegate/escalate using the raw inbox channel.

## Non-goals

No bulk, interactive, edit, reject, delegate, or triage subcommands. No required
intake schema and no remote adapter implementation.

## Proposed behavior

The abstract store exposes an opaque `InboxEntry` summary, an `InboxEntryDetail`
with a primary readable body and resource metadata, and `inbox_list`,
`inbox_show`, and `inbox_accept`. Acceptance is one store operation returning
the created backlog item.

The filesystem adapter treats each non-hidden direct child of `docs/work/inbox`
as an entry. A folder must contain exactly one of `INDEX.md` and `INDEX.txt`.
Hidden files, empty directories, and symlinks are ignored. Other regular files
are copied beneath `attachments/` with hierarchy preserved. A standalone text
file becomes the request body; a binary file becomes an attachment.

The generated `initial-request.md` uses the deterministic structure and sorted
manifest specified in `initial-request.md`. The adapter builds the complete work
item in a temporary sibling directory, moves it into backlog, and removes the
source only after the backlog item exists. Failures clean up the temporary work
item and preserve the source.

Formal statuses become `backlog`, `active`, and `completed`. `start` and `drop`
accept backlog items only. The inbox directory remains part of work scaffolding
as a raw channel, but is not scanned as formal work.

## Acceptance criteria

- The three inbox CLI commands produce stable, human-readable output and useful
  errors for missing, ambiguous, hidden, or unsafe entries.
- Folder and standalone acceptance preserve the required body and resources;
  binary contents are never printed.
- Failed acceptance leaves the source intact and no partial backlog item.
- Existing work commands, web status filtering, docs, skills, capability ledger,
  validation, and tests agree on the three formal statuses.
- Full tests and `tcw validate` pass.

## Risks

Filesystem rollback cannot be globally transactional with Git staging, so the
adapter must validate all sources before writing and use a temporary complete
item plus rename. Symlink and binary detection must fail safe and remain bounded
to the inbox entry.
