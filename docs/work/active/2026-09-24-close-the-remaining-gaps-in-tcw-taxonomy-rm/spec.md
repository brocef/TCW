# Spec: close the remaining gaps in tcw taxonomy rm

## Capability changes

None: `tcw taxonomy rm` keeps its purpose; it refuses two more unsafe removals.

## Problem

`FsTaxonomyStore.remove` (`tcw/store/fs.py:2237-2272`) refuses a git-tracked
nested term and a local `relatesTo`/`vocabulary` referrer, then `git rm -rf`s the
folder.

1. **Capabilities are not asked.** A local capability naming the term in
   `Subject` or `Feature` does not stop the removal; `tcw capabilities check`
   then fails.
2. **The listing and the refusal disagree about children.** The listing counts
   every readable folder under the store as a term (`_local_slugs`,
   `fs.py:2125-2150`, via `_node_readable`), with or without a `meta.yaml`. The
   refusal asks git (`ls-files`). A child written by hand and never staged, or a
   leftover folder holding only untracked junk, survives `git rm -rf`, so `rm`
   prints "Removed term zed" while `zed` still lists. A term whose own
   `meta.yaml` was never staged makes `git rm` fail with git's raw error.

## Goals

1. `remove` refuses when a local capability's `Subject` or `Feature` resolves to
   the term (by folder identity, as `_referrers` does), listing
   `<capability> (Subject|Feature)`. The rule is stated in the abstract
   `TaxonomyStore.remove` contract, so every caller — CLI, web app — gets it.
2. The node's capabilities store is found by the normal resolution (not a
   hard-coded folder). None there: no capability check. Present but unable to
   open, or unreadable while listing: the removal is refused with that reason
   (fail closed — the check cannot be made). A broken capabilities `extends` is
   such a reason.
3. *(Revised during implementation — see `outcome.md`.)* Before anything is
   removed, `remove` refuses when any file under the term is not tracked by git,
   naming it and the way out: "`git add` it (`git add -f` if ignored) and remove
   it first, or delete it". Operating-system metadata files (`.DS_Store`,
   `Thumbs.db`, `desktop.ini`, named exactly) do not block: they are deleted
   with the term, so a folder holding only them stops listing too.
4. A term whose own files are not tracked is refused with a clear message.
5. After `git rm`, the term must no longer list; if it still does, `remove`
   raises rather than reporting success.

## Non-goals

- Capabilities in other nodes that inherit this taxonomy through `extends`.
- Changing what the listing counts as a term.

## Acceptance criteria

1. A local capability with `Subject: [zed]` → `tcw taxonomy rm zed` exits 1 naming
   the capability; `zed` still lists. Same for `Feature: zed`.
2. A capability naming another term, or none → `rm zed` succeeds.
3. `capabilities.path` pointing nowhere → `rm zed` exits 1 with that reason, and
   nothing is removed. A node with no capabilities tree → `rm` works as before.
4. An unstaged `zed/kid/meta.yaml`, or a stray `zed/notes.md` or
   `zed/kid/notes.md` → `rm zed` exits 1 naming it and the way out; nothing
   removed. `zed/.DS_Store` and a `zed/kid/` holding only `Thumbs.db` → `rm zed`
   succeeds and neither `zed` nor `zed/kid` lists (keeping
   `tests/test_taxonomy.py`'s leftover-folder test passing).
5. `zed/meta.yaml` never staged → exit 1, a TCW message, not git's.
6. The web app's term DELETE refuses case 1 too.
7. Full suite passes.

## Risks

- A stray untracked file under a term now blocks its removal where it used to
  be silently left behind (keeping the term listed). The message names it.
- Deleting the three named OS metadata files is the one place `rm` deletes
  something git does not track; they are recreated by the OS on demand.

## Notes

- Decisions from two advisors (Codex, Opus), both: fail closed, adapter-side
  check with the contract in the abstract store, judge children by the
  listing's folder set. See `outcome.md`.
