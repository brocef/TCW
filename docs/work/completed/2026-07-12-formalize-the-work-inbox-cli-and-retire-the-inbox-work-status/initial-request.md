# Formalize the work inbox CLI and retire the inbox work status

## Product changes

Add a deliberately small CLI surface for inspecting raw work intake and
accepting it into TCW's formal backlog:

```text
tcw work inbox list
tcw work inbox show <entry>
tcw work inbox accept <entry> [--title <title>]
```

`accept` signifies that the caller has reviewed an inbox entry and chosen to
turn it into a formal backlog work item. Acceptance always targets `backlog` for
this first version. Do not add bulk acceptance, interactive triage, editing,
delegation, rejection, or other inbox subcommands as part of the MVP.

The optional `--title` lets a caller replace the fallback work-item title after
reading the intake. Without it, derive the title from the standalone filename
without its extension or from the folder name.

Retire `inbox` as a `WorkItem` status. Raw inbox entries are intentionally not
required to be well-formed work items. The lifecycle should instead be:

```text
raw inbox entry --accept--> backlog --start--> active --complete--> completed
```

The new Missing capability is `work/manage-the-work-inbox`, associated with the
registered `work-inbox` Feature.

## Technical changes

### Abstract model

Represent raw intake separately from `WorkItem`, using an abstract inbox-entry
handle and named resources rather than filesystem paths. The store operations
should support listing entries, showing one entry, and atomically accepting one
entry into a backlog work item. A non-filesystem store must be able to implement
the same operations using its own intake queue and attachment mechanism.

Acceptance is one logical store operation. On any failure, leave the source
entry intact and do not leave a partially created backlog item.

### Permissive inbox entries

An entry directly inside `docs/work/inbox/` may be either:

- a standalone file of any extension; `.md` and `.txt` are encouraged because
  they are readily agent-readable; or
- a folder grouping all files associated with one request.

Standalone file contents have no structural requirements. Provide an optional
Markdown template that users can adopt to improve request quality, but do not
require the template or parse its sections as intake metadata.

A folder entry must contain exactly one conventional index file: `INDEX.md` or
`INDEX.txt`. If neither exists, acceptance fails. If both exist, acceptance
fails with an ambiguity error. The index contents are the request body. Other
regular files are associated resources, including images, data, additional
text, and nested folder trees.

Ignore hidden files and empty directories. Do not follow or copy symlinks.
Preserve resource hierarchy beneath a bounded `attachments/` collection in the
created work item. This prevents collisions with TCW-managed files such as
`state.yaml`, `initial-request.md`, `spec.md`, `plan.md`, and
`capabilities.yaml`, while keeping attachments implementable by non-filesystem
stores.

### Deterministic generated request

Generate `initial-request.md` deterministically when accepting either kind of
entry. For a folder entry, use this shape:

```md
# <accepted or derived title>

## Product changes

TBD

## Technical changes

TBD

## Meta changes

TBD

## Inbox contents

### Inbox manifest

- `initial-request.md` — accepted from `INDEX.md`
- `attachments/asset1.ext`
- `attachments/nested/asset2.ext`

### Inbox body

<verbatim contents of INDEX.md>
```

Sort manifest entries lexicographically by preserved relative path. Copy the
index contents verbatim into `Inbox body`; do not also copy the index as an
attachment. The manifest records its original filename even though its content
is now in `initial-request.md`.

For a standalone readable text file, use the same generated structure, name the
source file in the manifest, and place its verbatim contents in `Inbox body`.
For a standalone non-text file, preserve it beneath `attachments/`, include it
in the manifest, and generate an empty or explanatory `Inbox body` without
printing binary content.

### CLI presentation

`inbox list` identifies each direct child of the inbox as one entry and reports
at least its opaque reference, derived title, and whether it is a file or
folder.

`inbox show` prints entry metadata, readable primary content when available,
and a resource manifest with relative paths and useful file metadata. It must
not emit arbitrary binary contents.

`inbox accept` creates the backlog item, generated request, and attachments;
removes the complete source file or folder only after success; and prints the
new work-item slug. Filesystem entry references may use the direct child's
filename or folder name, while the abstract model treats the reference as an
opaque store-provided handle.

### Status retirement

Remove `inbox` from the formal work-status enum and legal transitions. Starting
and dropping formal work items become backlog-only operations. Update the CLI,
filesystem store, web viewer, tests, README, work capability ledger, and
`tcw-work` skill anywhere they currently present inbox as a work-item status.
Keep `docs/work/inbox/` as the raw intake location and inter-node channel.

## Meta changes

This item captures an active brainstorm, not an implementation-ready design.
Keep it in backlog while the intake and attachment semantics are refined. Do
not start implementation merely because the MVP command names and the two
index-file failure cases are settled.

When planning resumes, include documentation tasks for the public CLI and
behavior changes in `README.md`, `docs/release-notes/upcoming.md`,
`docs/changelogs/upcoming.md`, and `skills/tcw-work/SKILL.md`, plus the matching
work capability descriptions. Apply the normal taxonomy/capability planning and
completion gates.
