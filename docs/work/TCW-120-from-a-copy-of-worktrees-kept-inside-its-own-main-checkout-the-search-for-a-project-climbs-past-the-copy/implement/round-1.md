# Implement round 1 — TCW-120

Built on the branch `worktree-agent-a388988fcf0063238`, in the worktree
`.claude/worktrees/agent-a388988fcf0063238`, with the code under test run
from that worktree's own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). The spec and plan were revised first, after a spec review
returned NOT DONE (commit `c026f48c`); this round builds the revised plan.
No review or qa round has judged an earlier implement round, so this round
answers no rejection. It gives no verdict.

## Step 1 — tests, run red against today's code

Added to `tests/test_manifest_worktree.py` a section "A copy kept inside the
main checkout it was made from", with the helpers `_main_with_a_child`,
`_copy`, `_migrate_branch`, `_repo` and `_prints`, and twelve tests; and two
tests to `tests/migrate/test_migrate_search_worktrees.py`.

Run before the fix, `pytest tests/test_manifest_worktree.py
tests/migrate/test_migrate_search_worktrees.py`:

```
FAILED tests/test_manifest_worktree.py::test_a_copy_kept_inside_its_own_main_checkout_finds_the_root_in_the_copy
FAILED tests/test_manifest_worktree.py::test_a_copy_kept_inside_a_3x_main_checkout_finds_the_root_in_the_copy
FAILED tests/test_manifest_worktree.py::test_a_worktree_in_a_linked_worktree_inside_its_main_checkout_finds_the_root_there
FAILED tests/test_manifest_worktree.py::test_a_copy_three_deep_finds_the_outermost_root_in_the_copy
FAILED tests/test_manifest_worktree.py::test_a_clone_between_the_worktrees_does_not_hide_the_outer_one
FAILED tests/test_manifest_worktree.py::test_a_related_projects_search_inside_the_copy_finds_the_root_in_the_copy
FAILED tests/test_manifest_worktree.py::test_a_clone_kept_in_a_copy_inside_its_main_checkout_finds_the_root_in_the_copy
FAILED tests/test_manifest_worktree.py::test_a_separate_repository_between_the_copy_and_its_main_checkout_is_still_searched
FAILED tests/test_manifest_worktree.py::test_a_copy_inside_its_main_checkout_lacking_the_root_does_not_find_the_mains
FAILED tests/migrate/test_migrate_search_worktrees.py::test_a_copy_kept_inside_its_own_main_checkout_predicts_the_copys_root
FAILED tests/migrate/test_migrate_search_worktrees.py::test_migrating_a_copy_inside_its_main_checkout_writes_what_the_main_checkout_writes
11 failed, 37 passed in 17.27s
```

Each failure was read, and each is the defect the plan's "Today" column
names: the eight `project path` tests failed with "declared by more than one
folder near this one: …/w and …/MAIN" (or `…/ZM`, `…/WS`), the 3.x test with
"…/MAIN: is a TCW 3.x project … run 'tcw migrate'", the lacking-the-root test
with `code=0` printing `…/MAIN`, the prediction test with `[w, MAIN]`, and
the migrate test with the copy's manifest holding `r: {path: ..}`. The three
controls passed: the copy kept outside MAIN, the project above MAIN, and the
worktree in MAIN's own `.worktrees/` folder.

## Step 2 — the fix

`tcw/store/project.py`:

- `_CHECKOUT_CACHE`, beside the other two caches.
- `_under_a_linked_worktree(folder)`: a `.git` that is a file in `folder` or
  above it; disk only, no git process.
- `_checkout_of(folder)`: `(top, main, common)` from one `git rev-parse
  --show-toplevel --git-common-dir`, cached.
- `_left_out_of_the_climb(start)`: walks the checkouts outward from `start`,
  main or linked; for each linked worktree inside its own main checkout,
  lists the folders enclosing it, up to and including the main checkout,
  that are the main checkout or share its git common folder
  (`_repository_of`). A guard stops the walk when a checkout is not strictly
  further out.
- `_climb(named_by, start)`: `named_by`'s enclosing folders without those,
  compared with `_below`.
- `search_rounds`: the early return uses `_climb(named_by, named_by)` when
  `_under_a_linked_worktree(named_by)`, and the plain climb otherwise; after
  the `read_as_written` check, the round read as written uses
  `_climb(named_by, top.parent)`. `from_main` is unchanged. The docstring
  gains a paragraph stating the rule.

After the fix, the same two files: `48 passed in 18.17s`. The plan's wider
set (`tests/test_manifest_worktree.py tests/migrate/
tests/test_override_in_linked_worktree.py tests/test_worktree_remote_forms.py
tests/test_worktree_sibling_nodes.py tests/test_run_in_folder.py`):
`478 passed in 217.70s`.

### Mutation checks

Each mutation was applied to the fixed file, the two test files were run,
and the file was restored (confirmed identical afterwards).

