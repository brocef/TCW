# Plan — From a copy of worktrees kept inside its own main checkout, the search for a project climbs past the copy into the main checkout

Spec: [`../spec/spec.md`](../spec/spec.md). One code change, in
`search_rounds` (`tcw/store/project.py`), written test first. No new
operation. Ships in 4.0.1 with TCW-119, so the version is not cut here.

The tests are written first and run red (Step 1). The fix (Step 2) turns them
green. Both are committed together, so no commit leaves the suite red.

## Step 1 — Tests of every layout in the spec, run red against today's code

**Files changed:** `tests/test_manifest_worktree.py`,
`tests/migrate/test_migrate_search_worktrees.py`.

Every layout uses real `git init` and `git worktree add`, through the
helpers already in `tests/test_manifest_worktree.py` (`proj`, `git`,
`_commit_all`, `_linked`, `_repository`) and `tcw` from
`tests/test_project_files_cli.py`. Project IDs are lowercase single letters,
as in the spec.

### 1a. `tests/test_manifest_worktree.py`

Add a section headed
`# -- A copy kept inside the main checkout it was made from ---`, after the
section "The search from a worktree inside another repository's checkout".

Helpers:

- `_main_with_a_child(base: Path, *, root_3x: bool = False) -> tuple[Path, Path]`
  builds the request's two repositories and returns `(main, child_main)`.
  - Repository X at `base/MAIN` holds project `r`, and a manifest placing `p`
    at `path: p` (written with `write_manifest(main, {"p": "p"})`). Its
    `.gitignore` reads `/p/\n/.claude/\n/.worktrees/\n`.
  - Repository Y at `base/MAIN/p` holds project `p`, naming nothing, and an
    empty manifest (`tcw-version: 4.0.0\nprojects: {}\n`).
  - Each is committed on branch `main` (`_commit_all`).
  - With `root_3x=True`, X's `main` branch holds a root `tcw-config.yaml`
    reading `id: r` and no `.tcw/` folder, and the manifest is not written.
- `_copy(main: Path, child_main: Path, at: Path, *, child_at: str = "p") -> tuple[Path, Path]`
  makes X's linked worktree at `at` and Y's at `at / child_at`, both with
  `_linked`, and returns both, resolved.
- With `root_3x=True`, the test moves X's linked worktree to 4.0 after making
  it, on the worktree's own branch: delete `tcw-config.yaml`, write
  `.tcw/tcw-config.yaml` (`proj(w, "r")`), write the manifest placing `p`,
  and commit in `w`. A second helper, `_migrate_branch(w: Path) -> None`,
  does this, so `_copy` stays one thing.

Tests, each with a docstring naming the spec's case and criterion:

| Test | Layout | Asserts | Today |
| --- | --- | --- | --- |
| `test_a_copy_kept_inside_its_own_main_checkout_finds_the_root_in_the_copy` | case 1: copy at `MAIN/.claude/worktrees/w` | `tcw(w/p, "project", "path", "r")`: code 0, out is `f"{w}\n"`, err is `""` (AC 1) | red: code 1, "more than one folder" |
| `test_a_copy_kept_inside_a_3x_main_checkout_finds_the_root_in_the_copy` | case 2: `root_3x=True`, then `_migrate_branch(w)` | code 0, out `f"{w}\n"`, `"tcw migrate"` not in err (AC 2) | red: code 1, names MAIN as 3.x |
| `test_a_copy_kept_outside_its_main_checkout_finds_the_root_in_the_copy` | case 3: copy at `base/elsewhere/w` | code 0, out is the copy's `w` (AC 3) | green (control) |
| `test_a_worktree_in_a_linked_worktree_inside_its_main_checkout_finds_the_root_there` | case 4: Y's main checkout at `base/ymain` (so not inside MAIN), Y's linked worktree at `w/.worktrees/p` | code 0, out `f"{w}\n"` (AC 4) | red |
| `test_a_copy_three_deep_finds_the_outermost_root_in_the_copy` | case 5: Z at `ZM` holding X at `ZM/x` holding Y at `ZM/x/y`; linked worktrees `ZM/.claude/worktrees/w`, `w/x`, `w/x/y` | `project path z` from `w/x/y`: code 0, out `f"{w}\n"` (AC 5) | red |
| `test_a_clone_between_the_worktrees_does_not_hide_the_outer_one` | case 7: Z at `ZM`, its linked worktree `zw` at `ZM/.claude/worktrees/zw`, a separate repository X initialised at `zw/x` (a main checkout), Y's main checkout at `base/ymain` and its linked worktree at `zw/x/.worktrees/y` | `project path z` from it: code 0, out `f"{zw}\n"` (AC 5a) | red |
| `test_a_copy_inside_its_main_checkout_lacking_the_root_does_not_find_the_mains` | case 6: case 1, then `(w / ".tcw/tcw-config.yaml").unlink()` | code ≠ 0 and out is `""` (AC 6) | red: prints MAIN, code 0 |
| `test_a_worktree_in_a_main_checkouts_worktrees_folder_finds_that_checkouts_project` | the contrast case: Y's linked worktree at `MAIN/.worktrees/p`, no linked worktree of X | code 0, out `f"{main}\n"` (AC 9) | green (control) |

