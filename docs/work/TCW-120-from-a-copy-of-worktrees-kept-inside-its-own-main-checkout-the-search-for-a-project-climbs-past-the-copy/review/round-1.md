---
verdict: accepted
judges: 2
---
# Review round 1 (TCW-120)

**Verdict: accepted.** This round judges implement round 2
(`implement/round-2.md`, the code review's fixes in `6be60856`, `0e1bdd5a`
and `6e6f88b0`) and the spec note added in `09e1727b`, on branch `v4.0.1` at
`09e1727b`, which also holds TCW-119.

## Who reviewed

A separate read-only reviewer agent (the `tcw:reviewer` type), which did not
write the code, read the change against the spec, plan and
`capabilities.yaml`, ran the tests, checked the new tests against the old
code and by mutation, and recommended `accepted`. This session ran the full
suite and the documentation evaluation and wrote this round. It did not
write the code either.

Earlier reviews this round relies on:

- The first adversarial code review returned NOT DONE. Its findings S1, S2,
  S3, T1, D1 and N4 were accepted and fixed in `6be60856`, `0e1bdd5a` and
  `6e6f88b0` (implement round 2). N1 (a bare repository) and N5 (`_git_lines`)
  are recorded in the spec's notes, one as known behavior kept and one as a
  separate change.
- A bounded recheck of those fixes returned DONE. Its one leftover, a main
  checkout made with `git init --separate-git-dir`, is recorded in the spec
  as a separate change (`09e1727b`).
- A combined review of TCW-119 and TCW-120 together found no interaction
  defect: neither change reaches the other's code paths. The one point of
  contact is that, in a copy made of worktrees, an `extends` source that
  TCW-119's routing consults can now be found once in the copy instead of
  being refused as found twice, which moves the answer toward the one the
  main checkout already gives.

## The suite, run as CI runs it

One run serves both TCW-119 and TCW-120, since they ship together on this
branch. A fresh clone of the worktree's branch, checked out at `v4.0.1`, was
run with `bash ~/.tcw-4.0-release/ci-suite.sh` (bare `pytest` in a new
virtual environment with a scratch home folder and no `TCW_` variables, then
the web build):

- HEAD line: `== Tue Nov  3 18:33:38 UTC 2026 in .../scratchpad/c401b, HEAD 09e1727b00119683ca6c76565ff231379084103e`
- Summary line: `================ 8297 passed, 115 skipped in 1317.17s (0:21:57) ================`
- Then `== suite and web build passed`, exit 0.

`tcw validate` in this repository: `0 errors, 0 warnings, 0 unresolved`.

The reviewer also ran the six worktree test files on the branch (108
passed), ran the two changed test files against `main`'s
`tcw/store/project.py` (13 failed, 38 passed: exactly the tests that should
fail without the fix fail, and the unchanged-layout tests pass), and made
two mutations: removing the early filter in `search_rounds` turns the case 8
and case 9 tests red, and making `_under_a_linked_worktree` always true
turns `test_a_search_from_a_plain_checkout_starts_no_git_process` red.

## Acceptance criteria

Tests are in `tests/test_manifest_worktree.py` unless another file is named.
"Red before" means the test fails on `main`'s code.

1. **Met.** `test_a_copy_kept_inside_its_own_main_checkout_finds_the_root_in_the_copy`
   asserts `(0, "<w>\n", "")`. Red before.
2. **Met.** `test_a_copy_kept_inside_a_3x_main_checkout_finds_the_root_in_the_copy`:
   exit 0, prints `w`, no `tcw migrate` on standard error. Red before.
3. **Met.** `test_a_copy_kept_outside_its_main_checkout_finds_the_root_in_the_copy`
   (passes before and after).
4. **Met.** `test_a_worktree_in_a_linked_worktree_inside_its_main_checkout_finds_the_root_there`.
   Red before.
5. **Met.** `test_a_copy_three_deep_finds_the_outermost_root_in_the_copy`.
   Red before.
5a. **Met.** `test_a_clone_between_the_worktrees_does_not_hide_the_outer_one`.
   Red before.
