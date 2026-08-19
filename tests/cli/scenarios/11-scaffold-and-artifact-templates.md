# 11 — Scaffolding lifecycle artifacts from templates

`tcw work scaffold` writes a draft of an artifact from its template. It is the
one write path where a node's config can substitute a whole document.

## Functionality covered

- `tcw work scaffold <artifact> <slug>` and `--force`
- All artifact ids: `initial-request`, `spec`, `plan`, `outcome`,
  `refined-outcome`, `rework`, `post-mortem`, `intake`
- `work.lifecycle.artifacts` config: `blob:`, `file:`, and `when:` conditions
- The prompt-vs-artifact distinction for `{{tcw:documentation}}`

## What is tested

| # | Assertion |
| - | --------- |
| 1 | `tcw work scaffold spec $SLUG` writes **`spec.draft.md`** — *not* `spec.md` — into the item folder, and prints that path on **stdout**, usable as `$(…)` for a follow-on `$EDITOR`. The `.draft.` infix is the whole point: scaffolding produces a draft, and the artifact does not count as written until it is renamed. Assert the exact filename; an assertion on `spec.md` would be wrong **and** would mask the distinction. |
| 2 | The scaffolded file is non-empty and carries the built-in template's headings. |
| 3 | Re-running without `--force` is **refused** non-zero and does not overwrite; the existing content is unchanged byte-for-byte. |
| 4 | `--force` replaces it. |
| 5 | Every artifact id in the `--help` list scaffolds successfully — table-driven, so a newly added artifact with no template is caught. |
| 6 | An unknown artifact id exits non-zero and lists the valid ids. |
| 7 | A node binding `artifacts.spec: [{blob: "CUSTOM"}]` gets `CUSTOM` instead of the built-in — `artifacts:` is **first-match-wins**, so a bound template replaces rather than composes. |
| 8 | A `when: {tags: [bug]}` binding applies only to items carrying that tag; an item without it gets the built-in. Both branches asserted. |
| 9 | Two `when:` bindings where both match: the **first** wins, and the second's content is absent. |
| 10 | A `file:` template resolves relative to the node root; a missing file exits non-zero naming the path. |
| 11 | A `{{tcw:documentation}}` span inside an **artifact template** is written **verbatim**, token and all — substitution is a prompt-role behaviour. Asserted on a node that *does* configure documentation entries, so a passing test means "deliberately not substituted", not "nothing to substitute". |
| 12 | The same node's `tcw work stage plan` **does** substitute. Both in one scenario, because the pair is the contract. |
| 13 | Scaffolding **does** respect stage legality — measured. `tcw work scaffold outcome $SLUG` on a `backlog` item exits 1 with `'outcome' is written by the 'implement' stage, which is not legal for an item in 'backlog'; it runs in active`. Pair it with the same call succeeding once the item is `active`. |
| 14 | The scaffolded draft **is staged in git** — measured: `git status --porcelain` shows `A  …/spec.draft.md` immediately after scaffolding, with no commit. This is a **known open question**, not a settled design (`2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`). Assert the current behaviour so a future decision to change it is a visible test change rather than a silent one, and mark the assertion in the script as pinning-not-endorsing. |

## Refusals asserted

3, 6, 10, and whichever branch 13 turns out to be.

## Explicitly not covered here

The content quality of the built-in templates, which
`tests/test_repo_lifecycle.py` pins against this repo's own bindings.

## Notes for the implementer

Assertions 11 and 12 exist as a pair on purpose: `tcw work scaffold` has an
implicit built-in fallback path that bypasses the shared resolver, so the two
scaffold paths must be shown to agree. Test both — the configured-template path
*and* the unconfigured fallback path — with the token present in each.

Assertions 1, 13 and 14 are measured, not assumed — assertion 1 in particular
corrects an error in this document's first draft, which said `spec.md`. Take the
filenames from the CLI's own stdout rather than constructing them, and the same
goes for every other artifact id in assertion 5.

Assertion 14 pins a behaviour the project has not yet decided it wants. Say so in
the script, so nobody reads a passing test as an endorsement.
