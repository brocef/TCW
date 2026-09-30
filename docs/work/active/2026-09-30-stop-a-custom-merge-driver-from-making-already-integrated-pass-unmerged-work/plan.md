# Plan: Stop a custom merge driver from making --already-integrated pass unmerged work

_Compressed plan, agreed with the maintainer for a small fix._

## Tasks

1. **Tests first** — add to `tests/test_already_integrated_check.py` (it already
   builds repositories for `branch_integration`): in-tree `* merge=ours` with
   `merge.ours.driver=true` and a branch changing a line `HEAD` also changed →
   refused, message mentions custom merge drivers (criteria 1, 5); the same
   with the attribute only in `.git/info/attributes` (2); squash merge with no
   drivers still passes (3 — likely already covered; confirm, else add); merge
   commit with a driver configured still passes (4); a `GIT_CONFIG_COUNT` already
   set in the environment is not clobbered into a wrong answer. Red before task 2.
2. **Code** — `tcw/store/fs.py` `branch_integration`: read custom driver names
   with `git config --null --name-only --get-regexp '^merge\..+\.driver$'`
   (exit 1 = none); run the `merge-tree` trial with each overridden to `false`
   through `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>`,
   appended after any the caller's environment already carries; when the trial
   refuses and drivers exist, add a sentence naming them. Docstring states the
   trade-off. Proof: task 1 green, suite green under bare `pytest`.

## Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change] — `## Fixed`.
- `docs/release-notes/upcoming/<slug>.md` [Public-API].
- `skills/work/references/transitions.md` and `docs/guide/work.md` — the
  `--already-integrated` text gains one sentence: a squash merge touching files a
  custom merge driver governs is not confirmed; delete the branch yourself.

## Verification

- The spec's reproduction by hand in a scratch repository, before and after.
