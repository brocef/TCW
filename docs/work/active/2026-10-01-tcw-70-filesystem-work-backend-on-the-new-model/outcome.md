# Outcome — Filesystem work backend on the new model

## Where the work is

All code is on branch `work/2026-10-01-tcw-70-filesystem-work-backend-on-the-new-model`,
in the worktree `.worktrees/2026-10-01-tcw-70-filesystem-work-backend-on-the-new-model`,
branched from `epic/tcw-3.0` at `ed44523e` and merged back into it when this
item completes. `main` receives 3.0 only when the epic is finished (the owner's
choice of 2026-10-02), because this branch's `tcw` refuses this repository's
own 2.x configuration.

The board was driven by editing files on `main` throughout, as `CLAUDE.md`
requires while `tcw/` is being changed. Tests and `tcw` ran from a private
virtual environment with an editable install of the worktree; the shared
editable install was never re-pointed.

Work paused after Task 9 on 2026-10-02 and resumed on 2026-10-08.

## What shipped, task by task

| Task | Commit | What |
| --- | --- | --- |
| 1 | `496a31d9` | The Jira HTTP client moved to `tcw/work/jira/client.py`, with its tests. |
| 2 | `81f226b3` | Tests that TCW-74 rewrites are skipped at module level. |
| 3 | `08543df9` | 63 test files of 2.x behavior deleted (collection 5,263 → 3,385). |
| 4 | `e801d775` | `FsWorkBackend`, `item_record` (`tcw/work/record.py`), `Finding` (`tcw/findings.py`), and a contract test run over both backends. |
| 5 | `078e28b2` | `tcw/work/open.py`: `open_backend`, `open_project`, `delegate`, `open_for_update`, `uncommitted_changes`. |
| 6 | `7efe8417` | 3.0 prompt composition in `resolve.py`: `compose`, `stage_prompt`, `procedure_prompt`, `stage_header`, `substitute_request`, `generate_payload`, `packaged_text`. |
| 7 | `59051bc3` | The 3.0 checks beside the 2.x ones: `_work_findings` and `_shared_work_paths` (validate), `_resolve_work` (refs), `_completed_but_missing` (drift), `project_reader` (gates). |
| 8 | `7421249d` | The 3.0 item commands in `cli_next.py`, not yet registered. |
| 9 | `0a55f6e5` | `tcw serve` keeps a two-route work stub until TCW-77. |
| 10 | `dc247d47` | The switch-over: `cli_next.py` becomes `tcw/work/cli.py` with `stage prompt`, `procedure prompt`, `lifecycle`, `docs`, `tags`, `nodes` and `init`; `main` maps `TcwError` to its exit code; `init`, `validate`, `tcw://W/` references and `drift` run on the 3.0 model; `WorkLocation` replaces `FsWorkStore` as `STORE_CLASSES["work"]`; `{{tcw:body}}` becomes `{{tcw:request}}`; `cli_suggest.py` examples; the documentation allowance. |
| 11 | `83bd6aa4` | The 2.x work code deleted: `FsWorkStore` and its helpers (`fs.py` 8,900 → 3,700 lines), the work half of `base.py` (4,810 → 1,170 lines, 129 names found unreachable), `tcw/tracker/`, `tcw/harness.py`, `recursion.py`, `projection.py`, `templates.py`, and the 2.x halves of `resolve.py` and `hooks.py`. |
| 12 | `cb6b7578` | Capability records: 23 removed, 3 new, 34 changed. Taxonomy: 3 new terms, 6 reworded, 5 removed, 4 features' references dropped. |
| 13 | `d9b2b1fb` | Changelog and release-notes entries, and `tests/test_upcoming_entries.py`. |

## Departures from the plan

