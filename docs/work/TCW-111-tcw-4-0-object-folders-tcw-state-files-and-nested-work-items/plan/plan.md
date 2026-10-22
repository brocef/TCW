# Plan — TCW 4.0: object folders, `tcw-` state files and nested work items

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). The spec
is `spec/spec.md` beside this folder; "Design n", "AC n" and "row x" (a row
of Design 2.6's table) refer to it.

File and line references are to commit `40d19b82` on `v4`: TCW-106 has
landed there, and TCW-107, TCW-110 and TCW-108 have not. The children land
in the order TCW-106, TCW-107, TCW-110, TCW-108, then this item, so most
lines cited below will have moved by the time this item starts, and some
functions will have been rewritten by TCW-110. Step 0 re-reads every
citation against the commit TCW-108 finishes on and corrects this plan
where a line moved; a citation that names a function TCW-110 rewrote is
re-pointed at what TCW-110 left.

**The gate at every step boundary.** Every step starts by writing its
tests, which are run and seen to fail for the reason they name, and ends
with them passing and with the whole Python suite passing: `.venv/bin/pytest`
with no arguments, run from the worktree's root, as CI runs it. A step that
touches the web client also ends with, from the worktree's root:
`pnpm exec tsc --noEmit`, `pnpm test`, `pnpm lint`,
`pnpm exec prettier --check <each file the step changed or created that
.prettierignore does not exclude>`, and `pnpm build` (which rewrites the
committed folder `tcw/serve/dist`). Not `pnpm typecheck`, which runs
`prettier --check .` over the whole repository first and fails on files no
child of TCW-99 touches (TCW-110 plan, header). A step that cannot end green
is two steps.

**Which `tcw` drives this repository's lifecycle.** The `tcw` first on
`PATH`: the primary checkout's editable install of `main` (3.0.2), which
imports `main`'s code even when run from this worktree (spec Risks, "This
repository's own records, read by v4's code"). It reads this repository's
3.x `tcw-config.yaml`, `meta.yaml` and `item.yaml` files, which stay as they
are until TCW-116. So:

- The 4.0 code is run only by the suite, whose projects are under
  `tmp_path`, and in throwaway projects under the session's scratchpad with
  the current folder set there. Never `.venv/bin/tcw` from a folder inside
  the worktree, never `.venv/bin` first on `PATH` in a shell that runs a
  lifecycle command, and never `scripts/remote_session_setup.sh --force` from
  the worktree (it would repoint the shared install at `v4`). These are the
  rules of TCW-110's plan header, rows 1, 2, 5 and 7, and they matter more
  here: once Step 5 lands, the 4.0 code finds none of this repository's
  items, terms or capabilities (every folder holds a 3.x file), so
  `.venv/bin/tcw work list` here would print nothing and `.venv/bin/tcw
  validate` would report every folder.
- Lifecycle commands (`show`, `advance`, `comment`) for this item use the
  `tcw` on `PATH`, checked first with `which tcw` to be the pyenv shim.

## What this plan relies on

**From TCW-106 (on `v4` now).**

- `tcw/project_files.py`: `VERSION_KEY` (`:39`), `version_line()`
  (`:101-103`), `version_problem(mapping)` (`:111-131`, rows a–d of TCW-106
  Design 3.4), `without_version(mapping)` (`:134-137`). The one version check
  every state-file reader calls.
- `tests/projectfiles.py`: `_versioned(data)` (`:42-63`), the rule for adding
  a version line only to text that stays one mapping, reused by Step 3's
  helper so the rule exists once.

**From TCW-107 (its plan).**

- `tests/projectfiles.py`'s `write_manifest(root, entries)` (TCW-107 plan,
  Step 2), used by AC 15's fixture.
- The `tmp_path` override in `tests/conftest.py` (TCW-107 plan, Step 2), so a
  fixture made at `tmp_path` has its own parent folder.
- The safeguards for a mass conversion of tests (TCW-107 plan, Step 9): an
  inventory before and after, a mutation check, and a mechanical commit kept
  apart from the hand edits. Step 5 uses all three.

**From TCW-110 (its plan, Steps 1, 4, 6, 7, 8, 9).**

- `tcw/ids.py`: `FullId(project, namespace, id_path)` with `parts` and
  `with_id_path`, its equality across subclasses, `ID_PART` and
  `ID_PART_LIMIT`, `IdError`/`MalformedId`, `parse_full_id`, `parse_stored`,
  `sort_input` (forms a–d), `identity(full_id)`. TCW-110 sets no limit on a
  whole identifier's length; Step 2 adds it there (spec Design 4.2,
  TCW-110's handoff).
- `Slug`, a subclass of `FullId` with namespace `work` whose constructor keeps
  `(project, folder)` and whose `folder` property reads `id_path`;
  `Slug.stored(value)` and `Slug.typed(text, current_project)`, the latter
  accepting form a and a one-part form d only (TCW-110 plan, Step 4). Step 8
  widens `typed` to an id-path of several parts.
- `tcw/work/open.py`'s `resolve_work_input(text, backend, root)` and the
  `--parent`/`--blocked-by` resolution in `_new` and `_edit` (TCW-110 plan,
  Step 8): each reference is read from its owner's backend and stored as
  that backend answered it.
- `tcw/locate.py`: `Locator.of(root)`, `read(full_id, named_by) -> Outcome`,
  `owner_root`, `find_tree(store, namespace, text)` and
  `find_tree_writable` (TCW-110 plan, Steps 7 and 8).
- `tcw/store/fs.py`: `FsTreeStore.project_id`, `Term.owner`/`full_id` and
  `Capability.owner`/`full_id` (Step 6 of TCW-110's plan); `get_view`,
  `_found` (Step 8); `_stored_ref(value, namespace) -> Outcome` (Step 9);
  `exact_child(parent, name)` and `exact_path(root, id_path)` (Step 8), which
  Step 1 below moves into the new module so the work layer can use them
  without importing the store module.
- `tests/fullids.py`: `fid(project, namespace, id_path)` and `wid(project,
  folder)`, through which every expected identifier is written.
- `web/client/src/model/identifier.ts` and `work.ts`'s `folderOf`, which
  returns the id-path of a work full identifier (TCW-110 plan, Steps 2 and 4).
- `tests/test_identifier_sweep.py` (TCW-110 plan, Step 15), which refuses a
  project ID joined to a name with `/` by hand; every message this plan adds
  prints identifiers through `FullId`.

**From TCW-108 (its spec; its plan is being written alongside this one).**

- `parents:` in `.tcw/tcw-config.yaml`, with `inherit: none` (TCW-108 Design
  1.1, 1.2), and the refusal of the 3.x `projects:` key (Design 3.5): no
  fixture of this item writes `projects:` (ticket handoff from TCW-108).
- `tcw validate` reporting one `unresolved` finding for a parent project not
  on this machine (Design 6.5 a), which AC 15 allows for.
- Whatever helper TCW-108's plan gives the tests for writing relations
  (its Risks promise one); Step 13 writes AC 15's fixture through it, and
  Step 0 records its name here.

## Choices this plan makes where the spec leaves room

Each is reported to the dispatching session with this plan; the ones marked
**(spec)** are, in this plan's reading, small defects in the spec rather
than room it leaves.

1. **(spec) The checks before a removal keep searching the folder itself.**
   Design 8 lists `remove`'s nested-object checks (`tcw/store/fs.py:1888-1889`,
   `_nested_entries`, `:2528-2534`) among the sites that call the walk. The
   walk skips hidden folders and symbolic links (Design 2.5 step 2), but a
   removal deletes the whole folder, hidden folders included, which is why
   `_nested_entries` says it is "asked of the folder itself rather than
   `_all_meta_dirs`" and why `test_remove_refuses_capability_nested_in_a_dot_directory`
   (`tests/test_capabilities_rm.py:192`) exists. So both checks keep their
   `rglob`, searching for the state file name, and refuse whenever anything
   the removal would delete holds one. They list nothing, so Design 2.5's
   "every lister calls it" still holds.
2. **(spec) `tcw work tickets adopt` keeps its full identifier within 255
   characters too.** Design 4.2 lists where the limit is enforced and leaves
   out a fresh adoption, which makes the folder `<KEY>-<title words>`
   (`tcw/work/jira/tickets.py:160`) and sets `TCW Item` before writing it
   (`:178-180`). In a project with a long ID that value can pass 255, and
   Jira would refuse the edit with its own message. Step 11 applies Design
   4.3's room to adopt, with the real key (known before anything is
   written), and refuses with exit 2 when fewer than 8 characters are left.
3. **(spec) `tcw capabilities set --parent` on an inherited capability is
   refused** (`Refused`, exit 3, "its parent is set in project '<owner>'"),
   since the only place to write it would be an override, which until TCW-112
   holds only field changes, and Design 3.1 says nothing else reads `parent`.
4. **(spec) `tcw validate`'s scans of every `*.yaml` and every `tcw://` link
   keep reading `resources/`.** Design 2.2 says TCW reads `resources/` "in two
   places only". The scans of `tcw/validate.py:280-330` (YAML well-formedness)
   and the link check read every file under the store roots as text; they do
   not read an object's content, and dropping them would leave a design
   document's links unchecked once TCW-116 moves such documents into
   `resources/`. One sentence in Design 2.2 would settle it either way.
5. **(spec) A missing work parent stays a warning.** Row l says "error; for
   work, the existing rules", and the existing rule is a warning
   (`reference_problems`, `tcw/work/references.py:48-51`). The plan keeps the
   warning; AC 16a still exits 1, from row h.
6. **The folder parent of an object below a folder that is not an object is
   none.** Design 3.2 defines it as "the object whose folder directly holds
   its folder". For an item under `<epic>/drafts/` that is `drafts/`, which is
   not an object, so there is no folder parent and no row m warning; AC 6a
   asks for no finding at either item, which this reading gives.
