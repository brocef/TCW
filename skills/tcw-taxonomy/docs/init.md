# Bootstrap a taxonomy from an existing codebase

Seed `docs/taxonomy/` for a project adopting TCW. Four beats. Ground every step in
the actual repo; **do not invoke `superpowers:brainstorming`** — run the lightweight
refine loop below.

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
Survey the codebase for candidate domain nouns: core models/entities, ubiquitous-
language terms, bounded-context or module names, key value objects. **Skip generic
framework nouns** (Controller, Service, Request) unless they carry domain meaning.
Produce a draft forest: each term with a one-line description and a proposed parent.

## 4. Refine + write
Present the draft. Run a lightweight loop with the user — add / cut / rename / merge /
re-nest — until they're satisfied. Then write the agreed terms:
`tcw taxonomy add "<Name>" [--parent <path>]` (pipe the description on stdin).
Finish with `tcw taxonomy check` and show the resulting `tcw taxonomy list`.
