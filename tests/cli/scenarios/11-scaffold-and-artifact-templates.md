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
| 1 | `tcw work scaffold spec $SLUG` writes `spec.md` into the item folder and prints its **path on stdout** — usable as `$(…)` for a follow-on `$EDITOR`. |
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
| 13 | Scaffolding respects stage legality, or does not — pin whichever. (Scaffolding `outcome` on a `backlog` item: refused, or allowed as a draft?) |
| 14 | Whether the scaffolded draft is staged in git is a **known open question** (`2026-08-18-decide-whether-tcw-work-scaffold-should-stage-its-draft-in-git`). Assert and record the current behaviour without endorsing it. |

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

Assertions 13 and 14 are open questions. Answer them by observation, encode the
answer, and flag 14 to the user rather than deciding it in a test.