Each of the three-repository layouts (cases 5 and 7) is built inline in its
test with `proj`, a `.gitignore` per repository naming its nested folders,
`git init -q -b main` and `_commit_all`, as `_siblings` does. Two layouts do
not justify a third helper.

### 1b. `tests/migrate/test_migrate_search_worktrees.py`

Import `_main_with_a_child` and `_copy` from `tests.test_manifest_worktree`,
as this file already imports that module's other helpers.

| Test | Layout | Asserts | Today |
| --- | --- | --- | --- |
| `test_a_copy_kept_inside_its_own_main_checkout_predicts_the_copys_root` | case 1 | `family.search_4(w / "p", "r") == [w]`, and `tcw(w/p, "project", "path", "r")` prints `w` (AC 7, first half; the same pairing `_agree` makes, written out because `_agree` is fixed to the ID `r2`) | red: returns `[w, MAIN]` |
| `test_migrating_a_copy_inside_its_main_checkout_writes_what_the_main_checkout_writes` | case 1, except that Y's project is 3.x on `main`: a root `tcw-config.yaml` reading `id: p\nprojects:\n  parent:\n    r: ..\n` and no `.tcw/`, so both of Y's checkouts are 3.x | `tcw(w / "p", "migrate", "--no-jira")` code 0, then `(w / "p" / ".tcw/tcw-manifest.yaml")` either does not exist or has no `r` under `projects`; and the same assertion after `tcw(child_main, "migrate", "--no-jira")` (AC 7, second half) | red: the copy's run writes `r: {path: ..}` |

`_main_with_a_child` takes one more keyword for this,
`child_3x: str | None = None`. When given, it is Y's root `tcw-config.yaml`
text, written in place of the 4.0 configuration and manifest.

**Done when:** `pytest tests/test_manifest_worktree.py
tests/migrate/test_migrate_search_worktrees.py` reports exactly the tests
marked red above as failing, each with the failure the "Today" column
names, and the two controls passing. Read each failure's message. A test that
fails for another reason, such as a fixture git error, is a broken test, not
a reproduction. Record the run in the implement round.

## Step 2 — The fix in `search_rounds`

**File changed:** `tcw/store/project.py`.

1. Add a module-level cache beside `_ANCHOR_CACHE` and `_REPOSITORY_CACHE`:
   `_CHECKOUT_CACHE: dict[Path, tuple[Path, Path] | None] = {}`. Like them,
   it lives as long as the process (the comment at `:50-54` says why, and
   applies unchanged). No code clears those two; two tests do
   (`tests/test_run_in_folder.py:234`, `tests/test_worktree_remote_forms.py:110`),
   because they change a layout within one process. Read both. If either
   would now see a stale answer from the new cache, clear it there too.
2. Add `_checkout_of(folder: Path) -> tuple[Path, Path] | None`. It returns
   `(top, main)` for the git checkout `folder` is in, main or linked, and
   None outside one. `top == main` for a main checkout. It is cached as
   above. For a linked worktree it reuses `worktree_anchors(folder)`. For a
   main checkout it asks `git rev-parse --path-format=absolute
   --show-toplevel` through `_git_lines`. A submodule's answer follows
   `worktree_anchors`' existing rule (`_probe_worktree`, `:234-238`).
3. Add `_left_out_of_the_climb(start: Path) -> list[tuple[Path, Path]]`. It
   lists, nearest first, each `(linked, main)` for a linked worktree
   enclosing `start`, found by walking checkouts outward: `_checkout_of(start)`,
   then `_checkout_of(top.parent)`, until None or until `top.parent == top`.
   It keeps only those with `linked != main` and `_below(linked, main)` not
   None.
4. In `search_rounds`, build the round read as written, for the active
   worktree's case only (after the early return at `:382-383`), as
   `(named_by.parent, named_by, enclosing_as_written)`. Here
   `enclosing_as_written` is `list(named_by.parents)` without each folder
   `F` for which some `(linked, main)` from
   `_left_out_of_the_climb(top.parent)` has
   `F != linked and _below(linked, F) is not None and _below(F, main) is not None`.
   Use it in both returns that give that round, `:393` and `:394`. The early
   return at `:382-383` keeps the plain `as_written`: the non-goal in the
   spec.
5. Extend the docstring of `search_rounds`. In the paragraph on a worktree
   read from where it is, add one sentence: its climb leaves out a linked
   worktree's main checkout, and the folders between that worktree and it,
   when the linked worktree holding this one, however far out, is stored
   inside its own main checkout; the folders above that main checkout are
   still climbed (TCW-120).
6. `tcw/migrate/family.py` is **not** changed. `search_4` calls
   `search_rounds` (`:230`); the step 1b tests prove that it follows.