5b. **Met.** `test_a_related_projects_search_inside_the_copy_finds_the_root_in_the_copy`
   (`project path r` and `project list`, each exit 0). Red before, and red
   under the first mutation.
5c. **Met.** `test_a_clone_kept_in_a_copy_inside_its_main_checkout_finds_the_root_in_the_copy`.
   Red before.
5d. **Met.** `test_a_separate_repository_between_the_copy_and_its_main_checkout_is_still_searched`
   checks both the `tools` and the `r` answers.
5e. **Met.** `test_a_project_above_the_main_checkout_is_still_found_from_the_copy`.
6. **Met.** `test_a_copy_inside_its_main_checkout_lacking_the_root_does_not_find_the_mains`:
   non-zero exit, empty standard output, `MAIN`'s path absent from both
   streams, and the "no project with ID 'r' is known or found" error.
7. **Met.** In `tests/migrate/test_migrate_search_worktrees.py`:
   `test_a_copy_kept_inside_its_own_main_checkout_predicts_the_copys_root`
   (`search_4` returns `[w]` from the copy and `[MAIN]` from `MAIN/p`) and
   `test_migrating_a_copy_inside_its_main_checkout_writes_what_the_main_checkout_writes`
   (no `r` entry written from either). Both red before.
8. **Met.** The seven named tests exist and pass, and every test in
   `tests/migrate/test_migrate_search_worktrees.py` passes.
9. **Met.** `test_a_worktree_in_a_main_checkouts_worktrees_folder_finds_that_checkouts_project`.
10. **Met.** The suite run above.
11. **Met.** `docs/guide/multi-repo.md` ("Git worktrees"),
    `docs/capabilities/cli/run-from-a-git-worktree/description.md` and
    `docs/use-cases.md` S-4 each state the rule as the code keeps it
    (wherever the command runs; folders of the main checkout's own
    repository left out; a separate repository between them still searched;
    the climb goes on above the main checkout), and none claims more. Both
    `upcoming/` entry files exist, named by the item's folder.

## Capability records

`capabilities.yaml` lists one path under `changed:`,
`tcw.capabilities/cli/run-from-a-git-worktree`. The record is present and
its new sentences match the code: the early filter in `search_rounds`
applies whenever a `.git` file is at or above the folder searched from;
`_left_out_of_the_climb` compares each folder's git common folder with the
main checkout's; the walk stops at the first folder not below the main
checkout, so folders above it stay searched (criterion 5e).

## Documentation entries (`documentation-sync`)

The `documentation-sync` skill was run over the whole branch difference
(`main...HEAD`). For this item:

| Entry | Fires? | Answered by |
| --- | --- | --- |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | the item's file, `cec54e28`, corrected in `0e1bdd5a` |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | the item's file, `cec54e28`, corrected in `0e1bdd5a` |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | `docs/guide/multi-repo.md` ("Git worktrees"), `cec54e28` and `0e1bdd5a` |
| `docs/use-cases.md` [Project-Setup-Change] | yes | S-4, `cec54e28` and `0e1bdd5a` |
| `docs/guide/jira.md` [Jira-Change] | no | the Jira backend is not involved |
| `README.md` [Public-API] | no | its worktree passage (around line 814) is about the editable install, not the search |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | no | no skill describes the search's folders |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | no key changes; `stores.md` and `personal.md` mention linked worktrees only for store paths and personal configuration |

Capability record: `docs/capabilities/cli/run-from-a-git-worktree/description.md`, `cec54e28` and `0e1bdd5a`.

## Notes, not defects

- `tests/test_run_in_folder.py` clears only `_ANCHOR_CACHE`, while the probe
  now also reads the new `_CHECKOUT_CACHE` (`tcw/store/project.py`). The test
  passes because its paths are unique to it; its docstring's promise that
  clearing makes the probe run is now weaker. A long-running `tcw serve`
  keeps this cache for the life of the process, as it already kept
  `_ANCHOR_CACHE`.
- The documents' claim for a command run outside every worktree rests on the
  early return's logic and implement round 2's manual script, not on a test.
- The originating report is not a GitHub issue, so nothing waits on
  publication for this item beyond the 4.0.1 release itself.
