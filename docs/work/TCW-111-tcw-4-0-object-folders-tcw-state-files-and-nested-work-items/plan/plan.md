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

**Four parts, each ending green and committed.** The user decided on
2026-10-22 to keep this item whole rather than split it (spec Notes), on the
condition that its four parts stay in separate steps and that each part ends
with the whole suite green and a commit, so each can be reviewed on its own
before the next adds to it. The steps are done in this order, which is not
their numbering (the numbers are kept so the plan's cross-references and the
review's hold):

| Part  | What it delivers                                                      | Steps, in order          | Ends with                           |
| ----- | --------------------------------------------------------------------- | ------------------------ | ----------------------------------- |
| 1     | state files and the version                                           | 0, 1, 3, 4, 5            | Step 5's third commit, suite green  |
| 2     | the walk and organising folders (and bounded folders, nested reading) | 6, 7, 8, 17              | a commit after Step 17, suite green |
| 3     | nesting, the length limit and rename                                  | 2, 9, 10, 11, 12, 15, 16 | a commit after Step 16, suite green |
| 4     | parents for terms and capabilities                                    | 13, 14                   | a commit after Step 14, suite green |
| after | records, notes, documentation, the suite as CI runs it                | 18, 19, 20, 21           | the move to review                  |

Step 1's module serves Parts 1 and 2 (its walk is unused until Part 2) and
Step 2's limit serves Part 3, so Step 2 is done at the start of Part 3. The
sweep guard (Step 17) closes Part 2, since Step 8 is the last step that
replaces a listing; it then keeps Parts 3 and 4 from adding one. A step
inside a part may commit on its own as well; Step 5 makes three commits
(Step 5, "Changes, tests").

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
- `connect_projects(root, relation, *ids, inherit=...)` in
  `tests/projectfiles.py`, which TCW-110 creates (its Step 3) and TCW-108
  rewrites to write `parents:` and `children:` (TCW-108 plan, the fixture
  step's commit 2, and its handoff to this item, also posted on this item's
  ticket). Step 13 writes AC 15's fixture as
  `connect_projects(app_root, "parent", "core", inherit="none")`; Step 0
  confirms the relation's spelling against what TCW-108 lands.
- TCW-108's revised plan does not change `tests/projectfiles.py`'s
  `_versioned` ("nothing in this plan hooks into `_versioned`"), so Step 3's
  reuse of it is unaffected; Step 0 confirms that too.

## Choices this plan makes where the spec leaves room

The first draft of this plan settled six questions that were defects in the
spec. The plan review asked for the spec to be fixed instead, and it was
(spec Notes, "Decisions made when the plan review was answered"), so
choices 1 to 6 now only point at the spec rule the plan builds:

1. **The checks before a removal** are not listings: they search everything
   the removal deletes, for every state file and the 3.x names, and refuse
   (spec Design 2.5, "The checks before a removal are not listings"; review
   decision 16). Step 6.
2. **A fresh `tcw work tickets adopt`, and delegation, keep within 255
   characters** (spec Design 4.2). Step 11.
3. **`tcw capabilities set --parent` on an inherited capability is refused**,
   the whole command, before anything is written (spec Design 3.4). Step 13.
4. **`tcw validate` and `resources/`:** the YAML check skips it, the link
   check reads it, and a Markdown file there that is not UTF-8 is a warning
   (spec Design 2.2; review decision 14). The first draft's reason, that
   these scans "do not read an object's content", was wrong: the YAML check
   parses every `*.yaml` and one syntax error switches off every tree check
   (`tcw/validate.py:310-317`, `:418-421`). Step 7.
5. **A missing work parent stays a warning** (spec Design 2.6 l); AC 16a
   still exits 1, from row h. Step 14.
6. **An object in a folder that holds no state file has no folder parent**
   (spec Design 3.2). Step 1 (`folder_parent`).
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
  of this item's folder, so the correction is part of the item's record).
  In particular: `connect_projects`'s relation spelling and `inherit`
  keyword as TCW-108 leaves them (Step 13 uses them), and that TCW-108 left
  `_versioned` unchanged (Step 3 reuses it).
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
  object, with its class), `files` (the loose files and where they sit) and
  `resources` (each object's `resources/` folder, found by its exact
  spelling, which the walk does not enter; Step 7's YAML check skips what is
  under them). `object_paths(root, namespace)` returns `walk(...).objects`.
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
  folder that directly holds this one when it is an object, else None,
  including when it is a misplaced or organising folder (spec Design 3.2).
- `removal_blockers(folder, project_root) -> list[tuple[str, str]]`: for the
  checks before a removal (spec Design 2.5), every file below `folder`, not
  in `folder` itself, named as any of `STATE_FILES` or `LEGACY_STATE_FILES`,
  found with `rglob` so hidden folders, fixed folders and `resources/` are
  all searched; each as `(path relative to the store, "state" or the 3.x
name)`. It lists nothing; Step 17's allowlist names it.
- `shape_problems(walk, root, namespace, project, *, item_named=None) ->
list[Finding]`: rows a–g with Design 2.6's messages, and row h when
  `item_named` (a backend's naming rule for a folder's last part) is given;
  each folder reported once by choice 7. A `skip` argument names files
  another check already reports, which row d leaves out (a tree store's
  leftover `config.yaml`, Step 7). A full identifier in a message is
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
`disagreement` for none, agreeing and disagreeing parents; `folder_parent`
of an item under `<epic>/drafts/` is None; `removal_blockers` finding a state
file under `.drafts/` and under `resources/`, and a 3.x `meta.yaml`, and not
the folder's own state file; `walk(...).resources` holding `resources/` and
not `Resources/`. Nothing else uses the module yet.

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

