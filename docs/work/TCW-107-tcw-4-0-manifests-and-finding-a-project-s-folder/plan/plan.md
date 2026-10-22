# Plan — TCW 4.0: manifests and finding a project's folder

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). The
lifecycle is driven by the released 3.x CLI from the same worktree, as for
TCW-106, so this repository's records stay in the 3.x ledger format.

File and line references are to commit `05d42988` on `v4`. TCW-106 is still
being finished there and TCW-107's implement stage does not begin until
TCW-106 is completed (the blocker is already recorded on the ticket). The
first thing implement does is re-check every reference below against the
commit TCW-106 finishes on, and correct the plan where a line moved. The test
lists in steps 3, 7 and 9 were made with `grep` at `05d42988`; implement runs
the same `grep` again at the start of each of those steps and adds anything
new to the list before changing code.

Every step starts by writing its tests, which fail, and ends with them passing
and with the **full suite** green (`.venv/bin/pytest`, bare, as CI runs it).
A step that cannot end green is two steps.

Revised on 2026-10-22 after the adversarial plan review (must-fix M1-M6,
should-fix S1-S10, and the user's decision on U1, which is now spec Design
2.3).

## What this plan relies on from TCW-106

- `tcw/project_files.py`: `TCW_FOLDER`, `CONFIG_NAME`, `SENTINEL` (`:34`),
  `LEGACY_SENTINEL` (`:37`), `VERSION_KEY`, `root_of` (`:59`), the `.tcw`
  exception in `find_marker` (`:78`), `legacy_message` and `LEGACY_PROJECT`
  (`:86-93`), `version_line` (`:100`) and `version_problem` (`:110-130`).
  This item adds the manifest file names to the same module.
- `tcw/store/project.py`: `_read_config` already refuses a 3.x connection and
  a version this TCW cannot read (`:559-563`, `:599-603`), and every project
  folder is taken with `root_of`.
- `tcw/config.py`: `Origin.folder` is the project root for the `project` and
  `local` layers (`:71-81`), and the local layer is
  `root / LOCAL_SENTINEL` (`:692`).
- `tcw/store/fs.py`: `personal_file_tracked` and `ignore_personal_file`
  (`:205-237`) work on `.tcw/`; `refuse_legacy_project` (`:310`).
- `tests/projectfiles.py`: `config_file`, `write_config`, `write_config_file`
  and the version-line rule (`_versioned`, `:42-63`), which this item extends
  to manifests.
- This repository's own `.tcw/tcw-config.yaml` and `.tcw/.gitignore`.
- `tests/test_project_files_cli.py`, whose AC 13 and 13a tests (`:494-566`)
  connect projects with locators under `projects:` and are rewritten at step 9.

## Choices this plan makes where the spec leaves room

1. **Walking past a project being looked up** is now written in the spec
   (Design 2.2, "Walking past the project being looked up"), since TCW-108
   inherits Design 2.2's wording. The plan implements it as written there.
2. **`tcw validate` reports each active-project manifest entry once.** Design
   5.1 owns every entry of the active project's two manifests. A project the
   walk recorded as not on this machine, whose deciding entry is in one of
   those two files, is not reported a second time from the walk's list (AC 7
   asks for one `unresolved` finding). `_cmd_validate` tells which file
   decided from `UnreachableProject.decided_by` (step 3). With the user's
   decision on U1 (Design 2.3), the walk and Design 5.1 now agree on every
   folder: an absent or empty folder is `unresolved` in both, and a folder
   with contents and no project is an error in both.
3. **Counting reads (AC 24, 27)** counts the registry's own reads, through two
   module-level functions in `tcw/store/project.py`, `_read_text(path)` and
   `_list_folder(path)`, which every read the registry makes goes through and
   which the tests replace with counting versions. AC 27 was reworded in the
   spec to say so (review M1): `tcw validate` also reads each ancestor's
   configuration itself (`_shared_work_paths`, `tcw/validate.py:677-703`,
   `load_config` at `:686` and `work_path` at `:693`), outside the registry,
   and sending those reads through the registry is not this item's work. The
   AC 27 test counts both of Design 2.6's files per candidate.
4. **Messages never use the words git, branch or worktree.**
   `tests/test_static_guards.py:27-41` refuses those words in messages outside
   a short list of functions. The manifest parser therefore says "the text
   after '#'", not "the branch".
5. **Test folders are isolated from each other** (step 2): the search lists
   the folder holding a project's root, so a fixture project made directly at
   `tmp_path` would otherwise be searched for among every other test's
   folders.
6. **`tcw provision` keeps refusing a wrong `TCW_PROJECT_<ID>`**
   (`tcw/cli.py:113-135`) after it stops fetching projects (step 7): store
   rung 1.5 can still resolve a store inside a project placed by the variable.
7. **`FsStoreProvisioner`'s project branch is kept** (`PROJECT_TARGET`,
   `tcw/store/fs.py:3121`, `:3150`, `:3410`, `:3467`), unused until TCW-115
   rebuilds fetching a project on it; a comment says so. The review found
   deleting it equally acceptable; it is four short branches, and keeping
   them leaves TCW-115 the clone code it will reuse.
8. **A graph problem still ends `tcw validate` early** (`tcw/cli.py:421-426`),
   before the `unresolved` findings and before Design 5.1's findings, as it
   does today for `unresolved`. This is intended: a manifest entry Design 5.1
   would report as wrong (rows b-e) is, for an ID the walk looks up, already
   one of those graph problems (Design 2.3); an entry no `projects:` relation
   names is reported once the graph problems are fixed. The early-return
   branch is unchanged.

## Step 0 — the macOS permission check, before anything is built

The spec's Risks make this the one belief that could send the search design
back to TCW-99, so it is checked first (review S5). On a Mac, from a terminal
program that has **not** been granted access to Documents, Desktop or
Downloads (System Settings, Privacy & Security, Files and Folders; a newly
installed terminal, or one whose access was removed there): run
`stat ~/Documents/.tcw/tcw-config.yaml` and the same for `~/Desktop` and
`~/Downloads`, and watch for a system dialog asking for access. Recorded in
the implement round with the terminal used and what macOS did. If macOS asks,
the finding goes to TCW-99 before step 3. If no terminal without access is
available on the machine, the round says so, and that the belief was not
checked.

Nothing is changed in the repository.

## Step 1 — the manifest files and their parser

