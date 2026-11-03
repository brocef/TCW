# Plan — From a copy of worktrees kept inside its own main checkout, the search for a project climbs past the copy into the main checkout

Spec: [`../spec/spec.md`](../spec/spec.md). One code change, in
`search_rounds` (`tcw/store/project.py`), written test first. No new
operation. TCW-119, a separate item, is planned for the same 4.0.1 release,
so the version is not cut here.

This plan was revised after a spec review returned NOT DONE: the filter now
applies to the early return in `search_rounds` too (spec cases 8 and 9), a
folder is left out only when it is in the main checkout's own repository
(case 10), the walk is computed only when it can matter, and three more
tests and three more mutation checks were added.

The tests are written first and run red (Step 1). The fix (Step 2) turns them
green. Both are committed together, so no commit leaves the suite red.

## Step 1 — Tests of every layout in the spec, run red against today's code

**Files changed:** `tests/test_manifest_worktree.py`,
`tests/migrate/test_migrate_search_worktrees.py`.

Every layout uses real `git init` and `git worktree add`, through the
helpers already in `tests/test_manifest_worktree.py` (`proj`, `git`,
`_commit_all`, `_linked`, `_repository`) and `tcw` from
`tests/test_project_files_cli.py`. Project IDs are lowercase, as in the
spec.

### 1a. `tests/test_manifest_worktree.py`

Add a section headed
`# -- A copy kept inside the main checkout it was made from ---`, after the
section "The search from a worktree inside another repository's checkout".

Helpers:

- `_main_with_a_child(base: Path, *, root_3x: bool = False, child_3x: str | None = None) -> tuple[Path, Path]`
  builds the request's two repositories and returns `(main, child_main)`.
  - Repository X at `base/MAIN` holds project `r`, and a manifest placing `p`
    at `path: p`. Its `.gitignore` reads `/p/\n/.claude/\n/.worktrees/\n`.
  - Repository Y at `base/MAIN/p` holds project `p`, naming nothing, and an
    empty manifest. With `child_3x`, that text is Y's root `tcw-config.yaml`
    instead, and there is no `.tcw/`.
  - With `root_3x=True`, X's `main` branch holds a root `tcw-config.yaml`
    reading `id: r` and no `.tcw/` folder, and the manifest is not written.
  - Each is committed on branch `main`.
- `_copy(main, child_main, at, *, child_at="p") -> tuple[Path, Path]` makes
  X's linked worktree at `at` and Y's at `at / child_at`, both with
  `_linked`, and returns both, resolved.
- `_migrate_branch(w)` moves X's linked worktree to 4.0 on its own branch
  (for case 2): delete `tcw-config.yaml`, write `.tcw/tcw-config.yaml` and the
  manifest placing `p`, and commit in `w`.

Tests, each with a docstring naming the spec's case and criterion:

| Test | Layout | Asserts | Today |
| --- | --- | --- | --- |
| `test_a_copy_kept_inside_its_own_main_checkout_finds_the_root_in_the_copy` | case 1 | `project path r` from `w/p`: code 0, out `f"{w}\n"`, err `""` (AC 1) | red: "more than one folder" |
| `test_a_copy_kept_inside_a_3x_main_checkout_finds_the_root_in_the_copy` | case 2 | code 0, out `f"{w}\n"`, `"tcw migrate"` not in err (AC 2) | red: names MAIN as 3.x |
| `test_a_copy_kept_outside_its_main_checkout_finds_the_root_in_the_copy` | case 3 | code 0, out the copy's `w` (AC 3) | green (control) |
| `test_a_worktree_in_a_linked_worktree_inside_its_main_checkout_finds_the_root_there` | case 4 | code 0, out `f"{w}\n"` (AC 4) | red |
| `test_a_copy_three_deep_finds_the_outermost_root_in_the_copy` | case 5 | `project path z` from `w/x/y`: out `f"{w}\n"` (AC 5) | red |
| `test_a_clone_between_the_worktrees_does_not_hide_the_outer_one` | case 7 | `project path z` from `zw/x/.worktrees/y`: out `f"{zw}\n"` (AC 5a) | red |
| `test_a_related_projects_search_inside_the_copy_finds_the_root_in_the_copy` | case 8: X a monorepo, `r` at MAIN, `s` at `MAIN/s` naming `r`; `p` names `s` with `s: ../s` | from `w/p`: `project path r` prints `w`, `project list` code 0 (AC 5b) | red |
| `test_a_clone_kept_in_a_copy_inside_its_main_checkout_finds_the_root_in_the_copy` | case 9: `WS`, its linked worktree `WS/.claude/worktrees/w`, a `git init` repository at `w/x` | `project path ws` from `w/x` prints `w` (AC 5c) | red |
| `test_a_separate_repository_between_the_copy_and_its_main_checkout_is_still_searched` | case 10: `MAIN/tools` a repository of its own, the copy at `MAIN/tools/wt/w` | `project path tools` prints `MAIN/tools`; `project path r` prints `w` (AC 5d) | red (the `r` half) |
| `test_a_project_above_the_main_checkout_is_still_found_from_the_copy` | case 1 plus a project `o` at `base` | `project path o` from `w/p` prints `base` (AC 5e) | green (control) |
| `test_a_copy_inside_its_main_checkout_lacking_the_root_does_not_find_the_mains` | case 6 | code ≠ 0, out `""`, `str(main)` in neither out nor err, `"no project with ID 'r' is known or found"` in err (AC 6) | red: prints MAIN |
| `test_a_worktree_in_a_main_checkouts_worktrees_folder_finds_that_checkouts_project` | Y's linked worktree at `MAIN/.worktrees/p` | out `f"{main}\n"` (AC 9) | green (control) |

