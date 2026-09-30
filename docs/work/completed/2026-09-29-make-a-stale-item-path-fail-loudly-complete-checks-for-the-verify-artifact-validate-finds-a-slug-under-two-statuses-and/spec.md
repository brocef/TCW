# Spec — Make a stale item path fail loudly

## Capability changes

- **changed:** `work/complete-a-work-item` — completing as `done` from review
  needs `refined-outcome.md`, and a stray folder for the slug is reported.
- **changed:** `work/validate-the-work-store` (or whichever capability owns
  `tcw validate` for work; confirm at implementation) — one slug held by two
  folders, and a stray folder with a slug's name, are reported, not crashed on.
- **changed:** `work/run-a-lifecycle-stage` — the `implement` and `verify`
  instructions say where the item's folder is now.

## Problem

An agent holds an item's folder path across many turns. `submit` moves
`active/<slug>/` to `review/<slug>/`. If the agent then writes
`refined-outcome.md` to the path it was holding, the write recreates
`active/<slug>/` with one stray file in it. Nothing fails. The item completes
as `done` with its acceptance record outside it, and every command still
reports one healthy item, because item folders are found by their
`state.yaml` alone (`_item_dirs`, `tcw/store/fs.py`).

Two folders that both hold a `state.yaml` for one slug are worse: `_find`
raises `MultipleMatch`, and `tcw validate` crashes with a traceback. That is
uncaught in `FsWorkStore.check` itself, and in `_carried_by_its_parent`,
`_require_dir` and `_declared_plan_stages`, not only `_parent_problems`. The
web app runs validate through its API, so there it is a 500 error.

Separately, for a qualified reference (`tcw work start kid/<slug>`), the folder
printed after a transition is relative to the child project, so it names a
path that does not exist from where the command ran.

## Goals

1. **`complete --resolution done` from `review` refuses without
   `refined-outcome.md`** in the item's folder. `--force` overrides it, as it
   already overrides blockers and gates. The refusal names the file, the
   folder it should be in (`tcw work path <slug>`), and the verify stage that
   writes it.
   - The check lives in the store's `complete` (`tcw/store/base.py`), so the
     web app's complete is covered too.
   - Unaffected: completing from `active` (verify skipped, already a legal
     route that warns); an epic closed from `backlog`; every resolution other
     than `done`.
   - The CLI checks the same thing before the worktree merge-back, against the
     copy it already reads. A refusal must never leave the branch merged and
     the item open.
2. **A stray folder is reported.** A stray folder is a directory named like a
   known slug (an item, or a tombstone in `graveyard.yaml`) that:
   - sits directly under a status folder, or directly inside a folder that
     holds child items;
   - holds no `state.yaml`;
   - is not the slug's own current folder;
   - holds at least one file other than `.DS_Store`.
   Dot-prefixed directories (such as `.claiming/`) are never stray.
   - `tcw validate` reports each one with its path and the files in it. This is
     a whole-store scan, run from validate only.
   - `tcw work complete` checks for its own slug only: for each status folder,
     does `<status>/<slug>/` exist, plus the same under the parent's folder for
     a nested item. It prints a warning naming the path and files. When the
     goal-1 refusal fires and a stray folder exists, the refusal names it:
     that is the stale-path case exactly.
   - `show` and `list` are unchanged.
3. **One slug held by two folders is reported, not crashed on.**
   - `validate` groups the folders `_item_dirs` already found by slug, reports
     each duplicate with both paths, and skips per-item checks for that slug.
   - No other `MultipleMatch` from `check` escapes: any item-level lookup that
     raises it is reported as that item's problem.
   - The web app's validate call then returns problems, not a 500 error.
4. **The stage text says where to write.** The `implement` and `verify`
   prompts (`tcw/work/prompts/implement.md`, `verify.md`) gain the wording the
   `postmortem` prompt already has: write in the item's folder wherever it
   currently lives, which `tcw work path <slug>` prints. The skill's copies of
   those stages say the same.
5. **Printed folders are relative to where the command ran.** After `new`,
   `start`, `submit`, `rework` and `complete`, the folder shown is relative to
   the current directory, or absolute when it is not under it. That covers
   qualified references, and running from a subdirectory.