- `TAXONOMY_STATE = "tcw-taxonomy.yaml"`, `CAPABILITY_STATE =
"tcw-capability.yaml"`, `ITEM_STATE = "tcw-work-item.yaml"`, written as
  literal strings, **not** taken from `STATE_FILES`, so that the code's names
  and the tests' names are two separate facts and Step 5's second mutation
  check can move one without the other. A test never spells a state file's
  name except through these.
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
parse, bytes that are not UTF-8); and one test that the three constants
equal `STATE_FILES`' values, so the two facts cannot drift apart unnoticed.

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
  which leave such an object out and go on (Design 1.5). Because only a
  listing fills it, each `check()` begins by clearing `unreadable` and
  running one full listing of its own store before it reports from it, so its
  findings never depend on what was called before it.
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

**Changes, tests.** Step 5 is three commits, so that each kind of change can
be read on its own:

- **Commit 1, the code and the new tests.** Every production change above,
  `tests/test_state_files.py` and `tests/work/jira/test_jira_state_files.py`.
  No existing test is touched. The suite is red after this commit, on
  purpose: every old fixture still writes `meta.yaml` or `item.yaml`, which
  the code no longer reads.
- **Commit 2, mechanical.** A one-off script kept in the scratchpad, not the
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
  Nothing else is in this commit, and the script itself is not committed. The
  suite is still red after it, where the hand edits are needed.
- **Commit 3, by hand.** The lines the script listed; assertions that
  compare a whole state file's text (`== "ticket: …\n"`) or mapping
  (`yaml.safe_load(…) == {…}`), changed to `read_state` or to text with the
  version line, since the file now carries it (Design 1.2); and then every
  failure of the suite, read one by one. An assertion is changed only where
  the spec deliberately changed what it checks, and each such change is
  listed in the implement round with its design rule. One is known now:
  `tests/work/jira/test_jira_validate_offline.py:50` expects today's
  `exactly one key, ticket; it also has stage`, which becomes the message
  for "must hold exactly tcw-version and ticket" (Design 1.2). The suite is
  green after this commit; that is the end of Part 1.

Between commits 1 and 3 the suite is red, so no other agent working in this
worktree treats a red run then as its own; the implement round says when
commit 3 is in.

**Proves it**, each result recorded in the implement round:

1. The two new test files, and the full suite, green.
2. **Mutation check, the helper.** With `write_state` and `write_state_data`
   made to write no version line (a one-off patch in a pytest plugin kept in
   the scratchpad, loaded with `-p`; it patches `tests.statefiles` in
   `pytest_configure`, which runs before collection imports any test module,
   so a test's `from tests.statefiles import write_state` binds the patched
   function), the converted tests that read an object go red: the number red
   is recorded, every converted file holding such a test is confirmed to have
   at least one red test, and the failure reasons of at least ten red tests
   in different files are read and confirmed to be the missing
   `tcw-version`, not an unrelated crash.
3. **Mutation check, the names.** With only the test side moved, the
   constants in `tests/statefiles.py` set back to `meta.yaml`, `meta.yaml`
   and `item.yaml` by the same kind of plugin, and `STATE_FILES` left alone,
   the converted tests that read an object go red for "not found" or "no
   such". The code still reads the new names while the fixtures now write the
   old ones, so this proves both that the code reads the new names and that
   the tests write through the constants. (Patching `STATE_FILES` instead
   cannot prove this: depending on when the patch lands, the code's copies
   and the tests' constants move together, or only some readers move, and
   the result says nothing.) The one test expected to go red for another
   reason is the helper's own check that the constants equal `STATE_FILES`.
4. **The tests that stay green under both mutations** are listed, and each is
   read by hand. A converted test that asserts something is _not_ listed,
   found or reported passes under every mutation whether it is right or
   empty, for instance when the script guessed taxonomy for a capability
   fixture and the fixture became unreadable. Each such test is confirmed to
   write a fixture its subject actually reads, or fixed, and the list is in
   the round.
5. The inventory: no test ID disappeared, and no test's count of assertions
   dropped, except the ones listed with their reason.
