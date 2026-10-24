# Bootstrap a taxonomy from an existing codebase

Seed `docs/taxonomy/` for a project adopting TCW. Four beats. Ground every step in
the actual repo; **do not invoke `superpowers:brainstorming`** — run the lightweight
refine loop below. Bootstrap both taxonomy entry kinds:

- **Vocabulary** — conceptual project terms.
- **Features** — user- or application-facing manifestations that operate on or
  involve vocabulary.

## 1. Ensure the tree exists

`tcw project new taxonomy` in the project's folder if `tcw taxonomy path` fails (it does nothing if the tree exists).

## 2. Inheritance

Ask whether this project inherits taxonomy from another TCW project, its
parent. If it does, name that project under `parents:` in
`.tcw/tcw-config.yaml`, with an `inherit` that includes `taxonomy` (a parent
named by its ID alone passes everything; the configure skill's reference on
projects explains the declaration), then continue. This project's features
can then name the parent's terms, so the draft below leaves out every term the
parent already has: `tcw taxonomy list --scope up` lists them, while a plain
`tcw taxonomy list` shows only this project's own entries.

## 3. Deep-dive (draft)

Survey the codebase for two related drafts:

- **Vocabulary candidates:** core models/entities, ubiquitous-language terms,
  bounded-context or module names, key value objects. **Skip generic framework
  nouns** (Controller, Service, Request) unless they carry domain meaning.
- **Feature candidates:** interaction areas, workflows, screens, APIs, commands,
  or system behaviors where users/applications touch the vocabulary. A feature
  should name the interaction area only; do not put capability details,
  acceptance criteria, support status, or user stories in taxonomy.

Produce a draft forest with each vocabulary entry's one-line description and
proposed parent. Then list proposed features with a one-line description,
proposed parent if any, and the vocabulary refs each feature operates on or
involves.

## 4. Refine + write

Present the draft. Run a lightweight loop with the user — add / cut / rename /
merge / re-nest / split vocabulary from feature — until they're satisfied. Then
write the agreed entries:

**Write all vocabulary first, then the features.** This ordering is a
requirement, not a convention: `add` refuses a `--vocab` ref that does not
resolve yet, so a feature written before the vocabulary it names fails and
writes nothing.

- Vocabulary: `tcw taxonomy add "<Name>" [--parent <path>]` (pipe the
  description on stdin).
- Features: `tcw taxonomy add "<Name>" --kind feature --vocab <ref> [--vocab <ref>...]`
  (pipe the description on stdin). A `<ref>` is the term's full identifier
  (`<project>.taxonomy/<path>`, the name every store keeps for it), its path in
  this project, or a leaf slug (the last part of its path) unique among the
  terms this project can see, its parents' included; whichever is given, the
  full identifier is what is stored.

Finish with `tcw validate` and show the resulting `tcw taxonomy list`.