The three-repository layouts (cases 5 and 7), the monorepo (case 8), the
clone (case 9) and the tools repository (case 10) are built inline in their
tests with `proj`, `write_manifest`, a `.gitignore` per repository naming its
nested folders, `git init -q -b main` and `_commit_all`.

`str(main)` in case 6 is checked with a trailing separator or as a whole
word, since `w`'s own path begins with `main`'s: the test asserts that no
line names `main` other than as the start of `w`'s path, by removing every
occurrence of `str(w)` first.

### 1b. `tests/migrate/test_migrate_search_worktrees.py`

Import `_main_with_a_child` and `_copy` from `tests.test_manifest_worktree`.

| Test | Layout | Asserts | Today |
| --- | --- | --- | --- |
| `test_a_copy_kept_inside_its_own_main_checkout_predicts_the_copys_root` | case 1 | `family.search_4(w / "p", "r") == [w]`; `family.search_4(child_main, "r") == [main]`; `tcw` from `w/p` prints `w` (AC 7, first half) | red: `[w, MAIN]` |
| `test_migrating_a_copy_inside_its_main_checkout_writes_what_the_main_checkout_writes` | case 1, Y on 3.x (`child_3x`: `id: p\nprojects:\n  parent:\n    r: ..\n`) | `tcw(w/p, "migrate", "--no-jira")` code 0, and its `.tcw/tcw-manifest.yaml` has no `r`; the same after `tcw(child_main, "migrate", "--no-jira")` (AC 7, second half) | red: the copy's run writes `r` |

**Done when:** `pytest tests/test_manifest_worktree.py
tests/migrate/test_migrate_search_worktrees.py` reports exactly the tests
marked red above as failing, each with the failure the "Today" column
names, and the controls passing. A test that fails for another reason, such
as a fixture git error, is a broken test, not a reproduction. Record the run
in the implement round.

## Step 2 — The fix in `search_rounds`

**File changed:** `tcw/store/project.py`.

1. A module-level cache beside `_ANCHOR_CACHE` and `_REPOSITORY_CACHE`:
   `_CHECKOUT_CACHE: dict[Path, tuple[Path, Path] | None] = {}`, living as
   long as the process for the reason the comment above them gives. The two
   tests that clear those caches (`tests/test_run_in_folder.py:234`,
   `tests/test_worktree_remote_forms.py:110`) are read; neither changes a
   layout that this cache would answer about, so neither needs to clear it.
2. `_checkout_of(folder) -> tuple[Path, Path] | None`: `(top, main)` for the
   git checkout `folder` is in, `main == top` for a main checkout, None
   outside one. One `git rev-parse --path-format=absolute --show-toplevel
   --git-common-dir` through `_git_lines`; `main` is the common folder's
   parent when the common folder is named `.git`, and `top` otherwise (a
   submodule or other arrangement is treated as a checkout of its own, and
   the walk goes on outward from it). Cached.
3. `_under_a_linked_worktree(folder) -> bool`: whether `folder` or a folder
   above it has a `.git` that is a file (`_is_file`). No git process.
