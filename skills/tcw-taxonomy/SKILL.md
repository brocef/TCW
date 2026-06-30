---
name: tcw-taxonomy
description: Use when planning, seeding, or maintaining a project's registered language and feature registry — declaring Vocabulary terms, declaring Features that operate on vocabulary, linking related entries, federating shared vocabulary across repos, or bootstrapping a taxonomy from an existing codebase. Drives `tcw taxonomy`; the capabilities axis is tcw-capabilities, the work axis is tcw-work.
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
- **Run `tcw taxonomy check` after edits** — it validates extends aliases,
  taxonomy kinds, feature vocabulary refs, and every relatesTo / subject
  reference (cycles, dup aliases, dangling/ambiguous refs).

## Inheritance (federation)

Import another node's taxonomy so shared nouns mean the same thing everywhere:
`tcw taxonomy extends add <alias> <path>` (writes the `extends:` map; `rm <alias>`
drops it). The path is local and relative to this node — a sibling repo, or a
sibling project subfolder in the same repo (e.g. `../project-a`). Inherited terms
show in `list` flagged by origin and qualify as `<alias>/<slug>`; they can't be
removed locally. Remote git/URL sources are not yet supported (local paths only).

## Bootstrap (read on demand)

To seed a new or empty taxonomy from an existing codebase (deep-dive → draft →
refine with the user → write) → read [`docs/init.md`](docs/init.md).

## Quick reference

| Goal | Command |
|---|---|
| add vocabulary | `tcw taxonomy add "<Name>" [--parent <path>] [-s <slug>]` |
| add a feature | `tcw taxonomy add "<Name>" --kind feature --vocab <term> [--vocab <term>...]` |
| nest under a parent | `tcw taxonomy add "<Name>" --parent <path>` |
| link related terms | edit `relatesTo` in the term's `meta.yaml`, then `check` |
| browse / read / find | `tcw taxonomy list` · `tcw taxonomy show <path>` · `tcw taxonomy search <q>` |
| inherit another node's terms | `tcw taxonomy extends add <alias> <path>` · `… extends rm <alias>` (sibling repo or subfolder) |
| validate | `tcw taxonomy check` |
| remove a local term | `tcw taxonomy rm <path>` |