7. **Precedence among rows f, h, b and c.** A folder is reported once: row f
   (a 3.x file) before row h (an item-shaped name without a state file),
   before row b or c. The files inside a 3.x folder are not reported again
   under row d, and a 3.x folder is not reported under row e. A folder whose
   name is a reserved name in another letter case (`Resources`) is never the
   fixed folder, and is row c wherever it sits.
8. **Edits keep a hand-written `id:`** in a work item's state file, as they
   keep the version line (Design 1.4): TCW never writes one (Design 1.3), and
   the files backend rebuilds the file from the item (`_dump`,
   `tcw/work/fs_backend.py:169-184`), which would otherwise drop it.
9. **`tcw taxonomy add --parent <P>`** takes any input form of TCW-110 Design
   3.1, through `find_tree`. A `<P>` that is not found exits 4 and one in a
   project not on this machine exits 5, before anything is written, as
   `tcw work new --parent` does after TCW-110.
10. **`show` prints a `parent:` line only when a parent is set**, as it
    prints `id:` only when there is one (`tcw/capabilities/cli.py:77-78`);
    JSON always carries the key (AC 11).
11. **The web app's create with `nest: true` and no parent** is refused
    with 400, as the CLI refuses `--nest` without `--parent` (exit 2).
12. **"not nested" is said by the backend** through its `report` (standard
    error for the CLI), since the backend is what decides whether the parent
    is one of its items.
13. **A loop of `parent` among terms or capabilities is looked for within the
    active project's own objects**, as the work cycle check is
    (`validate_changes`, `tcw/work/model.py:188-233`, "within this project
    only").
14. **The web app leaves out a term or capability whose state file has a
    version problem**, as `list` does (Design 1.5), and its board does not
    fail for it.

## Step 0 — start from what TCW-106, TCW-107, TCW-110 and TCW-108 left

Nothing is changed in code. **Checks**, in order:

- TCW-106, TCW-107, TCW-110 and TCW-108 are completed and on `v4`.
- Every name in "What this plan relies on" exists with the shape described;
  where one differs, this plan is corrected before Step 1 (it is a document
  of this item's folder, so the correction is part of the item's record). The
  name of TCW-108's relation helper is written into Step 13.
- Every file and line cited below is re-read and corrected.
- `node_modules` exists at the worktree's root (TCW-110's Step 0 ran
  `pnpm install --frozen-lockfile`); otherwise it is run now.
- This item's `spec/spec.md` and `plan/plan.md` are formatted with
  `pnpm exec prettier --write`, as TCW-110 did its own, so later checks of
  changed files include them cleanly.
- **The tests that read this repository's own records.** A fresh search
  (`grep -rn "REPO\b" tests` intersected with `docs/work`, `docs/taxonomy`,
  `docs/capabilities`, `meta.yaml`, `item.yaml`) confirms what was found at
  `40d19b82`: only `tests/test_ledger_3_0.py` reads them, as plain YAML files
  by their 3.x names (`:17-18`, `:31`, `:45-46`, `:52`), never through TCW's
  code, so it keeps passing while the records stay 3.x; and the tests that run
  the worktree's CLI with this repository as their current folder run only
  `--help` (`tests/test_documented_cli_surface.py:130-147`) or serve a
  temporary folder (`tests/serve/test_jira_launcher.py:28-40`). A new hit is
  added to Step 19's note to TCW-116, or, if it runs TCW code against these
  stores, raised before Step 5.

**Proves it:** bare `.venv/bin/pytest` passes, and its count of passing
tests is recorded in the implement round as the baseline.

## Step 1 — one module for object folders

**Creates** `tcw/object_folders.py`, the module Design 1.1 asks for. It
imports only `tcw.findings`, `tcw.project_files` and `tcw.ids`; the work
stage names are read from `tcw.work.model.STAGES` inside the one function
that needs them (`fixed_folders("work")`), so that `tcw/store/fs.py`, which
imports this module, never imports the work layer at load time. It holds,
and nothing else holds:

- `STATE_FILES = {"taxonomy": "tcw-taxonomy.yaml", "capabilities":
  "tcw-capability.yaml", "work": "tcw-work-item.yaml"}` (Design 1.1);
  `LEGACY_STATE_FILES = {"taxonomy": "meta.yaml", "capabilities":
  "meta.yaml", "work": "item.yaml"}`, used only by row f's recogniser
  (AC 21); `RESOURCES = "resources"`; `DESCRIPTION = "description.md"`.
- `fixed_files(namespace)` and `fixed_folders(namespace)` (Design 2.1): for
  taxonomy and capabilities the state file and `description.md`, no fixed
  folder; for work the state file, `capabilities.yaml` (the name
  `tcw/work/layout.py:26` holds, imported from there inside the function) and
  the folders `comments` and every stage name in `STAGES`
  (`tcw/work/model.py:305-319`).
- `reserved_names(namespace)` (Design 2.4): `resources`, and for work also
  `comments` and every stage name; compared in lower case.
- `exact_child(parent, name)` and `exact_path(root, id_path)`, moved here
  from `tcw/store/fs.py` (TCW-110 plan, Step 8) and imported back into it
  under the same names, so every existing caller is unchanged.
- **The walk** (Design 2.5): one private generator, `_visit(root,
  namespace)`, which is the only code in TCW that lists a store's folders
  to find objects. From the root, in name order, skipping hidden names and
  never entering a folder reached through a symbolic link, it classifies
  each folder it meets as an object (holds the state file as a file), an
  organising folder (no state file, directly in the root or in another
  organising folder), a misplaced folder (no state file, inside an object
  folder: row b), a reserved-name folder outside its place (row c), or a 3.x
  folder (holds the legacy name and no state file: row f); and each file it
  meets directly in the root, in an organising folder, or in an object folder
  that is not one of its fixed files. Inside an object folder it does not
  enter the fixed folders or `resources/`; every other folder is entered,
  so a misplaced folder hides nothing (step 4).
- `walk(root, namespace) -> Walk`: a frozen record of `objects` (id-paths,
  `/`-joined, in name order), `folders` (each visited folder that is not an
  object, with its class) and `files` (the loose files and where they sit).
  `object_paths(root, namespace)` returns `walk(...).objects`.
- `is_object(root, namespace, id_path) -> bool`: the same rule for one
  id-path without listing the store (Design 2.5, last paragraph). An id-path
  that is empty, starts or ends with `/`, or has an empty, `.`, `..` or
  hidden part is refused before the disk is read; then each part must exist
  with exactly that spelling (`exact_child`), no folder on the way down may be
  a symbolic link, or a fixed folder or `resources/` of an object above it,
  and the last folder must hold the state file as a file.
- `objects_below(root, namespace, id_path)`: the walk's objects whose
  id-path starts with `id_path + "/"`, for the work rename's refusal (Step
  12), computed from one walk.
- `folder_parent(root, namespace, id_path) -> str | None`: the id-path of the
  folder that directly holds this one when it is an object, else None
  (choice 6).
- `shape_problems(walk, root, namespace, project, *, item_named=None) ->
  list[Finding]`: rows a–g with Design 2.6's messages, and row h when
  `item_named` (a backend's naming rule for a folder's last part) is given;
  each folder reported once by choice 7. A full identifier in a message is
  printed through `FullId`.
- `read_state(path) -> tuple[dict | None, str | None]`: the mapping without
  `tcw-version` and None, or None and `version_problem`'s message; an absent
  file reads as `({}, None)`, so Step 5 can change file names without changing
  what a folder with no state file means (Step 6 changes that).
- `state_text(path, mapping) -> str`: what a writer writes. The first line is
  the existing file's `tcw-version` line exactly as written, wherever it
  stood in the file, or `version_line()` for a new file (Design 1.4); then the
  mapping without `tcw-version`, dumped as the stores dump today
  (`yaml.safe_dump(..., sort_keys=False, allow_unicode=True)`).
- `disagreement(child, folder_parent, parent) -> str | None`: Design 3.2's
  warning text, `<full id> sits in the folder of <folder parent>, but its
  parent is <parent or "not set">; parent: decides (set it to <folder
  parent>, or move the folder)`, or None when there is no folder parent or
  the two agree. Every place that warns (Steps 13 and 14) calls it, so the
  text is one.

**Proves it:** new `tests/test_object_folders.py`, unit tests on folders
built under `tmp_path`: each row of the walk's classification; hidden names
and a symbolic-linked folder skipped; a stage folder of a work item not
entered, and an item inside a `drafts/` folder of an item found; an organising
folder in all three namespaces; `is_object` agreeing with `walk` on every
folder of a mixed fixture (a parametrised test over every folder the fixture
holds), and refusing `/etc`, `a/../b`, `a//b`, `.x`; `exact_path` refusing a
letter-case variant; `state_text` keeping `tcw-version: "4.0.0"` (quoted)
and a version line written after a comment, and starting a new file with
`version_line()`; `read_state` on each of TCW-106 Design 3.4's rows a–d;
`disagreement` for none, agreeing and disagreeing parents. Nothing else uses
the module yet.

## Step 2 — the 255-character limit and the room for title words

**Changes** `tcw/ids.py`:

- `ID_LIMIT = 255` (Design 4.2), and `length_problem(full_id) -> str | None`:
  `<full id> is <n> characters; a full identifier is at most 255`.
- `parse_full_id`, `parse_stored` and `sort_input` refuse text longer than
  `ID_LIMIT` with `MalformedId` (exit 2) naming the limit.

**Changes** `tcw/work/model.py`, beside `title_words` (`:78-92`):

- `MIN_TITLE_WORDS = 8` (Design 4.3) and `words_room(project, parent,
  prefix) -> int`: `ID_LIMIT` minus the project ID, `.work/`, the parent's
  id-path and `/` when `parent` is given, and `prefix` (the backend's prefix
  with its `-`).
