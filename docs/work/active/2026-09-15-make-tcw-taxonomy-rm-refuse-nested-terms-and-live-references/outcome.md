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
- Full suite at `79bef735` (before review fixes): 3625 passed. After review fixes:
  see `refined-outcome.md`.

## What the plan or spec got wrong

- **"Walk the folder itself" was the wrong rule for nested terms.** It copied
  capabilities' reasoning ("`git rm -rf` would delete all the same") without checking
  it: git deletes only what it tracks. Found by review.
- **The spec said `vocabulary` generally** while `check` reads it only on Features.
- **The spec said the refusal reaches the web app**; there is no taxonomy delete
  route, so the CLI is the only caller today.
