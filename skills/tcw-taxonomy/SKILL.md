---
name: tcw-taxonomy
description: Drives `tcw taxonomy` — the Taxonomy axis of TCW (the registered Vocabulary + Feature registry). Use when declaring or maintaining a project's registered language and features, federating shared vocabulary across repos, or bootstrapping a taxonomy from an existing codebase. The capabilities axis is tcw-capabilities, the work axis is tcw-work.
when_to_use: Use when planning, seeding, or maintaining a project's registered language and feature registry — declaring Vocabulary terms, declaring Features that operate on vocabulary, linking related entries, federating shared vocabulary across repos, or bootstrapping a taxonomy from an existing codebase.
allowed-tools: Bash(tcw *), Read, Grep, Glob
metadata:
    author: Brian Cefali
license: Apache-2.0
---

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
one-directional — **taxonomy never points back** at capabilities or work. See
`tcw-plugin` for the cross-skill map.

Drive `tcw taxonomy`; never hand-edit entry markdown when a command applies. Read
with `list` / `show` / `search`; create with `add`; validate with `check`; remove a
local term with `rm`. The capabilities axis is **REQUIRED SUB-SKILL: Use tcw-capabilities**.

`Term.modified` is read-only, adapter-provided presentation metadata for
viewers; it is not an editable taxonomy field.

> **Web editing:** Taxonomy entries can also be created and edited through the
> local `tcw serve` web app; check failures are surfaced in the UI.

## Judgment

- **One entry per distinct concept or feature.** A near-synonym or merely-related concept is a
  `relatesTo` link (in the term's `meta.yaml`), not a second term.
- **Choose Vocabulary vs Feature deliberately.** Vocabulary is conceptual
  language; Feature is how users or applications interact with that language.
  Users do not interact with vocabulary directly — they interact through
  features.
- **Features list vocabulary.** Create feature entries with `--kind feature` and
  repeat `--vocab <ref>` for each vocabulary term they operate on or involve.
- **Stop at the registry boundary.** A taxonomy Feature names the interaction
  area; it does not describe behavior, acceptance criteria, support status, or
  user stories. Put those details in capabilities.
- **Nest specializations** under a parent: `tcw taxonomy add <Name> --parent <path>`
  (`-s` to override the leaf slug; description inline or piped on stdin).
- **Keep descriptions short** — one or two sentences of what the noun means here.
- **Run `tcw taxonomy check` after edits** — it validates inherited project IDs,
  taxonomy kinds, feature vocabulary refs, and every relatesTo / subject
  reference (cycles, duplicate IDs, dangling/ambiguous refs).
- **Cross-reference in prose with `tcw://` links** — a term description may link
  to another object with `[text](tcw://T/<slug>)` (or `C`/`W`, and an
  `<project-id>/`-prefixed namespace for inherited terms). `tcw validate` resolves
  those links node-wide and the `tcw serve` viewer makes them clickable.

## Inheritance (federation)

Import another registered project's taxonomy explicitly:
`tcw taxonomy extends add <project-id>` (`rm <project-id>` drops it). The ID must
be reachable through the validated project graph; a connection alone does not
imply inheritance. `extends` is a list and the source project ID is the inherited
namespace (`<project-id>/<slug>`). Legacy alias/path maps fail closed.

## Bootstrap (read on demand)

To seed a new or empty taxonomy from an existing codebase (deep-dive → draft →
refine with the user → write) → read [`references/init.md`](references/init.md).

## Quick reference

| Goal                            | Command                                                                                                      |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| add vocabulary                  | `tcw taxonomy add "<Name>" [--parent <path>] [-s <slug>]`                                                    |
| add a feature                   | `tcw taxonomy add "<Name>" --kind feature --vocab <term> [--vocab <term>...]`                                |
| nest under a parent             | `tcw taxonomy add "<Name>" --parent <path>`                                                                  |
| link related terms              | edit `relatesTo` in the term's `meta.yaml`, then `check`                                                     |
| browse / read / find            | `tcw taxonomy list` · `tcw taxonomy show <path>` · `tcw taxonomy search <q>`                                 |
| inherit another project's terms | `tcw taxonomy extends add <project-id>` · `… extends rm <project-id>`                                        |
| validate                        | `tcw taxonomy check` (this tree) · `tcw validate` (whole node: YAML + `tcw://` links + all component checks) |
| remove a local term             | `tcw taxonomy rm <path>`                                                                                     |