- **Tests (the owner's choice, 2026-10-08: "New 3.0 tests only").** The plan's
  long table of 2.x test files to port was not followed. The new 3.0 tests
  the plan names were written. 2.x tests whose subject a later slice
  rewrites are skipped through `tests/not_ported.py` (116 test ids, applied
  by a collection hook in `tests/conftest.py`). Tests of deleted code were
  removed one test at a time rather than one file at a time, so the rest of
  each file still runs. 18 files with nothing left in them were deleted in
  Task 10 and five more in Task 11.
- **`REMOVED_FLAGS`** was added to the documentation allowance beside
  `REMOVED_COMMANDS` and `REFUSED_KEYS`: the README, guides and skills
  still name `list --status`, `--include-descendants`, `new --initiative`
  and `--epic`, `edit --type` and `--initiative`, and
  `lifecycle --transition`. It is guarded like the other two lists.
- **`resolve._hook_env` was kept**, because the 3.0 `compose` uses it.
- **`run_bindings` takes the 3.0 `Binding`** (`tcw.work.config`), so
  `base.Binding` could be deleted.
- **`load_builtins` reads the stages that have a packaged prompt file.**
  `review` and `qa` have none until TCW-74 writes them; without this, every
  command that composes a prompt failed on the missing file.
  `test_shipped_prompts.py` is keyed on the stage table less those two.
- **`FsStoreProvisioner` is also allowed `git merge`** in AC 12's scan:
  `tcw provision --refresh` fast-forwards its own checkout with
  `merge --ff-only`, which the spec's allowance (clone, checkout, fetch)
  missed. Until TCW-73, `git_stage` and `git_rm`, which the taxonomy and
  capabilities stores still use, are allowed `add` and `rm`.
- **The help-coverage floor** in `test_cli_help_coverage.py` was lowered
  from 60 to 40 commands, since 15 commands are gone.
- **`import tcw.tracker`** is checked against this package's own tree rather
  than by the import alone: a second editable install (the primary
  checkout's, in the venv's path) can still answer for it.
- **`RESERVED_PROJECT_IDS`** is `t`, `c`, `w` and `local`; the 2.x status
  names are valid project ids again, with a test.
- From the paused session (Tasks 4–9), recorded in its handoff:
  `FsWorkBackend` takes `today=` and `now=` for tests;
  `work_store_problems` takes the config; `ConnectedProject.jira` and
  `FsProjectRegistry.entry(id)` were pulled forward from TCW-71's plan;
  `hook_env` and `binding_applies` are public in `advance.py`;
  `compose()` takes `builtin_kind` and `env`; `resolve_item` returns
  `(slug, backend, project_root)`; serve's `_put`/`_delete` keep the CSRF
  check, then answer 404.

## Tests

- Whole suite, run in parallel after each of Tasks 11, 12 and 13:
  **2,614 passed, 131 skipped, 0 failed** after Task 12 (Task 13 added one
  test). The drop from 2,658 after Task 11 is the documentation-surface tests,
  which run once per tracked document: 28 documents were removed and 6 added.
- Bare `pytest -q` from the branch checkout, as CI runs it (AC 23):
  **2,615 passed, 131 skipped, 0 failed** in 4 minutes 14 seconds, after
  Task 13.
- The same suite in a throwaway copy of the tracked tree with no root
  `tcw-config.yaml` and no `docs/work/`, as a fresh git repository (AC 23):
  **2,615 passed, 131 skipped, 0 failed**.
- `tcw validate` on this repository, with the released 2.8.1 (the branch
  refuses this repository's 2.x configuration until the epic migrates it):
  `validate OK`.
- pyflakes over `tcw/`: no new warnings. The nine it prints (unused imports in
  `tcw/serve/__init__.py` and `tcw/capabilities/cli.py`, and an f-string with
  no placeholder) were all on `epic/tcw-3.0` before this branch.

### Mutation checks

Each guard was broken on purpose, seen to go red for the reason it names,
and restored.

| Guard | Mutation | Result |
| --- | --- | --- |
| `test_doc_allowance.py`, commands | `tcw work list` added to `REMOVED_COMMANDS` | red: the command still exists |
| `test_doc_allowance.py`, keys | `work.tags` added to `REFUSED_KEYS` | red, after the guard was tightened to require the "removed in TCW 3.0" message (it first passed, because `work.tags: {}` is refused for its shape) |
| `test_doc_allowance.py`, flags | `--tag` claimed removed from `list` | red |
| `test_compose.py` | the request not passed into the composed prompt; a missing packaged file not failing | both red |
| `test_model_guards.py` (AC 14) | `"request/request.md"` added to `fs_backend.py` | red |
| `test_no_2x_names.py` (AC 13) | `graveyard.yaml` named in `validate.py` | red |
| `test_git_write_scan.py` (AC 12) | `["git", "-C", str(root), "add", "x"]` in `tcw/work/open.py` | red: `work/open.py:168: git add (in _mutant)` |
| `test_git_write_scan.py` (AC 12) | the same in an `fs.py` function outside `FsStoreProvisioner` | red: `store/fs.py:233: git add (in _mutant)` |
| `test_git_state_unchanged.py` (AC 12) | `tags add` runs `git add` on `tcw-config.yaml`, as 2.x did | red: `('tags', 'add', 'x')` |
| `test_upcoming_entries.py` (AC 22) | a line of text above the release-notes entry's first heading | red, naming the line |

The Tasks 4–9 checks were made in the paused session; its handoff records
that each task's key checks were mutation-checked, without listing them.

### Hand trace

Two scratch projects made with the branch's `tcw init`, `p` with `q` as its
child, and a `spec` `pre` hook in `p` requiring the request document:

```text
$ tcw work new "Add dark mode" </dev/null          → p/2026-10-08-add-dark-mode   [exit 0]
$ tcw work advance …-add-dark-mode --dry-run
spec pre hook `test -f "$TCW_ITEM_PATH/request/request.md"` failed (exit 1)   [exit 3]
$ echo "Users want a dark theme." | tcw work new "Theme toggle"
… wrote …/2026-10-08-theme-toggle/request/request.md → p/2026-10-08-theme-toggle   [exit 0]
$ tcw work list                                     → both items                    [exit 0]
  (request/request.md written for add-dark-mode)
$ tcw work advance …-add-dark-mode                  → spec                          [exit 0]
$ tcw work advance …-add-dark-mode --to implement
moving from spec to implement skips a stage; that needs --force and a --reason [exit 3]
$ tcw work advance …-add-dark-mode --to implement --force --reason "plan agreed in review meeting"
… wrote comments/20261008T185342Z.md → implement                                  [exit 0]
  comment: "Moved from spec to implement (forced).\nReason: plan agreed in review meeting"
$ tcw work edit …-theme-toggle --blocked-by …-add-dark-mode --priority high       [exit 0]
$ tcw work rename …-add-dark-mode dark-theme
moved …-add-dark-mode to …-dark-theme; wrote …-theme-toggle/item.yaml
items in other projects that name p/2026-10-08-add-dark-mode are not rewritten; `tcw validate` there reports them
→ p/2026-10-08-dark-theme                                                          [exit 0]
$ tcw work show …-theme-toggle                      → blocked-by: p/2026-10-08-dark-theme
$ tcw work new "Shared colour tokens" --project q </dev/null
created …/q/docs/work/2026-10-08-shared-colour-tokens (uncommitted in …/q) → q/2026-10-08-shared-colour-tokens
$ git -C ../q status --short                        → ?? docs/work/2026-10-08-shared-colour-tokens/
$ tcw work discard …-theme-toggle --reason "folded into dark-theme" → discarded     [exit 0]
$ tcw validate
[p] warning: …-dark-theme/item.yaml: stage is at implement but has nothing from spec; …
[p] warning: …-dark-theme/item.yaml: stage is at implement but has nothing from plan; …
validate OK                                                                        [exit 0]
$ git status --short                                → only ?? for the two item folders
```

The commands fit together: the hook refused the move until its document
existed, the forced skip left its reason as a comment, the rename rewrote the
blocker, delegation left `q` with uncommitted files, `validate` warned about
the forced item without failing, and nothing was staged or committed in
either repository.

## Not done here, and why

- **The Playwright suite** (Task 9's spec edits) was not run, and the
  `shell-system-dark` and `shell-explicit-light` snapshots still need
  regenerating. Deferred to the end of the epic, by the owner's rule for
  this epic.
- **Re-reading `fs_backend.py` and `open.py` against TCW-71's spec** has not
  been done. It moves to the start of TCW-71's turn, which is next, where
  anything found outside TCW-71's four seams is fixed as part of TCW-71.
- **Documents deferred by the spec (Design 14):** the README, the guides
  (including `docs/guide/jira.md`), the skills and the configure references
  still describe 2.x. TCW-74 and TCW-75 rewrite them, and the documentation
  allowance lists exactly what they may still name until then.