Red first: **creates** `tests/test_manifest.py`, unit tests of the parser
alone, one per format rule: both entry forms (Design 1.3); every refusal AC 2
lists (no `tcw-version`, with the message containing `a manifest starts with
'tcw-version:` and not `tcw migrate`; `tcw-version: 99.0.0` with
`version_problem`'s upgrade message; a top-level key `other`; an entry key
`ref`; `lib: /abs/lib` and `lib: ~/lib` in the shared file; a mapping with no
`path`; `repository: …#`, `'#main'`, `x#a#b`; `subfolder: ../x`;
`subfolder: apps/x` with `path: ../app`; `subfolder` without `repository`;
the ID `Lib`); absolute and `~` paths accepted in the local file (Design 1.4);
`<url>#<branch>` split at the first `#` (Design 1.5); a `subfolder` whose
`path` ends with it accepted (Design 1.6); an empty file and a file holding
only `tcw-version` having no entries (Design 1.1). And
`personal_files_skipped()`: true for `1` and for any other non-empty value,
false for an unset and for an empty `TCW_NO_PERSONAL_CONFIG`, matching
`_personal_layers` (`tcw/config.py:680-684`) on each of the four.

**Changes** `tcw/project_files.py`: adds `MANIFEST_NAME = "tcw-manifest.yaml"`,
`LOCAL_MANIFEST_NAME = "tcw-manifest.local.yaml"`, `MANIFEST =
".tcw/tcw-manifest.yaml"`, `LOCAL_MANIFEST = ".tcw/tcw-manifest.local.yaml"`.
Moves `SKIP_VARIABLE` (`tcw/config.py:40`) here, with a function
`personal_files_skipped() -> bool`: true when `TCW_NO_PERSONAL_CONFIG` is set
to a **non-empty** value. An empty value is unset, as `_personal_layers`
already treats it (`tcw/config.py:680-684`), so the two readers never
disagree (Design 1.10). Only `1` is valid; the configuration reader keeps
reporting any other non-empty value (`tcw/config.py:683-687`), and personal
files are skipped for it, as today. `tcw/config.py` imports the constant from
here and calls the function.
Also moves `PROJECT_ID_PATTERN`, `RESERVED_PROJECT_IDS` and
`validate_project_id` (`tcw/store/project.py:25-37`) here (review S8), since
`tcw/store/manifest.py` needs the rule and `tcw/store/project.py` will import
`manifest.py`; importing back from `project.py` would be a circular import.
`tcw/store/project.py` imports the three names from `tcw.project_files`, so
every existing `from tcw.store.project import validate_project_id` keeps
working. The rule uses only `re`, so the module still imports nothing from
`tcw` but the version.

**Creates** `tcw/store/manifest.py`, which reads no file and imports nothing
from `tcw` but `tcw.project_files`:

- `ManifestEntry` (frozen): `id`, `path` (as written), `url`, `branch`,
  `subfolder` (each `None` when absent), `file` (the manifest's path, as TCW
  names it).
- `parse_manifest(mapping, file, *, personal: bool) -> tuple[dict[str,
  ManifestEntry], list[str]]`: Design 1.2-1.6. Returns no entries at all when
  there is any problem (a manifest with a problem is not used, Design 1.8).
  The `tcw-version` check calls `version_problem`, except a missing
  `tcw-version`, which gives `has no tcw-version; a manifest starts with
  'tcw-version: <running version>'`.

**Proves it:** `tests/test_manifest.py`; the full suite (the two moves change
no behaviour).

## Step 2 — test helpers, and test folders kept apart

Red first: **creates** `tests/test_projectfiles_helper.py`, testing the
helpers below on literal inputs (a bare locator, an absolute locator, a
`path` and `repository` mapping, a `jira` block kept, text that does not parse
written unchanged, an entry the helper cannot move refused), and one test that
`tmp_path.parent` holds only `tmp_path`, so removing the override below later
goes red.

**Changes** `tests/projectfiles.py`:

- `manifest_file(root, *, local=False) -> Path` and
  `write_manifest(root, entries, *, local=False) -> Path`. `entries` is a
  mapping, written as `projects:` under the version line and merged into a
  manifest already there; or text, written as given with the version line
  added by the rule `_versioned` (`:42-63`) applies, so a test of a broken
  manifest still tests that file. `_CONFIG_NAMES` (`:25`) gains the two
  manifest names, so `write_config_file` versions them too.
- `write_connected_config(root, text)` and `write_connected_config_file(path,
  text)`: write a configuration that may still hold 3.x locations under
  `projects:`. Each `projects.<relation>.<id>` that is a string, or a mapping
  with `path` or `repository`, is moved into the root's shared manifest:
  `path` as written, an absolute one made relative to the root with
  `os.path.relpath`; `repository: {url, ref, path}` becomes
  `repository: "<url>#<ref>"` and `subfolder: <path>`. The configuration keeps
  `<id>:` (or `<id>: {jira: …}`). The configuration is re-written through
  `yaml.safe_dump(sort_keys=False)` only when something moved. An entry with
  `repository.checkout`, or with a repository and no path, raises an
  assertion error saying the test must be converted by hand. Text that does
  not parse, or holds nothing to move, is written exactly as `write_config`
  writes it. The name says what it does at every call site, so a reader of a
  converted test can see that its locations are now in a manifest. TCW-108
  replaces `projects:` and will retire this helper.

**Changes** `tests/conftest.py`: a `tmp_path` fixture overriding pytest's,
returning a new folder `w` inside the folder pytest made for the test, with a
docstring in the style of the file's other guards saying why (the search lists
the folder holding a project's root, and pytest makes every test's folder
inside one shared folder). The folder holding a fixture project made at
`tmp_path` then holds only that project, so the search (Design 2.4) never
meets another test's projects. Checked by the review: nothing in the suite
reads `tmp_path.parent` or `tmp_path.name`; `tcw init` without `--id`
defaults to `test-project`, not the folder name (`tcw/store/fs.py:293`); the
autouse fixtures' `tmp_path / "cache"` and `tmp_path / "xdg-config"`
(`tests/conftest.py:148-177`) move inside `w` consistently; `tmp_path_factory`
is not affected, and its users put their projects one level down.

**Proves it:** the new test file, and the full suite (the override must change
nothing).

## Step 3 — finding a project's folder from its ID

The core of the item. Until step 10 a `projects:` entry still holding a 3.x
locator or `repository` is resolved by the 3.x ladder (`_target_path`,
`tcw/store/project.py:681-724`); an entry holding only its ID (`lib:`, `{}` or
`{jira: …}`) is resolved by the new lookup. Existing fixtures all use locators,
so they keep passing while the lookup is built and tested beside them; step 9
then moves them onto the lookup.

Red first: **creates** `tests/test_project_lookup.py`, calling
`FsProjectRegistry.open(<root>)` and `project_folder` directly, on fixtures
built with `write_config` and `write_manifest` under `tmp_path`:

