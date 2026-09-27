# Outcome: close the remaining gaps in tcw taxonomy rm

## What shipped

- **Code** — `d48ee853`: `FsTaxonomyStore.remove` (`tcw/store/fs.py`) refuses a
  term whose own files git does not track; refuses, before any write, when a
  file under the term is untracked (`_untracked_under`), except the named OS
  metadata files (`OS_METADATA_FILES`: `.DS_Store`, `Thumbs.db`, `desktop.ini`),
  which are deleted with the term; refuses when a local capability's Subject or
  Feature names the term (`_capability_referrers`), failing closed when the
  capabilities cannot be read; raises if the term still lists after `git rm`.
  The abstract `TaxonomyStore.remove` contract states the new refusals.
  Tests: `tests/test_taxonomy_rm_gaps.py`.
- **Docs** — `f2442ca0`: `skills/taxonomy/SKILL.md`, changelog, release notes.
- **Review fold-in** — `a56bd549`: symlinks compared as themselves; a malformed
  capability worded as the capabilities check; `FsCapabilitiesStore._term_refs`,
  one definition of a capability's term references, shared with `check`.

## Tests

- New tests failed on the old code for the stated reasons (the reviewer
  confirmed 9 of 11 on an extracted copy; the 2 that pass are guards); the
  review fold-in's three tests failed on the commit before it.
- `tests/test_taxonomy_rm_gaps.py`, `test_taxonomy.py`, `test_capabilities.py`,
  `test_capabilities_rm.py`: 178 passed — including `test_taxonomy.py`'s
  leftover-`.DS_Store` test from an earlier item.
- Full suite on the final code: see `refined-outcome.md`.
- Hands-on with the worktree's `tcw`: a capability with `Subject: zed` →
  refused naming it; an unstaged `zed/kid/meta.yaml` → refused naming it and the
  way out; `zed/.DS_Store` only → "Removed term zed", and `tcw taxonomy list` is
  empty.

## What the plan or spec got wrong

- **Criterion 4 was revised mid-implementation.** It said a child folder holding
  only `.DS_Store` must refuse the parent's removal. That contradicts an earlier
  item's deliberate test (a leftover `.DS_Store` must not block its parent), and
  the first implementation also let `git rm` run before failing on a leftover
  in the term's own folder — an error after a half-removal. Now every untracked
  file is found before anything is touched; OS metadata files go with the term.
- **Criterion 6 assumed a web-app term DELETE route**; there is none. The guard
  is in the store, tested directly.
- The spec referred to this outcome before it existed; this is it.

## Documentation Sync

| Entry | Fired? | Done |
| --- | --- | --- |
| `README.md` | Checked, no | Its `rm` line ("nothing refers to") still holds. |
| `docs/guide/jira.md` | No | — |
| `docs/guide/<topic>.md` | Checked, no | No guide lists `taxonomy rm`'s refusals. |
| `docs/release-notes/upcoming.md` | Yes | Two lines. |
| `docs/changelogs/upcoming.md` | Yes | Two Fixed entries. |
| `skills/<component>/SKILL.md` | Yes | `skills/taxonomy/SKILL.md` command table. |
| `skills/configure/references/` | No | — |

## Autonomous decisions

Run unattended on 2026-09-26 (`extras-autonomous-work`).

- **Capabilities store present but unreadable: fail closed or warn? Check in the
  store or in callers?** Codex and Opus: fail closed; in the store, with the rule
  in the abstract contract. Both also said to judge children by the listing's
  own folders, not by `meta.yaml`. Chose all three.
- **An untracked leftover under a term: refuse everything (B) or delete OS
  metadata (A)?** Codex: B, and change the old test. Opus: A, because B as first
  built reported failure after `git rm` had run, and would make every folder a
  file browser opened unremovable. Chose A narrowed to three exact file names,
  with every other untracked file refused before any write — which also answers
  Codex's concern about a filename rule reaching a person's files.
- **Code review round 1** (adversarial-code-reviewer): NOT DONE — symlinks slipped
  past the pre-write check; a malformed capability escaped unlabeled; duplicated
  reference resolution. All fixed with tests. Its question — should a broken
  capabilities `extends` block every term removal? — kept as specified: the store
  cannot be opened without resolving `extends`, and failing closed was the
  advisors' choice. Filed the override gap as
  `2026-09-26-check-capability-overrides-for-taxonomy-references-in-capabilities-check-and-taxonomy-rm`.
  Not filed: a possible false refusal on a case-insensitive disk when git's and
  the disk's spelling differ (unverified, errs toward refusing).
- **Code re-review**: DONE, merge; each round-1 fix confirmed with new probes
  (symlinks to folders, tracked links, a node reached through a symlink).
- **Verify** (tcw:verifier): accept; all criteria met as revised (135 targeted
  tests; hands-on for each, symlink cases included). It asked that the rewritten
  criteria 3, 4 and 6 be approved: they were decided with both advisors, above,
  and are kept. Decision: accept.
