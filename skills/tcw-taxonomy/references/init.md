# Bootstrap a taxonomy from an existing codebase

Seed `docs/taxonomy/` for a project adopting TCW. Four beats. Ground every step in
the actual repo; **do not invoke `superpowers:brainstorming`** — run the lightweight
refine loop below. Bootstrap both taxonomy entry kinds:

- **Vocabulary** — conceptual project terms.
- **Features** — user- or application-facing manifestations that operate on or
  involve vocabulary.

## 1. Ensure the tree exists
`tcw taxonomy init` if `docs/taxonomy/` is absent (no-op if present).

## 2. Inheritance
Ask the user: **"Does this project inherit its taxonomy from other repos?"**
- If yes, collect a list of sibling-repo paths. For each, derive an alias from the
  repo directory name, confirm it with the user, and run
  `tcw taxonomy extends add <alias> <path>`.
- You may also write other `docs/taxonomy/config.yaml` keys directly if bootstrapping
  additional adapter config — but `extends` always goes through the command.
- Run `tcw taxonomy check`.

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

- Vocabulary: `tcw taxonomy add "<Name>" [--parent <path>]` (pipe the
  description on stdin).
- Features: `tcw taxonomy add "<Name>" --kind feature --vocab <term> [--vocab <term>...]`
  (pipe the description on stdin).

Finish with `tcw taxonomy check` and show the resulting `tcw taxonomy list`.
