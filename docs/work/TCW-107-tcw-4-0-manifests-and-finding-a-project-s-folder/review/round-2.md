---
verdict: rejected
judges: 2
---

# Review round 2 — TCW-107

Reviewed by a separate read-only agent (the `tcw:reviewer` agent) on
2026-10-23 at `c1b19027`, against review round 1's items (a) to (e) and the
fixes in `3603c970..HEAD`. The dispatching session checked the finding below
against the code and spec 5.1 before writing this round.

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/test_manifest_worktree.py
  tests/test_manifest_cli.py tests/test_store_provisioning.py`:
  `220 passed, 13 skipped in 29.45s`.
- The full suite as CI runs it, at `6ab800b0` (the last code commit):
  `5441 passed, 118 skipped in 607.45s`, recorded in `implement/round-2.md`.
- `.venv/bin/tcw validate`: `0 errors, 1 warning, 0 unresolved`; the warning
  is the repository's deliberate 3.x root `tcw-config.yaml`.
- The dispatching session confirmed that
  `test_a_borrowed_personal_manifest_reports_a_missing_project_once` fails
  with `3f4060c0`'s code change reverted and passes with it.
- `documentation-sync`: unchanged from round 1. The changelog entry now has
  the two lines round 1 asked for; the other entries are as round 1 records.

## Round 1's items

- (a) Resolved. The `find-a-projects-folder-from-its-id` record now says the
  skip of `Desktop`, `Documents` and `Downloads` happens on macOS, matching
  `_protected` (`tcw/store/project.py:1687-1699`).
- (b) `read-a-file-by-the-format-version-it-records`: resolved, checked with
  a `tcw-version: 9.0.0` project placed by each manifest, by the variable and
  by the search.
- (b) `point-tcw-at-a-project-i-already-have`: **not resolved.** Lines 32-35
  say an overridden committed entry "is reported only when that entry is
  itself wrong, and then as a warning". An overridden entry whose folder is
  not on this machine is still reported as `unresolved`, as spec 5.1 says
  (only rows b to e become warnings). Reproduced: committed `lib: ../gone`
  with `TCW_PROJECT_LIB` set gives `0 errors, 0 warnings, 1 unresolved`.
- (c) Resolved. `manifest_files()` builds the path `_manifests_of` reads and
  leaves the personal file out when personal files are skipped; its only
  caller is the filter at `tcw/cli.py:240`. The double report is gone in the
  worktree, in the main checkout, and with `TCW_NO_PERSONAL_CONFIG=1`.
- (d) Resolved: the two changelog lines, and the AC 8 and AC 22 test gaps
  (`tests/test_manifest_cli.py:289-292`, `tests/test_store_provisioning.py:531-540`).
- (e) Resolved. Round 2 corrects the claim about `git config --get
  core.worktree`, which predates this item; TCW-107 adds no git call.

## A further finding, folded in

When an override places the project on this machine, the overridden committed
entry pointing at a missing folder still says "project 'lib' is not on this
machine", which is untrue on this machine. Decided by the dispatching
session, 2026-10-23: fold it into this item rather than open a separate one,
since the fix is one suffix. The finding stays `unresolved`, as spec 5.1
requires, and gains the same `(overridden on this machine by <the personal
manifest's path, or the variable>)` that rows b to e already carry. This
amends spec 5.1 for row a only in its wording.

## What implement must do

- (a) Reword `docs/capabilities/cli/point-tcw-at-a-project-i-already-have/description.md:32-35`
  to give all three outcomes for an overridden committed entry: a folder not
  on this machine is still `unresolved`; wrong in any other way (not a
  project, a 3.x project, an unreadable version, another ID) is a warning;
  correct is not reported.
- (b) Add the `(overridden on this machine by …)` suffix to the `unresolved`
  finding for an overridden committed entry (`manifest_findings`,
  `tcw/store/project.py:1601-1631`), with a test for the variable and for the
  personal manifest, and say in the record that the finding names the
  override.
- (c) Write `implement/round-3.md`, with a full suite run.
