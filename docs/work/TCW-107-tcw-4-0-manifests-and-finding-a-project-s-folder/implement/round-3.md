# Implement round 3 — TCW-107

Answers review round 2, items (a) to (c) of its "What implement must do".
Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). It gives no verdict.

## A wording amendment to spec 5.1, row a

Spec 5.1 says an entry in `tcw-manifest.yaml` that the personal manifest or
`TCW_PROJECT_<ID>` overrides is still checked, and that rows b to e are then
reported as a `warning` with `(overridden on this machine by <the personal
manifest's path, or the variable>)` added. It said nothing about row a, so an
overridden entry whose folder is not on this machine said only "project 'lib'
is not on this machine", which is untrue on a machine where the override
places it. The dispatching session decided on 2026-10-23, in review round 2,
to fold the fix into this item: row a's finding stays `unresolved`, as 5.1
requires, and gains the same suffix. This changes only the finding's wording,
not its kind, so the run's result is unchanged.

## What was done, item by item

- **(a) The record gives the three outcomes** (`1ac9226a`).
  `docs/capabilities/cli/point-tcw-at-a-project-i-already-have/description.md`
  now says that a committed manifest entry that `TCW_PROJECT_<ID>` or the
  personal manifest overrides is still checked, and that:
  - one pointing at a folder not on this machine is still reported as
    unresolved, and the report names the override;
  - one wrong in any other way (the folder holds no TCW project, holds a 3.x
    project, has a version that cannot be read, or declares another ID) is a
    warning rather than an error, naming the override;
  - a correct one is not reported.

  The earlier wording named only the variable, and said an overridden entry
  is reported "only when that entry is itself wrong, and then as a warning",
  which a missing folder contradicted.
- **(b) The `unresolved` finding names the override** (`1ac9226a`).
  `manifest_findings` (`tcw/store/project.py`) now works out which override
  places the project before it decides the finding's kind, and builds the
  `(overridden on this machine by …)` suffix once, adding it to the
  `unresolved` message as well as to the warning. Nothing changes for an
  entry that is not overridden, or for an entry in the personal manifest
  itself. The changelog entry's line on `tcw validate` says any finding for
  an overridden entry names the override.

  New test
  `tests/test_manifest_cli.py::test_ac8a_an_overridden_missing_entry_names_the_override`:
  `app`'s committed manifest places `lib` at `../gone`. With no override,
  `tcw validate` gives one `unresolved` finding without the suffix, and that
  message is kept. Then, once with the personal manifest placing `lib` at
  `../lib` and once with `TCW_PROJECT_LIB` set, the run exits 0 with no error
  or warning, and the single `unresolved` finding on `.tcw/tcw-manifest.yaml`
  is exactly the message without an override followed by `(overridden on this
  machine by <the personal manifest's path>)` or `(overridden on this machine
  by TCW_PROJECT_LIB)`.

  Before the code change, it failed in both cases: with the personal manifest
  first, and with the variable when that case was run alone; each time the
  finding ended `places it at ../gone` with no suffix. After it, it passes.
  `tests/test_manifest_cli.py` gives `50 passed`, and
  `tests/test_project_overrides.py`, `tests/test_validate.py`,
  `tests/test_manifest_worktree.py`, `tests/test_project_lookup.py` and
  `tests/test_store_provisioning.py` together give `251 passed, 25 skipped`.
  `.venv/bin/tcw validate` on this repository: `0 errors, 1 warning,
  0 unresolved`, the warning being the deliberate 3.x root `tcw-config.yaml`.

## The suite

`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it, at `f2af0cdc`
(2026-10-23): `5442 passed, 118 skipped in 496.20s`.