**Done when:** every test from Step 1 passes, including the two controls.
`pytest tests/test_manifest_worktree.py tests/migrate/ tests/test_override_in_linked_worktree.py tests/test_worktree_remote_forms.py tests/test_worktree_sibling_nodes.py`
passes, which covers AC 8 (the named existing tests among them). Then
**mutation-check** the new behaviour, as the evals rule asks of any
assertion: (a) make `_left_out_of_the_climb` return `[]`, and confirm the
step 1 tests marked red go red again with their original messages; (b)
make the walk in it stop after the first checkout, and confirm
`test_a_copy_three_deep_finds_the_outermost_root_in_the_copy` and
`test_a_clone_between_the_worktrees_does_not_hide_the_outer_one` go red
while case 1 stays green. Restore, and record both in the implement round.

**Commit** Steps 1 and 2 together: `TCW-120: the search from a copy kept
inside its main checkout no longer climbs into it`.

## Step 3 — Whole suite as CI runs it

**Files changed:** none.

Run bare `pytest` from the worktree's root, with a virtual environment made
for this worktree, as `CLAUDE.md` "Working in a git worktree" describes
(`.venv/bin/pytest`). CI runs bare `pytest`, not `python -m pytest`.

**Done when:** it passes (AC 10). A failure in a test this change did not
touch is read before anything else is changed: it may be the shared editable
install answering instead of the worktree's code.

## Step 4 — Documentation Sync

**Files created or changed:** listed per entry. Run the `documentation-sync`
skill against the entries from `tcw work docs`. Expected outcome, entry by
entry:

| Entry | Fires? | What changes |
| --- | --- | --- |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | New file `docs/changelogs/upcoming/TCW-120-from-a-copy-of-worktrees-kept-inside-its-own-main-checkout-the-search-for-a-project-climbs-past-the-copy.md`, under `## Fixed`: `search_rounds` leaves out of its climb the folders between an enclosing linked worktree and its own main checkout, and that main checkout, when the linked worktree is stored inside it, for every checkout outward; this also fixes `tcw migrate`'s prediction (`search_4`), which wrote a needless manifest entry in such a copy. Name the layouts (`.claude/worktrees`). |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes: user-facing behaviour changes | New file of the same name, under `## Fixes`: in plain words, running TCW from a copy of nested worktrees kept inside the project's own folder (where Claude Code keeps its worktrees) no longer reports a project as "declared by more than one folder", or asks to migrate the original, when looking up a project no manifest lists. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/multi-repo.md` | In "Git worktrees", after the sentence ending "in the folders the copy was made from." (line 630), add a sentence. In plain words: looking from the worktree means climbing its own enclosing folders, but never into the main checkout of a worktree that holds it when that worktree is kept inside its own main checkout (as Claude Code's `.claude/worktrees` is), nor the folders between them; the folders above that main checkout are still looked in. The same holds for a worktree kept in such a worktree that is not a copy. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: S-4 | Under S-4 **Seen**, add that Claude Code keeps worktrees at `.claude/worktrees/<name>`, inside the main checkout. Under **Requirements**, add a bullet: a copy made of linked worktrees one inside another, kept inside the main checkout it was made from, finds its own projects by the search and never the main checkout's copy on another branch (`search_rounds` in `tcw/store/project.py`; `tests/test_manifest_worktree.py`). |
| Capability record `docs/capabilities/cli/run-from-a-git-worktree/description.md` | yes: declared `changed` in `capabilities.yaml` | After "...is not found rather than read from the folders the copy was made from.", add: the search never climbs into the main checkout of a worktree holding this one when that worktree is kept inside its own main checkout, as Claude Code keeps its worktrees, so the copy's own project is found once. Change it with `tcw capabilities` if a command edits a description, or by editing the file directly otherwise. |
| `README.md` [Public-API] | no | The README does not describe the search's rules for worktrees. |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | no | No skill describes the search's folders. Check with `grep -rln "worktree" skills/` and confirm nothing states the climb. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No key changes. `stores.md` describes store paths, which do not climb. |
| `docs/guide/jira.md` [Jira-Change] | no | Nothing about Jira changes. |

Also checked, and expected unchanged: `docs/migration-guide-3.X-to-4.0.0.md`
lines 53-61. They describe store paths in a copy of nested worktrees, not
the search.

**Done when:** each "yes" row's file exists or is changed as described, and
`tcw validate` passes. Commit as `TCW-120: documentation`.

## Verification beyond the tests

- Re-run the reproduction scripts, kept outside the repository, against the
  fixed code: cases 1-7 from the spec, plus the `tcw migrate` comparison.
  Record the outputs in the implement round beside the outputs the spec
  recorded.
- Not tested, as the spec says: git submodules inside these layouts. The
  submodule rule in `_probe_worktree` is relied on unchanged. Windows is also
  not tested, as no test in this file runs there.

## Coverage of the acceptance criteria

| AC | Step |
| --- | --- |
| 1, 2, 3, 4, 5, 5a, 6, 9 | 1a, made green by 2 |
| 7 | 1b, made green by 2 |
| 8 | 2 ("Done when") |
| 10 | 3 |
| 11 | 4 |