- `fitted_words(title, *, project, parent, prefix) -> str`: `title_words`
  with the smaller of today's limit (`FOLDER_LIMIT - PREFIX_ALLOWANCE`,
  `:24-27`) and `words_room(...)`; when the room is under
  `MIN_TITLE_WORDS`, a `UsageError` naming the parent's full identifier and
  saying to nest the item higher or not at all (leave out `--nest`), or, with
  no parent, naming the project ID and saying it leaves no room for any item.

**Proves it:** in `tests/test_ids.py`, a 255-character identifier parsed and
a 256-character one refused naming 255; in new `tests/work/test_title_room.py`,
`words_room` and `fitted_words` at the numbers of AC 14 (a parent of 235
characters leaves exactly 8 with the 11-character date prefix; 227 with the
20-character allowance leaves 7 and refuses naming the parent; a project ID
of 231 characters with no parent refuses naming it). No caller yet.

## Step 3 — a test helper for state files

**Creates** `tests/statefiles.py`, in the style of `tests/projectfiles.py`:

- `TAXONOMY_STATE`, `CAPABILITY_STATE`, `ITEM_STATE`, taken from
  `STATE_FILES`, so a test never spells a state file's name.
- `write_state(path, data="", encoding="utf-8")`: writes `data` with the
  version line in front by `tests.projectfiles._versioned`'s rule (only to
  text that stays one mapping; a test of a broken file, or of a file that
  already says `tcw-version`, gets exactly what it wrote).
- `write_state_data(path, mapping)`: the version line, then
  `yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True)`.
- `read_state(path) -> dict`: the file's mapping without `tcw-version`, for
  assertions that compared a whole `item.yaml` or `meta.yaml` mapping.

**Creates** `tests/test_statefiles_helper.py`: the helpers on literal inputs
(a mapping's text, text already versioned, a list, text that does not
parse, bytes that are not UTF-8).

**Proves it:** the new test file. Nothing else uses the helper yet.

## Step 4 — the inventory, before any test is converted

Taken and kept in the scratchpad, not the repository, exactly as TCW-107's
plan does at its Step 9:

- `.venv/bin/pytest --collect-only -q` (every test ID);
- from a one-off script that walks each test function's syntax tree, the
  number of `assert` statements and `pytest.raises` blocks in each test
  function;
- the list of test files that name a 3.x state file or write a record:
  `grep -rlE "meta\.yaml|item\.yaml|ITEM_FILE" tests` (54 files at
  `40d19b82`), plus the files that call one of the per-file record writers
  (`write_cap`, `write_term`, `term`, `cap`, `_write_term`, `write_item`,
  `_item`; the list is `grep -rlnE "def (write_cap|write_term|_write_term|term|cap|write_item|_item)\(" tests`).

Taken again at the end of Step 5 and at the end of Step 8, the two steps
that change many tests.

## Step 5 — state files replace `meta.yaml` and `item.yaml`

The riskiest step: every reader and writer of the three files changes at
once, and so does every test fixture, because once the code reads the new
names no old fixture is read. It changes **only** the names and the version
line (Design 1.1–1.5, and the `id:` rule of 1.3, row k), never which folders
are objects (Step 6) or what an object folder may hold (Step 7), so that a
failure here can only come from a renamed file or a version line.

**Tests first.** New `tests/test_state_files.py`, in a project `demo`:

- AC 1: `tcw taxonomy add Invoice`, `tcw capabilities add cli/x` and, in a
  files-backend project, `tcw work new 'Add login'` each write its state file
  with `tcw-version: <tcw --version>` as its first line and no `meta.yaml` or
  `item.yaml`; the taxonomy and work state files hold no `id`, the
  capability's holds `id: cap-` and six hexadecimal digits.
- AC 2: with `tcw.project_files.__version__` patched to `4.1.0`, a
  `tcw-capability.yaml` and a `tcw-work-item.yaml` whose first line is
  `tcw-version: 4.0.0` keep it after `tcw capabilities set cli/x --status
  Supported` and `tcw work edit <item> --priority high`.
- AC 3 (trees and files): each of rows a–d written into `cli/x`'s state
  file: `tcw validate` exits 1 naming the file and `tcw-version`;
  `tcw capabilities show cli/x` and `set cli/x --status Supported` exit 1
  and the file is byte for byte unchanged; `tcw capabilities list` beside
  `cli/w` exits 1, prints `demo.capabilities/cli/w` only, names `cli/x`'s
  file on standard error, and its `--json` holds one record; the same rows in
  an item's state file make `tcw work show` and `tcw work list` exit 1
  naming the file.
- AC 8: `id: <its folder name>` passes `tcw validate`; `id: other` is an
  error naming `id`, and `tcw work show <folder>` still shows the item.

