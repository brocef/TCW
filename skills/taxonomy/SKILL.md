---
name: taxonomy
description: Drives `tcw taxonomy` — the Taxonomy axis of TCW (the registered Vocabulary + Feature registry). Use when declaring or maintaining a project's registered language and features. The capabilities axis is the `capabilities` skill, the work axis the `work` skill.
when_to_use: Use when planning or maintaining a project's registered language and feature registry — declaring Vocabulary terms, declaring Features that operate on vocabulary, or linking related entries.
allowed-tools: Bash(tcw *), Read, Grep, Glob
metadata:
    author: Brian Cefali
license: Apache-2.0
dynamic_skill: false # which skills a project may override, and why: ../README.md
---
**Version check.** Under Claude Code, skip this: the session-start hook already ran it. Under any other harness, once per session before your first `tcw` command, run `bash "<plugin>/scripts/check_versions.sh"`, where `<plugin>` is two folders above the folder holding this `SKILL.md`, and pass on anything it prints to the user.

# The taxonomy process

**What it is:** the taxonomy axis is the project's registered language and
feature registry. It has two entry kinds:

- **Vocabulary** — the canonical conceptual terms a project reasons about.
- **Feature** — the user- or application-facing manifestations that operate on
  or involve vocabulary terms.

It is the first layer in the TCW chain: `Vocabulary -> Features -> Capabilities
-> Work`. It exists so the other axes point at shared, unambiguous entries
instead of re-defining words: capabilities can name a loose **Subject** and a
strong **Feature**, and work references taxonomy entries. The pointers are
one-directional — **taxonomy never points back** at capabilities or work.

Drive `tcw taxonomy`; never hand-edit entry markdown when a command applies. Read
with `list` / `show` / `search`; create with `add`; remove a local term with
`rm`; `tcw validate` checks the tree with the rest of the project. The
capabilities axis is **REQUIRED SUB-SKILL: Use the `capabilities` skill**.

**The taxonomy tree is not necessarily `docs/taxonomy`.** `taxonomy.path` in
`tcw-config.yaml` can put it anywhere, and a `taxonomy.repository` block can put
it in another repository entirely, fetched here by `tcw project provision`. So never
compose a store path from the project root — ask `tcw taxonomy path`. A command
that needs a declared but missing tree fails, names where it lives, and tells
you to run `tcw project provision`; do not work around that by running `tcw project new`,
which would create a second, empty tree beside the real one. A malformed
`taxonomy.repository` fails the same way and names the offending config line.

Use `tcw taxonomy path` when an agent needs the absolute, resolved filesystem
store folder. Because `path` is reserved as that command, read a term literally
named `path` with explicit `tcw taxonomy show path`.

`Term.modified` is read-only, adapter-provided presentation metadata for
viewers; it is not an editable taxonomy field.

> **Web editing:** Taxonomy entries can also be created and edited through the
> local `tcw serve` web app; check failures are surfaced in the UI.

## Terms change with the code

A work item that adds, changes or removes terms or Features declares them in
the spec, under `taxonomy:` in the item's `capabilities.yaml` (the `capabilities`
skill shows the file). **Implement changes the taxonomy in the same change as
the code**, with `tcw taxonomy add` and `rm`, so the records say what the code
does by the time review reads them. The move out of implement checks every
declared term: a `new` or `changed` one present, a `removed` one gone.

## Judgment

