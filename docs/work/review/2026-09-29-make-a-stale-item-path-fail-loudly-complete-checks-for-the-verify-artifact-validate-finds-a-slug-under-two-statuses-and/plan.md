# Plan — Make a stale item path fail loudly

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.

## Task 1 — Failing tests

**Creates** `tests/test_stale_item_paths.py`, with one test per acceptance
criterion 1-8, in scratch nodes with git.

- Criteria 1, 3, 4, 6, 7 and 8 fail today and are committed
  `xfail(strict=True)`. Criterion 6's crash is itself the failure.
- Criteria 2 and 5 pass today.

## Task 2 — `complete` needs the verify artifact

**Modifies** `tcw/store/base.py` `complete`: inside `if not force:`, for
`review → completed` with resolution `done`, it refuses when
`refined-outcome` is absent. `rework`'s docstring and the `complete` step's
`gates` are updated.

**Modifies** `tcw/work/cli.py` `_complete`: the same check before the
merge-back, against the item it read, and the refusal names the stray folder
when one exists (Task 3).

**Updates** existing tests that complete from review as `done` without
`refined-outcome.md`, by writing the file in their fixture, never by adding
`--force`. Grep `complete` and `resolution done` across `tests/`.

**Proves** criteria 1-3.

## Task 3 — Stray and duplicate folders

**Modifies** `tcw/store/fs.py`:

- `_stray_folders(slug=None)` and `_duplicate_slugs()`;
- `check` reports both, and catches `MultipleMatch` per item.

`_complete` warns about a stray folder for its slug.

**Removes** the inbox entry `2026-09-29-tcw-validate-crashes-on-a-duplicate-slug.md`.

**Proves** criteria 4-6, including the web app's validate endpoint.

## Task 4 — Stage text

**Modifies** `tcw/work/prompts/implement.md` and `verify.md`, and
`skills/work/references/lifecycle/stage-implement.md` and `stage-verify.md`:
one sentence each. **Re-baselines** the prompt-fallback fixture: capture, then
diff so that only those two entries move, then add a history note. **Proves**
criterion 7.

## Task 5 — Printed folders

**Modifies** `tcw/work/cli.py`: `_shown(st, bare)` gives the folder relative
to the current directory, or absolute. It is used at every `st.locate`
printing site (new, start, submit, rework, complete). Tests that pin printed
folders are updated. **Proves** criterion 8.

## Task 6 — Documentation Sync

- `skills/work/references/transitions.md` and `commands.md`: `complete` needs
  `refined-outcome.md` from review, and `--force` overrides.
  [Skill-Driven-Component]
- `docs/guide/work.md`: the same, and what `validate` reports.
  [Guide-Topic-Change]
- Capability descriptions and `capabilities.yaml`. Confirm which capability
  owns `tcw validate` for work.
- A follow-up inbox entry for the non-moving folder idea.
- The changelog, and release notes calling out the new refusal.

## Task 7 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 9.

## Verification

By hand: reproduce the stale path from the issue in a scratch node (submit,
write to the old path), then run `complete` and `validate`. Make a duplicate
slug and run `validate`, then run the web app's validate endpoint.
