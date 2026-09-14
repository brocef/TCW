# Curate taxonomy and capabilities documents in Obsidian

> **Not finalized.** This is a scratchpad, not a settled request. It records how
> TCW *would* support Obsidian **if** the project decides to — nobody has decided
> that yet. Nothing here is committed to: not the scope, not the constraints, not
> the boundary between what Obsidian edits and what TCW manages. Treat every
> statement below as a starting position to argue with rather than a requirement
> to satisfy, and expect it to be rewritten before `spec` runs. The item exists so
> the thinking is not lost, not because the work is agreed.

## What is being asked for

A project that keeps its taxonomy and capabilities in TCW should be able to open
those documents in [Obsidian](https://obsidian.md) and work on them there
natively — reading them, navigating between related entries, and **editing their
contents in place**, with the edits landing in the canonical TCW store rather
than in a copy.

"Natively" is the operative word. The ask is not for an export, a preview, or a
published site. It is that Obsidian, pointed at the project, behaves the way it
does for any vault a person writes by hand: entries have names, related entries
are linked and reachable, and typing in the editor changes the real document.

## Why

Taxonomy and capabilities are the two axes that **should be curated by humans,
not by an agent.** They are a project's registered language and its statement of
what a user can do — judgement calls about meaning and scope, not code. TCW's
existing surfaces are built for a terminal and for agents: `tcw taxonomy show`
reads one entry at a time, and nothing puts the relationships between entries in
front of a person. Obsidian is a mature, pleasant, human-facing editor for
exactly this kind of linked prose, and the requester wants curation to happen
somewhere that invites it.

The relationships already exist and are already dense — in this repository, 30
taxonomy entries and 86 capabilities, wired together by `relatesTo`,
`vocabulary`, `Subject` and `Feature`, plus 48 `tcw://` references written into
prose. None of that is currently visible as a graph to anybody.

## Scope of the edit

**Obsidian edits contents. TCW manages everything else.**

The bodies of taxonomy and capability documents are what a curator writes in
Obsidian. Metadata and any other non-Markdown data — an entry's fields, status,
subjects, feature associations, federation wiring — stay managed through the
`tcw` CLI as they are today. This is a division of responsibility, not a lock:
nothing stops a person from hand-editing a YAML file, and nothing is expected to
prevent them.

The requester was explicit that this is the boundary, so a solution that
requires curators to maintain metadata through Obsidian is not what was asked
for.

## Navigation is wanted; querying is undecided

Navigation is the request: naming entries, linking related ones, moving between
them, seeing what points at what.

Whether the requester also wants to **query** the axes from inside Obsidian —
live tables along the lines of "every capability whose status is Missing", which
Obsidian's ecosystem builds from YAML frontmatter inside each Markdown file — is
**not known**. It was not raised in the conversation the request came from, and
the requester has not been asked. It is recorded here as an open question rather
than as a want, because the answer pulls directly against the scope boundary
above and `spec` should put it back to the requester before resolving it either
way.

## Constraints

- **Only taxonomy and capabilities.** See "Out of scope".
- **Metadata stays TCW-managed**, per "Scope of the edit".
- **A project that does not use Obsidian must be unaffected.** No new required
  configuration, no behavior change, nothing new to learn.
- **`tcw serve` is not being changed, and is not expected to understand
  Obsidian's syntax.** The requester's position is that the two are alternative
  front ends and a project picks one: a project that uses Obsidian should use
  Obsidian. Whatever a curator writes there need not render in the local web app.
- Both harnesses matter. Anything guaranteed here lives in the `tcw` CLI, which
  behaves the same under Claude and Codex.

## Out of scope

**The work axis.** Work artifacts are not meant to be pretty, and a completed
work item is archived or deleted outright depending on configuration, so
Obsidian's navigation and graph features have little to offer them. The
requester ruled this out explicitly, with the qualifier "at least not for now" —
so it is a deferral, not a permanent boundary.

## References

Asked; none provided.

The request reached this repository through an **informal conversation**: a
person interested in the plugin asked for it, and the requester relayed it. There
is no issue, thread, or written statement from the original requester, so their
own words are not available and their intent is secondhand throughout this
document. `spec` should treat the reasoning above as the relaying requester's,
and should not assume the original asker's mental model of TCW.

No prior art was nominated. Tools that keep a structured store legible to
Obsidian-style editors exist (Foam, Dendron, Quartz, and Obsidian community
plugins that front other structured data), and `spec` may find them worth
examining, but none was pointed at.

## Notes

Three observations from the codebase, recorded because they bear on whether the
request is already satisfied. They are findings, not a proposed solution.

1. **The write-back the request asks for already exists in one direction.** Entry
   bodies are stored as plain Markdown at `description.md`, with no frontmatter
   in any of the 116 files in this repository. A person who opens one of those
   files in Obsidian today and types into it has already edited the canonical
   store. No import, synchronization, or conflict resolution stands between
   Obsidian and TCW for body text.

2. **What is missing is not the round trip but the vault.** Obsidian names a note
   by its filename, and every entry's body file is named `description.md`, so a
   vault opened on the store presents 116 identically-named notes. The
   relationships are held in `meta.yaml`, which Obsidian does not read, and the
   `tcw://` references in prose are not links Obsidian can follow. Nothing is
   navigable, which is the substance of the ask.

3. **Two behaviors will collide with Obsidian's, and `spec` should decide about
   both rather than discover them.** First, a federated entry's local file is a
   **body delta**, not a body: `FsCapabilitiesStore` composes an inherited
   capability as prepend + (local body if present, else upstream body) + append
   (`tcw/store/fs.py:2329`), so a curator editing an inherited entry in Obsidian
   is editing a fragment while appearing to edit the whole. Second, Obsidian
   rewrites links automatically when a note is renamed or moved — but an entry's
   folder path **is** its slug and its `tcw://` identity, so a curator
   reorganizing their vault would re-identify entries underneath the references
   that point at them.

Assumption marked for `spec`: the requester's answers here describe a single
coherent piece of work. If closing the navigation gap turns out to require a
change to how bodies are stored, that may be larger than one item, and saying so
is cheaper before a spec is written than after.
