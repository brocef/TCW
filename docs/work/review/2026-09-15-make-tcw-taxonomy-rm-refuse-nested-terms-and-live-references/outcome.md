# Outcome: Make tcw taxonomy rm refuse nested terms and live references

## What shipped

1. **Refusal** — `aaa201bf`. `FsTaxonomyStore.remove` refuses a term with nested
   terms, or one another local term's `relatesTo` or Feature `vocabulary` resolves
   to (compared by folder identity; self-references ignored), and a local spelling
   that is not the listed slug. `relators()` and the CLI's post-removal warning are
   gone; `TaxonomyStore.remove` documents the contract. Six new tests in
   `tests/test_taxonomy.py`; `tests/test_non_git_writes.py` reads `_referrers`
   instead of `relators`.
2. **Docs** — `25119c68`: README row, `skills/taxonomy/SKILL.md`, CLI scenario 08
   assertion 7, `taxonomy/remove-a-local-term` capability, changelog, release note
   (stated as a behaviour change); `capabilities.yaml` declares the capability.
3. **Review fixes** — `8fb0c0b0`:
    - nested terms are asked of git (`ls-files` under the folder), not the disk: a
      folder holding only untracked files (a `.DS_Store` left in a removed child's
      folder) deleted nothing and blocked its parent with a "term" no `rm` could
      reach;
    - `vocabulary` counts only on a Feature, the one kind `check` reads it on;
    - a folder that vanishes mid-check is not a match instead of a crash; the
      helper is now shared with `FsCapabilitiesStore._referrers` (`_same_folder`).

## Evidence

- Tests red before code: the nested, `relatesTo`, `vocabulary` and spelling cases
  (the same-leaf and self-reference tests first failed on test setup — hand-written
  terms were not staged, so `git rm` refused — fixed by staging); then the three
  review-fix tests.
- Mutation checks, each turning its test red: no nested check; no referrer check;
  `vocabulary` not read; self-reference counted; leaf-name match instead of identity;
  no spelling guard; `vocabulary` read on every kind; vanished folder raising; a disk
  walk instead of git.
- Hands-on (installed CLI, scratch project): `rm admin` with `admin/permission`
  refused naming it; `rm invoice` referenced by a feature refused naming
  `pdf-export (vocabulary)`; removals in the right order all succeed and `check` is
  OK. The reviewer's `.DS_Store` reproduction now removes the child, then the parent.
- Full suite at `79bef735` (before review fixes): 3625 passed. After review fixes,
  at `4c099f78`: 3628 passed.

## What the plan or spec got wrong

- **"Walk the folder itself" was the wrong rule for nested terms.** It copied
  capabilities' reasoning ("`git rm -rf` would delete all the same") without checking
  it: git deletes only what it tracks. Found by review.
- **The spec said `vocabulary` generally** while `check` reads it only on Features.
- **The spec said the refusal reaches the web app**; there is no taxonomy delete
  route, so the CLI is the only caller today.

## Autonomous decisions

Run unattended under `autonomous-work`; these replace the human checkpoints.

- **Refuse on a Feature's `vocabulary` as well as `relatesTo`?** Codex: yes — same
  store, same resolution, and leaving it out keeps `check` failing after a successful
  `rm`. Opus: yes, and put the refusal in the store, deleting `relators`. Chose yes.
- **Refuse on capabilities naming the term (`Subject`, `Feature`)?** Both: no
  (option C1) — a cross-store dependency the taxonomy store does not have; a CLI-only
  check leaves other callers unprotected; warning-only restores what the maintainer
  rejected. Chose no; filed
  `2026-09-17-tcw-taxonomy-rm-does-not-check-capabilities-that-name-the-term`.
- **Count references from inherited taxonomies?** Both: no — local terms only, as
  `check` and capabilities' `_referrers` do. Chose no.
- **Advisors' implementation cautions adopted:** compare by resolved folder identity
  (not `relators`' leaf match); exact listed spelling; skip self-references.
- **Code review findings accepted:** untracked leftover folders blocking removal
  (now asked of git); `vocabulary` on non-Features; unwrapped `samefile`; sharing the
  same-folder helper with capabilities.
- **Code review findings deferred or rejected:** non-string or scalar `relatesTo`
  crashes and malformed `meta.yaml` (pre-existing, affect `check` equally — not
  filed, already reachable through `check`); an extends alias whose store path points
  back into this project (contrived, not filed); refusal message naming how to edit
  `relatesTo` (no CLI command exists to name — skipped).
- **Verifier note: an unstaged hand-written child does not block its parent**, which
  then still lists after "Removed term". Not a regression; filed
  `2026-09-17-tcw-taxonomy-rm-reports-removed-while-an-unstaged-child-keeps-the-term-listed`.
- **Verify decision:** accept. Verifier: criteria 1-7 met, including the review
  fixes; criterion 8 met by the 3628-test run.
- **Interruption:** the machine crashed during the first code review; it was rerun.