4. `_left_out_of_the_climb(start) -> set[Path]`: walk checkouts outward from
   `start` (`_checkout_of(start)`, then `_checkout_of(top.parent)`, until
   None or the filesystem root). For each `(top, main)` with `top != main`
   and `_below(top, main)` not None, add every `F` in `top.parents` with
   `_below(F, main)` not None and `F == main` or `_repository_of(F)` naming
   the same common folder as `_repository_of(main)`.
5. `_climb(named_by, start) -> list[Path]`: `list(named_by.parents)` without
   the folders of `_left_out_of_the_climb(start)`, compared with `_below` in
   both directions so a disk that ignores letter case behaves the same.
6. In `search_rounds`:
   - The early return gives `(named_by.parent, named_by, _climb(named_by,
     named_by))` when `_under_a_linked_worktree(named_by)`, and the plain
     climb otherwise.
   - After the `read_as_written(top.parent, anchors)` check, the round read
     as written is `(named_by.parent, named_by, _climb(named_by,
     top.parent))`, used in both returns that give it.
   - `from_main` is unchanged, and built as today.
7. The docstring of `search_rounds` gains a paragraph stating the rule
   (TCW-120).
8. `tcw/migrate/family.py` is **not** changed.

**Done when:** every test from Step 1 passes, including the controls, and
`pytest tests/test_manifest_worktree.py tests/migrate/
tests/test_override_in_linked_worktree.py tests/test_worktree_remote_forms.py
tests/test_worktree_sibling_nodes.py tests/test_run_in_folder.py` passes
(AC 8). Then **mutation-check** each part of the rule, confirming the named
tests go red for the reason expected, and restore:

- (a) `_left_out_of_the_climb` returns an empty set: the step 1 tests marked
  red go red again.
- (b) The walk stops after the first checkout: the case 5, case 7 and case 9
  tests go red, case 1 stays green.
- (c) The climb is truncated at the linked worktree (every folder above
  `top` left out, not only those in `main`'s repository): the
  project-above-the-main-checkout test goes red.
- (d) The same-repository test is dropped (every `F` inside `main` left
  out): the case 10 test goes red on `project path tools`.
- (e) The early return keeps the plain climb: the case 8 and case 9 tests go
  red.

Record each in the implement round. **Commit** Steps 1 and 2 together.

## Step 3 — Whole suite as CI runs it

Run bare `pytest` from the worktree's root, with this worktree's own virtual
environment (`.venv/bin/pytest`). **Done when:** it passes (AC 10).

## Step 4 — Documentation Sync

Run the `documentation-sync` skill against the entries from `tcw work docs`.
Expected outcome:

| Entry | Fires? | What changes |
| --- | --- | --- |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | New file named by this item's folder, under `## Fixed`: the rule, the layouts it fixes (cases 1-2, 4-9), and `search_4`'s prediction. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | New file of the same name, under `## Fixes`, in plain words for a user. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/multi-repo.md` | In "Git worktrees", after the sentence ending "in the folders the copy was made from.", a sentence stating the rule exactly as AC 11 words it. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: S-4 | Under **Seen**, that Claude Code keeps worktrees at `.claude/worktrees/<name>`, inside the main checkout. Under **Requirements**, a bullet with the rule as AC 11 words it, citing `search_rounds` and `tests/test_manifest_worktree.py`. |
| Capability record `docs/capabilities/cli/run-from-a-git-worktree/description.md` | yes: declared `changed` | One sentence with the rule as AC 11 words it, edited directly. |
| `README.md`, `skills/**`, `skills/configure/references/*`, `docs/guide/jira.md` | no | None describes the search's folders, keys or Jira. Check with `grep -rln "worktree" skills/`. |

**Done when:** each "yes" row's file exists or is changed as described, and
`tcw validate` passes. Commit.

## Verification beyond the tests

- Re-run the reproduction layouts, kept outside the repository, against the
  fixed code: cases 1-10 and the contrast layout. Record the outputs in the
  implement round.
- Not tested, as the spec says: git submodules inside these layouts, and
  Windows.

## Coverage of the acceptance criteria

| AC | Step |
| --- | --- |
| 1, 2, 3, 4, 5, 5a, 5b, 5c, 5d, 5e, 6, 9 | 1a, made green by 2 |
| 7 | 1b, made green by 2 |
| 8 | 2 ("Done when") |
| 10 | 3 |
| 11 | 4 |