- AC 24 whole: next to `app`; only in `app`'s manifest at `../x/lib`; its own
  ID; `Unreachable` with Design 6.2's message for `../gone`; `UnknownProject`,
  exit 1, `check the spelling`; two folders next to `app` (`ProjectGraphError`
  naming both); the later call from another found project finding `core` at a
  second folder (`ProjectGraphError`, and `check()` lists it); the repeated
  call reading no file (counted through `_read_text` and `_list_folder`).
- `ValueError` for a `named_by` the registry has not found (Design 2.12).
- Design 2.3's folders, at the library level: an absent folder, an empty
  folder, a folder holding only a `.git` file, and one holding only a `.git`
  folder each raise `Unreachable`; a folder holding `README.md`, and one
  holding `.DS_Store`, raise `ProjectGraphError` naming the manifest and the
  folder; a folder TCW cannot list (`chmod 000`, skipped where the test runs
  with permission to read it anyway) raises `ProjectGraphError`.
- A cycle (review S2): `p` and `q` each name the other under `children`, and
  `r` names `p` as its parent; looking up an ID only `q`'s manifest would
  hold, from `r`, ends (no `RecursionError`) and `check()` reports the cycle
  as `_validate_cycles` does today. The same for a `parent` cycle.
- An entry holding only its ID on both sides of a reciprocal pair (review
  S1): `tcw validate`'s problems hold no "does not point back"; the same for
  a pair where one side is upstream-only (`:885`).
- At the library level, the lookups behind AC 5, 5a, 6, 9, 10, 11, 12, 13 and
  25, so a failure is seen without the CLI around it.

**Changes** `tcw/errors.py`: `ProjectGraphError(TcwError)` and
`UnknownProject(ProjectGraphError)`, both `codes.ERROR` (exit 1).

**Changes** `tcw/store/base.py`:

- `UnreachableProject` (`:124-142`) gains `message: str = ""`, the rendered
  Design 6.2 text, and `decided_by: Any = None`, the manifest file holding the
  deciding entry (or `None` when no entry decided); presentation only, like
  its other fields, and opaque in the same way `declared_in` is.
- `parse_connected_entry` (`:865-916`) accepts `None`, `{}` and a mapping
  holding only `jira` as an entry holding its ID only (Design 3.1, the
  accepted half). The locator forms are still parsed; step 10 refuses them.

**Changes** `tests/test_project_registry.py` (review M2): the case
`("      {}\n", "needs 'path', 'repository', or both")` (`:469`) of
`test_a_malformed_entry_is_an_error_naming_the_line` (`:461-481`) is removed,
because `{}` is now accepted (Design 3.1), and a new test there asserts that
`children: {child-project: {}}` is accepted and recorded as not on this
machine when nothing finds `child-project`.

**Changes** `tcw/store/project.py`:

- Two module-level functions, `_read_text(path) -> str` and
  `_list_folder(path) -> list[tuple[str, bool]]` (each entry's name and
  whether it is a folder, through `os.scandir`, or the `OSError` raised).
  Every file and folder the registry reads goes through them, so tests can
  count them (choice 3), and a third, `_search(project_id, named_by)`,
  holds Design 2.4-2.8 alone, so a test run can replace it (step 9).
- New registry state in `__init__` (`:194-229`): `_texts` (each file read at
  most once, its text or the error reading it), `_listings`, `_probes` (per
  folder, what its `.tcw/tcw-config.yaml` and root `tcw-config.yaml` say:
  nothing, a 4.0 project's ID, a version problem, a 3.x project's ID, or
  unreadable), `_manifests` (per project root: its two parsed manifests, or
  that one has a problem), `_answers` (Design 2.11 b, keyed by the ID and the
  canonical root of the naming project), `_looking_up` (IDs whose lookup is in
  progress) and `_returned` (folders `project_folder` has returned).
- `_read_config` (`:554-652`) reads its file through the `_texts` cache, so a
  folder the search probed is not read again when the walk visits it (AC 27).
- `_manifests_of(root)`: the personal manifest, unless
  `personal_files_skipped()`, then the shared one, read through `_text` and
  parsed with `parse_manifest`. A problem is recorded with `_problem` against
  the file (Design 1.8), and that root's manifests are marked unusable. The
  active project's manifests are read once in `_load_graph` (`:467-475`) so
  `tcw validate` reports their problems whether or not anything is looked up;
  a missing file costs one failed read (AC 21).
- `_locate(project_id, named_by) -> _Answer`, memoised in `_answers`. An
  `_Answer` holds the folder (or none), how it was found (`manifest`,
  `variable`, `search`), the deciding manifest entry, a problem, and whether
  anything in the walk names the ID. It applies, in order:
  - 2.1: `_override_path` (`:726-754`), unchanged.
  - 2.2: the manifests of `named_by`, of its ancestors nearest first and of
    its descendants breadth first (children in configuration order), each
    personal file before the shared one, walking past a project being looked
    up as Design 2.2 now says. Both walks keep a set of the roots already
    visited and stop at one seen before (review S2): the existing
    `FsProjectRegistry.descendants()` (`:289-300`) recurses with no such set
    and is not reused, and `ancestors()`'s guard (`:281-286`) is copied. A
    family member whose manifests are unusable makes the lookup a problem
    (Design 1.8). The first entry for the ID decides, whole (entries never
    merge).
  - 2.3: the deciding entry's folder: `~` expanded (personal file only), an
    absolute path as written, a relative one through `_locator_path`
    (`:792-815`) from the manifest's project root, which applies today's
    worktree rules to it. Probed first for its two files. When neither file
    is there, the folder is listed once through `_list_folder`: no folder, or
    an empty one (no entries, or only one named `.git`), is not on this
    machine; any other contents, or a listing that fails, is a problem naming
    the manifest and the folder. Another ID, a 3.x project or an unreadable
    version is a problem naming the manifest and the folder.
  - 2.4-2.8, in `_search`: when no entry decided. Lists the folder holding
    `named_by` once; tests each subfolder except `named_by` itself and any
    `.tcw`, then each enclosing folder up to the filesystem root, reading only
    the two files of Design 2.6 through `_probes`. Collects every match before
    deciding; compares matches by folder identity through `_canonical`
    (`:849-861`); two are a problem with Design 2.7's message; a candidate
    that is the ID but cannot be read as 4.0 is a problem (2.8); anything else
    unreadable is ignored.
  - Otherwise: not on this machine when the walk names the ID (an entry in a
    consulted manifest, or a `projects:` entry of a project in the walk),
    unknown when nothing does (Design 2.12).
- `project_folder(project_id, named_by) -> Path`, exactly as the spec's
  Design 2.12 states: validates `named_by` (the current root, a root in the
  graph, or a folder in `_returned`, else `ValueError`); returns `named_by`
  for the ID it declares; reads `named_by`'s configuration when it is not in
  the graph, to learn its family; raises `Unreachable`, `UnknownProject` or
  `ProjectGraphError` for the other outcomes, adding a problem to
  `_problems` and `_findings` first; compares a found folder with the folder
  this registry already holds for the ID (`_by_id`) and reports a different
  one as Design 2.9's duplicate.