New `tests/work/jira/test_jira_state_files.py`, with the suite's Jira fake:
AC 1's Jira half (`tcw work new` and `tcw work tickets adopt <KEY>` each
write a state file holding exactly `tcw-version` and `ticket`); a flat item's
state file of row d with an extra key `added-in-4-1: x`: `tcw work show
<KEY>` shows the item, `tcw validate` reports the file as written by a newer
TCW and does not say "must hold exactly"; and adopt refusing, writing
nothing, on a state file with a version problem (Design 1.5). (AC 3's nested
Jira case is Step 8's, once a nested folder is read.)

**Changes, taxonomy and capabilities** (`tcw/store/fs.py`):

- `FsTaxonomyStore.STATE_FILE` and `FsCapabilitiesStore.STATE_FILE` from
  `STATE_FILES`; every `"meta.yaml"` in the module becomes the store's
  `STATE_FILE`: `_capability_resources` (`:135-142`, given the name),
  `_entry_readable` (`:1382-1391`), `_entry_texts` (`:1577-1581`),
  `_entry_reserved` (`:1600`), `_load_entry` (`:1654`), `_write_entry`
  (`:1681`), `_term` (`:1744`), taxonomy `remove` (`:1888-1889`),
  `_validation_resources` (`:2106`), `update_term` (`:2156`),
  `_is_capability` (`:2255-2256`), `_local_paths` (`:2277`),
  `_override_fields` (`:2290`), `_override_index` (`:2305`), `get_local`
  (`:2399`), `_nested_entries` (`:2534`), `_referrers` (`:2562`),
  `_write_meta` (`:2651`), `_write_target` (`:2668`), `check` (`:2800`,
  `:2856`), `_validation_resources` (`:2891`, `:2900`, `:2903`); and every
  comment and docstring that names `meta.yaml` (`:1387`, `:1569-1575`,
  `:1593`, `:1881-1886`, `:2229-2232`, `:2259`, `:2274`, `:2395`,
  `:2529`, `:2688`, `:3051`).
- `OWNED_YAML_NAMES` (`:794-800`) becomes the three state files, and its
  comment says so.
- `FsTreeStore._state(d) -> dict` replaces each `load_yaml(d / "meta.yaml")`:
  `read_state`; a version problem raises `StateFileProblem`, a new
  `BackendError` subclass in `tcw/errors.py` (exit 1) whose message names the
  file and carries `version_problem`'s text. `FsTreeStore.unreadable`, a
  mapping from file to message, is filled by the listers (`_local_slugs`,
  `_local_paths`, `_override_fields`, `_override_index`, `list_all`, `get_by_id`),
  which leave such an object out and go on (Design 1.5).
- `_write_entry` and `_write_meta` write `state_text(path, meta)`, so a new
  file starts with `version_line()` and an edited one keeps its line; the
  override folder `_write_target` creates (`:2691`) is a new file and starts
  with the version line.
- Both `check()`s (`:2044-2084`, `:2761-2882`) add an error for each entry in
  `self.unreadable` (`<file>: <message>`, which names `tcw-version`), and run
  no other check of that object, since it is not listed. The taxonomy
  `check` adds row k: an `id` that differs from the term's folder name is an
  error naming `id` (capabilities keep their opaque `id`, Design 1.3).
- `tcw/taxonomy/cli.py` `_list`, `_search` (`:68-73`) and
  `tcw/capabilities/cli.py` `_list`, `_search` (`:58-64`): after printing,
  each message in `st.unreadable` goes to standard error and the command
  exits 1. `show`, `set`, `reset`, `rm` meet `StateFileProblem` from `_state`
  before anything is written, and exit 1.

**Changes, work** (`tcw/work/fs_backend.py`, `tcw/work/jira/`,
`tcw/validate.py`):

- `ITEM_FILE` (`tcw/work/fs_backend.py:44`) becomes `STATE_FILE =
  STATE_FILES["work"]`, imported by `tcw/work/jira/backend.py:34` and
  `tcw/work/jira/tickets.py:22` under the new name; the module docstring
  (`:1-6`) names `tcw-work-item.yaml`.
- `KEYS` (`:52-54`) gains `tcw-version` and `id`; `_load` (`:94-166`) calls
  `version_problem` first and raises `Unreadable(path, "tcw-version",
  message)` for rows a–d, so `show` exits 1 naming the file and `list` exits
  1 as for any unreadable item (`:335-339`). `_write` (`:271-274`) writes
  `state_text`, keeping the existing version line and an existing `id`
  (choice 8); `_dump` (`:169-184`) returns the mapping it builds.
- `work_store_problems` (`:528-566`) adds row k for the files backend: an
  `id` that differs from the folder's name is an error at the state file
  naming `id`.
- Jira: `_item_file` (`tcw/work/jira/backend.py:641-650`) writes
  `version_line()` then `ticket: …`. `_item_file_problems` (`:146-167`)
  calls `version_problem` first and, on a problem, reports only that (Design
  1.5); otherwise the keys must be exactly `tcw-version` and `ticket`, and
  may include `id` ("must hold exactly tcw-version and ticket"), and an `id`
  must equal the folder's name (row k). `tickets.py:150-153` and `:182-183`
  use `STATE_FILE`; `adopt`, finishing a folder whose state file exists,
  reads it with `read_state` first and refuses (exit 1) on a version problem,
  writing nothing.
- `tcw/validate.py`: `:300-304`, `:545`, `:592` and the docstrings at `:481`
  and `:502` name `STATE_FILE`.

**Changes, tests.** Every test of Step 4's list, in two commits:

- **Commit 1, mechanical.** A one-off script kept in the scratchpad, not the
  repository, rewrites: `"item.yaml"` and `ITEM_FILE` to `ITEM_STATE`;
  `"meta.yaml"` to `CAPABILITY_STATE` or `TAXONOMY_STATE`, chosen by the line
  (a path holding `capabilities` or `taxonomy`, or the enclosing helper's
  name: `write_cap`/`cap` or `write_term`/`term`/`_write_term`), and listed
  for hand conversion when neither decides; `(<expr> / <STATE>).write_text(<args>)`
  to `write_state(<expr> / <STATE>, <args>)`; `<name> = <expr> / <STATE>`
  followed by `<name>.write_text(` to `write_state(<name>, `;
  `yaml.safe_dump(<m>, <file>)` into a state file to `write_state_data`; and
  adds the imports. The shared writers are converted with them:
  `tests/work/projects.py:62-67` (`write_item`), `tests/work/jira/conftest.py:72`,
  `tests/serve/memory.py:64`, `tests/work/test_backend_contract.py:55`.
  Nothing else is in this commit.
- **Commit 2, by hand.** The lines the script listed; assertions that
  compare a whole state file's text (`== "ticket: …\n"`) or mapping
  (`yaml.safe_load(…) == {…}`), changed to `read_state` or to text with the
  version line, since the file now carries it (Design 1.2); and then every
  failure of the suite, read one by one. An assertion is changed only where
  the spec deliberately changed what it checks, and each such change is
  listed in the implement round with its design rule.

**Proves it**, each result recorded in the implement round:

1. The two new test files, and the full suite, green.
2. **Mutation check, the helper.** With `write_state` and `write_state_data`
   made to write no version line (a one-off patch in a pytest plugin kept in
   the scratchpad, loaded with `-p`), the converted tests that read an object
   go red: the number red is recorded, every converted file holding such a
   test is confirmed to have at least one red test, and the failure reasons
   of at least ten red tests in different files are read and confirmed to be
   the missing `tcw-version`, not an unrelated crash.
3. **Mutation check, the names.** With `STATE_FILES` patched back to
   `meta.yaml` and `item.yaml` in the same way, the converted tests that read
   an object go red for "not found" or "no such", confirming they exercise
   the new names.
4. The inventory: no test ID disappeared, and no test's count of assertions
   dropped, except the ones listed with their reason.
5. `grep -rnE "meta\.yaml|item\.yaml|ITEM_FILE" tests` finds only
   `tests/test_ledger_3_0.py` (this repository's own records, Step 0) and
   `tests/test_git_example.py` (Step 16 rewrites it), each named in the
   round.

## Step 6 — taxonomy and capability stores list objects by the walk

Only a folder holding its state file is a term or a capability now (Design
1.1, 2.3); this step changes which folders are objects, and nothing about
what an object folder holds.

**Tests first**, in new `tests/test_object_walk.py`:

- AC 4 (taxonomy and capabilities): a folder `docs/taxonomy/group/` with no
  state file holding `group/refund`: `tcw taxonomy list` prints
  `demo.taxonomy/group/refund` and not `demo.taxonomy/group`, and `tcw
  taxonomy show group` exits 4; the same layout lists
  `demo.capabilities/group/x`.
- AC 6 (the refusals): `tcw taxonomy add Resources` and `tcw capabilities
  add cli/resources` exit 2 and write nothing; `tcw taxonomy add Review`
  succeeds (reserved names are per store).
- AC 17 (taxonomy, listing): a taxonomy folder holding only `meta.yaml` is
  not listed.
- The 3.x override folders (Design 2.5, last paragraph): an override folder
  at the mirror path and one at `<alias>/<path>` are applied as today and not
  listed as objects of their own.

**Changes** (`tcw/store/fs.py`):

- `_local_slugs` (`:1763-1769`) is `object_paths(self.root, "taxonomy")`,
  filtered by `_entry_readable` (a state file reached through a symbolic link
  out of the store, `:1382-1391`).
- Taxonomy `get_local` (`:1748-1761`) and capabilities `get_local`
  (`:2391-2399`) answer only when `is_object(self.root, <namespace>,
  id_path)` and `_entry_readable`, so `show group` exits 4.
- `_all_meta_dirs` (`:2258-2271`) becomes `_object_dirs`, which is
  `object_paths(self.root, "capabilities")` filtered by `_entry_readable`;
  `_is_capability` (`:2255-2256`) is `is_object`. Its callers keep separating
  override folders by `overrides:` (`_local_paths`, `:2273-2277`).
- `FsTaxonomyStore.add` (`:1830-1865`) and `FsCapabilitiesStore.add`
  (`:2472-2500`): a part of the new id-path that is a reserved name, ignoring
  case, is a `UsageError` (exit 2) before the first `mkdir`; the parent
  check of taxonomy `add` (`:1839-1841`) asks `is_object`, so a parent that
  is an organising folder is "parent term does not exist". Both web create
  routes (`tcw/serve/records.py:82-98`, `:161-178`) inherit it.
- The removal comment at `:1881-1886` loses "a sub-folder without a
  `meta.yaml` still lists as a term"; the check itself keeps its folder
  search (choice 1).
- `tests/test_store_bounds.py`'s two symbolic-link cases
  (`test_taxonomy_list_does_not_advertise_a_symlinked_entry`, `:186`;
  `test_capabilities_list_does_not_advertise_a_symlinked_entry`, `:224`) are
  re-pointed at the walk, as the spec's Coverage says: each also asserts
  that `object_paths` leaves the entry out.

**Changes the tests** whose subject was Problem 2 (a folder without
`meta.yaml` listed as a term), each listed in the round with Design 2.3:
expected to be few, since Step 5's fixtures write state files; found by
the full suite.

**Proves it:** the new file; `tests/test_store_bounds.py`,
`tests/test_taxonomy.py`, `tests/test_capabilities.py`,
`tests/test_capabilities_federation.py`, `tests/test_capabilities_reset.py`
green; the full suite.

## Step 7 — a term's or capability's folder is bounded

**Tests first**, in new `tests/test_object_folder_shape.py`:

- AC 5 (trees): `tcw validate` exits 1 with one error each, with Design
  2.6's message, for a folder `drafts/` with no state file in a term's folder
  (b), a folder `resources/` directly in the capabilities store root (c), a
  capability folder holding a 3.x `meta.yaml` and no state file (f), and a
  `tcw-taxonomy.yaml` in the taxonomy store root (g); it passes with
  `resources/notes.md` and `resources/a/b.png` in a term's folder; it warns
  for `README.md` in the capabilities store root (d) and an empty organising
  folder in the taxonomy store (e).
- AC 6: `docs/taxonomy/review/` with a state file passes.
- AC 7: a term with `resources/diagram.png` and a loose `old.txt`: `tcw
  taxonomy show <term> --json` has `attachments: ["resources/diagram.png"]`
  and `tcw validate` reports `old.txt` (a); a capability with
  `appendedDocs: [resources/camera.md]` shows that file's text at the end of
  its body; `appendedDocs: [camera.md]` with `camera.md` beside the state
  file is an error in `tcw validate` and is not in the body.
- AC 17 (taxonomy, validate): a taxonomy folder holding only `meta.yaml` is
  reported with `tcw migrate` (f), once, and its files are not reported under
  d (choice 7).

**Changes** (`tcw/store/fs.py`):

- `_load_entry` (`:1642-1664`): attachments are the files under the entry's
  `resources/`, at any depth, each `_within_store`, as paths relative to the
  entry's folder, sorted (Design 2.2); `_entry_reserved` (`:1583-1603`) is
  deleted with the loose-file listing it served, and its docstring's
  reasoning moves to `_load_entry`.
- `_compose_body` (`:2311-2326`) reads a `prependedDocs` or `appendedDocs`
  entry only when it resolves inside the capability's `resources/` (and,
  as today, inside the store).
- Capabilities `check` (`:2846-2881`): an entry outside `resources/` is an
  error (`'<entry>' is not in resources/`); "missing attachment" stays; the
  "unlisted extra doc" check (`:2862-2867`) is deleted, since row a now
  reports any loose file, `.md` or not.
- Both `check()`s, when not scoped to one object (`identifier is None`), add
  `shape_problems(walk(self.root, ns), self.root, ns, self.project_id)`:
  rows a–g. A scoped check (the web app's after a save) adds the rows that
  name that object's own folder.
- `_capability_resources` (`:135-142`) and `_validation_resources`
  (`:2086-2109`, `:2884-2910`) keep naming the state file, `description.md`
  and the listed documents, now under `resources/`.

**Changes the tests** that put attachments or prepended documents loose in an
entry's folder (`write_cap(..., docs=…)`, `tests/test_capabilities_federation.py:28-39`,
and the attachment tests of `tests/test_taxonomy.py`): the documents move into
`resources/` and the `prependedDocs`/`appendedDocs` values gain
`resources/`, which is Design 2.2's deliberate change, listed in the round.

**Proves it:** the new file; `tests/test_capabilities_federation.py`,
`tests/test_taxonomy.py`, `tests/test_validate.py`,
`tests/test_tree_store_files_only.py` green; the full suite.

## Step 8 — both work backends find items by id-path, at any depth

This step changes reading only: a nested folder made by hand is found,
listed and checked in both backends. Creating one is Step 9.

**Tests first.** New `tests/work/test_nested_items.py` (files backend) and
`tests/work/jira/test_jira_nested.py` (the Jira fake):

- AC 4 (work): `docs/work/2026/<date>-x/` lists `demo.work/2026/<date>-x`.
- AC 5 (work): `tcw validate` exits 1 with one error each for `notes.md` in
  an item's folder (a), a folder `<date>-x` directly in the work store with no
  state file (h) and a folder `notes` holding a `tcw-work-item.yaml` (i); it
  passes with `resources/notes.md` and `resources/a/b.png` in the item's
  folder; it warns for an empty organising folder `docs/work/empty/` (e).
- AC 6: a hand-made organising folder `docs/work/review/` holding an item is
  an error naming `review`.
- AC 6a: an item `<date>-x` under that `review/` folder and an item
  `<date>-part` under `<epic>/drafts/`: `tcw work list` lists
  `demo.work/review/<date>-x` and `demo.work/<epic>/drafts/<date>-part`,
  `tcw work show` of each id-path shows it, and `tcw validate` exits 1
  reporting `review` (c) and `drafts` (b) and neither item.
- `tcw work show <epic>/<part>` and `demo.work/<epic>/<part>` for a nested
  part made by hand, and `edit`, `comment`, `advance --dry-run`, `path` of
  it (AC 9's reading half).
- AC 10: two folders holding the state file with the key `TCW-5`, one at the
  top and one nested: `tcw work show TCW-5` exits 1 naming both; `tcw
  validate --remote` reports a nested item's `TCW Item` that names another
  id-path; an organising folder `2026/` holding an item passes `tcw
  validate` and the item is listed; a key-named folder `TCW-7-x/` with no
  state file is an error (h) and `tcw work show TCW-7` exits 4; a folder
  `notes/` holding a state file is an error (i).
- AC 3 (Jira, nested): a nested item's state file of row d with an extra
  key: `tcw work show <KEY>` shows the item, and `tcw validate` reports it as
  newer and not "must hold exactly".
- AC 17 (work): an item folder holding only `item.yaml` is not listed by
  `tcw work list` and is reported by `tcw validate` with `tcw migrate` (f).
- AC 18 (reading): `GET /api/work/<id-path, percent-encoded>` for a nested
  item returns its record, and `GET /api/work` lists it (in
  `tests/serve/test_nested_items.py`).

**Changes, the layout and the files backend**

- `Layout.item_folders` (`tcw/work/layout.py:102-109`) is `object_paths(
  self.work_root, "work")`: id-paths, which callers filter with
  `is_item_folder` (Design 5). `Layout.item_dir` (`:90-91`) is unchanged; it
  joins an id-path already.
- `tcw/work/fs_backend.py`: the module function `is_item_folder(path)`
  (`:57-67`) becomes `item_named(name)` (the last part's rule: `ITEM_FOLDER`,
  a real date, at most `FOLDER_LIMIT`); `FsWorkBackend.is_item_folder(id_path)`
  (`:483-484`) is `item_named(last part) and is_object(work_path, "work",
  id_path)` (row 12). `_folder` (`:258-262`) refuses through it, with no `/`
  test. `read_all` (`:193-208`) reads `Layout.item_folders()` filtered by
  `item_named`. `_load` takes the id-path and reads `created` from its last
  part (`:157`, Design 7.1).
- `work_store_problems` (`:528-566`): the walk once; `shape_problems(walk,
  …, item_named=item_named)` for rows a–h, replacing the top-level loop's
  "is not part of a work store" warning and "is not an item folder" error
  (`:541-548`); row i for a folder holding the state file whose last part
  breaks `item_named` ("is not an item folder: its name must be a date, then
  title words"); then today's per-item checks for every item the walk finds.

**Changes, the Jira backend**

- `folder_key` (`tcw/work/jira/backend.py:98-101`) reads the id-path's last
  part (Design 6.1), which corrects every caller that passes `slug.folder`
  (`:454`, `:475`, `:585`, `tickets.py:239`) at once.
- `link_exists` (`:104-109`) takes an id-path and is `folder_key(id_path)
  and is_object(work_path, "work", id_path)` (row 12): a key-named folder
  without the state file is no longer an item (Design 6.1's change in
  behaviour). `is_item_folder` (`:311-312`) and `_key` (`:327-331`) go
  through it.
- `lookup` (`:314-325`) searches a key index built once per backend from
  the walk (`{key: [id-paths]}`, kept on the instance and dropped after a
  write that makes or moves a folder: `create`, `rename`, adopt's
  `_item_file`), so `resolve_keys` (`:391-…`), which calls `lookup` once per
  key, walks the store once per command rather than once per key (spec
  Risks, "Walking costs more"). Two folders anywhere with one key is today's
  error, now naming both id-paths.
- `list` (`:470-482`): a ticket is kept when `is_item_folder(slug.folder)`
  holds (Design 5 row 3), replacing the top-level test at `:474-476`.
- `jira_store_problems` (`:112-143`): the walk once; rows a–h through
  `shape_problems` with `item_named = KEY_FOLDER.fullmatch`, so a key-named
  folder with no state file is row h with today's message (`:151`) at its
  state file, and the top-level "is not a Jira item folder" error (`:125-130`)
  applies only to a folder holding the state file (row i); keys counted
  across every depth; `_item_file_problems` and the warning for record
  folders Jira keeps (`:133-137`) for every item folder.
- `tcw/work/jira/remote.py`: `_folders` (`:415-421`) groups the walk's item
  folders by key, so `_items_and_tickets` (`:451-…`) and `_model_checks`
  (`:505-…`) compare every item folder with its ticket (Design 6.5).

**Changes, the checks and the web app**

- `tcw/validate.py`: `round_findings` (`:644-675`, its loop at `:659`) and
  `_declaration_findings` (`:619-641`, `:634`) read `Layout.item_folders()`,
  filtered by the backend's naming rule; `folders=` is a set of id-paths.
  `_work_target_findings` (`:472-546`) accepts a target id-path containing
  `/` when `backend.is_item_folder` holds (replacing `:500`), and keeps only
  findings under the target's folder and not under a nested item's folder.
  The missing-reference test at `:542-546` asks `is_item_folder`.
- `tcw/work/model.py`: `Slug.typed` (TCW-110) accepts a form d id-path of
  several parts for work, each part checked against `ID_PART`, so a nested
  item is named by its whole id-path (spec Non-goals). TCW-110's 3.4 hint is
  unchanged: it is tried only when such an id-path is not found.
- `tcw/serve/work.py`: nothing beyond the layout: `item_folders`
  (`:74-78`), `item_folder` (`:237-246`) and `checked_reference` (`:365-377`)
  read `Layout.item_folders()`, which is now the walk, so the check that a
  reference names an item of this project uses it (Design 8). The routes
  (`ONE`, `:583`; `ITEM`, `tcw/serve/files.py:357`) already take an id-path
  percent-encoded as one segment, decoded once (`Request.param`,
  `tcw/serve/server.py:172-175`); the existing
  `test_the_web_answers_404_for_an_encoded_slash`
  (`tests/test_literal_store_names.py:39-50`) stays green because
  `is_object` refuses `/etc/passwd` before reading the disk.

**Changes the tests** that asserted today's top-level-only behaviour, each
listed in the round with its design rule: a stray folder at the top of the
work store is no longer "is not an item folder" (Design 2.3, row e or
nothing), a file there says "is not part of any object" (row d), and in Jira
mode a key-named folder without its state file is not found (Design 6.1).
The inventory of Step 4 is taken again and compared.

**Proves it:** the new files; `tests/work/test_fs_backend.py`,
`tests/work/test_validate_work.py`, `tests/work/jira/test_jira_validate_offline.py`,
`tests/work/jira/test_jira_validate_remote.py`, `tests/work/jira/test_jira_tickets.py`,
`tests/test_validate_target.py`, `tests/serve/test_work_read.py` green; the
inventory; the full suite.

## Step 9 — creating a nested item

**Tests first**, added to `tests/work/test_nested_items.py` and
`tests/work/jira/test_jira_nested.py`:

- AC 9: `tcw work new 'Flat' --parent <epic>` creates `<work>/<date>-flat/`
  at the top; `tcw work new 'Part' --parent <epic> --nest` creates
  `<work>/<epic>/<date>-part/` and prints `demo.work/<epic>/<date>-part`;
  `tcw work list` lists all three; `tcw work list --parent <epic>` lists the
  two children. With the Jira fake the same `--nest` command makes
  `<work>/<EPIC-KEY>-…/<KEY>-part/`, sets `TCW Item` to
  `demo.work/<EPIC-KEY>-…/<KEY>-part`, and `tcw work show <KEY>` shows it.
  `--nest` with a parent of another project (form a) creates the folder at
  the top, exits 0 and prints `not nested:` on standard error; `--nest`
  without `--parent` exits 2 and creates nothing (no folder, and with the
  fake no request).
- AC 9a: with the fake set to fail the folder write after `TCW Item` is set,
  the nested `new` exits 1 naming `tcw work tickets adopt <KEY>`, and that
  command then makes `<work>/<EPIC-KEY>-…/<KEY>-part/` holding the state
  file; with the fake set to fail setting `TCW Item`, the adoption makes
  `<work>/<KEY>-part/` at the top.
- In `tests/work/test_backend_contract.py`: `create(..., nest=True)` with a
  parent of this backend puts the folder under the parent's in each backend
  the contract runs.

**Changes**

- `tcw/work/backend.py`: `create(self, title, props, *, stage, request,
  nest=False)` (`:75-77`), with its docstring; the parameter of every other
  operation is renamed `id_path`, with "an item's id-path: its folder's path
  in the work store" in the docstrings (Design 5); `is_item_folder`'s
  docstring (`:108-113`) reads "a folder at any depth under the work path".
  A module function `nesting_parent(backend, parent, nest) -> tuple[str |
  None, str | None]` gives the parent's id-path when `nest` is true and the
  parent is one of this backend's items (`parent.project ==
  backend.project` and `backend.is_item_folder(parent.folder)`), else None,
  with the "not nested: <P> belongs to <project>" note when `nest` is true
  and the parent belongs to another project.
- `tcw/work/fs_backend.py` `create` (`:295-330`): the parent is read with
  `_as_slug` (`tcw/work/model.py:155-161`); the folder is made at
  `<parent id-path>/<date>-<words>` when `nesting_parent` gives one, else at
  the top, and the note goes to `self.report`. (The words are still today's
  `title_words` here; Step 11 fits them.)
- `tcw/work/jira/backend.py` `create` (`:654-738`): the same rule; the
  folder (`:693`) and the `TCW Item` value (`:705-711`) carry the parent's
  id-path; `_item_file` (`:641-650`) already makes parent folders
  (`mkdir(parents=True)`).
- `tcw/work/jira/tickets.py` adopt: nothing new is needed for AC 9a's first
  case, since it resumes from the folder `TCW Item` names (`:142-153`,
  `:183-185`) and `folder_key` reads the last part (Step 8); the test proves
  it.
- `tcw/work/cli.py`: `new_item` (`:159-164`) takes `nest` and passes it on;
  `_new` (`:186-232`) refuses `--nest` without `--parent` as a `UsageError`
  before reading standard input (with the other early refusals, `:188-210`);
  the `new` parser (`:706-718`) gains `--nest` ("put the new item's folder
  inside its parent's folder, when the parent is an item of this project")
  and the example `new 'Part' --parent 2026-10-01-epic --nest`.
- The interface's other implementations in the tests:
  `tests/work/memory_backend.py` and `tests/serve/memory.py` take `nest`.

**Proves it:** the tests above; `tests/work/test_cli_items.py`,
`tests/work/jira/test_jira_write.py`, `tests/test_cli_help_standard.py`
green; the full suite.

## Step 10 — the web app's create offers nesting

**Tests first.** In `tests/serve/test_nested_items.py`: a `POST /api/work`
with a parent and no `nest` makes the item at the top; with `nest: true`
inside the parent's folder; `nest: true` with no parent answers 400 (choice
11). In `web/client/src/ui/work-forms.test.tsx`, "the new item form": the
"inside the parent's folder" option is unticked by default, the request body
carries no `nest` then, and carries `nest: true` when it is ticked with a
parent given (AC 18, the client half).

**Changes**

- `tcw/serve/work.py` `create` (`:468-520`): `nest = request.field("nest",
  bool, required=False, default=False)`, refused without a parent before
  anything is made, and passed to `new_item` (`:512`).
- `web/client/src/ui/work-forms.tsx` `NewItemForm` (`:491-…`): a state
  `nest` (default `false`) and, under the Parent input (`:705-713`), a
  checkbox in the style of the "Start at the first stage" one (`:727-740`):
  "Put its folder inside the parent's folder", shown only for this project
  (`here`) and disabled while Parent is empty; `save` (`:520-…`) adds
  `body.nest = true` when it is ticked and a parent is set.
- `pnpm build` rewrites `tcw/serve/dist`.

**Proves it:** the tests above, `tests/serve/test_work_write.py`, and the web
gate (header).

## Step 11 — no full identifier is longer than 255 characters

**Tests first**, in new `tests/test_identifier_length.py` and
`tests/work/jira/test_jira_nested.py`:

- AC 14: `tcw capabilities add` of an id-path whose full identifier would be
  256 characters exits 2 naming 255 and writes nothing, and one of 255
  succeeds; the same for `tcw taxonomy add` with a long `--slug` under a
  parent. `tcw work new --parent <P> --nest` with a long title under a parent
  whose full identifier is 200 characters prints a full identifier of at most
  255 characters, in the files backend and with the fake. Files backend,
  under a parent of 235 characters: created. Fake, under a parent of 227:
  exits 2 naming the parent, and the fake records no create request. Under a
  parent of 240, both exit 2 naming the parent. A project whose ID is 231
  characters: `tcw work new 'x'` exits 2 naming the project ID. (The parents
  are built by hand, an item nested in an item, with folder names chosen so
  the full identifier has the length named.)
- Choice 2: `tcw work tickets adopt <KEY>` in a project whose ID leaves fewer
  than 8 characters exits 2 and makes no edit on the fake.
- The web app's create under a 200-character parent gets a shortened folder.

**Changes**

- `tcw/store/fs.py`: taxonomy `add` (`:1830-1865`) and capabilities `add`
  (`:2472-2500`) call `length_problem(FullId(self.project_id, ns, path))`
  before the first `mkdir`, as a `UsageError`.
- `tcw/work/fs_backend.py` `create`: the words are `fitted_words(title,
  project=self.project, parent=<parent id-path or None>, prefix=11)` (a date
  and `-`).
- `tcw/work/jira/backend.py` `create`: before the ticket is created (step 1,
  `:672-681`), `fitted_words(..., prefix=PREFIX_ALLOWANCE)` is called for its
  refusal only; after Jira answers with the key (`:693`), the words are
  `fitted_words(..., prefix=len(key) + 1)`, so the room only grows (Design
  4.3).
- `tcw/work/jira/tickets.py:160`: a fresh adoption's words are
  `fitted_words(..., parent=None, prefix=len(key) + 1)`, refusing before step
  3's edit (`:178-180`) (choice 2).

**Proves it:** the tests above; the full suite.

## Step 12 — renaming by id-path, and refusing an item with nested items

**Tests first**, in `tests/work/test_nested_items.py` and
`tests/work/jira/test_jira_nested.py`:

- AC 16 (files): an epic holding a nested part, and a third item whose
  `blocked-by` names the part. `tcw work rename <epic> new-words` exits 3
  naming the part and TCW-114 and changes nothing (the folder, every state
  file byte for byte). `tcw work rename <epic>/<part> new-words` renames the
  part inside the epic's folder: its identifier is
  `demo.work/<epic>/<date>-new-words`, the third item's state file names it,
  and standard error names the old and the new identifier.
- AC 16 (fake): the same nested rename sets the part's `TCW Item` to the new
  id-path; with the fake set to fail the folder move, it exits 1 and `TCW
  Item` is set back.
- AC 14 (rename): `tcw work rename <item> <words>` that would make the item's
  identifier 256 characters exits 2 and moves nothing.

**Changes**

- `tcw/work/fs_backend.py` `rename` (`:424-477`): first, `objects_below`
  filtered by `item_named` (Design 5 row 7); any item found is `Refused`
  (exit 3) with `<full id> has items nested in it (<first nested full id>,
  …); renaming it waits for TCW-114`. The prefix is the date of the last part
  (`:426`, Design 7.1); the new id-path keeps the parent part; then
  `length_problem` of the new identifier as a `UsageError` (Design 4.2);
  `os.rename` within the folder that holds the item (`:452`, Design 7.2);
  `read_all` is the walk (Step 8), so every state file of the store that names
  it is rewritten; `report_mentions` (`:211-223`) searches for the old last
  part, as it searched for the old folder name, skipping `STATE_FILE`.
- `tcw/work/jira/backend.py` `rename` (`:870-909`): the same refusal and
  length check before the `TCW Item` edit; old and new paths under the same
  parent folder; today's setting back on a failed move (`:893-904`, Design
  6.3).
- `tcw/work/cli.py` `rename`'s help (`:805-811`) says "the item: its id-path
  or full identifier".

**Proves it:** the tests above, `tests/work/test_fs_backend.py`'s and
`tests/work/jira/test_jira_write.py`'s existing rename tests; the full suite.

## Step 13 — `parent` for terms and capabilities

**Tests first**, in new `tests/test_tree_parents.py`:

- AC 11: `tcw taxonomy add Refund --parent invoice` writes
  `docs/taxonomy/invoice/refund/tcw-taxonomy.yaml` holding `parent:
  demo.taxonomy/invoice`; `tcw taxonomy show invoice/refund --json` has
  `"parent": "demo.taxonomy/invoice"` and a term with no parent `"parent":
  null`. With capabilities `cli/x` and `cli/y`: `tcw capabilities add cli/w
  --parent cli/x` writes `parent: demo.capabilities/cli/x`, exits 0 and
  prints nothing on standard error; `tcw capabilities add cli/x/z --parent
  cli/y` writes `parent: demo.capabilities/cli/y`, exits 0, and prints a
  warning containing `sits in the folder of demo.capabilities/cli/x` and
  `parent: decides`; `tcw capabilities set cli/w --parent ''` removes
  `parent`.
- AC 13: `tcw validate` reports an error for a capability whose `parent` is
  `demo.taxonomy/x`, names itself, names a capability that does not exist, or
  forms a loop with another capability's `parent`.
- AC 15: two projects side by side in two git repositories, `app` with
  `parents: [{id: core, inherit: none}]` written through TCW-108's relation
  helper, and `core` placed by `write_manifest`: a term of `app` with
  `parent: core.taxonomy/payment` passes `tcw validate` when `core` has that
  term, fails when it does not, and is `unresolved` with exit 0 when `core`'s
  folder is removed, beside TCW-108's one `unresolved` finding for `core`
  itself.
- Choice 3: `tcw capabilities set <inherited> --parent x` exits 3.
- Choice 9: `tcw taxonomy add X --parent core.taxonomy/payment` writes the
  folder at the store root with that `parent`; a `--parent` that is not found
  exits 4 and writes nothing.

**Changes**

- `tcw/store/base.py`: `Term` (`:324-343`) and `Capability` (`:483-508`)
  gain `parent: FullId | None = None`; the abstract `add` of both stores
  (`:372`, `:540`) and `set` (`:573`) take `parent`.
- `tcw/store/fs.py`: `_term` (`:1731-1746`) and `_capability`
  (`:2328-2342`) read `parent` with `parse_stored(value, ns)`, keeping None
  when absent and keeping the text unread when it is malformed (the check
  reports it); `_CAP_STRUCTURAL` (`:2198`) gains `parent`, so it is never a
  field, never merged by an override, and never "unknown field".
- Taxonomy `add` (`:1830-1865`): `--parent` goes through `find_tree`; when
  it names a term of this project's own store the folder is made inside it, as
  today (`:1839-1843`), otherwise at the root; `parent: <its full
  identifier>` is written in both cases (Design 3.3).
- Capabilities `add` (`:2472-2500`) takes `parent` (through `find_tree`),
  writes it, and returns the folder parent's `disagreement` for the CLI to
  print; `set` (`:2707-2716`) takes `parent` (`''` clears it), refuses it on
  an inherited capability (choice 3), and returns the same.
- Both `check()`s: row l, through `_stored_ref` (TCW-110): wrong namespace,
  malformed or 3.x is an error; naming the object itself is an error; not
  found is an error; a project not on this machine is `unresolved`; a loop
  among this project's own objects (choice 13) is an error naming each.
- `tcw/taxonomy/cli.py` and `tcw/capabilities/cli.py`: `_record` gains
  `parent` (text or null) after `owner` (Design 3.1, after TCW-110's
  `identity`); `show` prints `parent:` after `owner:` when set (choice 10);
  capabilities `add` (parser `:250-262`) and `set` (`:264-277`) gain
  `--parent` ("the capability this one belongs under; its full identifier or
  its path here"; for `set`, "an empty value clears it"); `_fields`
  (`:99-118`) accepts `--parent` alone; a returned warning is printed on
  standard error.
- `tcw/serve/records.py` `jsonable` (`:27-37`): `parent` is serialised as
  its text (TCW-110 Step 6 already serialises the identity fields).

**Proves it:** the tests above; `tests/test_taxonomy_cli_contract.py` and
`tests/test_capabilities_cli_contract.py` moved to records with `parent`;
`tests/serve/test_records.py`; the full suite.

## Step 14 — where the folder and `parent` disagree

**Tests first**, in `tests/test_tree_parents.py`,
`tests/work/test_nested_items.py` and `tests/work/jira/test_jira_nested.py`:

- AC 12: `tcw validate` warns, with Design 3.2's text and exit 0, for a
  nested term with no `parent`, a files-backend item nested in `<epic>` whose
  `parent` is another item, and, with the fake under `--remote` only, a
  nested Jira item whose ticket's parent is another ticket; it does not warn
  for an item at the top whose `parent` is `<epic>`, nor for one whose parent
  is in another project; `tcw work edit <part> --parent <other>` prints the
  same warning on standard error. Offline `tcw validate` in Jira mode gives no
  such warning.
- AC 16a: the merge case built by hand (S-7): the epic renamed to
  `<date>-new-words`, and the old folder `<date>-old-words/`, with no state
  file, holding only a part whose `parent` is `demo.work/<date>-old-words`.
  `tcw validate` exits 1 reporting the old folder (h) and the part's `parent`
  (choice 5: today's warning naming the missing item); `tcw work show
  <date>-old-words/<part>` shows the part; after moving the part's folder into
  `<date>-new-words/`, removing the old folder and `tcw work edit
  <date>-new-words/<part> --parent <date>-new-words`, `tcw validate` passes.

**Changes**

- Tree stores' `check()`: row m for each listed local object, with
  `folder_parent` and `disagreement`.
- `tcw/validate.py` `_work_findings` (`:550-617`): for every item read, row m
  from `folder_parent(work_path, "work", id_path)`, kept only when the
  backend's `is_item_folder` holds for it, and `disagreement`, as a warning
  at the item's state file.
- `tcw/work/jira/remote.py` `_model_checks` (`:505-536`): the same, for the
  items read from Jira, at the item (Design 3.2, Notes decision 10).
- `tcw/work/cli.py` `_edit` (`:328-361`): after a change to `--parent`, the
  item is read back and `disagreement` printed on standard error, in both
  backends.

**Proves it:** the tests above; the full suite.

## Step 15 — the plan stage prompt, the abstraction document, the docstring

**Tests first.** In `tests/test_shipped_prompts.py`: `tcw work stage prompt
plan <item>` contains `--parent <slug> --nest` and the sentence that the
part's folder goes inside the parent's folder, and still passes
`test_plan_says_how_to_file_a_part_into_another_project` (`:331-341`). In
`tests/test_docs_describe_3_0.py`: `docs/lifecycle/abstraction.md` holds
Design 9.1's bullet with `resources/` and "id-path" in the interface list,
and `test_the_backend_interface_names_exactly_twelve_operations` (`:373-378`)
still passes. A new test that `tcw/work/backend.py`'s docstring says
"Twelve operations" (AC 19).

**Changes**

- `tcw/work/prompts/plan.md:38-46` (step 6): each part is made with
  `tcw work new "<title>" --parent <slug> --nest`, which puts its folder
  inside the parent's folder so the folders read the way the items relate;
  `--parent`, not the folder, is what makes it a part; `--nest` is passed
  every time, and where the parent cannot hold the part's folder the command
  says so and makes it at the top. The `--project` half of the paragraph is
  unchanged (TCW-114 rewrites it).
- `docs/lifecycle/abstraction.md`: the bullet at `:92-94`, the interface
  list at `:46-66`, and one sentence under "Abstract spine" (`:72-…`), each as
  Design 9.1 writes it.
- `tcw/work/backend.py:8`: "Twelve operations".

**Proves it:** the tests above; `tests/test_shipped_text.py`; the full suite.

## Step 16 — the example commit hook leaves nested items out

**Tests first.** In `tests/test_git_example.py`, AC 20: in a git repository,
a filesystem-mode project with an epic holding a nested part, where the part
has an untracked new file and a tracked file with uncommitted changes and the
epic has a changed file of its own; the hook, run as the `post` hook of a move
of the epic, commits the epic's file and leaves both of the part's files
uncommitted (`git status --porcelain` still shows them). The test file's
existing fixtures move from `item.yaml` to `ITEM_STATE` here.

**Changes** `docs/guide/examples/commit-item-after-move.sh`: it collects every
folder below `$TCW_ITEM_PATH` that holds `tcw-work-item.yaml` (`find . -mindepth
2 -name tcw-work-item.yaml -type f`, read line by line), and passes
`:(exclude)<folder>` for each after `.` to `git add -A --`, to `git diff
--cached --quiet --`, and to `git commit … --`, so neither the staging nor the
commit, which takes the working-tree content of every tracked file its paths
name (Design 9.4), reaches a nested item. It still runs only git.

This hook is bound in this repository's own `tcw-config.yaml` and runs after
every lifecycle move made from the worktree. This repository's items hold
`item.yaml` until TCW-116, so the new search finds nothing here and the hook
commits exactly what it commits today; the first move after this step (the
move to review) is checked to have committed the item's folder as before
(Verification).

**Proves it:** `tests/test_git_example.py`; `tests/test_repo_lifecycle.py`
(the binding is unchanged); the full suite.

## Step 17 — the sweep, and a guard that keeps it swept

**Creates** `tests/test_object_folder_sweep.py` (AC 21), over the `.py`,
`.ts`, `.tsx` and `.mjs` files under `tcw/`, `web/client/src/`, `scripts/`
and `evals/`, test files and `tcw/serve/dist` excepted:

- no match of `meta.yaml`, `item.yaml` or `ITEM_FILE` outside
  `tcw/object_folders.py`, where they appear only in `LEGACY_STATE_FILES` and
  row f's message;
- every `.iterdir()`, `.rglob(` and `.glob(` call is on an allowlist of
  `(file, function)` pairs, each with the reason it is not a listing of a
  store's objects; the only call that lists a store root to find objects is
  `_visit` in `tcw/object_folders.py`.

The allowlist at `40d19b82`, re-made from a fresh search after Step 14 and
checked by the reviewer against that search: `tcw/work/layout.py:120`
(`rounds`, one stage folder) and `:170` (`latest_handoff`);
`tcw/work/fs_backend.py:214` (`report_mentions`: every file's text, for
mentions, not objects), `:324` (`create`'s rollback of its own folder),
`:501` (`read_comments`, the `comments/` folder); `tcw/serve/files.py:67`
(`_handoffs`, one stage folder); `tcw/work/resolve.py:63` (the package's
prompt files); `tcw/store/fs.py:686` (`init`'s test that a default store
folder is empty before it scaffolds one: it reads no object),
`:1543` (`_rm`'s list of the files it deletes), `:1889` and `:2534` (the
removal checks, choice 1), `_load_entry`'s listing of `resources/` (Step 7);
`tcw/validate.py:99` (`_iter`, the YAML and link scans, choice 4). Every
store-root listing the spec's Problem 4 and Design 8 name is gone:
`tcw/work/layout.py:108`, `tcw/work/fs_backend.py:201`, `:538`,
`tcw/work/jira/backend.py:121`, `:320`, `tcw/work/jira/remote.py:418`,
`tcw/validate.py:659`, `tcw/store/fs.py:1768`, `:2261`, and the
attachment listing `:1661` and the "unlisted extra doc" listing `:2864` (Step 7).

Mutation-checked: an `iterdir()` of `self.work_path` put back into
`tcw/work/fs_backend.py`, and `"meta.yaml"` put back into `tcw/store/fs.py`,
each make the test fail naming its file.

**Proves it:** the new test; `tests/test_identifier_sweep.py` (TCW-110) still
green, so no new message joins a project and a name by hand; the full suite.

## Step 18 — this repository's records

In this repository's ledgers, in their **3.x form** (`meta.yaml` and
`description.md`), because the lifecycle `tcw` (header) reads them and
TCW-116 converts them; `.venv/bin/tcw` cannot read them by design.

- New `docs/capabilities/cli/keep-an-objects-other-files-in-its-resources-folder/`
  and `docs/capabilities/cli/group-objects-in-organising-folders/`, status
  `Supported`, `Subject` naming the new terms.
- The 14 changed capabilities in `capabilities.yaml`: the sentence the
  spec's "Capability changes" gives each, in its `description.md`.
- New `docs/taxonomy/state-file/`, `docs/taxonomy/object-folder/`,
  `docs/taxonomy/organising-folder/`; `docs/taxonomy/work-item/`,
  `docs/taxonomy/term/` and `docs/taxonomy/capability/` descriptions
  updated.

The new descriptions are Markdown outside `docs/work/`, so
`tests/test_documented_cli_surface.py` checks every `tcw …` command they put
in backticks against the worktree's CLI; they name only commands and flags
that exist after Step 14 (`tcw work new --nest`, `tcw capabilities add
--parent`), and `tcw migrate` only as the existing descriptions already do.

**Proves it:** with the lifecycle `tcw` from the worktree: `tcw validate`;
`tcw work advance TCW-111 --dry-run` at the end of implement (the records
gate); and `tests/test_documented_cli_surface.py` with the suite.

## Step 19 — notes for the later children

The spec's handoffs (spec, after Risks) were to be recorded on each ticket
when the spec was accepted. The dispatching session checks each is on its
ticket (TCW-110, TCW-112, TCW-114, TCW-116, TCW-117, TCW-99) and posts any
that is missing, and posts what planning added (the text goes in the
implement round first):

- **TCW-112:** `tcw capabilities set --parent` refuses an inherited
  capability (choice 3) until overrides by path; the walk returns 3.x
  override folders, separated by `overrides:`; `prependedDocs` and
  `appendedDocs` are read only from `resources/`.
- **TCW-114:** `objects_below` and `nesting_parent` are the helpers its
  move and rename can reuse; `report_mentions` searches for the old last
  part; the removal checks keep searching the folder itself (choice 1), and a
  rename of a term or capability with nested objects meets the same question.
- **TCW-116:** `tests/test_ledger_3_0.py` reads this repository's
  `meta.yaml` files by name (`:17-18`, `:31`, `:45-46`, `:52`) and must change
  when this repository is migrated; the example commit hook leaves out folders
  holding `tcw-work-item.yaml`, so after migration a nested child here is
  committed with its own moves only (intended); `tcw migrate` must also give a
  hand-written `id:` that differs from the folder's name a report.
- **TCW-117:** beyond the spec's list: the web create form's "inside the
  parent's folder" option; `tcw capabilities add|set --parent`; the new
  `tcw validate` messages of rows a–n; that a long design goes in an item's
  `resources/`; `tcw work new --nest` in `docs/guide/cli.md`.

## Step 20 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: the state files, `resources/`, `--nest` | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99 design, "How 4.0 is built"); what it must say is in the spec's handoff and Step 19; recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | yes: the item folder holds `tcw-work-item.yaml`; `TCW Item` holds a nested id-path; a key is found at any depth | Deferred to TCW-117, as above. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: which files TCW treats as its records, `resources/`, organising folders | Deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written: each kind of record has its own named file with a version; an object's folder holds its own files, its children and `resources/`; folders can group records; `tcw work new --parent … --nest` and the web option; `tcw validate`'s new reports; renaming an item with nested items waits for a later release; names stay within 255 characters; 3.x files are reported with `tcw migrate`. Plain language, no module names. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`tcw/object_folders.py`, `--nest`, `capabilities add|set --parent`, `parent` on term and capability records, `ID_LIMIT`, `fitted_words`, the web option), Changed (state file names, the version line on every state file, the walk replacing every top-level listing, `Layout.item_folders` returning id-paths, the backend operations taking id-paths and `create`'s `nest`, Jira key-named folders needing the state file, attachments and composed documents from `resources/`, the commit hook, the plan stage prompt, `abstraction.md`), Removed (`ITEM_FILE`, `_entry_reserved`, the "unlisted extra doc" check, the top-level "is not an item folder" error), Internal (`tests/statefiles.py`, the sweep guard). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: the `work`, `taxonomy` and `capabilities` skills | Deferred to TCW-117 (spec Design 9.3, Non-goals). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No configuration key is added or changed. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: S-10's "item folder" becomes "object folder" | Deferred to TCW-117 (spec handoff). |

The two `upcoming/` files are named
`TCW-111-tcw-4-0-object-folders-tcw-state-files-and-nested-work-items.md`
(the item's folder name), checked by `tests/test_upcoming_entries.py`, and
formatted with `prettier`.

## Step 21 — the suite as CI runs it

What `.github/workflows/test.yml` runs (AC 22), done locally, since CI does
not run on `v4`:

- the `pytest` job: bare `.venv/bin/pytest` from the worktree's root, never
  `python -m pytest`;
- the `web-build` job: `pnpm install --frozen-lockfile` and `pnpm
  check:build`, which fails if `tcw/serve/dist` differs from a fresh build;

and, beyond CI, `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint`, and
`pnpm exec prettier --check` over every file this item changed or created
(from `git diff --name-only <Step 0's commit>` plus the new files) that
`.prettierignore` does not exclude. A failure is fixed in the step it belongs
to, not with a skip.

## Verification the tests cannot do

- **The QA plan's seven scenarios**, by hand with `.venv/bin/tcw` in
  throwaway projects under the scratchpad (made with `tcw init`), with the
  current folder set there; the Jira scenarios against a Jira test project
  only, never this repository's board, at qa.
- **This repository's lifecycle still runs on `v4`** with the lifecycle `tcw`
  (header) after Step 5 and after Step 16: `which tcw` first, then `tcw work
  show TCW-111` and `tcw validate` from the worktree; and the first lifecycle
  move after Step 16 commits this item's folder as the old hook did (`git
  show --stat HEAD`).
- **A case-insensitive disk.** The reserved-name refusal of `Resources` and
  the walk's exact-spelling rule on macOS's default disk, run locally and
  recorded, since CI's Linux disk is case-sensitive (the test detects the
  disk, as TCW-110's AC 25 test does, and is skipped elsewhere).
- **`pnpm test:e2e`** (`web/e2e/parity.spec.ts`), run as the single command
  `PATH=.venv/bin:$PATH pnpm test:e2e`, so no lifecycle command inherits that
  `PATH`; it is not in CI and needs a browser. It creates items through the
  CLI, so it exercises the new state files end to end; its result is
  recorded.
- **The cost of the walk** on a store of a few hundred items: `tcw work list`
  and `tcw validate` timed on a scratchpad project of 300 generated items
  before and after, recorded, so the spec's Risk "Walking costs more" has a
  number.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1 | 5 |
| 2 | 5 |
| 3 | 5 (trees, files, a flat Jira item); 8 (the nested Jira item) |
| 4 | 6 (taxonomy, capabilities); 8 (work) |
| 5 | 7 (b, c, d, f, g, e in a tree; passing with `resources/`); 8 (a, h, i, e in the work store; passing with `resources/`) |
| 6 | 6 (refusals, `review` as a term); 8 (`review` as a work organising folder) |
| 6a | 8 |
| 7 | 7 |
| 8 | 5 |
| 9 | 8 (reading a nested item); 9 (creating it, both backends, `not nested`, `--nest` without `--parent`) |
| 9a | 9 |
| 10 | 8 |
| 11 | 13 |
| 12 | 14 |
| 13 | 13 |
| 14 | 11 (add, new, both backends, the project ID); 12 (rename) |
| 15 | 13 |
| 16 | 12 |
| 16a | 14 |
| 17 | 6 (taxonomy listing); 7 (taxonomy validate); 8 (work) |
| 18 | 8 (record and board); 10 (create with and without `nest`, the client) |
| 19 | 15 |
| 20 | 16 |
| 21 | 17 |
| 22 | 21 |

Every design rule of the spec's Coverage table reaches a step through these
criteria; in addition 1.1's "one module" is Step 1 and its guard Step 17;
2.5 step 2 (symbolic links) is Step 6's re-pointed `test_store_bounds.py`
cases; 2.5's override folders are Step 6; 5 row 11 (current user) is
unchanged; 9.2 is Step 15. Every step traces to a criterion except 0 (the
starting point), 3 and 4 (the helper and the inventory Steps 5 and 8 rely
on), 18 (the spec's Capability changes), 19 (the spec's handoffs) and 20
(documentation).

**The suite at each step boundary**, checked against the callers each step
leaves behind:

- 1→2→3→4: new modules and a helper only; nothing calls them.
- 5: one step, two commits. The suite is red between the commits (the code
  reads the new names, the fixtures are being moved), so the boundary is the
  end of commit 2, where it is green. A folder with no state file still reads
  as `{}` (`read_state` on an absent file), so the taxonomy store still lists
  such a folder as a term, as 3.x does, until Step 6.
- 5→6: Step 6 changes which folders are objects; the tests that relied on
  Problem 2 are changed in Step 6 itself.
- 6→7: the attachment and prepended-document fixtures move into `resources/`
  in Step 7, with the code that reads them there.
- 7→8: the work store still lists only top-level items until Step 8, which
  changes every top-level listing of the work store together (the layout,
  both backends, the remote check, `validate.py`), so no reader sees nested
  folders while another does not.
- 8→9: `create` gains `nest` with a default of false, and the two test
  backends gain it in the same step, since `new_item` passes it by keyword.
- 9→10→11→12→13→14→15→16→17: each adds behaviour behind a new flag, a new
  check or new text; Step 13's `parent` key is added to `_CAP_STRUCTURAL` in
  the same step as the first writer of it, so no capability ever shows it as
  an unknown field.

## Spec issues found while planning

None of them changes a criterion; each is settled by a numbered choice above
and reported to the dispatching session rather than edited into the spec:
choice 1 (Design 8 lists the removal checks as walk callers, which would
weaken an existing safety test), choice 2 (Design 4.2 omits a fresh
`tcw work tickets adopt` from the 255-character enforcement), choice 3
(`tcw capabilities set --parent` on an inherited capability is undecided),
choice 4 (Design 2.2's "two places only" and `tcw validate`'s file scans),
choice 5 (row l's severity for work), and the store-root listing in `init`
(`tcw/store/fs.py:686`) that AC 21's wording would catch, which Step 17's
allowlist names.