6. `grep -rnE "meta\.yaml|item\.yaml|ITEM_FILE" tests` gives a classified
   list in the round, each hit either converted or kept with its reason. The
   hits expected to be kept: `tests/test_ledger_3_0.py` (this repository's
   own records, Step 0); `tests/test_git_example.py` (Step 16 rewrites it);
   `tests/test_documented_cli_surface.py:306` (a string in a test of a
   regular expression, not a file); `tests/test_migration_guide.py:350`,
   `:359` and `:589` (assertions about the 3.x migration guide's text); and,
   from Steps 6 to 8, the row f, AC 17 and AC 17a tests, which write 3.x
   files on purpose. Any other hit is converted.

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
- AC 17a, in new `tests/test_removal_blockers.py`: `tcw taxonomy rm invoice`
  with `invoice/old/` holding only `meta.yaml` exits 3 naming `invoice/old`
  and `tcw migrate`, every file unchanged (a tree hash before and after, as
  `tests/test_capabilities_rm.py` does); `tcw capabilities rm cli/x` with
  `cli/x/.drafts/y/tcw-capability.yaml` exits 3 with `nested under it`, and
  with `cli/x/resources/sample/tcw-capability.yaml` exits 3 naming that path;
  with none of these, both succeed. The existing
  `test_remove_refuses_capability_nested_in_a_dot_directory`
  (`tests/test_capabilities_rm.py:192-200`) stays green.

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
- The checks before a removal (choice 1, review decision 16): taxonomy
  `remove` (`:1888-1889`) and `_nested_entries` (`:2528-2534`) call
  `removal_blockers(d, …)`. A state-file hit keeps today's message (`nested
under it: …`); a 3.x hit refuses first with `<path> holds a TCW 3.x <file>;
run 'tcw migrate' in this project first`. Both are `Refused` before
  anything is deleted. The comment at `:1880-1887` loses "a sub-folder
  without a `meta.yaml` still lists as a term" and says why the check is not
  the walk; `_nested_entries`' docstring names `removal_blockers`.
- `tests/test_store_bounds.py`'s two symbolic-link cases
  (`test_taxonomy_list_does_not_advertise_a_symlinked_entry`, `:186`;
  `test_capabilities_list_does_not_advertise_a_symlinked_entry`, `:224`) are
  re-pointed at the walk, as the spec's Coverage says: each also asserts
  that `object_paths` leaves the entry out.

**Changes the tests** whose subject was Problem 2 (a folder without
`meta.yaml` listed as a term), each listed in the round with Design 2.3.
Known now: `tests/test_taxonomy_rm_gaps.py:176-201`, the two tests under
"review fix S1: a sub-folder without a meta.yaml still lists as a term"
(`test_a_reference_to_a_folder_under_the_term_refuses_the_removal`, which
asserts `lists(root, "zed/sub")` for a folder with no state file, and
`test_a_term_naming_a_folder_under_the_term_refuses_the_removal`). Their
subject no longer exists: `zed/sub` with no state file is not a term (a
misplaced folder, row b), so a reference to it names no term. Each is
rewritten so `zed/sub` holds a state file, which makes the removal refused as
nested (the reason it is still refused); the inventory lists both. Others
are found by the full suite.

**Proves it:** the new files; `tests/test_store_bounds.py`,
`tests/test_taxonomy_rm_gaps.py`, `tests/test_capabilities_rm.py`,
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
- AC 5's other cases (review decision 14, and row d's skip): a leftover
  `config.yaml` at the taxonomy store's root gives exactly one finding, the
  existing `no longer read since TCW 2.5.0` error, and no row d warning; a
  `resources/sample.yaml` holding `a: [unclosed` in a term's folder gives no
  finding, and a capability beside it with `appendedDocs:
[resources/ghost.md]` and no such file still gives `missing attachment`, and
  the note `taxonomy and capabilities checks skipped` is absent; the same
  `sample.yaml` loose in the term's folder, not under `resources/`, is still a
  YAML error and still switches the checks off, as today; a
  `resources/old.md` holding bytes that are not UTF-8 is a warning naming
  `not checked for tcw:// links`, and validate exits 0 for it; a
  `resources/design.md` with a broken `tcw://` link is still an error.

**Changes** (`tcw/store/fs.py`, `tcw/validate.py`):

- `_load_entry` (`:1642-1664`): attachments are the files under the entry's
  `resources/`, found with `exact_child(d, "resources")` so a `Resources/`
  folder on a disk that ignores case is never read as it, at any depth, each
  `_within_store`, as paths relative to the entry's folder, sorted (Design
  2.2); `_entry_reserved` (`:1583-1603`) is
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
  `shape_problems(walk(self.root, ns), self.root, ns, self.project_id,
skip={self.root / self.LEGACY_CONFIG_NAME})` when `LEGACY_CONFIG_NAME` is
  set: rows a–g, with row d leaving out the file `_legacy_config_problems`
  (`:1619-1640`) already reports. A scoped check (the web app's after a save)
  adds only the rows that name a file or folder inside that object's own
  folder (a, b, f, and c for a folder directly inside it), never b or c of a
  folder above it, which belong to the whole-store check.
- `tcw/validate.py` `_file_findings` (`:280-349`): before its two loops it
  takes, for each scan root that is a store root, `walk(root, ns).resources`
  (for the work root, `walk(work_root, "work")`), and:
  the YAML loop (`:298-325`) skips every file under one of those folders, so
  nothing there sets `yaml_syntax_error`; the link loop (`:327-348`) still
  reads every `*.md` under them, and for one `_read_text` cannot read adds a
  `warning` `not checked for tcw:// links: <reason>` instead of an error. A
  scan root that is one object (`_target_roots`) uses the walk of the store
  it belongs to. The comment above the YAML loop says why `resources/` is
  skipped (spec Design 2.2).
- `_capability_resources` (`:135-142`) and `_validation_resources`
  (`:2086-2109`, `:2884-2910`) keep naming the state file, `description.md`
  and the listed documents, now under `resources/`.

**Changes the tests** that put attachments or prepended documents loose in an
entry's folder (`write_cap(..., docs=…)`, `tests/test_capabilities_federation.py:28-39`,
and the attachment tests of `tests/test_taxonomy.py`): the documents move into
`resources/` and the `prependedDocs`/`appendedDocs` values gain
`resources/`, which is Design 2.2's deliberate change, listed in the round.
Known now, each listed in the round with its rule:

- `tests/test_capabilities_federation.py:210-214`
  (`test_check_unlisted_extra_doc`): the "unlisted extra doc" check is
  deleted; the loose `stray.md` is now row a, so the test asserts `is not one
of` … `move it into resources/`.
- `tests/test_taxonomy.py:877-889`
  (`test_a_config_yaml_in_a_term_folder_is_still_not_an_attachment`): with
  attachments read only from `resources/`, neither the loose `config.yaml` nor
  the loose `notes.md` is an attachment (`attachments == []`), and both are
  row a in `tcw validate`; the test is rewritten to say so, keeping its point
  that `config.yaml` is never an attachment.
- `tests/test_capabilities.py:690-712`: its docstring names
  `_entry_reserved`, which is deleted; the docstring is updated and the
  assertions are unchanged.

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
  state file is an error (h), `tcw work show TCW-7` exits 4, and a fresh
  `tcw work tickets adopt TCW-7` (the fake's ticket naming no item, its
  summary giving other words) exits 3 naming `TCW-7-x`, records no edit on
  the fake and makes no folder (spec Design 6.4); a folder `notes/` holding a
  state file is an error (i). And a resumed adoption whose `TCW Item` names
  `TCW-8-y`, where `TCW-8-y/` exists with no state file, finishes that folder
  (the existing resume tests of `tests/work/jira/test_jira_tickets.py` stay
  green).
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
  behaviour). Its callers all take the new rule with no change of their own,
  and each is named in the round: `is_item_folder` (`:311-312`) and `_key`
  (`:327-331`); `tcw/refs.py:147` (`tcw://` links to work items);
  `tcw/work/open.py:232` (a reference into another project's Jira store);
  `tcw/work/jira/remote.py:497` (the remote check).
- `lookup` (`:314-325`) searches a key index built once per backend from
  the walk (`{key: [id-paths]}`, kept on the instance), so `resolve_keys`
  (`:391-…`), which calls `lookup` once per key, walks the store once per
  command rather than once per key (spec Risks, "Walking costs more"). The
  index is dropped inside the two methods that make or move a folder,
  `_item_file` (`:641-650`) and `rename`, not at their call sites, since
  `delegate_to_jira` (`tcw/work/jira/tickets.py:389`) and adopt call
  `_item_file` directly. (`tcw serve` opens a backend per request,
  `tcw/serve/work.py:69`, so the index never outlives one request there.)
  Two folders anywhere with one key is today's error, now naming both
  id-paths.
- `key_folders(key) -> list[str]`, new on `JiraBackend`: every folder the walk
  met whose last part is named for `key`, with a state file or without one
  (the walk's objects and its row h folders), as id-paths. Only adopt uses it.
- `tcw/work/jira/tickets.py` adopt (`:138-160`, spec Design 6.4): `here`
  comes from `key_folders(key)` instead of `lookup(key)` (`:138`): no folder
  is None, one is its id-path, two or more is `lookup`'s existing error
  naming them all. Every rule after it is unchanged, so the "unfinished" test
  (`:150-153`) still lets a stateless folder be finished at a status nothing
  moved on from, `:154-155` still refuses a moved-on ticket whose state file
  is gone, and `:158-159` still refuses a fresh adoption beside any folder
  for the key. The first plan draft's reading, that the "unfinished" branch
  becomes dead code and can go, was wrong: with `lookup` answering it would
  silently lose the refusal `tests/work/jira/test_jira_tickets.py:337-348`
  (`test_an_item_moved_on_whose_item_yaml_is_gone_is_not_taken_back`)
  checks.
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
Known now:

- `tests/work/test_fs_backend.py:353-375` (`test_work_store_problems`): the
  empty `inbox/` at the top is still an error, now row c (`'inbox' is
reserved in the work store`), and `dod.yaml` is still a warning, now row d
  (`is not part of any object`). Neither of the new messages carries today's
  pointer to the 2.8-to-3.0 migration guide, so the two `MIGRATION_GUIDE`
  assertions (`:373-374`) become assertions of the row c and row d messages.
- `tests/work/test_validate_work.py:81-86`
  (`test_an_inbox_folder_names_the_guide`) and `:178-181`
  (`test_validate_names_the_guide_for_a_status_folder`): the same `inbox/`
  folder is still the one error and validate still exits 1, now with row c's
  message; the `MIGRATION_GUIDE` assertions change to it, and both tests are
  renamed to say what they now check.
- `tests/work/jira/test_jira_validate_offline.py:55`: an empty `tcw-5-x/` is
  now an organising folder with nothing in it, a row e warning and exit 0,
  not "is not a Jira item folder"; that case moves out of `test_each_error`
  into a warning test, and a `tcw-5-x/` holding a state file takes its place
  as row i.
- `tests/work/jira/test_jira_validate_offline.py:116-122`
  (`test_link_exists`): `TCW-1-x/` is made with a state file, and a stateless
  `TCW-1-z/` is added as not an item.
- `tests/work/test_backend_contract.py:235-245`
  (`test_only_its_own_item_folders_are_items`) stays green unchanged:
  `notes/` and `2026-10-02-no-item-file/` were not items and are not.

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
- A nested create's `created` date (the `folder[:10]` read below): in the
  files backend, with the clock set to 2026-10-22, `tcw work new 'Part'
--parent 2026/2026-10-01-epic --nest`, the parent inside an organising
  folder `2026/` as AC 4 allows, exits 0 with no traceback, makes
  `2026/2026-10-01-epic/2026-10-22-part/`, and `tcw work show` of it says
  `created: 2026-10-22`; and under a parent at the top
  (`2026-10-01-epic`), the part's `created` is 2026-10-22, not the parent's
  2026-10-01.

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
  the top, and the note goes to `self.report`. The `created` date of the
  record it builds (`:311`, `date.fromisoformat(folder[:10])`) is read from
  the id-path's last part, since `folder` is now the whole id-path: under a
  parent at the top `folder[:10]` would silently take the parent's date, and
  under a parent in an organising folder it reads `2026/2026-`, whose
  `ValueError` the `except BaseException` rollback (`:321-328`) re-raises as
  a traceback. (The first draft named `:157` for Design 7.1; `:157` already
  reads `folder.name[:10]` of a `Path` and needs no change.) The words are
  still today's `title_words` here; Step 11 fits them.
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

**Proves it:** the tests above, the nested-date test first seen to fail
with the traceback; `tests/work/test_cli_items.py`,
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
  than 8 characters exits 2 and makes no edit on the fake; a delegation
  (`tcw work new --project <other>`) into a project whose ID leaves fewer
  than 8 characters sets a `TCW Item` of at most 255 characters.
- After the ticket exists (spec Design 4.3): under a parent of 226
  characters (exactly 8 left at the 20-character allowance), the fake set to
  answer with the 24-character key `ABCDEFGHIJKLMNOPQRSTU-12` makes the item
  with title words of 3 characters, exits 0, and its `TCW Item` is at most
  255 characters; under the same parent, a 28-character key
  (`ABCDEFGHIJKLMNOPQRSTUVWXY-12`, leaving 253 - 226 - 28 = -1 characters)
  leaves no character, so `TCW Item` is never edited, the command exits 1
  naming `tcw work tickets adopt ABCDEFGHIJKLMNOPQRSTUVWXY-12`, and no usage
  error is raised. (Every length here is of a full identifier, as in AC 14:
  the room after the key is 255 - parent - 1 - (key + 1).)
- Row n (spec AC 14's `tcw validate` part): a capability folder made by hand
  whose full identifier is 256 characters, and in a files-backend project an
  item nested by hand whose full identifier is 256 characters (a parent item
  folder and a child folder, each a legal id-part, sized to the total), each
  give one error at its state file naming 255, `tcw validate` exits 1, and
  `tcw capabilities list` and `tcw work list` still list them; the same
  layouts at 255 characters give no row n finding. With the Jira fake, a
  nested key-named folder of 256 characters gives the same error offline.
- The web app's create under a 200-character parent gets a shortened folder.

**Changes**

- `tcw/store/fs.py`: taxonomy `add` (`:1830-1865`) and capabilities `add`
  (`:2472-2500`) call `length_problem(FullId(self.project_id, ns, path))`
  before the first `mkdir`, as a `UsageError`.
- `tcw/work/fs_backend.py` `create`: the words are `fitted_words(title,
project=self.project, parent=<parent id-path or None>, prefix=11)` (a date
  and `-`).
- `fitted_words` gains `refuse=True`. With `refuse=False`, the rule for after
  a ticket exists (spec Design 4.3), it never raises: it cuts the words to
  the room however short, and returns None when the room is under 1
  character. It never falls back to `title_words`' `untitled` (8 characters)
  when that would not fit.
- `tcw/work/jira/backend.py` `create`: before the ticket is created (step 1,
  `:672-681`), `fitted_words(..., prefix=PREFIX_ALLOWANCE)` is called for its
  refusal only; after Jira answers with the key (`:693`), the words are
  `fitted_words(..., prefix=len(key) + 1, refuse=False)`. A None stops before
  the `TCW Item` edit (`:705-711`) with the existing message, `created Jira
ticket <KEY>, but …; finish with tcw work tickets adopt <KEY>`, the reason
  being that no room is left under the parent for this key.
- `tcw/work/jira/tickets.py:160`: a fresh adoption's words are
  `fitted_words(..., parent=None, prefix=len(key) + 1)`, refusing before step
  3's edit (`:178-180`) (choice 2); the key is known before anything is
  written, so this one may refuse.
- `tcw/work/jira/tickets.py:385` (`delegate_to_jira`, until TCW-114 removes
  it): the words are `fitted_words(..., project=project_id, parent=None,
prefix=len(key) + 1, refuse=False)`, after the ticket exists; a None skips
  the `TCW Item` edit and raises the existing `did not finish` error
  (`:391-394`). Adopt and delegation now both go through `fitted_words`, so
  the rule lives in one place.
- Row n: both tree `check()`s, `work_store_problems` and
  `jira_store_problems` call `length_problem(<full id>)` for every object the
  walk lists (3.x override folders excepted), as an error at its state file.
  The limit lives in the parsers and the builders, never in `FullId`'s
  constructor, so these objects are still listed and read (spec Design 2.6,
  after the table).

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
  and standard error names the old and the new identifier; a Markdown file
  in the third item's `resources/` naming `<epic>/<part>` is listed as still
  naming the old identifier, and one naming only `<other-epic>/<part>`, the
  same last part under another parent, is not.
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
  it is rewritten; `report_mentions` (`:211-223`) searches for the old
  id-path (for an item at the top, the old folder name it searches for
  today), skipping `STATE_FILE` (spec Design 7.2).
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
  `parents: [{id: core, inherit: none}]` written by
  `connect_projects(app_root, "parent", "core", inherit="none")` (TCW-108's
  form of TCW-110's helper), and `core` placed by `write_manifest`: a term of `app` with
  `parent: core.taxonomy/payment` passes `tcw validate` when `core` has that
  term, fails when it does not, and is `unresolved` with exit 0 when `core`'s
  folder is removed, beside TCW-108's one `unresolved` finding for `core`
  itself.
- Choice 3: in a project whose parent project `core` (linked with
  `connect_projects(..., inherit=["capabilities"])`) holds `cli/v`,
  `tcw capabilities set core.capabilities/cli/v --parent cli/x --status
Supported` exits 3 naming `core`, and a tree hash of both projects is
  unchanged: the `--status` half is not applied either (spec Design 3.4,
  AC 11).
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
  print; `set` (`:2707-2716`) takes `parent` (`''` clears it) and returns the
  same. On an inherited capability (`_write_target`, `:2655-2697`, would
  choose an override folder) a given `parent` raises `Refused` before
  `_write_target` is called, so no other field of the same command is
  written (choice 3).
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

**Changes the tests** that assert no findings, or count them, over a term
or capability nested by hand in another's folder with no `parent`, which row
m now warns about (the suite at each step boundary, Part 4); each is listed in
the round with Design 3.2.

**Proves it:** the tests above; the full suite. This step closes Part 4: the
suite green, and a commit.

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
uncommitted (`git status --porcelain` still shows them), while the epic's
`resources/sample/tcw-work-item.yaml` is committed with the epic. A second
test makes a folder below the item unreadable (`chmod 000`, skipped when
run as root) and checks the hook exits non-zero and commits nothing. The test
file's existing fixtures move from `item.yaml` to `ITEM_STATE` here.

**Changes** `docs/guide/examples/commit-item-after-move.sh`: it collects every
folder below `$TCW_ITEM_PATH` that holds `tcw-work-item.yaml`, with a `find`
that prunes what the walk does not enter (spec Design 9.4): hidden folders,
`resources`, `comments` and every stage folder, the stage names written into
the script as one list with a comment naming `tcw/work/model.py`'s `STAGES`
(a test compares the two, so the list cannot drift). It collects the result
with `found=$(find …)`, so `set -e` sees `find`'s exit status (a pipe into
`while read` would hide it), then reads it line by line, and passes
`:(exclude)<folder>` for each after `.` to `git add -A --`, to `git diff
--cached --quiet --`, and to `git commit … --`, so neither the staging nor the
commit, which takes the working-tree content of every tracked file its paths
name (Design 9.4), reaches a nested item. It still runs only git and `find`.
Under the script's `set -eu`, a `find` that cannot read a folder fails the
hook before anything is staged, which the move reports as a failed `post`
check (exit 6); that is intended, since committing without knowing which
files are a nested item's would be the failure this change exists to
prevent.

This hook is bound in this repository's own `tcw-config.yaml` and runs after
every lifecycle move made from the worktree. This repository's items hold
`item.yaml` until TCW-116, so the new search finds nothing here and the hook
commits exactly what it commits today; the first move after this step (the
move to review) is checked to have committed the item's folder as before
(Verification).

**Proves it:** `tests/test_git_example.py`; `tests/test_repo_lifecycle.py`
(the binding is unchanged); the full suite. This step closes Part 3: the
suite green, and a commit.

## Step 17 — the sweep, and a guard that keeps it swept

**Creates** `tests/test_object_folder_sweep.py` (AC 21), over the `.py`,
`.ts`, `.tsx` and `.mjs` files under `tcw/`, `web/client/src/`, `scripts/`
and `evals/`, test files and `tcw/serve/dist` excepted:

- no match of `meta.yaml`, `item.yaml` or `ITEM_FILE` outside
  `tcw/object_folders.py`, where they appear only in `LEGACY_STATE_FILES`,
  row f's message and `removal_blockers`' message, and the removal checks'
  3.x message in `tcw/store/fs.py`, which takes the names from
  `LEGACY_STATE_FILES` (so it spells neither);
- every `.iterdir()`, `.rglob(`, `.glob(`, `os.listdir(`, `os.scandir(` and
  `os.walk(` call is on an allowlist of `(file, function)` pairs, each with
  the reason it is not a listing of a store's objects; the only call that
  lists a store root to find objects is `_visit` in `tcw/object_folders.py`.

The allowlist at `40d19b82`, re-made from a fresh search at the end of Part
2 (after Step 8) and again after Step 14, and checked by the reviewer against
that search: `tcw/work/layout.py:120`
(`rounds`, one stage folder) and `:170` (`latest_handoff`);
`tcw/work/fs_backend.py:214` (`report_mentions`: every file's text, for
mentions, not objects), `:324` (`create`'s rollback of its own folder),
`:501` (`read_comments`, the `comments/` folder); `tcw/serve/files.py:67`
(`_handoffs`, one stage folder); `tcw/work/resolve.py:63` (the package's
prompt files); `tcw/store/fs.py:686` (`init`'s test that a default store
folder is empty before it scaffolds one: it reads no object),
`:1543` (`_rm`'s list of the files it deletes), `_load_entry`'s listing of
`resources/` (Step 7); `tcw/object_folders.py`'s `exact_child` (TCW-110's
`os.listdir` of one folder, to compare spellings) and `removal_blockers`
(the checks before a removal, choice 1, which replace the `rglob`s at
`tcw/store/fs.py:1889` and `:2534`); `tcw/validate.py:99` (`_iter`, the YAML
and link scans, choice 4); and outside `tcw/`, which the guard also scans:
`evals/coverage.py:88` (the skill folders), `evals/grade.py:216` and `:681`
(a run's own output folders), `evals/seed_fixture.py:737` (whether a
destination folder is empty), `scripts/cut_version.py:137-138` (the
`upcoming/` entry files). Every
store-root listing the spec's Problem 4 and Design 8 name is gone:
`tcw/work/layout.py:108`, `tcw/work/fs_backend.py:201`, `:538`,
`tcw/work/jira/backend.py:121`, `:320`, `tcw/work/jira/remote.py:418`,
`tcw/validate.py:659`, `tcw/store/fs.py:1768`, `:2261`, and the
attachment listing `:1661` and the "unlisted extra doc" listing `:2864` (Step 7).

Mutation-checked: an `iterdir()` of `self.work_path` put back into
`tcw/work/fs_backend.py`, an `os.listdir(self.root)` put into
`tcw/store/fs.py`, and `"meta.yaml"` put back into `tcw/store/fs.py`, each
make the test fail naming its file.

This step closes Part 2: the suite green, and a commit.

**Proves it:** the new test; `tests/test_identifier_sweep.py` (TCW-110) still
green, so no new message joins a project and a name by hand; the full suite.

## Step 18 — this repository's records

In this repository's ledgers, in their **3.x form** (`meta.yaml` and
`description.md`), because the lifecycle `tcw` (header) reads them and
TCW-116 converts them; `.venv/bin/tcw` cannot read them by design.

- New `docs/capabilities/cli/keep-an-objects-other-files-in-its-resources-folder/`
  and `docs/capabilities/cli/group-objects-in-organising-folders/`, status
  `Supported`, `Subject` naming the new terms.
- The 19 changed capabilities in `capabilities.yaml`: the sentence the
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
- **TCW-114:** the release note and changelog of this item do not mention
  that renaming an item with nested items is refused, because TCW-114 lifts
  that in the same release; if TCW-114 does not land in 4.0 after all, its
  own `upcoming/` entry must say so. `objects_below` and `nesting_parent`
  are the helpers its move and rename can reuse; `report_mentions` searches
  for the old id-path; the removal checks search the folder itself with
  `removal_blockers` (choice 1), and a rename of a term or capability with
  nested objects meets the same question.
- **TCW-116:** `tests/test_ledger_3_0.py` reads this repository's
  `meta.yaml` files by name (`:17-18`, `:31`, `:45-46`, `:52`) and must change
  when this repository is migrated; until a store is migrated, `rm` of a
  term or capability with a 3.x folder below it is refused naming `tcw
migrate` (review decision 16); the example commit hook leaves out folders
  holding `tcw-work-item.yaml`, so after migration a nested child here is
  committed with its own moves only (intended); `tcw migrate` must also give a
  hand-written `id:` that differs from the folder's name a report.
- **TCW-117:** beyond the spec's list: the web create form's "inside the
  parent's folder" option; `tcw capabilities add|set --parent`; the new
  `tcw validate` messages of rows a–n; that a long design goes in an item's
  `resources/`; `tcw work new --nest` in `docs/guide/cli.md`.

## Step 20 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry                                                                  | Fires?                                                                                                          | Answer                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md` [Public-API]                                               | yes: the state files, `resources/`, `--nest`                                                                    | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99 design, "How 4.0 is built"); what it must say is in the spec's handoff and Step 19; recorded in the implement round.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `docs/guide/jira.md` [Jira-Change]                                     | yes: the item folder holds `tcw-work-item.yaml`; `TCW Item` holds a nested id-path; a key is found at any depth | Deferred to TCW-117, as above.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `docs/guide/<topic>.md` [Guide-Topic-Change]                           | yes: which files TCW treats as its records, `resources/`, organising folders                                    | Deferred to TCW-117.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `docs/release-notes/upcoming/<folder>.md` [Public-API]                 | yes                                                                                                             | Written: each kind of record has its own named file with a version; an object's folder holds its own files, its children and `resources/`; folders can group records; `tcw work new --parent … --nest` and the web option; `tcw validate`'s new reports; names stay within 255 characters; 3.x files are reported with `tcw migrate`, and removing a record above one is refused. Plain language, no module names. It does **not** say that renaming an item with nested items waits for a later release: TCW-114 is part of the same 4.0 release, every `upcoming/` file is merged at TCW-118's cut, so by then the sentence would be false, and the house rule stops TCW-114 from editing this item's file. The limitation is told to TCW-114 instead (Step 19). |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]               | yes                                                                                                             | Written, under Added (`tcw/object_folders.py`, `--nest`, `capabilities add                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | set --parent`, `parent`on term and capability records,`ID_LIMIT`, `fitted_words`, the web option), Changed (state file names, the version line on every state file, the walk replacing every top-level listing, `Layout.item_folders`returning id-paths, the backend operations taking id-paths and`create`'s `nest`, Jira key-named folders needing the state file, attachments and composed documents from `resources/`, `tcw validate`skipping YAML under`resources/`, the removal checks naming `tcw migrate`, the commit hook, the plan stage prompt, `abstraction.md`; not the rename refusal of an item with nested items, for the release note's reason), Removed (`ITEM_FILE`, `_entry_reserved`, the "unlisted extra doc" check, the top-level "is not an item folder" error), Internal (`tests/statefiles.py`, the sweep guard). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component]                 | yes: the `work`, `taxonomy` and `capabilities` skills                                                           | Deferred to TCW-117 (spec Design 9.3, Non-goals).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no                                                                                                              | No configuration key is added or changed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `docs/use-cases.md` [Project-Setup-Change]                             | yes: S-10's "item folder" becomes "object folder"                                                               | Deferred to TCW-117 (spec handoff).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

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
- **A case-insensitive disk.** The reserved-name refusal of `Resources`, the
  walk's exact-spelling rule, and a term folder holding `Resources/x.png`
  (not `resources/`) whose `tcw taxonomy show --json` has no attachment
  while `tcw validate` reports `Resources` as row c, on macOS's default disk, run locally and
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

| AC  | Step                                                                                                                                                                                                                                                           |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 5                                                                                                                                                                                                                                                              |
| 2   | 5                                                                                                                                                                                                                                                              |
| 3   | 5 (trees, files, a flat Jira item); 8 (the nested Jira item)                                                                                                                                                                                                   |
| 4   | 6 (taxonomy, capabilities); 8 (work)                                                                                                                                                                                                                           |
| 5   | 7 (b, c, d, f, g, e in a tree; passing with `resources/`; d's skip of a leftover `config.yaml`; YAML under `resources/` skipped and the tree checks still run; a non-UTF-8 `.md` there a warning); 8 (a, h, i, e in the work store; passing with `resources/`) |
| 6   | 6 (refusals, `review` as a term); 8 (`review` as a work organising folder)                                                                                                                                                                                     |
| 6a  | 8                                                                                                                                                                                                                                                              |
| 7   | 7                                                                                                                                                                                                                                                              |
| 8   | 5                                                                                                                                                                                                                                                              |
| 9   | 8 (reading a nested item); 9 (creating it, both backends, `not nested`, `--nest` without `--parent`; the nested `created` date)                                                                                                                                |
| 9a  | 9                                                                                                                                                                                                                                                              |
| 10  | 8 (including adopt beside a stateless key-named folder)                                                                                                                                                                                                        |
| 11  | 13 (including `set --parent` on an inherited capability)                                                                                                                                                                                                       |
| 12  | 14                                                                                                                                                                                                                                                             |
| 13  | 13                                                                                                                                                                                                                                                             |
| 14  | 11 (add, new, both backends, the project ID, adopt, delegation, a long key after the ticket exists, row n in `tcw validate`); 12 (rename)                                                                                                                      |
| 15  | 13                                                                                                                                                                                                                                                             |
| 16  | 12 (including `report_mentions` by id-path)                                                                                                                                                                                                                    |
| 16a | 14                                                                                                                                                                                                                                                             |
| 17  | 6 (taxonomy listing); 7 (taxonomy validate); 8 (work)                                                                                                                                                                                                          |
| 17a | 6                                                                                                                                                                                                                                                              |
| 18  | 8 (record and board); 10 (create with and without `nest`, the client)                                                                                                                                                                                          |
| 19  | 15                                                                                                                                                                                                                                                             |
| 20  | 16 (including the `resources/` sample and the unreadable folder)                                                                                                                                                                                               |
| 21  | 17                                                                                                                                                                                                                                                             |
| 22  | 21                                                                                                                                                                                                                                                             |

Every design rule of the spec's Coverage table reaches a step through these
criteria; in addition 1.1's "one module" is Step 1 and its guard Step 17;
2.2's exact spelling of `resources/` is Step 7 and the case-insensitive-disk
check (Verification); 2.5 step 2 (symbolic links) is Step 6's re-pointed
`test_store_bounds.py` cases; 2.5's override folders are Step 6; 2.5's checks
before a removal are Steps 1 (`removal_blockers`) and 6; 5 row 11 (current
user) is unchanged; 6.4's restated adopt is Step 8; 9.2 is Step 15. Every
step traces to a criterion except 0 (the starting point), 3 and 4 (the helper
and the inventory Steps 5 and 8 rely on), 18 (the spec's Capability changes),
19 (the spec's handoffs) and 20 (documentation).

**The suite at each step boundary**, in the order of work (the header's
table), checked against the callers each step leaves behind:

- Part 1, 0→1→3→4: a new module and a test helper; nothing calls them.
- Part 1, Step 5: three commits. The suite is red after commits 1 and 2 (the
  code reads the new names while fixtures still write the old ones, then
  the hand edits are still to do), and green after commit 3, which is the
  end of Part 1. A folder with no state file still reads as `{}`
  (`read_state` on an absent file), so the taxonomy store still lists such a
  folder as a term, as 3.x does, until Step 6.
- Part 2, 5→6: Step 6 changes which folders are objects and the removal
  checks; the tests that relied on Problem 2
  (`tests/test_taxonomy_rm_gaps.py:176-201`) change in Step 6 itself.
- Part 2, 6→7: the attachment and prepended-document fixtures move into
  `resources/` in Step 7 with the code that reads them there, and the three
  tests named in Step 7 change with it.
- Part 2, 7→8: the work store still lists only top-level items until Step 8,
  which changes every top-level listing of the work store together (the
  layout, both backends, adopt, the remote check, `validate.py`), so no
  reader sees nested folders while another does not; the five tests named in
  Step 8 change with it.
- Part 2, 8→17: the guard only adds a test; every listing it forbids is gone
  by Step 8. End of Part 2.
- Part 3, 17→2: `ID_LIMIT`, `length_problem` and `fitted_words` are added
  with no caller; the parsers' new refusal reaches only text over 255
  characters, which no existing test types.
- Part 3, 2→9: `create` gains `nest` with a default of false, and the two test
  backends gain it in the same step, since `new_item` passes it by keyword.
- Part 3, 9→10→11→12→15→16: each adds behaviour behind a new flag, a new
  check or new text. Step 11's row n can only fire on an identifier over 255
  characters, which no existing fixture has. End of Part 3 after Step 16.
- Part 4, 16→13→14: Step 13's `parent` key is added to `_CAP_STRUCTURAL` in
  the same step as the first writer of it, so no capability ever shows it as
  an unknown field. Step 14's row m does fire on fixtures that exist today:
  every term or capability nested in another's folder by hand (`write_cap(root,
"routes/login")` under `routes`, a term written under another term's
  folder) has no `parent`, so it now warns. Warnings do not change an exit
  code, but a test that asserts no findings, or counts them, goes red; each
  is found by the full suite, read, and given the `parent` its folder
  implies (or, where its subject is the warning-free output, an assertion
  that ignores row m), listed in the round with Design 3.2. A term made with
  `tcw taxonomy add --parent` after Step 13 writes `parent` and never warns.
  End of Part 4 after Step 14.
- After, 14→18→19→20→21: records, notes and documents; Step 21 runs the suite
  as CI does.

## Spec issues found while planning

The first draft settled five spec defects by choices of its own and reported
them rather than editing the spec. The plan review (round one) held that
this was planning around a spec the plan no longer believed, and the spec has
since been fixed (spec Notes, "Decisions made when the plan review was
answered"): the removal checks (Design 2.5), adopt and delegation within 255
characters (4.2, 4.3), `set --parent` on an inherited capability (3.4),
`resources/` in `tcw validate` (2.2), a missing work parent's severity
(2.6 l), and three the review added: row n's criterion (AC 14), the folder
parent below a folder with no state file (3.2), and row d's skip of a
leftover store `config.yaml` (2.6 d). Also, in the spec now: nothing is
refused for length after a Jira ticket exists (4.3), adopt keeps seeing
key-named folders with no state file (6.4), and `report_mentions` searches
the old id-path (7.2). The store-root listing in `init`
(`tcw/store/fs.py:686`) that AC 21's wording would catch is on Step 17's
allowlist, which the spec says a reviewer checks against a fresh search.
