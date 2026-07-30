# Plan: untrack resolved work, scrub private repository references

Ordering rationale: the code fix lands **before** this repo's own `.gitignore`
changes, because the moment `completed/` is ignored, the very next
`tcw work complete` — including this item's own — depends on the fix being in
place. Tasks 1–2 are the risky pair and carry the test; task 3 is the
irreversible-ish index change; task 4 is independent prose.

## 1. Test first: a transition into an ignored destination

**Changes** `tests/test_work_autocommit.py` — one new test. Its `node()` helper
builds a `tmp_path` repo; write a `.gitignore` containing `completed/` into it,
commit that, create and `start` an item, then `complete(slug, "done", [])`.

Assert: the folder exists at `docs/work/completed/<slug>`; `git ls-files
docs/work/completed` is empty; `git status --porcelain` is empty; the commit
count increased.

**Verified by** `pytest tests/test_work_autocommit.py -k ignored` — red before
task 2, green after.

## 2. Make `git_mv` ignore-aware

**Changes** `tcw/store/fs.py` — add `git_ignored(node_root, path)` beside the
other git helpers, and a branch at the top of `git_mv`: when the destination is
ignored, `git rm -rq --cached --ignore-unmatch -- <src>` then `shutil.move`,
returning before `git mv`. `shutil` is already imported (`fs.py:17`). Leave
`_commit_transition` and `git_commit_result` alone — `_has_committable_changes`
already drops a pathspec git has nothing for.

Comment the branch with *why* (`git mv` ignores `.gitignore` for its
destination), since the code reads as a pointless special case without it.

**Verified by** `pytest tests/test_work_autocommit.py` — the new test green and
the five existing `test_every_transition_commits_its_own_move` cases unchanged
(their repos ignore nothing, so they exercise the untouched path).

## 3. Ignore and untrack this repo's resolved work

**Changes** `.gitignore` — append `docs/work/completed/` and
`docs/work/discarded/` under the "Local artifacts" group. Then
`git rm -r --cached --quiet docs/work/completed docs/work/discarded`.

**Verified by** `git check-ignore -q` on both paths exits 0; `git ls-files` on
both prints nothing; the folders and their contents are still on disk; and
`tcw work list --all | wc -l` matches its pre-change count.

## 4. Scrub the private project name

**Changes** the four tracked files carrying it: `docs/plan/phase-5-work.md`,
`docs/plan/phase-6-beyond.md`, and the `initial-request.md` of the two
`2026-07-29-*` backlog items. Read each in context and substitute a neutral
equivalent; in the two backlog items the name appears inside quoted repro
material, so keep the substituted names internally consistent across the
example or the repro stops making sense.

**Verified by** a case-insensitive grep for the name across `git ls-files`
output returning nothing, and re-reading each edited passage for sense.

## Documentation Sync

Evaluated against `CLAUDE.md`; run as one block after tasks 1–4, over the
finished diff.

- **`docs/changelogs/upcoming.md`** `[Any-Code-Change]` — **fires.** A `Fixed`
  entry: transitions into a gitignored destination no longer track the
  destination.
- **`docs/release-notes/upcoming.md`** `[Public-API]` — **fires.** Plain-language
  note that a node can gitignore `completed/`/`discarded/` and TCW will honor it.
- **`skills/tcw-work/SKILL.md`** `[Skill-Driven-Component]` — **fires**, in
  `references/transitions.md`: one line under the auto-commit paragraph saying an
  ignored destination is untracked rather than moved. The router itself needs no
  change.
- **`README.md`** `[Public-API]` — **does not fire.** No CLI surface changes: no
  new command, flag, or output. Behavior only shifts for a node that has already
  chosen to ignore a status folder.

## Verification

Beyond the suite:

- `tcw validate` exits 0 (the new capability resolves, `tcw://` links in
  `spec.md` resolve).
- Manual, on this repo, at completion: `tcw work complete` on **this item** is
  the real end-to-end proof — it is the first completion into the newly ignored
  folder. Confirm afterwards that `git status --short` is clean, the item sits
  at `docs/work/completed/<slug>` on disk, and the transition commit records
  deletions rather than a rename.
- `tcw capabilities set work/keep-resolved-work-out-of-git --status Supported`
  before `complete`, or its gate refuses.
