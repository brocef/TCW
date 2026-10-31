---
verdict: rejected
judges: 1
---

# Review round 1 — TCW-107

Reviewed by a separate read-only agent (the `tcw:reviewer` agent), which did
not write the code, on 2026-10-23 at `dea2e0a4`. The dispatching session
checked each finding below against the repository before writing this round.
TCW-107's own commits are `3fe4a61e~1..HEAD`; the range `5b35e655..HEAD` also
holds TCW-106's review and qa commits, which were not judged here.

## Checks run

- The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, at
  `cd51a2ba`: `5440 passed, 118 skipped in 497.74s`. The only later commit
  edits `implement/round-1.md`.
- The tests for the changed code (21 files: manifest, lookup, worktree,
  registry, provisioning, documented commands, taxonomy, config, open,
  delegation): `1454 passed, 59 skipped in 95.49s`.
- `.venv/bin/tcw validate`, with HOME and the XDG folders in a scratch
  folder: `0 errors, 1 warning, 0 unresolved`, exit 0. The warning is this
  repository's deliberate 3.x root `tcw-config.yaml`.
- `documentation-sync`, through `tcw work docs`: the two `upcoming/` entry
  files are written. The `skills/work/SKILL.md` exit-5 line is changed as the
  spec requires. README, `docs/guide/`, `skills/configure/references/` and
  `docs/use-cases.md` fire and are deferred to TCW-117, whose spec covers
  them; the TCW-107 spec's non-goals allow that, and nothing ships before
  4.0. `docs/guide/jira.md` does not fire. The changelog entry leaves out
  two developer-visible behaviours (see finding 5).

## Acceptance criteria

| AC | Result | Evidence |
|---|---|---|
| 1 | met | `test_manifest_cli.py::test_ac1_a_manifest_entry_both_forms` |
| 2 | met | `test_ac2_a_manifest_format_problem`, 14 cases: exit 1, the `.tcw/tcw-manifest.yaml` location, no "tcw migrate" |
| 3 | met | `test_ac3_the_personal_manifest` (absolute path, `~`, `=1`, `=true`) |
| 4 | met | `test_ac4_a_manifest_entry_connects_nothing` |
| 5, 5a, 6 | met | `test_ac5_…`, `test_ac5a_…`, `test_ac6_…` |
| 7 | met | `test_ac7_an_entry_decides_and_a_project_not_here`: both messages, no merging, exit 5 |
| 8 | met, with a test gap | `test_ac8_an_entry_that_is_wrong`, `test_ac8_an_empty_folder_is_not_on_this_machine`. The uninitialised-submodule test checks `tcw validate` only, not `projects list` or `work show` (finding 4) |
| 8a | met | `test_ac8a_an_overridden_entry_is_a_warning` |
| 9–14 | met | `test_ac9_…` to `test_ac14_…` |
| 15 | met | `test_ac15_a_location_in_projects_is_refused`, `…_holding_only_an_id_are_accepted` |
| 16–19, 26 | met | `tests/test_manifest_worktree.py`, with real `git worktree add` |
| 20 | met | `test_ac20_init_and_the_ignore_rule` |
| 21 | met | `test_ac21_a_single_project_pays_nothing` |
| 22 | met, with a test gap | `test_ac22_*`; the `TCW_PROJECT_SERVER` case asserts `checkout_of` is None but not how the store then resolves (finding 4) |
| 23 | met | the full suite above |
| 24 | met | the AC 24 block in `tests/test_project_lookup.py` |
| 25 | met | `test_ac25_…`, `test_one_answer_whichever_project_runs` |
| 27 | met | `test_ac27_each_candidate_is_read_once_by_the_registry` |

Decisions checked: an empty or `.git`-only folder counts as not on this
machine, with TCW-115's wording (`tcw/store/project.py:1576-1581`,
`:1643-1653`); `UnknownProject` subclasses `ProjectGraphError` and no code yet
catches either separately; `Unreachable` carries `.project` and `.repository`
(TCW-114's handoff); a `repository` or branch starting with `-` is a manifest
problem (TCW-115's handoff, `tcw/store/manifest.py:148-160`). TCW-107 adds no
git call. One note for TCW-114: besides `git rev-parse`, the registry's
worktree probe also runs the read-only `git --git-dir <common> config --get
core.worktree` (`project.py:186-187`), which predates this item, so
`round-1.md`'s "the only process the lookup starts is git rev-parse" is not
quite true.

## Capability records

Every path in `capabilities.yaml` is present. Three do not match the code:

1. **Rejection.** `docs/capabilities/cli/find-a-projects-folder-from-its-id/description.md:17`
   says the search never reads inside `Desktop`, `Documents` or `Downloads`
   in the home folder. The code skips them only on macOS
   (`_ON_MACOS`, `project.py:228`, checked in `_protected` at `:1689`). On
   Linux the search tests `~/Documents` like any other folder next to the
   project.
2. `docs/capabilities/cli/point-tcw-at-a-project-i-already-have/description.md`
   says `tcw validate` reports a committed entry the variable overrides as a
   warning. `manifest_findings` warns only when that overridden entry is
   itself wrong; a correct one produces nothing.
3. `docs/capabilities/cli/read-a-file-by-the-format-version-it-records/description.md`
   says an unreadable version is a problem with the manifest entry that
   placed the project. That holds only when a manifest placed it; a project
   found by the search or by `TCW_PROJECT_<ID>` gets a problem naming its
   folder (`project.py:289`, `:785`).

The other records and the taxonomy terms match the code.

## Defects

4. **`tcw validate` reports a project twice in a linked worktree that uses
   the main checkout's personal manifest.** Reproduced: `app` declares
   `upstream: {lib:}`; its ignored `.tcw/tcw-manifest.local.yaml` places
   `lib` at `../gone`; after `git worktree add`, validate in the worktree
   gives `2 unresolved` where the main checkout gives 1. `manifest_files()`
   (`project.py:1591-1594`) names the worktree's own personal manifest, while
   the deciding entry comes from the main checkout's, found by
   `personal_file` (`project.py:95-118`), so `_cmd_validate`'s filter misses
   it and `manifest_findings` reports the entry again.
5. The changelog entry omits the macOS-only skip of Desktop, Documents and
   Downloads, and the refusal of a `repository` starting with `-`.
6. Test gaps: AC 8's submodule case and AC 22's `TCW_PROJECT_SERVER` case, as
   in the table.

None needs a separate item.

## What implement must do

- (a) Make the `find-a-projects-folder-from-its-id` record say the skip
  happens on macOS. Decided by the dispatching session: keep the code's
  macOS-only condition and change the record, since the skip exists only to
  avoid macOS's permission prompt and other systems have no such prompt.
- (b) Reword `point-tcw-at-a-project-i-already-have` so the warning is only
  for a wrong overridden entry, and `read-a-file-by-the-format-version-it-records`
  so the manifest-entry wording applies only when a manifest placed the
  project.
- (c) Build the personal path in `manifest_files()` with
  `personal_file(root, LOCAL_MANIFEST_NAME, self._anchors)`, with a worktree
  test showing one unresolved finding.
- (d) Add the two changelog lines and close the two test gaps.
- (e) Correct `round-1.md`'s claim about the processes the lookup starts, or
  record the correction in round 2.