## Non-goals

- **A folder that never moves** (status kept only in `state.yaml`), as the
  issue's follow-up comment suggests. It removes the cause, but it changes the
  store layout, every reader, the web app and the tracker adapters. Goals 1-4
  make the symptom fail loudly at the moment it matters. The idea is recorded
  as a follow-up inbox entry.
- **Refusing `submit`** on a stray folder. It usually appears after `submit`.
- **Fixing stray folders automatically.** They are reported with their files
  so a person can move them.

## Design

- `FsWorkStore._stray_folders(slug=None)`: the per-slug probe for `complete`,
  and the whole-store scan for validate. Both walk only status folders and
  folders that hold child items, never the whole tree.
- `FsWorkStore._duplicate_slugs()`: groups `_item_dirs()` by folder name.
- `check`: run both first. Per-item checks are skipped for duplicated slugs,
  and any remaining `MultipleMatch` is caught per item.
- `WorkStore.complete`: the `refined-outcome` check, inside `if not force:`,
  only for `review → completed` with resolution `done`. It raises
  `ValueError`, which the CLI and the web app already turn into a refusal.
  `rework`'s docstring ("the only transition the artifact gates") and the
  `complete` step's `gates` in `LIFECYCLE_STEPS` are updated.
- `cli._complete`: the same check on the item it read, before
  `merge_worktree`, then the stray-folder warning.
- `cli`: one helper that shows a path relative to the current directory, used
  wherever a transition prints the item's folder.

Litmus:
- The refined-outcome gate is an artifact-presence check, which any store can
  answer.
- Stray and duplicate folders are the filesystem adapter's own failure modes.
  They live in `FsWorkStore.check`, where a tracker store has no equivalent.
- Printed paths are CLI presentation.

## Acceptance criteria

1. An item in review with no `refined-outcome.md`:
   `complete --resolution done --confirm` exits 1, names the file and
   `tcw work path`, and moves nothing. With `--force` it completes. With
   `--resolution wontfix` it discards as today.
2. The same from `active` completes as today, with its existing warning.
3. A `--worktree` item in review with no `refined-outcome.md`: the refusal
   comes before the merge-back. The branch is unmerged afterwards, and main's
   HEAD has not moved.
4. The stale-path reproduction: submit, then write
   `active/<slug>/refined-outcome.md`. `complete` refuses, naming
   `active/<slug>/`. `tcw validate` reports the stray folder and its file.
5. `active/<slug>/` containing only `.DS_Store`, or empty: not reported.
6. Two folders each with a `state.yaml` for one slug: `tcw validate` exits 1
   listing both paths, with no traceback. The web app's validate endpoint
   returns the problem.
7. `tcw work stage prompt verify <slug>` and `implement` include the
   where-to-write sentence and `tcw work path`.
8. `tcw work start kid/<slug>` from the parent prints a folder that exists
   relative to the current directory.
9. Existing tests pass, updated only where they completed an item from review
   as `done` without `refined-outcome.md`, or pinned a printed folder. The full
   suite passes as CI runs it.

## Risks

- **Completing from review now needs the verify artifact.** Scripts that
  completed reviewed items without verifying break loudly, and `--force` is the
  way out. This is the point of the change. Release notes call it out.
- **Tests** that complete from review without writing `refined-outcome.md` need
  the file. Expect several: grep for `complete` in the tests at planning.

## Notes

- Advisors: Opus, and Sonnet in place of Codex (at its usage limit until
  2026-10-03).
  - Both chose to refuse in `complete` for a missing `refined-outcome.md`, and
    to warn rather than refuse on a stray folder.
  - Opus supplied:
    - putting the check in the store, since the web app calls
      `store.complete` directly;
    - exempting completion from `active` and epics from `backlog`;
    - checking before the merge-back;
    - counting tombstones as known slugs;
    - the other uncaught `_find` calls in `check`;
    - the web app's 500 error.
  - Sonnet supplied the per-slug probe for `complete` rather than a scan, and
    ignoring dot-folders. It also advised keeping goal 5 as its own task.
- The inbox entry `2026-09-29-tcw-validate-crashes-on-a-duplicate-slug.md` is
  covered by goal 3, and is removed when this item completes.