- **One entry per distinct concept or feature.** A near-synonym or merely-related concept is a
  `relatesTo` link (in the term's `meta.yaml`), not a second term.
- **Choose Vocabulary vs Feature deliberately.** Vocabulary is conceptual
  language; Feature is how users or applications interact with that language.
  Users do not interact with vocabulary directly — they interact through
  features.
- **Features list vocabulary.** Create feature entries with `--kind feature` and
  repeat `--vocab <ref>` for each vocabulary term they operate on or involve.
  A `<ref>` is a term path (`admin/permission`), an `<alias>/<path>` into an
  inherited taxonomy, or a **leaf slug unique across the local tree** — a unique
  leaf slug is accepted and stored as its full path. `add` **refuses** a ref that
  does not resolve, one that is ambiguous, and one that points at a Feature, and
  it refuses a Feature carrying no `--vocab` at all; a refused `add` writes
  nothing and exits non-zero. **So register vocabulary before the features that
  name it** — the ordering is now load-bearing. The leaf-slug convenience is
  write-time only: `tcw taxonomy show <ref>` and `rm <ref>` stay path-addressed,
  which is why what gets stored is the path.
- **Entries stay inside their own store.** A ref is joined onto the store root,
  so a symlink planted inside the store would otherwise carry it out. Every
  lookup, listing, write and validation resolves the path first and refuses one
  that lands outside — and the same holds for the files _inside_ an entry, so an
  entry whose `meta.yaml` or `description.md` is a symlink out is not read. Such
  an entry does not resolve, does not appear in `list`, and cannot be written
  to; a stored ref of that shape reports as **dangling**. Inheriting from a
  parent project (below) is the supported way to reference another project.
- **Stop at the registry boundary.** A taxonomy Feature names the interaction
  area; it does not describe behavior, acceptance criteria, support status, or
  user stories. Put those details in capabilities.
- **Nest specializations** under a parent: `tcw taxonomy add <Name> --parent <path>`
  (`--slug` to override the leaf slug, which must already be a slug:
  lowercase words joined by single hyphens, never a `/`, or it is refused with
  exit 2; the description piped on stdin). Reading
  stdin is bounded: nothing piped adds the term with no description and warns,
  and a stream that stalls part-way is refused rather than stored truncated
  (`TCW_STDIN_TIMEOUT` sets the bound).
- **Keep descriptions short** — one or two sentences of what the noun means here.
- **Run `tcw validate` after edits** — it checks taxonomy kinds, feature
  vocabulary refs, every relatesTo / subject reference (dangling refs), and
  that a term overriding nothing is complete (below).
- **Cross-reference in prose with `tcw://` links** — a term description may link
  to another object with `[text](tcw://T/<slug>)` (or `C`/`W`, and an
  `<project-id>/`-prefixed namespace for inherited terms). `tcw validate` resolves
  those links across the project and the `tcw serve` viewer makes them clickable.

## Inheritance

A project inherits the taxonomy of every parent whose `inherit` includes
`taxonomy`, through every level: a parent's own parents are inherited too,
without being listed. The parent links are configured under `parents:` in
`.tcw/tcw-config.yaml`, which the configure skill's reference on projects
explains; there is no taxonomy command for it. An inherited term is read by its
path like one of the project's own, and its full identifier
(`<project-id>.taxonomy/<path>`) names the project it belongs to.

**Overriding an inherited term.** To change an inherited term, the project puts
its own term at the same path, holding only what it changes; nothing else marks
it as an override. The two are combined field by field, and a list field
(`relatesTo`, `vocabulary`) is replaced whole. `tcw taxonomy add` at an
inherited path writes such an override, holding only what differs from the
inherited term, and says on standard error what it overrides; it is refused
when nothing given differs. `tcw taxonomy rm <path>` removes the override and
says what the path shows afterwards. The JSON records carry `overrides` (the
full identifier of the term overridden, or `null`), and `show` prints an
`overrides:` line.

A term that overrides nothing must be complete — a name and a `description.md`,
which may be empty — or `tcw validate` reports it; that is how an override whose
original was moved or removed is caught. When two parents that do not inherit
from each other both have a term at one path, the one that comes later in the
project's load order (the order in which TCW reads its parents) is used whole,
with a warning; a complete term of the project's own at that path settles it.

**When a parent is not on this machine.** `tcw taxonomy list`, whose default
`--scope own` lists only the project's own terms, and `show` of one of them
still work: each JSON record read that way has `"partial": true` and no
`overrides` key, since what it overrides is not known. The commands that need
the inherited terms (`list` and `search` with `--scope up`, `add`, `show` of an
inherited term) stop with exit code 7.

## Starting a taxonomy

To seed a new taxonomy from an existing codebase, use the `setup` skill.

## Quick reference

| Goal                            | Command                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| add vocabulary                  | `tcw taxonomy add "<Name>" [--parent <path>] [--slug <slug>]`                                                                                                                                                                                                                                                                                  |
| add a feature                   | `tcw taxonomy add "<Name>" --kind feature --vocab <ref> [--vocab <ref>...]` — a path, an `<alias>/<path>`, or a unique leaf slug; refused if it does not resolve                                                                                                                                                                               |
| nest under a parent             | `tcw taxonomy add "<Name>" --parent <path>`                                                                                                                                                                                                                                                                                                    |
| link related terms              | edit `relatesTo` in the term's `meta.yaml`, then `tcw validate`                                                                                                                                                                                                                                                                                |
| browse / read / find            | `tcw taxonomy list` · `tcw taxonomy show <path>` · `tcw taxonomy search <q>`                                                                                                                                                                                                                                                                   |
| locate the filesystem store     | `tcw taxonomy path` — prints only the absolute, resolved store folder                                                                                                                                                                                                                                                                          |
| inherit another project's terms | name it under `parents:` with an `inherit` that includes `taxonomy` (the configure skill's projects reference); no taxonomy command                                                                                                                                                                                                            |
| override an inherited term      | `tcw taxonomy add "<Name>" [--parent <path>]` at the inherited path — writes the project's own term there, holding only what differs; `tcw taxonomy rm <path>` removes it                                                                                                                                                                      |
| read without a parent present   | `tcw taxonomy list` · `show <own path>` — records marked `"partial": true`; commands needing inherited terms exit 7                                                                                                                                                                                                                            |
| validate                        | `tcw validate` (the whole project: YAML, `tcw://` links, every axis's checks)                                                                                                                                                                                                                                                                  |
| remove a local term             | `tcw taxonomy rm <path>` — refused while a term is nested under it, another local term names it in `relatesTo` or a feature's `vocabulary`, one of the project's own capabilities, an override included, names it in `Subject` or `Feature` (or the capabilities cannot be read); fix those first. Every other file in its folder goes with it |