| Mutation | Tests that went red |
| --- | --- |
| (a) `_left_out_of_the_climb` returns nothing | the same 11 as Step 1 (11 failed, 37 passed) |
| (b) the walk stops after the first checkout | three deep, clone between, clone kept in a copy (3 failed); case 1 stayed green |
| (c) the climb truncated at the linked worktree | project above the main checkout ("no project with ID 'o' is known or found"), and the separate-repository test (2 failed) |
| (d) the same-repository test dropped | separate repository between the copy and MAIN ("no project with ID 'tools' is known or found") (1 failed) |
| (e) the early return keeps the plain climb | related project's search inside the copy, clone kept in a copy (2 failed) |

## Step 3 — whole suite as CI runs it

Bare `.venv/bin/pytest` from the worktree's root:

```
================ 8285 passed, 115 skipped in 1075.11s (0:17:55) ================
```

## Step 4 — documentation

- `docs/guide/multi-repo.md`, "Git worktrees": a sentence stating the rule.
- `docs/capabilities/cli/run-from-a-git-worktree/description.md`: the same
  sentence (the capability declared `changed` in `capabilities.yaml`).
- `docs/use-cases.md` S-4: **Seen** names `.claude/worktrees/<name>`; a new
  requirement states the rule.
- `docs/changelogs/upcoming/<folder>.md` and
  `docs/release-notes/upcoming/<folder>.md`, named by this item's folder.
- Not changed, checked: `README.md`, `docs/guide/jira.md`, the skills
  (`grep -rln worktree skills/` names only `configure/references/stores.md`
  and `personal.md`, about store paths and personal files, not the search),
  and the configuration references (no key changes).

The sentence, in all three places, says "looking from where a worktree is",
so it does not cover the second round from the main checkout, which this
change leaves alone. `tcw validate`: `0 errors, 0 warnings, 0 unresolved`.

## Reproductions, rerun against the fixed code

The layouts kept outside the repository, with `.venv/bin/tcw`:

```
case1 migrated  path r: case-migrated/MAIN/.claude/worktrees/w  [exit 0]
case2 legacy    path r: case-legacy/MAIN/.claude/worktrees/w  [exit 0]
case3 outside   path r: case-outside/elsewhere/w  [exit 0]
case4 nocopy    path r: case-nocopy/MAIN/.claude/worktrees/w  [exit 0]
case5 three     path z: case-three/ZM/.claude/worktrees/w  [exit 0]
case6 lacking   path r: no project with ID 'r' is known or found near this one; check the spelling  [exit 1]
case7 clone     path z: case-clone/ZM/.claude/worktrees/zw  [exit 0]
contrast mainwt path r: case-mainwt/MAIN  [exit 0]
case8 mono      list  : p s  [exit 0]
case8 mono      path r: mono/MAIN/.claude/worktrees/w  [exit 0]
case9 gap       path ws: gapbase/WS/.claude/worktrees/w  [exit 0]
case10 tools    path tools: tools/MAIN/tools  [exit 0]
case10 tools    path r: tools/MAIN/tools/wt/w  [exit 0]
```

Before the fix, cases 1, 2, 4, 5, 7, 8 (both commands), 9 and 10's `r` failed
as the spec records, and case 6 printed `MAIN`. The `tcw migrate`
comparison: `tcw migrate --dry-run --no-jira` in the copy's 3.x `p` now
lists no manifest to write (only `.tcw/.gitignore`, `.tcw/tcw-config.yaml`
and the deletion of the root `tcw-config.yaml`), where before it wrote
`.tcw/tcw-manifest.yaml` with `r: { path: .. }`.

## What the plan or spec got wrong

- The plan's `_checkout_of` returned `(top, main)`, which would have needed
  a separate `_repository_of(main)` call for each linked worktree found to
  learn its common folder. It returns `(top, main, common)` instead, from
  the same single `git rev-parse`, so case 1 costs the four calls the spec
  states, not five.
- The plan's `_left_out_of_the_climb` returned a set; it returns a list,
  since the folders are compared with `_below` (folder identity), not by
  hashing their text.
- The plan did not say what stops the walk if git ever answered a checkout
  no further out than the last; a guard now ends the walk there.
- The plan's case 4 step would have rewritten `w/.gitignore`; X's linked
  worktree already has MAIN's `.gitignore`, so the test does not touch it.

## Records changed

- Capability `tcw.capabilities/cli/run-from-a-git-worktree`: its
  `description.md` gains the sentence above, as `capabilities.yaml`
  declares. No taxonomy change.

## Not done

- Submodules inside these layouts and Windows are not tested, as the spec
  says.
- The misleading "check the spelling" remedy when a copy lacks a project is
  a separate change (spec, Notes); no item was filed for it here.

## Commits

- `c026f48c` TCW-120: revise spec and plan after the spec review
- `cb2e5140` TCW-120: the search from a copy kept inside its main checkout no longer climbs into it
- `cec54e28` TCW-120: documentation
