# Outcome: untrack resolved work, scrub private repository references

All four plan tasks shipped, plus the Documentation Sync block. Suite green,
`tcw validate` exits 0.

## What shipped

### Task 1+2 — the test and the fix (`063ba02`)

Committed together rather than separately as the plan wrote them. The plan's own
ordering rule ("the suite is green at every commit boundary") forbids landing a
red test on its own, so writing the test first and committing it first are
different things. The test *was* written and run first, and it failed exactly as
predicted — `git ls-files docs/work/completed` returned the item's
`initial-request.md`, `state.yaml`, and `init`'s `.gitkeep` after a completion
into an ignored folder.

`tcw/store/fs.py`: added `git_ignored(node_root, path)` (a `check-ignore -q`
wrapper, false outside a repo) and a branch at the top of `git_mv` — an ignored
destination gets `git rm -rq --cached --ignore-unmatch -- <src>` plus
`shutil.move`, returning before `git mv`. The comment carries the *why*, since
without it the branch reads as an arbitrary special case.

`tests/test_work_autocommit.py`:
`test_a_transition_into_an_ignored_destination_untracks_instead_of_moving`.

**Correction to the plan.** Its test sketch was wrong. It had the test write
`.gitignore` and commit, but `init` (`fs.py:427`) drops a `.gitkeep` into every
status folder, and a file git already tracks stays tracked regardless of
`.gitignore` — so the `git ls-files` assertion would have failed even with the
fix in place. The test now performs the `git rm -r --cached` step in setup,
which is what a real node adopting the ignore has to do anyway, and what task 3
does to this repo. The spec's design was unaffected.

`_commit_transition` and `git_commit_result` were left alone, as specified: the
`_has_committable_changes` filter (`fs.py:288`) already drops a destination
pathspec git has nothing for. Confirmed in the passing test — no
"pathspec did not match" failure, and a clean tree afterwards.

### Task 3 — ignore and untrack (`23aca00`)

`.gitignore` gained `docs/work/completed/` and `docs/work/discarded/` under
Local artifacts, with a comment saying why. `git rm -r --cached` on both: 469
files, 33,687 lines out of the tracked tree, still on disk.

Verified: `git check-ignore -q` exits 0 for both; `git ls-files` on both prints
nothing; 74 completed and 7 discarded folders remain on disk; `tcw work list
--all` prints 94 lines before and after.

### Task 4 — the scrub (`1c89ee8`)

Four tracked files. Two are prose in `docs/plan/phase-5-work.md` and
`phase-6-beyond.md`, where the private name was a downstream consumer in the
Spec-4 migration paragraph — rewritten as "a downstream consumer" and "that
consumer's orchestrator repo", which reads better than the original anyway,
since the paragraph is about consumers generically.

Two are quoted GitHub-issue repro material in the `2026-07-29-*` backlog items,
where four related project ids had to stay mutually consistent for the repro to
parse: they became `example-app`, `example-server`, `example-shared`,
`example-mobile`.

**Not in the plan, and required:** both of those items carried a closing note
saying the quoted text "is the report as filed" / "has not been rewritten". That
became false the moment the scrub touched the quote. Both notes now say the
private project names were replaced with `example-*` placeholders and nothing
else was changed.

Verified: `git ls-files -z | xargs -0 grep -il` for the name returns zero files.

### Documentation Sync (`9d0de50`)

Evaluated over the finished diff. Three of four triggers fired, as the plan
predicted, and `README.md` did not — no CLI surface moved.

- `docs/changelogs/upcoming.md` — `Fixed` entry for `git_mv`, `Internal` entries
  for the ignore and the scrub.
- `docs/release-notes/upcoming.md` — "You can now keep finished work out of
  git", including the `git rm -r --cached` step, since a user who only edits
  `.gitignore` gets a half-working result.
- `skills/tcw-work/references/transitions.md` — a paragraph under the
  auto-commit rule. The router `SKILL.md` needed no change.

## Capability

`work/keep-resolved-work-out-of-git` (`cap-7e064f`) was seeded `Missing` at
planning and is declared `new:` in `capabilities.yaml`. Its body and the flip to
`Supported` are the pre-completion step.

Contradiction check: nothing in the ledger disagrees.
[Complete a work item](tcw://C/work/complete-a-work-item) and
[Discard a work item](tcw://C/work/discard-a-work-item) describe what the
resolution decides and where the item lands, which is unchanged — a node that
ignores nothing sees no difference at all.

## Test result

`pytest -q` — 1097 passed. `tcw validate` — `validate OK`, exit 0.

## Notes

The end-to-end proof is this item's own completion: it is the first `complete`
into the newly ignored folder in this repo. The `verify` stage should check
afterwards that the transition commit records deletions rather than a rename,
that `git status --short` is clean, and that the item is readable at
`docs/work/completed/<slug>` on disk.

Deliberately out of scope, per the request: the ~8 files under
`docs/work/completed/` that still name the private project on disk. They are no
longer in the repository.