- `found(project_id) -> dict | None`: Design 6.1's value for a project in the
  graph, from the answer that placed it (the manifest's file as TCW names it,
  the variable's name, or `search`); `None` for the current project and for a
  project not here. Used at step 4.
- `_follow_edges` (`:543-552`): parent first, then children in configuration
  order, then upstreams (Design 2.11 a). An entry holding only its ID is
  resolved by `_locate`; found, its configuration is visited as today; not on
  this machine, `_unreachable_edge` (`:1091-1111`) records it with its Design
  6.2 message and `decided_by`; a problem is recorded and the edge is not
  followed. An upstream's own manifests are never consulted, since an
  upstream's connections are not followed (Design 2.10).
- Every place that still runs the 3.x ladder learns about an entry holding
  only its ID (review S1), until step 10 removes the ladder. Without this,
  `_target_path` with no locator and no repository returns the naming
  project's own file (`:724`), which exists, so `_points_elsewhere` would
  report a false "does not point back":
  - `_validate_reciprocity` (`:878-938`): for an entry holding only its ID,
    the target is read from `_answers`, never looked up again (Design 2.11 b),
    in the children loop (`:891`), the parent loop (`:912`) and the
    upstream-only branch (`:885`).
  - `_points_elsewhere` (`:961-980`) returns `False` when the reciprocal entry
    holds only its ID: there is no locator to compare, and Design 2.9's
    duplicate check covers two different folders.
  - `misdirected()` (`:431-451`) leaves out entries whose naming entry held
    only its ID, since they have no written locator to report.
  - `checkout_of`'s loop (`:334-343`) reads `entry.repository`, which is
    `None` for an entry holding only its ID, so such entries are skipped there
    until step 8 replaces the loop.
- The duplicate-ID check of the walk (`:524-534`) is unchanged and covers
  Design 2.9 inside the walk.

**Proves it:** `tests/test_project_lookup.py`; `tests/test_project_registry.py`
with the one case changed above; `tests/test_project_overrides.py`,
`tests/test_upstream_projects.py` and `tests/test_projects_list.py` unchanged
and passing (the walk order changed, so a test that compared the order of a
list is read, and changed only if the order is all it checked, and the change
is listed in the implement round); the full suite.

## Step 4 — what a person sees

Red first: **creates** `tests/test_manifest_cli.py`, running `tcw` from the
folder the test builds, as `tests/test_project_files_cli.py:42-49` does, one
test or more per criterion: AC 1, 2 (exit 1 from `tcw projects list` and the
`where` of the `tcw validate` error), 3, 4, 5, 5a, 6, 7 (except its
provisioning sentences, step 7), 8 (including its empty-folder cases and the
real uninitialised submodule, built with `git submodule add` and a
`git clone` without `--recurse-submodules`), 8a, 9, 10, 11, 12, 13, 14, 15
(the accepted forms only), 20, 21 and 25. AC 3, 8a and 17 turn personal files
on with an environment like `personal_env`
(`tests/test_project_files_cli.py:52-57`), since `tests/conftest.py:176` sets
`TCW_NO_PERSONAL_CONFIG=1` for every test.

**Changes**

- `tcw/projects_cli.py:21-51`: each row gains `found`, from
  `registry.found(id)` (Design 6.1). The plain listing is unchanged.
- Design 6.2's messages, rendered once into `UnreachableProject.message` by
  the registry: `unreachable_project_note` (`tcw/store/fs.py:564-581`)
  returns it; `_cmd_validate` (`tcw/cli.py:428-436`) uses it as the
  `unresolved` finding's message; `open_project` (`tcw/work/open.py:88-99`)
  raises `Unreachable` with it, replacing "`tcw provision` obtains it". An
  edge still resolved by the 3.x ladder keeps its 3.x message until step 10
  removes the ladder.
- `FsProjectRegistry.manifest_findings() -> list[Finding]`: Design 5.1's table
  for every entry of the active project's two manifests, `where` the
  manifest's path within the project, with a committed entry that a personal
  entry or `TCW_PROJECT_<ID>` overrides reported as a `warning` for rows b-e,
  `(overridden on this machine by <file or variable>)` added. Row a covers an
  empty folder (Design 2.3), using the same probe and listing as `_locate`,
  through the same caches. `_cmd_validate` (`tcw/cli.py:427-443`) adds them
  after the unresolved findings, and drops a walk record whose `decided_by`
  is one of the active project's two manifests, which 5.1 already reports
  (choice 2). Format problems, duplicates and unreadable candidates are graph
  problems already and stay errors (Design 5.2, `tcw/cli.py:422-426`); the
  early return on graph problems is kept (choice 8).
- `tcw/store/fs.py:205-222`: `personal_file_tracked(root, relative=LOCAL_CONFIG)`
  takes the file to check; `tcw/validate.py:361-382` (`config_findings`) adds
  a warning for a tracked `.tcw/tcw-manifest.local.yaml`, beside the one for
  the configuration file (Design 1.9, 5.3).
- `tcw/store/fs.py:225-237`: `ignore_personal_file` becomes
  `ignore_personal_files`, writing `/tcw-config.local.yaml` and
  `/tcw-manifest.local.yaml`, each only when no line already reads it or its
  name without the `/` (Design 1.9); `tcw/cli.py:76-82` calls it and its
  outside-a-repository note names both files.
- `.tcw/.gitignore` in this repository gains `/tcw-manifest.local.yaml`
  (AC 22, last sentence).

**Proves it:** `tests/test_manifest_cli.py`; `tests/test_project_files_cli.py`
(its AC 2 test, `:123`, now also sees the second ignore line and is updated to
expect it); `tests/test_validate_command.py`, `tests/test_projects_list.py`,
`tests/work/test_open.py`; the full suite.

## Step 5 — one registry per command

Red first, in `tests/test_project_lookup.py`:

- AC 27: the monorepo of AC 9, one in-process `tcw.cli.main(["validate"])`
  from `app/packages/shared` with `_read_text`, `_list_folder` and
  `FsProjectRegistry.open` replaced by counting versions; the folder holding
  `shared`'s root is listed once, each candidate's `.tcw/tcw-config.yaml` and
  root `tcw-config.yaml` are each read at most once by the registry, and
  every `open(<root>)` in the command returns the same object.
- The drop after a write, inside one command (review M6): call
  `begin_command()`, open a registry on a project, write a changed
  configuration through `write_sentinel` (which goes through
  `_atomic_write_all`), open again, and assert the new registry is a
  different object that sees the new content; then `end_command()`. The same
  for a manifest written through `_atomic_write_all`. **Mutation check:**
  with the `forget_registries()` call removed from `_atomic_write_all`, the
  test goes red because the second `open` returns the first registry with
  the old content; the result is recorded in the implement round. (A test
  that runs `tcw init` and then a second command proves nothing, because
  every `tcw.cli.main` call runs `_dispatch`, which starts and ends a command,
  `tcw/cli.py:645`, `:693`.)
- A registry whose graph load raises is not kept: with `_load_graph` made to
  raise once, the next `open` in the same command builds a new registry.

**Changes**

- `tcw/store/project.py`: a module-level `_OPEN: dict[Path, FsProjectRegistry]
  | None`, with `begin_command()`, `end_command()` and `forget_registries()`.
  `open` (`:231-235`) returns the registry already opened for the same
  resolved root while a command runs, and a new one outside a command, so a
  library caller and a test always read afresh. The registry is stored only
  after `_load_graph` has finished, so a load that raised is never kept. The
  docstring of `forget_registries()` says that it cannot refresh a registry a
  caller already holds in a local variable: such a caller opens again after
  writing.
- `tcw/config.py:655-662`: `begin_command` and `end_command` also call the
  registry's, so the one switch `_dispatch` (`tcw/cli.py:645`, `:693`) already
  turns on and off covers both, and `tcw serve`'s `end_command()`
  (`tcw/cli.py:545`) makes each request open a fresh registry (Design 2.13).
  A comment there says that the configuration cache `_EFFECTIVE`
  (`tcw/config.py:652-672`) is still not dropped after a write, as in 3.x,
  while the registry now is.
- `tcw/store/fs.py:1149` (`_atomic_write_all`): after it writes, calls
  `forget_registries()` when a target is named `tcw-config.yaml` or either
  manifest name. Every writer of a configuration inside a command goes
  through it (checked by the review): `write_sentinel` (`:270`), `init`
  (`:766`), the store editors through `_write_files` (`:1524`) and
  `tcw work tags` (`tcw/work/cli.py:643`). A clone made by `tcw provision`
  is not written through it; TCW-115's handoff says so.

**Proves it:** the three tests and the mutation check; the full suite,
`tests/serve/` included.

## Step 6 — git worktrees

Red first: **creates** `tests/test_manifest_worktree.py`, building a real git
repository and a linked worktree with `git worktree add` in every test (never
a simulated one): AC 16, 17 (manifest, configuration, `tcw config show
--origin`, a `file:` binding, a command binding's `TCW_CONFIG_DIR`), 18, 19
and 26; and one more for Design 4.3 below the top folder: a project at
`app/packages/a` inside the worktree finds `ws`, which encloses the main
checkout, by the search.

**Changes**

- `tcw/store/project.py`, beside `worktree_anchors` (`:67-79`):
  `personal_file(root, name) -> Path`: `root/.tcw/<name>` when it is a file;
  otherwise, when `root` lies inside a linked worktree, the counterpart below
  the main checkout when that is a file; otherwise `root/.tcw/<name>`. Decided
  by the file's name, never by asking git (Design 4.2).
- `_manifests_of` reads the personal manifest through `personal_file`, and
  names the file it read (the main checkout's when borrowed) in `found.file`
  and problems; relative entries still resolve from the worktree's project
  root.
- `tcw/config.py`: `Origin` (`:62-94`) gains `root: Path | None =
  field(default=None, compare=False)`, and `folder` returns it when set;
  `_personal_layers` (`:676-693`) builds the local layer from `personal_file`,
  with `root` the worktree's project root, so a borrowed file's `file:`
  bindings and `TCW_CONFIG_DIR` are the worktree's while `str(origin)` names
  the main checkout's file.
- The search (`_search`), Design 4.3, for every `named_by` whose root lies
  inside the repository (review S9): the enclosing folders tested are the
  worktree's own, from `named_by`'s root up to the worktree's top folder
  (`self._anchors`, `:229`), then those enclosing the main checkout, nearest
  first, the main checkout's root excluded. Only the folder listed for 2.4
  depends on where `named_by` is: when `named_by` is the worktree's top
  folder, the folder listed is the one holding the main checkout; otherwise
  it is the folder holding `named_by`'s root, inside the worktree, as in
  step 3. A `named_by` outside the repository searches as in step 3.
- Design 4.4: every search match goes through `_worktree_copy`
  (`:817-847`) before matches are compared; manifest paths already do,
  through `_locator_path`.

**Proves it:** `tests/test_manifest_worktree.py`;
`tests/test_worktree_sibling_nodes.py` and the worktree tests of
`tests/test_project_registry.py`, still on 3.x locators, unchanged; the full
suite.

## Step 7 — `tcw provision` fetches no project

Red first: in `tests/test_manifest_cli.py`, AC 22's first sentence: in AC 7's
setup with a repository on the entry, `tcw provision --dry-run` lists only
component stores and contacts nothing for `lib` (`git` replaced by a script
that fails the test if run); `tcw work show lib/<slug>` exits 5 with Design
6.2's message naming the repository and `tcw project provision lib`; neither
command's output contains "run `tcw provision`" for `lib`.

**Changes**

- `tcw/cli.py`: removes `_declared_projects_in_graph` and
  `_provision_projects` (`:195-376`), their call sites (`:153-158`, `:190`);
  the message at `:161-162` says no component declares a home repository.
  The help text (`:571-574`) becomes "obtain the stores this project declares
  but does not have here", and `writes=` "a clone of each declared store
  repository that is missing" (review M4).
- `tcw/store/fs.py`: removes `declared_connected_projects` (`:3343-3386`) and
  its mention in the docstring at `:885-887`; adds the comment of choice 7 to
  `FsStoreProvisioner`.
- `tests/test_static_guards.py:38`: the `_provision_projects` entry goes.

**Changes the tests** (review M4). Every test that uses `tcw provision` to
fetch a project, or relies on it reading connected projects, found by
`grep -rn "provision" tests` at `05d42988` and read one by one:

| Test | What happens | What it covered, for TCW-115 |
| --- | --- | --- |
| `tests/test_store_provisioning.py`, section "provisioning a connected project" (`:1408-1774`): `test_a_declared_connected_project_is_obtained` (`:1425`) | removed | fetching a declared project |
| `test_provisioning_follows_a_declaration_inside_an_obtained_node` (`:1452`) | removed | fetching connected projects in turn |
| `test_two_entries_naming_one_repository_share_a_working_copy` (`:1481`) | removed | two entries naming one repository share one working copy |
| `test_a_repository_with_no_node_at_the_declared_path_is_refused` (`:1498`) | removed | a fetched repository with no project at the path is refused |
| `test_an_occupied_checkout_is_refused_before_any_fetch` (`:1516`) | removed | an occupied folder is refused before anything is fetched |
| `test_a_malformed_connected_declaration_refuses_and_names_the_line` (`:1534`) | removed | a malformed declaration refuses and names the line |
| `test_a_declaration_on_a_sibling_is_followed_from_anywhere_in_the_graph` (`:1544`) | removed | declarations followed from anywhere in the graph |
| `test_a_project_the_checkout_already_has_is_not_fetched` (`:1583`) | removed | a project already here is not fetched (`tcw/cli.py:256-275`) |
| `test_a_sibling_of_an_ancestor_is_recognised_as_already_here` (`:1640`) | removed | the same, for an ancestor's sibling |
| `test_provision_refresh_is_a_usage_error` (`:1704`) | kept, moved to the section on the verb (`:667`) | — |
| `test_a_present_project_is_still_read_for_its_own_declarations` (`:1711`) | removed | a project already here is still read for its own declarations |
| `test_dry_run_does_not_call_a_planned_obtain_already_available` (`:1750`) | removed | the `--dry-run` listing |
| `test_a_declaration_error_on_an_obtained_node_fails_the_run` (`:1832`) | removed (its subject is a node `tcw provision` obtained) | a declaration error on a fetched project fails the run |
| `test_an_unresolvable_checkout_is_a_declaration_error_not_a_crash` (`:1804`) | not about fetching; converted at step 9 | — |
| `tests/test_upstream_projects.py`: `test_a_public_upstream_is_provisioned_into_a_reader_only_checkout` (`:329`) | removed | an upstream fetched into a reader-only checkout |
| `test_provision_does_not_follow_an_upstreams_own_connections` (`:348`) | removed | an upstream's own connections are not followed |
| `tests/test_project_overrides.py`: the `provisionable` fixture (`:147-175`) | kept for the tests below that still use it | — |
| `test_without_an_override_the_declared_repository_is_fetched` (`:185`) | removed | the declared repository is fetched without a variable |
| `test_an_overridden_project_is_never_fetched` (`:197`) | removed: once nothing is fetched, its "never fetched" passes for a reason unrelated to the variable, and `"core-project: already available"` is no longer printed | a project placed by `TCW_PROJECT_<ID>` is never fetched |
| `test_one_variable_set_serves_both_session_shapes` (`:212-257`) | removed: its detached half asserts a fetch | a variable naming a folder that is not here falls through to the declared repository |
| `test_provision_refuses_an_override_that_is_not_a_node` (`:341`) and `..._naming_the_wrong_node` (`:353`) | kept: the refusal stays (choice 6); their "fetched nothing" half no longer distinguishes anything for a project, which a comment says | — |
| `tests/test_projects_list.py`: `test_provision_refuses_the_2x_key_in_a_child` (`:132-137`) | removed: `tcw provision` no longer reads connected projects' configurations; the 2.x key in a child stays covered by the other commands of the parametrized test above it (`:118` list) | — |
| `tests/config/test_personal_commands.py`: `test_graph_readers_tolerate_what_the_loader_refuses` (`:114-125`) | `provision` dropped from its comparison, which kept only "Nothing to provision" and so proved nothing about the graph; the `tcw projects list` half stays | — |

Tests that mention `tcw provision` for a **store**, which it still fetches,
are unaffected and stay: `tests/test_capabilities_federation.py:577`,
`tests/test_init_configured_tree_path.py:73-119`,
`tests/test_init_provision_contract.py`, `tests/work/test_init_provision.py`,
`tests/test_cli_contract.py:50`. Tests that assert the 3.x message "run
`tcw provision`" for a project still resolved by the 3.x ladder
(`tests/test_cli_contract.py:575`, `tests/test_project_registry.py:484-512`,
`tests/test_upstream_projects.py:339`) keep passing until step 10 changes the
message with the ladder, and are listed there.

**Proves it:** the new tests; the full suite.

## Step 8 — a store inside a project already here, from the manifest

Red first: in `tests/test_store_provisioning.py`, the section "the registry
rung" (`:414-533`) rewritten to write the repository in a manifest entry
instead of a `projects:` entry, and AC 22's rung sentences added: a store
whose `work.repository.url` equals a manifest entry's repository, for a
project found at `path` with `subfolder: apps/server`, resolves inside `path`
with `apps/server` removed; with that project placed instead by
`TCW_PROJECT_<ID>` at a folder not ending in `apps/server`, the rung gives no
answer and the store resolves as with no match. And the order (spec Design
6.4, review S3): two projects in the graph whose manifests both match the
URL, for two different found projects, give the answer of the one first in
Design 2.2's order, whether or not any lookup reached the second before.

**Changes** `tcw/store/project.py:306-344` (`checkout_of`): once the graph is
loaded, reads through `_manifests_of` the manifests of every project in the
graph that is not upstream-only, in Design 2.2's order from the active
project (its own, ancestors nearest first, descendants breadth first,
personal before shared); compares `normalized_url` of each entry's URL part
with the declared URL; for an entry whose ID this registry has found, returns
the found folder with the entry's `subfolder` removed, or goes on to the next
entry when the folder does not end with it (Design 6.4).
`_registry_checkout_root` (`tcw/store/fs.py:3157-3179`) is unchanged. Any
other test that relies on rung 1.5 through a `projects:` repository is found
by the full-suite run and rewritten the same way in this step.

**Proves it:** the rewritten section and the new tests; the full suite.

## Step 9 — the test fixtures move onto the lookup, with the 3.x ladder still there

Split from the removal (review M5), so that a failure here can only be a real
difference between the new lookup and the 3.x ladder, and a failure in step
10 can only come from the removal. No production code changes in this step.

**Before anything changes**, an inventory is taken and kept in the
scratchpad (not the repository): `pytest --collect-only -q` (every test ID),
and, from a one-off script that walks each test function's syntax tree, the
number of `assert` statements and `pytest.raises` blocks in each test
function. Taken again at the end of step 10.

**The files** (45: `grep -rlE "projects:(\\\\n| *$)|\"projects\": *\{|setdefault\(\"projects\"|connect\(" tests`
on `05d42988`; re-run at the start of the step).

**First, the tests that stay on 3.x locators.** Tests whose subject is a 3.x
behaviour that step 10 removes keep their locator fixtures and are not
converted here: the "does not point back" and "not in this checkout" tests
(`grep -rn "does not point back\|not in this checkout\|misdirected" tests`:
7 lines in `tests/test_project_registry.py`, 1 in
`tests/test_project_overrides.py`), the tests of the locator-versus-repository
order of `_target_path`, and the tests asserting the 3.x "run
`tcw provision`" message (`tests/test_cli_contract.py:575`,
`tests/test_project_registry.py:484-512`,
`tests/test_upstream_projects.py:339`), and the tests whose entry gives a
repository and no path or a `repository.checkout` (the helper refuses them,
since 3.x found such a project in its cache and `v4` does not). Each is
listed by test ID in the implement round before the conversion, with the design rule that will remove
or change it in step 10.

**Commit 1, mechanical.** A one-off script kept in the scratchpad, not the
repository, replaces `write_config(` with `write_connected_config(` and
`write_config_file(` with `write_connected_config_file(` in those files,
leaving the tests listed above as they are. Nothing else in the commit.

**Commit 2, by hand**, so a reviewer can read the hand edits on their own:

- `connect()` (`tests/work/projects.py:45-54`) writes the ID under
  `projects:` and the relative path with `write_manifest`; `_node_repo`
  (`tests/test_store_provisioning.py:1411-1422`), where it survives step 7;
  and TCW-106's AC 13 and 13a tests (`tests/test_project_files_cli.py:494-566`),
  rewritten with manifest entries.
- A test of path spelling, symlinks or letter case in a locator, and every
  worktree test (`tests/test_worktree_sibling_nodes.py`, the worktree tests
  of `tests/test_project_registry.py`, `tests/test_environment_hardness.py`),
  is converted by hand to a manifest entry written the same way (absolute
  stays absolute, in a personal manifest with personal files turned on for
  that test, or relative), keeping its assertions.
- A test that compares a configuration's text after an edit
  (`tests/test_config_edit_writers.py`, `tests/test_store_editor.py`) is
  converted by hand, since the helper re-writes the file through YAML.
- Every failure of the full suite is read one by one. An assertion is changed
  only where the spec deliberately changed the behaviour it checked; each such
  change is listed in the implement round with its design rule.

**Proves it**, each result recorded in the implement round:

1. The full suite, green, with the 3.x ladder still present.
2. **The search turned off.** A one-off pytest plugin kept in the scratchpad,
   loaded with `-p`, replaces `tcw.store.project._search` with a function
   that finds nothing. The full suite is run with it, leaving out the three
   files whose subject is the search (`tests/test_project_lookup.py`,
   `tests/test_manifest_cli.py`, `tests/test_manifest_worktree.py`). Every
   test must still pass, which shows each converted test's projects are placed
   by its manifest and not found by accident next to each other (most
   fixtures put connected projects side by side, `reciprocal()` in
   `tests/test_project_registry.py:28-38`, `make_project` at `tmp_path/<id>`).
   A test that fails here is fixed by writing the entry its fixture lacked,
   never by keeping it on the search.
3. **A mutation check**, in the style of CLAUDE.md's "Measuring the skill
   layer": with the search turned off as above and `parse_manifest` made to
   return no entries, the stated set goes red: every converted test that
   asserts a connected project is present or is part of the graph. The number
   that went red is recorded, every converted file holding such a test is
   confirmed to have at least one red test, and the failure reasons of at
   least ten red tests across different files are read and confirmed to be
   the project not being found, not an unrelated crash.
4. The inventory: no test ID disappeared in this step, and no test's count of
   assertions dropped, except the ones listed with their reason.

## Step 10 — `projects:` names IDs only

Red first: in `tests/test_manifest_cli.py`, AC 15's refusals: each of
`upstream: {lib: ../lib}`, `{lib: {path: ../lib}}` and
`{lib: {repository: {url: x}}}` is a configuration problem naming
`.tcw/tcw-manifest.yaml`, and no `tcw validate` message says "does not point
back" or "which is not in this checkout".

**Changes**

- `tcw/store/base.py`: `parse_connected_entry` (`:865-916`) refuses a string,
  a `path` and a `repository`, with Design 3.1's message showing the entry to
  write in `.tcw/tcw-manifest.yaml` (`lib: ../lib`, or
  `lib: {path: <a folder>, repository: <url>}`); `ConnectedProject`
  (`:699-720`) keeps `id` and `jira` only; `UnreachableProject` drops
  `declaration`.
- `tcw/store/project.py`: removes the 3.x ladder in `_target_path`
  (`:681-724`), every edge now going through `_locate`; `_points_elsewhere`
  (`:961-980`) and the two "does not point back" problems (`:901-905`,
  `:929-933`); `misdirected` (`:431-451`); the `declaration` parameter of
  `_visit`, `_read_config` and `_unreachable_edge`; the `provisioned_root`
  import (`:22`). `_locator_path` stays as the resolver of a manifest's
  relative path.
- `tcw/cli.py:438-443`: the `misdirected` findings go.
- `tcw/store/fs.py:3189`: the docstring of `resolve_store` stops citing
  `ConnectedProject` for a project's location.

**Changes the tests** left on 3.x locators in step 9, and nothing else:

- the "does not point back" and "not in this checkout" tests are removed with
  the behaviour (Design 3.2);
- a test whose subject is the locator-versus-repository order of
  `_target_path` is removed, or rewritten as the manifest rule it now
  corresponds to;
- a test whose entry gave only a repository, or a `repository.checkout`, is
  given a manifest entry with a `path` when its subject is not where 3.x
  cloned the project, and removed when it is (TCW-116 decides how such
  entries migrate, spec Notes);
- an unreachable project's "run `tcw provision`" becomes Design 6.2's message
  (`tests/test_cli_contract.py:575`, `tests/test_project_registry.py:484-512`,
  `tests/test_upstream_projects.py:339`), with the fixture moved to a manifest
  entry;
- the entry-parser tests, the cases of
  `test_a_malformed_entry_is_an_error_naming_the_line`
  (`tests/test_project_registry.py:461-481`), become tests of Design 3.1's
  refusals: `nonsense: 1`, `path: ''` and the `repository` cases are each
  refused with the message naming `.tcw/tcw-manifest.yaml` (review M3; the
  tests at `tests/test_store_provisioning.py:56-124` test
  `parse_repository_declaration`, a store's declaration, which this item does
  not change, and are left alone).

**Proves it:** AC 15's tests; the full suite; the inventory against step 9's
(every test ID that disappeared or was renamed across steps 3-10 listed
against the design rule that removed it, in the implement round); the search
turned off once more over the same files as step 9, still green.

## Step 11 — records

On `v4`, in this repository's 3.x-format ledgers, with the released 3.x CLI
from the worktree:

- New capabilities, with `tcw capabilities add`:
  `cli/record-where-other-projects-are-in-a-manifest` and
  `cli/find-a-projects-folder-from-its-id`, status `Supported`, subjects
  `project` and `manifest`, feature `project-registry`.
- Changed, `description.md` of each capability the spec's Capability changes
  names: `cli/host-multiple-projects-in-one-repo`,
  `cli/declare-a-connected-projects-home-repository`,
  `cli/point-tcw-at-a-project-i-already-have`, `cli/run-from-a-git-worktree`,
  `cli/list-connected-projects`, `cli/validate-a-project`,
  `cli/provision-declared-stores`, `cli/read-from-an-upstream-project`,
  `cli/scaffold-the-doc-trees`,
  `cli/override-the-team-configuration-for-myself`,
  `cli/read-a-file-by-the-format-version-it-records`, each with the sentence
  the spec gives it.
- Taxonomy: new vocabulary term `manifest` (`tcw taxonomy add`), relating to
  `project`; `description.md` of `docs/taxonomy/project/`,
  `docs/taxonomy/project-registry/` and
  `docs/taxonomy/personal-configuration/`.

**Proves it:** `tcw validate` with the 3.x CLI from the worktree, and
`tcw work advance --dry-run` at the end of implement (the records gate,
which compares `capabilities.yaml` with the ledgers).

## Step 12 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: where a connected project's location is written, and `tcw provision` (`:232`, `:263`, `:299`) | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (spec, Non-goals); the full list is in the spec's Notes, and recorded on TCW-117's ticket. |
| `docs/guide/jira.md` [Jira-Change] | no | Nothing a command does to a ticket changes. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/multi-repo.md`, `docs/guide/cli.md:147`, `docs/guide/work.md:383`, `:414` | Deferred to TCW-117, with the list in the spec's Notes. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written: manifests, how TCW finds a project without one, a project not on this machine (an empty folder included), `tcw provision` no longer fetching projects, worktrees using the main checkout's personal files, `projects:` naming IDs only. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`tcw/store/manifest.py`, `project_folder`, `found`, `ProjectGraphError`, `UnknownProject`), Changed (walk order, `parse_connected_entry`, `checkout_of`, `UnreachableProject.message` and `decided_by`, one registry per command, `validate_project_id` moved to `tcw/project_files.py`, `tcw provision`'s help), Removed (`_provision_projects`, `declared_connected_projects`, `misdirected`, the locator checks) and Internal (the test helpers and the `tmp_path` override). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: how connected projects are declared, and what to suggest on exit 5 | **`skills/work/SKILL.md:115` changed in this item** (spec, Non-goals; review S7): "On exit 5, or exit 3 for an absent project, report it and pass on the instruction its message gives (the manifest entry to add or correct, or the command that fetches the project); do not retry." Everything else deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: `projects:` entries change meaning; `projects.md`, `stores.md:88` | Deferred to TCW-117. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-1, UC-3, UC-6, UC-8, S-5, S-10 | Deferred to TCW-117, with the list in the spec's Notes. |

The two `upcoming/` files are named
`TCW-107-tcw-4-0-manifests-and-finding-a-project-s-folder.md`.

## Step 13 — the suite as CI runs it

Bare `.venv/bin/pytest` from the worktree root (AC 23). A failure is fixed in
the step it belongs to, not with a skip.

## Verification the tests cannot do

- **macOS permission prompts**: step 0, before anything is built.
- **The QA plan's scenarios** (the ticket's QA plan comment) are run by hand
  with `.venv/bin/tcw` in throwaway folders under the scratchpad, at qa.
- **The released 3.x CLI still reads this repository** after step 4 changes
  `.tcw/.gitignore` and step 11 changes the ledgers: `tcw work show TCW-107`
  and `tcw validate` from the worktree.
- AC 13's unreadable folder (`chmod 000`), and step 3's unlistable entry
  folder, cannot be tested when the suite runs as a user who can read them
  anyway; those tests skip there and say so.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1, 3, 4, 8, 8a, 14, 20, 21 | 4 (8's empty folders also 3, at the library level) |
| 2 | 1 (parser), 4 (commands) |
| 5, 5a, 6, 9, 10, 11, 12, 13, 25 | 3 (library), 4 (commands) |
| 7 | 4, and 7 for its provisioning sentences |
| 15 | 3 (accepted forms), 10 (refusals and the messages that go) |
| 16, 17, 18, 19, 26 | 6 |
| 22 | 7 (provision and messages), 8 (store rung), 4 (this repository's `.tcw/.gitignore`) |
| 23 | 13 |
| 24 | 3 |
| 27 | 5 |

Every design rule in the spec's Coverage table falls in a step above; 3.3 is
covered by the existing registry tests that step 13 runs, and the cycle guard
of Design 2.2 by step 3's cycle test. Steps 0 (the macOS check), 2 (helpers
and test isolation, which steps 3-10 rely on), 9 (moving the fixtures onto the
lookup), 11 (records, the spec's Capability changes) and 12 (documentation)
trace to no single criterion.

Every step ends with the full suite green: step 3 changes the one test its
change breaks (review M2); step 7 removes or rewrites every test that relied on
fetching a project, listed in its table (review M4); step 9 changes no
production code; step 10 changes only the tests step 9 left on 3.x locators.

The function's name, `FsProjectRegistry.project_folder(project_id, named_by)`,
is the one the spec's Design 2.12 gives and TCW-110's plan calls. Its four
outcomes are unchanged; after the user's decision on U1, an entry whose folder
is empty is "not on this machine" (`Unreachable`), and one whose folder has
contents but no project is a graph problem (`ProjectGraphError`).

No backend operation changes: the twelve operations in `tcw/work/backend.py`
are untouched. Two model types change and pass the litmus test:
`ConnectedProject` loses its filesystem location, and `UnreachableProject`
carries a rendered message and the deciding file, presentation only like its
other fields. `project_folder`, `found`, `manifest_findings` and `checkout_of`
are on `FsProjectRegistry` alone.

## Spec issues found, and how each was settled

1. **AC 27, read literally, could not pass** (`tcw validate` reads ancestors'
   configurations outside the registry). Settled: the spec's AC 27 now counts
   the registry's reads only, both files per candidate.
2. **Design 2.2 did not say whether the walk continues past the project being
   looked up.** Settled: written into Design 2.2, with its consequence (a
   stale entry pointing at a real second copy is a duplicate ID) and the
   cycle guard.
3. **One entry, two findings** (an existing folder without a project:
   "not on this machine" in Design 2.3 and 2.12, `error` in 5.1 b). Settled
   by the user on 2026-10-22: an empty folder (no entries, or only `.git`) is
   not on this machine; a folder with contents and no project is an error.
   Written into Design 2.3, the 2.12 table, 5.1 rows a and b, and AC 8.
4. **Not in the spec's Risks:** the search lists the folder holding a
   project's root, so in the test suite a fixture project at `tmp_path` would
   be searched for among other tests' folders. Handled by step 2's `tmp_path`
   override, and now in the spec's Risks with the same exposure for a real
   project kept directly in the home folder or `/tmp`.
5. **Design 6.4's "every manifest the command has read"** gave an answer that
   depended on which lookups came first (review S3). Settled: the spec now
   reads the manifests of every project in the graph whose connections are
   followed, in Design 2.2's order.
