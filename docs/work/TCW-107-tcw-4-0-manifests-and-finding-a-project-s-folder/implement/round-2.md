# Implement round 2 — TCW-107

Answers review round 1, items (a) to (e) of its "What implement must do".
Built on the `v4` branch in the worktree `.claude/worktrees/v4`, with the code
under test run from its own virtual environment (`.venv/bin/pytest`,
`.venv/bin/tcw`). It gives no verdict.

## What was done, item by item

- **(a) The search's skip of the folders macOS protects** (`7830a73f`).
  `docs/capabilities/cli/find-a-projects-folder-from-its-id/description.md`
  now says the search skips `Desktop`, `Documents` and `Downloads` in the home
  folder on macOS, which asks a person's permission before a program reads
  them. The code's `_ON_MACOS` condition is kept, as the dispatching session
  decided: the skip exists only to avoid that permission prompt, and other
  systems have no such prompt.
- **(b) Two records reworded to match the code** (`7830a73f`).
  - `point-tcw-at-a-project-i-already-have`: `tcw validate` reports a
    committed manifest entry that `TCW_PROJECT_<ID>` overrides only when that
    entry is itself wrong, and then as a warning; a correct overridden entry
    is not reported. This is what `manifest_findings` does: it skips every
    entry whose folder is found, and turns an error into a warning only when
    the personal manifest or the variable places the project.
  - `read-a-file-by-the-format-version-it-records`: a connected project whose
    version this TCW cannot read is a problem with the manifest entry only
    when a manifest entry placed it; when the search or `TCW_PROJECT_<ID>`
    found it, the problem names the project's own `.tcw/tcw-config.yaml`.
    Checked by running `tcw validate` in a scratch folder against a project
    with `tcw-version: 9.0.0` found each way: both errors begin
    `<folder>/.tcw/tcw-config.yaml: was written by TCW 9.0`.
- **(c) A project reported twice in a linked worktree** (`3f4060c0`).
  `manifest_files()` named the worktree's own `.tcw/tcw-manifest.local.yaml`,
  while the entry that decided came from the main checkout's file, which
  `_manifests_of` reads through `personal_file` when the worktree has none of
  its own. `_cmd_validate`'s filter therefore did not drop the lookup's
  record, and `manifest_findings` reported the entry a second time. It now
  builds the personal path with
  `personal_file(root, LOCAL_MANIFEST_NAME, self._anchors)`, and leaves the
  personal manifest out when personal files are skipped, the same way
  `_manifests_of` does. New test
  `tests/test_manifest_worktree.py::test_a_borrowed_personal_manifest_reports_a_missing_project_once`,
  with a real `git worktree add`: `app` declares `upstream: {lib:}`, its
  ignored personal manifest places `lib` at `../gone`, and `tcw validate`
  must report exactly one `unresolved` finding and `0 errors, 0 warnings,
  1 unresolved`, in the main checkout and in the worktree. Before the fix it
  failed in the worktree only, with `0 errors, 0 warnings, 2 unresolved` (one
  line for `.tcw/tcw-config.yaml`, one for the manifest); after it, it
  passes.
- **(d) The changelog entry and two test gaps** (`6ab800b0`).
  - `docs/changelogs/upcoming/TCW-107-tcw-4-0-manifests-and-finding-a-project-s-folder.md`
    gains two lines under "Changed": the search skips `Desktop`, `Documents`
    and `Downloads` directly in the home folder on macOS only, unless the
    project is already inside one; and a manifest `repository` URL or branch
    beginning with `-` is refused as a manifest problem. The line on
    `tcw validate` under "Added" now says an overridden committed entry is a
    warning when it is wrong, matching (b).
  - `tests/test_manifest_cli.py::test_ac8_an_uninitialised_submodule_is_not_on_this_machine`
    also checks that `tcw projects list --json` shows `lib` with
    `present: false`, and that `tcw work show lib/x` exits 5 with "not on this
    machine". The clone needed a `docs/work` folder for `work show` to reach
    the lookup, since git keeps no empty folder; the empty-folder test beside
    it creates the same folder.
  - `tests/test_store_provisioning.py::test_ac22_a_found_folder_not_ending_in_the_subfolder_gives_no_answer`
    also checks how the store then resolves: with the project found through
    `TCW_PROJECT_SERVER`, opening the work store is refused with
    `StoreNotProvisioned`, and the refusal's text is the same as with no match
    at all (no variable, and the manifest entry giving no repository).

## A correction to round 1

Round 1, under "Handoffs folded in", says for TCW-114 that "the only process
the lookup starts is `git rev-parse`, through `worktree_anchors`". That is not
quite true. Besides `git rev-parse`, the registry's worktree probe
(`_probe_worktree`, `tcw/store/project.py`) also runs the read-only
`git --git-dir <common> config --get core.worktree` when the repository's git
folder is not named `.git`, as in a submodule. That call predates this item.
TCW-107 adds no git call.

## The suite


`.venv/bin/pytest -q -p no:cacheprovider`, run in full as CI runs it, at
`6ab800b0` (2026-10-23): `5441 passed, 118 skipped in 607.45s`.
