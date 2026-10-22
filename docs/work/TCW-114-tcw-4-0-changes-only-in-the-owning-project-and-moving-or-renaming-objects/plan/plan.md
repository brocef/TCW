# Plan — TCW 4.0: changes only in the owning project, and moving or renaming objects

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). File and
line references are to commit `d2d02829` on `v4`, where only TCW-106's code
has landed. This item lands eighth, after TCW-106, TCW-107, TCW-110,
TCW-108, TCW-111, TCW-109 and TCW-112, and before TCW-113 and TCW-115 (spec
Notes, decision 3), so most of the code it changes will look different by
the time it starts. Step 0 re-checks every reference against what those
items left.

**The gate at every step boundary.** Every step ends with the named tests
passing, and with the whole Python suite passing: `.venv/bin/pytest` with no
arguments, run from the worktree's root. A step that touches the web client
also ends with, from the worktree's root: `pnpm exec tsc --noEmit`,
`pnpm test`, `pnpm lint`, `pnpm exec prettier --check <every file the step
changed or created that .prettierignore does not exclude>`, and the bundle
rebuilt (`pnpm build`, which writes `tcw/serve/dist`, a committed folder).
Not `pnpm typecheck`, for the reason TCW-110's plan gives (it runs
`prettier --check .` over the whole repository first, which fails on files
this item does not touch). Tests are written first and seen to fail for the
reason they name, then the change is made.

**Which `tcw` drives this repository's lifecycle.** The `tcw` first on
`PATH`: the primary checkout's install of `main` (3.x). The 4.0 code is run
only by the suite (whose projects are under `tmp_path`) and in throwaway
project folders under the scratchpad, with the current folder set there;
never from a folder inside the worktree, never with `.venv/bin` first on
`PATH` in a shell that runs a lifecycle command, and `tcw serve` is never run
from the worktree. These are TCW-110's eight rules (TCW-110 plan, the table
before its Step 0), adopted unchanged; they matter more here, because this
item adds a command, `tcw -C`, that can point the 4.0 code at any folder,
and a move that edits Jira tickets. This repository's tickets hold 3.x
`TCW Item` values, which Design 7.3 makes the 4.0 move refuse, but the rule
is to never reach the live board at all.

## What this plan relies on

From each earlier item, by name. For TCW-106, TCW-107, TCW-108, TCW-110 and
TCW-111 the source is the item's plan; for TCW-109 and TCW-112, whose plans
are being written at the same time as this one, the source is the item's
spec, and Step 0 records the names their plans chose.

- **TCW-106** (landed): `refuse_legacy_project` (`tcw/store/fs.py:310`,
  called first in `_dispatch`, `tcw/cli.py:649`), `find_project_root`
  (`tcw/store/fs.py:296`), the `tcw-version` line and its unreadable-version
  message.
- **TCW-107** (plan): `FsProjectRegistry.project_folder(project_id,
  named_by)` and its four outcomes (a folder; `Unreachable`, exit 5;
  `UnknownProject`, exit 1, "check the spelling"; `ProjectGraphError`, exit
  1); one registry per command (`FsProjectRegistry.open`, `begin_command` and
  `end_command`); manifest entries carrying a `repository`; the test helpers
  `write_manifest` and the `tmp_path` override; the safeguards of its Step 9
  (inventory, search turned off, mutation check).
- **TCW-110** (plan): `tcw/ids.py` (`FullId`, `parse_full_id`,
  `parse_stored`, `parse_address` returning a `FullId` or a
  `FolderAddress(project, namespace, folder_path)`, `sort_input` and its
  forms a to d, `IdError`, `MalformedId`, `ThreeXReference`); `tcw/locate.py`
  (`Locator.of(active_root)`, `owner_root(project_id, named_by)`,
  `read(full_id, named_by)`, `find_tree`, `find_tree_writable`);
  `tcw/work/open.py`'s `resolve_work_input`; `store_location` and its
  folder-address branch (TCW-110 plan Step 13, Design 7.2); the stores'
  `_stored_ref`; `tcw/refs.py`'s address resolution; the 15 stored-reference
  checkers its Step 9 moves to full identifiers; `print_json` writing
  `"schema": 2`; `tests/fullids.py` (`fid`, `wid`, `addr`);
  `tests/projectfiles.py`'s `connect_projects`; the web client's
  `web/client/src/model/identifier.ts`.
- **TCW-108** (plan): `read_only_reason` (`tcw/store/project.py`) and its use
  in `_check_declared`; the `read-only` field of `tcw projects list --json`
  (its Step 12); the web app's `readOnly` (its Step 13:
  `tcw/serve/work.py` `_projects`, `web/client/src/model/types.ts`,
  `work-forms.tsx`, `test-fixtures.ts`); `parents:` links and
  `InheritedUnavailable` (exit 7). TCW-108 marks all of the first three as
  interim until this item.
- **TCW-111** (plan): `tcw/object_folders.py` (`STATE_FILES`, `walk`,
  `object_paths`, `objects_below`, `folder_parent`, `fixed_folders`,
  `reserved_names`, `read_state`, `state_text`, `disagreement`);
  `ID_LIMIT = 255` and `length_problem`; `fitted_words` and `words_room`;
  `item_named`; `nesting_parent` and `--nest`; the Jira backend's
  `link_exists(id_path)`, key index, `_item_file` and `_item_file_problems`;
  its Step 12's rename by id-path with the refusal of an item with nested
  items, which this item removes; its Step 15's edit of
  `tcw/work/prompts/plan.md` step 6 (adds `--nest`); `tests/statefiles.py`;
  `tests/test_object_folder_sweep.py`.
- **TCW-109** (spec): personal files and environment variables are chosen by
  the active project's ID and folder. Nothing else.
- **TCW-112** (spec): "what is inherited at a path" (its Design 2.7), a store
  operation answering, for the active project and an id-path, the full
  identifier of the inherited object there or none, raising
  `InheritedUnavailable` (exit 7); `tcw capabilities set` on an inherited
  capability writes the active project's own object (its Design 4.2); its
  two refusals for another project's object (its Designs 4.2 and 4.4), which
  this item rewords; `extends` gone. Step 0 records the operation's name
  from TCW-112's plan; this plan calls it **inherited-at** below.

## Choices this plan makes where the spec leaves room

1. **Where the ownership check lives.** A new module, `tcw/ownership.py`,
   with one function, `check_owned(full_id, active_root, *, reason=None,
   hint=None)`. It is model code that asks the deployment layer
   (`tcw/locate.py`) for the owner's folder only to word the refusal.
   `tcw/locate.py` already holds `find_tree_writable`, which becomes a call
   of it.
2. **The writers call it through the shared code they already use**, as the
   spec's first Risk asks: work commands through `resolve_item(...,
   writing=True)` (`tcw/work/cli.py:50-66`), tree commands through
   `find_tree_writable`, web routes through the router. `new` and
   `tickets adopt` call it with the new item's identifier, which is always
   the active project's, so that the sweep finds a call at every writer.
3. **The route table marks a write by a function, not a flag.** `Route`
   (`tcw/serve/server.py:193-197`) gains `writes`, a function from the
   request to the objects it writes (a list of `Written(full_id, hint)`), or
   `None` for a read. A create route answers `[]`: it makes a new object of
   the active project, so there is nothing of another project's to check,
   but it is still marked a write. This lets AC 4's test read the table and
   lets the router word the inherited capability's hint (Design 1.4).
4. **`-C` is handled in `tcw.cli`**, in `_dispatch` after `begin_command`
   and before `refuse_legacy_project`, so that an address's lookup runs
   inside the command's one registry and reads the starting project the way
   any command does (Design 4.3). `main` saves `os.getcwd()` before
   dispatching and restores it in a `finally`.
5. **One module for moving**, `tcw/move.py`: the checks of Design 5.4, the
   call of the backend's or store's `move`, the repository rewrite it
   passes as `before_folder`, the tidy step, the output and the stop
   message. The CLI of each namespace only parses its arguments and calls it. The rewrite
   itself is a second module, `tcw/rewrite.py`, and the reference-field
   definition a third, `tcw/reference_fields.py`.
6. **Values in YAML are replaced by their position in the text.** For a
   state file or a `capabilities.yaml`, the rewrite reads the file with
   `yaml.scan`, which gives each scalar's start and end in the text, and
   replaces only the scalars whose parsed value is an old identifier,
   keeping their quoting style. Every other byte stays (Design 6.6). A
   value needing quotes it did not have before is written in single quotes.
7. **One helper moves an object's folder**, in `tcw/object_folders.py`:
   `move_object_folder(store_root, old_path, new_path) -> created`, which
   creates the missing organising folders, makes the one `os.rename`, and,
   when that fails, removes each folder it created that is still empty
   before raising (Design 5.3). The files work backend, the Jira backend
   (its folders are files too) and the tree stores all call it, so the
   folder rules are in one place.
8. **The stop message is built by `tcw/move.py`**, from a record of every
   ticket and file the run found done or wrote, and is raised as the same
   error class that stopped the run (so its exit code is kept: 1, 3, 4 or
   5), with the message replaced.
9. **A Jira item's recorded references are read in the folder scan** by
   `object_folders.read_state`, so reading them never needs the network.
10. **Partial failure is tested by stopping at every write in turn.** A test
   helper, `tests/move_stops.py`, counts the writes a clean run makes (state
   file writes, repository file writes, fake Jira edits, `mkdir`, the
   folder's `os.rename`), then, for each write `k`, runs the command with
   write `k` failing, checks the stop, runs it again healthy, and compares
   the result with the clean run's, byte for byte, including the fake's
   tickets. This covers "stop a move at each point and show that a re-run
   finishes it" without writing one test per point by hand.

## Step 0 — start from what the earlier items left

Before any change:

1. `git -C .claude/worktrees/v4 log --oneline` shows the TCW-112
   implement and review commits; `tcw work show TCW-112` (the lifecycle
   `tcw`) is at `completed`.
2. Every file and line this plan cites is re-checked against the tree, and
   each that moved is noted in the implement round, with its new place. The
   ones most likely to have moved: everything in `tcw/work/cli.py`,
   `tcw/work/open.py`, `tcw/work/fs_backend.py`,
   `tcw/work/jira/backend.py`, `tcw/serve/work.py`, `tcw/serve/records.py`,
   `tcw/store/fs.py` and `tcw/cli.py`, and `tcw/work/prompts/plan.md:38-46`
   as TCW-111 Step 15 leaves it.
3. The names this plan takes from TCW-109's and TCW-112's plans are
   recorded: the inherited-at operation's name and signature; the functions
   that word TCW-112's two refusals; where TCW-112's `set` writes an
   override.
4. **The git processes a plain command starts, measured.** In a scratchpad
   fixture of two git repositories side by side, `tcw work list` and
   `tcw work rename` are each run with every `subprocess.run` and
   `subprocess.Popen` call recorded (the recording plugin of Step 1). The
   result decides how AC 9's and AC 25's "starts no `git` process" are
   tested: if TCW-107's linked-worktree probe (`worktree_anchors`,
   `tcw/store/project.py:67-79`, which runs `git -C <folder> rev-parse` through
   `_git_lines`, `:119-128`) runs in either, the tests allow exactly that
   probe and nothing else, as `tests/serve/test_no_process.py:77-91` allows
   read-only git, and the spec issue below is raised (Spec issues, 1).
5. The repository URL a `project_folder` refusal can name: Step 0 finds how
   TCW-107 exposes the deciding manifest entry's `repository` to a caller
   (an attribute of the raised `Unreachable`, or a registry method). If it
   is only inside the message text, Step 2 adds a `repository` attribute to
   the `Unreachable` that `project_folder` raises, set where TCW-107 builds
   that message.
6. The suite passes: `.venv/bin/pytest`, and the web checks of the gate.

**Proves it:** the notes in the implement round; the suite green.

## Step 1 — the inventory, the outcome record, and the recording plugin

Before any test is removed or changed (Steps 3, 7, 8, 10 and 16 remove or
rewrite tests), in the style of TCW-107 Step 9 and TCW-108 Step 7:

- **The inventory.** `.venv/bin/pytest --collect-only -q` saved to
  `<scratchpad>/inventory-step1.txt`, and for each test file the count of
  `assert` statements (an `ast` walk), saved beside it.
- **The outcome record.** `.venv/bin/pytest -q
  --junitxml=<scratchpad>/outcomes-step1.xml` from the worktree's root.
- **The comparison script**, TCW-108's `compare_outcomes.py <before.xml>
  <after.xml> <allowed.txt>`, copied into the scratchpad unchanged. Each later
  step that removes or rewrites tests saves a new record and compares it,
  with `allowed.txt` listing exactly the test IDs removed or renamed, each
  with the design rule that removed it.
- **The recording plugin**, `<scratchpad>/record_processes.py`, a pytest
  plugin loaded with `-p`, which records every `subprocess.run` and
  `subprocess.Popen` call. Step 0 item 4 uses it; it is only for measuring,
  never part of the suite.

**Proves it:** the four files exist; the suite is unchanged.

## Step 2 — the ownership check

**Tests first**, new `tests/test_ownership.py`, two git repositories side by
side under `tmp_path`, `app` and `core`, placed by a manifest
(`write_manifest`):

- `check_owned(fid("app", "work", "x"), app)` returns.
- `check_owned(fid("core", "capabilities", "cli/x"), app)` raises `Refused`
  (exit 3) whose message is exactly `core.capabilities/cli/x belongs to
  project 'core'; run the command there: tcw -C <core's folder> …`, the
  folder absolute.
- With `reason=", and 'app' does not inherit it, so it cannot be overridden
  here"`, the reason sits between `'core'` and `;` (Design 1.3).
- With `core`'s folder removed and the manifest entry kept, giving
  `repository: https://example.invalid/core.git`: exit 3, `belongs to
  project 'core'; project 'core' is not on this machine
  (https://example.invalid/core.git)`. With no repository, no brackets.
- Unknown (nothing names `core`) and a graph problem (two folders beside
  `app` both declaring `core`): exit 3, `is not on this machine`. In every
  case the error is `Refused`, never `Unreachable` or `ProjectGraphError`:
  locating never changes the exit.
- With `hint="; or override it …"`, the hint ends the message.

**Creates** `tcw/ownership.py`: `check_owned(full_id, active_root, *,
reason=None, hint=None) -> None`. It compares `full_id.project` with the
active project's ID (read from the `Locator`'s registry, `current.id`); on a
match it returns. Otherwise it asks `Locator.of(active_root).owner_root(
full_id.project, named_by=active_root)` inside a `try` that turns every
`TcwError` into "not on this machine", reading the repository as Step 0
item 5 found, and raises `Refused` with Design 1.3's text. It writes
nothing and reads no file of the owner's.

**Proves it:** `tests/test_ownership.py`; the full suite.

## Step 3 — every CLI writer calls it

**Tests first**, new `tests/test_owning_project.py` (AC 1, AC 2, AC 3):

- AC 1: in `app`, each of `tcw work edit core.work/<c> --priority high`,
  `advance`, `discard --reason x`, `comment` (text on standard input),
  `rename core.work/<c> other` and `move core.work/<c> --top` exits 3, says
  `belongs to project 'core'`, core's absolute folder and `tcw -C`, and a
  snapshot of every file under `core` (path and bytes) is unchanged. The
  `rename` row passes from this step, since `tcw work rename` reaches
  `resolve_item(..., writing=True)` before the backend is called; the `move`
  row is `xfail(strict=True)`, reason "tcw work move arrives in Step 17",
  until Step 17 adds the command and removes the mark. The not-on-this-machine, unknown and
  graph-problem variants as AC 1 states them.
- AC 2: `app` with parent `core` passing taxonomy and capabilities.
  `tcw taxonomy rm core.taxonomy/t`, `tcw capabilities rm
  core.capabilities/cli/x` exit 3 naming core's folder; the `rename` and
  `move` rows marked `xfail(strict=True)` until Step 19 adds those
  commands. `tcw capabilities
  set core.capabilities/cli/x --status Supported` exits 0, writes `app`'s own
  `cli/x` and leaves `core`'s files unchanged. In `other` (no parent),
  the same `set` exits 3 with `belongs to project 'core', and 'other' does
  not inherit it, so it cannot be overridden here; run the command there:
  tcw -C`. Neither message contains `change it in`.
- AC 3: `workspace` and `app`, `app` with `work.path:
  tcw://workspace.path/docs/app/work`. In `workspace`, `comment`, `edit
  --priority low` and `advance` of `app.work/<a>` exit 3 naming `app`'s
  folder, and nothing under `<workspace>/docs/app/work` changes. The `-C`
  half of AC 3 is in Step 6.
- TCW-112's two message tests (Step 0 item 3 names them) change to Design
  1.3's text; each failure is read before its assertion is changed.

**Changes**

- `tcw/work/cli.py`: `_own` (`:69-74`) is removed; `resolve_item`
  (`:50-66`) gains `writing: bool = False` and, when true, calls
  `check_owned(<the item's full identifier>, root)` before returning. Every
  writer passes `writing=True`: `_edit` (`:328-361`), `_move` (the advance
  helper, `:364-371`), `_discard` (`:389-394`), `_comment` (`:397-403`),
  `_rename` (`:406-410`). `_new` (`:186-232`) and `_tickets_adopt`
  (`:427-433`) call `check_owned` with the identifier of the item they make
  or adopt, after the backend answers it, before printing; it always passes,
  and is there so the sweep finds every writer calling it (choice 2).
- `tcw/locate.py`: `find_tree_writable` becomes `find_tree(...)` followed by
  `check_owned(found, active_root)`, with TCW-112's override exception kept
  where TCW-112's `set` puts it (Design 1.5): `set` and `reset` on an
  inherited capability pass the check with the active project's own object
  at that path, which is what TCW-112 writes; `set` on a capability the
  active project does not inherit gives `reason=", and '<active>' does not
  inherit it, so it cannot be overridden here"`.
- TCW-112's `rm` refusal (its Design 4.4) becomes `check_owned` with no
  reason.
- `tcw/taxonomy/cli.py` `_add` (`:100`) at an inherited path and
  `tcw/capabilities/cli.py` `_add` (`:91`), `_set` (`:119`), `_reset`
  (`:127`), `_rm` (`:137`) all reach the check through `find_tree_writable`
  or, for `add`, with the new object's identifier.

**Proves it:** the tests above; `tests/test_capabilities_federation.py` and
TCW-112's override tests, unchanged except the two messages; the full suite.

## Step 4 — the web router makes the check

**Tests first**, new `tests/serve/test_route_writes.py` (AC 4, the server
half):

- Reading `tcw.serve.server._routes()`: the routes whose `writes` is not
  `None` are exactly Design 1.2's web column: `POST /api/work`, `PATCH
  /api/work/<item>`, `POST /api/work/<item>/comments`, `POST
  /api/tickets/<key>/adopt`, `PUT /api/work/<item>/files/<path>`, `POST
  /api/work/<item>/files`, `PUT /api/work/<item>/declaration`, `POST
  /api/taxonomy`, `PATCH /api/taxonomy/<key>`, `POST /api/capabilities`,
  `PATCH /api/capabilities/<key>`. `POST /api/resolve` is a read. (The
  `/blocks` route is removed in Step 7; until then it is marked a write and
  the test's expected list includes it, with a comment naming Step 7.)
- A test server with one extra route registered, marked a write naming
  `core.capabilities/cli/x`, whose handler writes a file: a request answers
  403, error kind `read-only`, message `belongs to project 'core'`, and the
  file does not exist.
- Served from `app` (parent `core`): `PATCH
  /api/capabilities/<core.capabilities/cli/x, encoded>` answers 403,
  `read-only`, with `belongs to project 'core'` and `tcw capabilities set`.
  `PATCH /api/taxonomy/<core's term>` answers 403 with no hint.

**Changes**

- `tcw/serve/server.py`: `Route` (`:193-197`) gains `writes:
  Callable[[Request], list[Written]] | None = None`; `route()` (`:200-201`)
  takes it as a keyword; `Written` is a small dataclass `(full_id, hint)`.
  In `_api` (`:299-311`), after the route is matched and the `Request`
  built, and before the handler runs: for each `Written` the route's
  `writes` returns, `check_owned(w.full_id, request.root, hint=w.hint)`; a
  `Refused` from it becomes `read_only(<its message>)` (`:61-62`).
- `tcw/serve/work.py` ROUTES (`:584-595`) and `tcw/serve/files.py` ROUTES
  (`:358-364`): each write route marked, with `writes` answering the item
  the path names (`item_folder`, `:237-246`, made into the active
  project's full identifier) or `[]` for create and adopt.
- `tcw/serve/records.py` ROUTES (`:245-254`): the two PATCH routes mark a
  write whose function resolves the key with `find_tree` (as TCW-110 Step 8
  makes the route key do) and answers its full identifier; for a
  capability the hint is today's (`:192-196`): `; or override it in this
  project with tcw capabilities set <id-path> --field <name>=<value>`. The
  two POST routes answer `[]`. The refusals inside `update_term`
  (`:116-119`) and `update_capability` (`:190-196`) are removed: the
  router has already refused (Design 1.4, "a route's own code never calls
  it").

**Proves it:** the tests above; `tests/serve/test_records*.py` and
`tests/serve/test_work_write.py`, whose inherited-object cases now get the
router's message; the full suite.

## Step 5 — `tcw -C` with a folder path

**Tests first**, new `tests/test_run_in_folder.py` (AC 8, the path half of
AC 10):

- From an empty folder that is no project, `tcw -C <path to demo> work
  list` prints what `tcw work list` prints in `demo`.
- `tcw -C a -C b work list` runs in `a/b` (a project at `a/b`).
- `tcw -C missing work list` exits 2, `cannot run in missing: no such
  folder`, and reads nothing (no `find_project_root` call: patched to fail).
- `tcw.cli.main(["-C", str(demo), "work", "list"])` in-process: `os.getcwd()`
  afterwards equals what it was before; also when the command fails (exit 4)
  and when it raises `BrokenPipeError`.
- AC 10's last part: from `workspace` with an empty `fresh/` inside it,
  `tcw -C fresh init --id fresh --work-path board` creates
  `fresh/.tcw/tcw-config.yaml` and `fresh/board/`, and no `workspace/board/`.
- From a folder holding a 3.x project, `tcw -C <path to app> work list`
  exits 0 (part of AC 9: a path reads nothing at the starting folder).
- `tcw --help` lists `-C`.

**Changes**

- `tcw/cli.py` `build_parser` (`:549-555`): `parser.add_argument("-C",
  dest="chdir", action="append", default=[], metavar="<folder or
  tcw://<id>.path/>", help="run as if tcw had been started in this folder;
  repeat to go further, as git -C does")`.
- `tcw/cli.py` `main` (`:616-638`): `start = os.getcwd()` before
  `_dispatch`, and `os.chdir(start)` in a `finally` around it (Design 4.5).
- `tcw/cli.py` `_dispatch` (`:641-693`): right after `begin_command`
  (`:645`), before `refuse_legacy_project` (`:649`), `for target in
  args.chdir: _enter(target)`. `_enter` for a path: `Path(target)`
  relative to the current folder; not an existing folder → `UsageError`
  (`cannot run in <target>: no such folder`); else `os.chdir`. The rest of
  `_dispatch` then reads the project, configuration, personal files and
  stages of the folder chosen, as any command does.
- **The ten reads of the current folder** (Design 11), each confirmed to run
  at command time, after `_enter`, and none at import or parser-building
  time: `tcw/cli.py:53` (`run_init`), `tcw/projects_cli.py:56` (`_list`),
  `tcw/config_cli.py:254` (`_show`), `tcw/project_files.py:74` (a default
  argument read at call time), `tcw/output.py:26` and `:28` (`shown`),
  `tcw/work/cli.py:44` (`project_root`) and `:527`,
  `tcw/store/project.py:768`, `tcw/store/fs.py:246` (`git_root`). There is no
  `os.getcwd()` in `tcw/`; the hooks and `generate:` commands run with
  `cwd=str(project_root)` (`tcw/work/hooks.py:76`, `tcw/work/generate.py:108`),
  unchanged. Step 21's sweep guard keeps the list.

**Proves it:** the tests above; the full suite.

## Step 6 — `tcw -C` with an address, and the test command checkers learn `-C`

**Tests first**, in `tests/test_run_in_folder.py` (AC 9, AC 10, the `-C`
half of AC 3):

- From `workspace`: `tcw -C tcw://app.path/ work list` prints `app`'s items;
  `tcw -C tcw://app.work/x work list` exits 2 naming `.path`;
  `tcw -C tcw://app.work.path/ work list` exits 2, `is a folder of project
  'workspace'` and `tcw://app.path/`; a manifest entry placing `gone` at
  `../gone` (absent): exit 5 naming `gone`; `tcw -C tcw://cor.path/ work
  list`: exit 1, `check the spelling`.
- From a folder that is no project: `tcw -C tcw://app.path/ work list` exits
  1, `give the folder's path instead`.
- `lone` with `work.path: ../board` (a folder in no project): `tcw -C
  tcw://lone.work.path/ work list` from `lone` exits 2, `which is in no TCW
  project`.
- From a folder holding a 3.x project: `tcw -C tcw://app.path/ work list`
  exits 1 with TCW-106's refusal.
- No `git` process is started by `-C`'s own resolution: a spy on
  `subprocess.run` and `subprocess.Popen` active only while `_enter` runs
  records none. For the whole command, the assertion is Step 0 item 4's
  (none, or only TCW-107's worktree probe).
- AC 10: `user.name: Alice` in `app`'s `.tcw/tcw-config.local.yaml`, `Bob`
  in `workspace`'s: from `workspace`, `tcw -C tcw://app.path/ work new 'x'
  --assign-me` makes an item assigned to `Alice`. A `pre` check bound in
  `app` to the next stage runs on `tcw -C tcw://app.path/ work advance <a>`
  with `TCW_PROJECT_ROOT` equal to `app`'s root (the check writes the
  variable to a file in the scratchpad of the test); a `pre` check bound in
  `workspace` does not run.
- AC 3's second half: from `workspace`, `tcw -C tcw://app.path/ work comment
  app.work/<a>` exits 0 and a new comment file appears under
  `<workspace>/docs/app/work/<a>/comments/`.
- The command checkers: `test_documented_cli_surface._check` accepts
  `tcw -C <target> work new "<title>" --parent <slug>` and rejects `tcw -C
  <target> work new --project x`; `test_shipped_text.command_problem`
  accepts `tcw -C tcw://<id>.path/ work new "<title>" --parent <slug>
  --nest`; `tests/test_docs_describe_3_0.py` `command_problems` likewise.

**Changes**

- `tcw/cli.py` `_enter` for a target starting with `tcw://`:
  `parse_address`; a `FullId` (an object address) → `UsageError` naming the
  `.path` form, as TCW-110 Design 7.1 words it for a store location. A
  `FolderAddress`: first the checks every command makes of the current
  folder, which this step moves out of `_dispatch` into one function,
  `_check_here()` (`refuse_legacy_project`, `refuse_retired_config` when
  the group is not `validate`, and the configuration-problems check of
  `:658-661`), called for each address target and once after the last
  target. Then `find_project_root()`; none → `TcwError` (exit 1) with
  Design 4.3's text. Then the folder by TCW-110 Design 7.2:
  `Locator.of(here).owner_root(id, named_by=here)` for `.path`, and for
  `.<namespace>.path` that root's store location for the namespace
  (`store_location`, TCW-110 Step 13). If TCW-110 left folder-address
  resolution only inside `store_location`, it is taken out into
  `tcw/locate.py` as `resolve_folder_address(address, locator, named_by) ->
  Path`, and `store_location` calls it, so both use one function.
  `owner_root`'s outcomes propagate with their own exits (5, 1, 1). A
  resolved folder that does not exist → Step 5's usage error. After
  `os.chdir`, `find_project_root()`'s project ID must equal the address's
  ID, or `UsageError` with Design 4.4's two texts.
- `tests/test_documented_cli_surface.py` `_check` (`:197-219`),
  `tests/test_shipped_text.py` `command_problem` (`:283-311`) and
  `tests/test_docs_describe_3_0.py` `command_problems` (`:282`): before
  reading the group, skip each `-C <target>` pair after `tcw`.

**Proves it:** the tests above; the full suite.

## Step 7 — `--project` and `--blocks` refused, and the code that served them removed, CLI and server

**Tests first** (AC 5, AC 22's CLI half, and AC 24's removals), in
`tests/work/test_removed_options.py`:

- `tcw work new 'x' --project core` exits 2, says `work new --project is
  removed`, `tcw -C` and `--parent`, creates nothing in either project, and
  returns while standard input is a pipe that never closes (the test runs it
  as a subprocess with a 10-second timeout and an open pipe).
- `tcw work edit <a> --blocks <b>`, `<b>` in the same project: exit 2,
  `work edit --blocks is removed`, `--blocked-by`, no `tcw -C`; neither
  item's state file changes. With `<b>` in `core`: the message also has
  `tcw -C`.
- `tcw work new --help` and `tcw work edit --help` mention neither option.
- `tcw projects list --json`: no row has a `read-only` key (AC 22).
- `tests/serve/test_work_write.py` (AC 4's server half): `POST /api/work`
  with `project: core` answers 400 (usage), message containing `tcw -C`,
  and creates nothing in either project; `POST /api/work/<item>/blocks`
  answers 404. `test_blocks_*` (`:167-210`), `test_targets_delegation_refuses`
  (`:272-280`) and the delegation create cases (`:253-270`) are removed; the
  Jira case at `:306` and the every-route list at `:376-388` lose their
  `/blocks` row.
- `tests/serve/test_no_process.py`: `every_route` (`:23-56`) loses the
  `project: q` create (`:42`) and the `/blocks` call (`:43-44`); the
  `prepared` fixture no longer needs project `s`; the assertion that "the
  create and blocks routes were reached" (`:117`) keeps the create route.
- `GET /api/project`'s connected-project rows have no `readOnly` key (AC 22).
- Step 4's route-table test no longer lists `/blocks`.

**Removed tests**, each listed in `<scratchpad>/allowed-step7.txt` with its
design rule (Design 2.1, 2.2, 2.4, 1.8), after reading each one to confirm it
tests only the removed behaviour: `tests/work/jira/test_jira_delegation.py`
(whole file); in `tests/work/test_open.py` the `delegate`,
`open_for_update`, `uncommitted_changes` and `_check_target` tests; in
`tests/work/test_cli_items.py`, `tests/work/test_review_findings.py` and
`tests/work/test_git_state_unchanged.py` the `--project` and `--blocks`
cases; in `tests/work/jira/test_jira_tickets.py` the `delegate_to_jira`
cases; in `tests/test_upstream_projects.py` and `tests/test_projects_list.py`
the delegation and `read-only` cases; the delegation rows of
`tests/test_cli_contract.py`, `tests/config/test_personal_commands.py`,
`tests/config/test_personal_identity.py`, `tests/test_procedure_config.py`,
`tests/test_migration_guide.py`, `tests/test_routing_nodes.py`,
`tests/test_environment_hardness.py`. A test in those files that uses
`--project` or `--blocks` only to set up something else is rewritten onto
`tcw -C … --parent` or `--blocked-by` on the other item, not removed. The
references in `tests/not_ported.py`, `tests/work/removed_2x.py`,
`tests/doc_vocabulary.py`, `tests/test_cli_help_standard.py` and
`evals/coverage.py` are read and changed to match (each names a removed
function or option as text). `tests/test_static_guards.py` EXEMPT
(`:33-42`) loses the `("work/open.py", "uncommitted_changes")` and
`("work/open.py", "_check_target")` rows, since
`test_every_exempt_function_still_exists` checks each row.

**Changes**

- `tcw/work/cli.py`: `--project` (`:714`) and `--blocks` (`:690-692`) kept
  with `help=argparse.SUPPRESS`. `_new` (`:193-210`): the `--project` block
  becomes one `UsageError` before the read of piped input, with Design 2.1's
  text, the ID and title filled in from the arguments: `work new --project
  is removed in TCW 4: an item is created in its own project; run tcw -C
  tcw://<id>.path/ work new "<title>" --parent <full id>`. `_edit`
  (`:339`, `:351-358`): any `--blocks` → `UsageError` with Design 2.2's text,
  before anything is opened. The value is read only to word the message:
  `sort_input` gives the target's project; for another project the folder
  is `owner_root`'s answer when it returns one, otherwise
  `tcw://<id>.path/`; for this project no `-C` (Spec issues, 3).
  `blocks_target` (`:167-176`) is removed; the `new` example
  `new 'Support SSO' --project platform --tag auth` (`:711`) becomes
  `new 'Support SSO' --parent planning.work/2026-10-01-sso --tag auth`.
- `tcw/work/open.py`: `uncommitted_changes`, `_check_declared`,
  `_check_target`, `delegate`, `open_for_update` and `_uncommitted_in`
  (`:106-207`) removed; the module docstring (`:1-10`), which says
  `delegate` and `open_for_update` "are the only two ways…", reworded to
  say what is left.
- `tcw/work/jira/tickets.py`: `delegate_to_jira`, `_Connection`,
  `_remote_metadata`, `_cannot_make_item` (`:311-458`) removed, with any
  import only they used.
- `tcw/serve/services.py`: the `delegate` service (`:34-37`, `:86`)
  removed.
- TCW-111's 255-character fitting for delegation (TCW-111 Design 4.2) is
  removed with `delegate`.
- TCW-108's interim rule (Design 1.8): `read_only_reason`
  (`tcw/store/project.py`) and the `read-only` field of `tcw projects list
  --json` (`tcw/projects_cli.py`, TCW-108 Step 12) removed, with whatever
  only they use.
- `tcw/serve/work.py`, in this step because it calls `blocks_target` and the
  `delegate` service: `create` (`:476-524`): a `project` other than the
  served one is `usage(...)` naming `tcw -C`, before anything else, and the
  delegation branch (`:490-500`) is removed; `add_blocks` (`:448-469`) and
  its route (`:591`) removed; `_projects` (`:143-148`) loses
  `upstream`/`readOnly` (TCW-108 Step 13). The `projects` key of the project
  answer stays until Step 8 removes its one reader.

The client still sends `project` only when a person picks another project
in the selector, which now answers a usage error; the selector goes in
Step 8, so at this boundary the page works and that choice is refused.

**Proves it:** the tests above; `compare_outcomes.py
<scratchpad>/outcomes-step1.xml <scratchpad>/outcomes-step7.xml
<scratchpad>/allowed-step7.txt` passes (the record taken again here);
`grep -rn "def delegate\|open_for_update\|blocks_target\|delegate_to_jira\|uncommitted_changes\|_cannot_make_item\|read_only_reason" tcw/ web/client/src/ scripts/ evals/`
finds nothing; the full suite.

## Step 8 — the web client: no project selector, no "Blocks (add)", no `readOnly`

**Tests first** (AC 4's client half):

- `web/client/src/ui/work-forms.test.tsx`: the create form shows no
  "Project" selector; the two `Blocks (add)` tests (`:192-230`, `:529-545`)
  are removed. `web/client/src/ui/app.test.tsx` (`:234-260`): the item page
  has no `Blocks (add)` combobox in either mode, and still lists the item's
  `blocks` (the data of `work-views.test.tsx:38`).
- A Jira-mode create form and edit form accept a blocker in another project
  with the other-project warning, as they accept a parent today (Design 3.3:
  the backend now records it; Spec issues, 4).

**Changes**

- `web/client/src/ui/work-forms.tsx`: `BlocksForm` (`:330-420`) removed;
  the create form's project selector (`:583-591`, the `SelectInput` at
  `:621-629`) removed, with the target always the served project; in Jira
  mode the blocker field's `crossProject` (`:600-606`) becomes the same
  `warn` as `crossParent` (`:607-609`), and the edit form's (`:228`) the
  same.
- `web/client/src/ui/app.tsx`: the `BlocksForm` import (`:85`) and use
  (`:1285`) removed.
- `web/client/src/model/types.ts`: `TConnectedProject` (`:30-31`, with
  TCW-108's `readOnly`) and `projects` (`:54`) removed when nothing else
  reads them (today only `work-forms.tsx:583-591` does);
  `web/client/src/test-fixtures.ts` to match; then `tcw/serve/work.py`'s
  project answer drops `projects` and `_projects`, with the server test that
  reads it.
- `pnpm build` rewrites `tcw/serve/dist`.

**Proves it:** the tests above; the web checks of the gate; the full suite.

## Step 9 — one definition of the reference fields

**Tests first**, new `tests/test_reference_fields.py` (AC 26, first part):

- `tcw.reference_fields.FIELDS` holds exactly these rows, compared as a
  set of `(record, field)` pairs: `work-item` `parent`, `blocked-by` (files
  state file); `jira-item` `parent`, `blocked-by` (the Jira state file,
  Design 3.3); `jira-ticket` `TCW Item`; `capabilities-yaml` `new`,
  `changed`, `removed`, `taxonomy.new`, `taxonomy.changed`,
  `taxonomy.removed`; `term` `relatesTo`, `vocabulary`, `parent`;
  `capability` `Subject`, `Feature`, `Superseded by`, `Blocked by`, `Roles`,
  `When`, `parent`; `markdown` link. That is TCW-110 Design 5.1's table,
  the terms' and capabilities' `parent` (TCW-111 Design 3.1), and the Jira
  state file's two (Design 3.3).
- Each row's attributes: one value or a list; the namespace named
  (`Subject` and `Feature` name taxonomy; `Superseded by`, `Blocked by`,
  `Roles`, `When` name capabilities; `capabilities-yaml` rows name
  capabilities and the `taxonomy.*` rows taxonomy; a link names any); the
  group (`roles/` for `Roles`, `conditions/` for `When`); `!` allowed only
  for `Roles` and `When`.

**Creates** `tcw/reference_fields.py`: `Field(record, name, many, namespace,
group, negatable)` and `FIELDS`, a tuple of them; helpers
`fields_of(record)` and `values(record, data) -> list[(field, value,
negated)]`, which every reader below uses to find the references in a
parsed record. `TCW Item` is a row so that the sweep and the rewrite see it,
but only the Jira backend reads and writes it (Design 6.1).

**Proves it:** `tests/test_reference_fields.py`; the full suite.

## Step 10 — the checkers move onto the definition, one at a time

Each checker below is changed to read which fields to look at from
`FIELDS`, keeping its own rule about a value (Design 6.3). One checker per
commit; after each, its own tests and the full suite pass, and
`compare_outcomes.py <outcomes-step9.xml> <after.xml> <empty allowed.txt>`
shows no outcome changed (this step changes no behaviour):

1. `tcw/store/fs.py` `_ref_problem` (`:1992`), `_require_ref` (`:2011`),
   `_resolve_vocab_ref` (`:2022`), the taxonomy `check`'s `relatesTo` and
   `vocabulary` loops, `_referrers` (`:1937`), `_capability_referrers`
   (`:1899`).
2. `_validate_fields` (`:2602-2637`), `_ref_problems` (`:2934-2948`),
   `_ref_error` (`:2950`), `_check_globals` (`:2958-2969`: its
   `(("roles", "Roles"), ("conditions", "When"))` pairs come from the
   rows' `group`), `_term_refs` (`:2971-2983`), `_check_subject`
   (`:2985`), `_check_feature` (`:2998`), the capabilities `_referrers`
   (`:2536`).
3. `tcw/work/references.py` `reference_problems` (`:28-61`): takes
   `(item, field, value)` triples built with `values("work-item", …)`,
   rather than reading `item.parent` and `item.blocked_by` by name, so the
   Jira backend's recorded references (Step 13) join it as more triples.
   Its two callers change with it: `tcw/validate.py:596` and the `--remote`
   model checks (`tcw/work/jira/remote.py:521`, in `_model_checks`).
4. `tcw/work/gates.py`: `parse_declarations` (`:109-157`) reads the
   `capabilities-yaml` rows; `route_capability_path` (`:331-380`) is
   unchanged.
5. TCW-112's `reset` refusal list (its Design 4.3; Step 0 names its code).

**Then the second half of AC 26** (`tests/test_reference_fields.py`):

- For each row except `TCW Item`, a fixture record holding that field with
  a value naming no object: `tcw validate` reports that file and that
  field. (The rename half of each row is added in Step 18, once rename
  exists: the same fixtures, the named object renamed, the value rewritten.)
- A test that adds a row to `FIELDS` (monkeypatched) naming a field
  `Reviewed by` of a capability fixture: `tcw validate` reports a dangling
  value in it, with no other change. (Its rename half is in Step 18.)

**Mutation check:** with a one-off plugin in the scratchpad removing the
`Roles` row from `FIELDS`, the `Roles` cases of
`tests/test_reference_fields.py` and the existing `Roles` tests of the
capabilities store go red, and their failure reasons are read and confirmed
to be the field not being checked.

**Proves it:** each checker's existing tests; the comparisons; the mutation
check; the full suite.

## Step 11 — code spans located, not deleted

**Tests first**, in `tests/test_validate.py`, beside today's link checks
(`_strip_code` has one caller, `tcw/validate.py:334`, and no test of its
own):

- `code_spans(text)` returns `(start, end)` for every fenced block and
  inline code span, by the same rules as `_FENCE_RE` (`tcw/validate.py:51-52`)
  and `_INLINE_CODE_RE` (`:55`), on the Markdown fixtures `tests/test_validate.py`'s
  link tests use today, and `"".join(text outside the spans) == _strip_code(text)` for
  each.
- `links_outside_code(text)` yields `(start, end, address)` for each
  `](tcw://…)` (`_LINK_RE`, `:49`) not inside a span, positions into the
  original text.

**Changes** `tcw/validate.py`: `code_spans` and `links_outside_code`
added; the link loop (`:327-348`, `_strip_code` at `:334`) uses
`links_outside_code`; `_strip_code` (`:70-72`), then uncalled, is removed. `tcw/rewrite.py` (Step 15) uses the same two
functions.

**Proves it:** the tests above; `tcw validate`'s link tests unchanged; the
full suite.

## Step 12 — the fake Jira gains three switches

**Tests first**, in `tests/work/jira/test_fake.py` (the fake's own tests):

- `fake.fail_edit(n, *, then_unreachable=False)`: the `n`-th later `PUT
  /issue/<key>` answers 500 (or, with `then_unreachable`, the connection
  drops and every later request fails, as `drop_after_next_write` does,
  `tests/work/jira/fake.py:220-224`).
- `fake.before_request(callback)`: `callback(method, path)` runs before
  each request is answered, so a test can change a ticket between a search
  and an edit (AC 12, two runs at once).
- `fake.hide(key)`: the ticket is left out of searches and answers 404 to a
  read, as a deleted or invisible ticket does.

**Changes** `tests/work/jira/fake.py`: the three switches, in `answer`
(`:268-306`), beside the existing ones.

**Proves it:** the fake's tests; the full suite.

## Step 13 — Jira: a parent or blocker Jira cannot link is recorded

**Tests first**, new `tests/work/jira/test_jira_recorded.py`, with
`install_sites` (`tests/work/jira/fake.py:761`) serving site A and site B
(AC 7, AC 6):

- AC 7, first bullet: `app` (site A), `far` (site B), `files` (files
  backend), side by side. In `app`, `tcw work new 'x' --parent
  files.work/<f> --blocked-by far.work/<FK>-…` exits 0; site A's fake
  records one create with no parent and no link, of the project's default
  issue type; the new folder's state file holds exactly `tcw-version`,
  `ticket`, `parent: files.work/<f>`, `blocked-by: [far.work/<FK>-…]`;
  standard error says `is not a ticket on` and `Jira shows no link for it`
  for each.
- AC 7, second bullet: `<a>` with a Jira parent on site A; `tcw work edit
  <a> --parent far.work/<FK>-…`: the fake records the edit clearing the
  parent, then the state file holds `parent: far.work/<FK>-…`; `edit <a>
  --parent <site A ticket>` makes the parent field and removes `parent`
  from the state file; `--parent none` leaves neither.
- AC 7, third bullet: a parent that is a ticket of another TCW project on
  site A is linked as today; no `parent` in the state file.
- AC 7, fourth bullet: `files` removed, manifest entry kept: `tcw work new
  'y' --parent files.work/<f>` exits 5 naming `files`; the fake records no
  create.
- AC 7, fifth bullet: `fake.drop_after_next_write(then_unreachable=True)`
  set so the connection drops after the parent is cleared: exit 5, the state
  file unchanged; again, healthy: the state file written, and the fake
  records no second clear.
- A created ticket whose state file cannot be written (the folder made
  unwritable): today's stop naming `tcw work tickets adopt <KEY>`, and the
  message adds the recorded values to set again with `tcw work edit`.
- `tcw work edit <a> --blocked-by files.work/<f>` and `--unblocked-by` of
  it: the state file's `blocked-by` gains and loses it; the fake records no
  link request.
- AC 6 (files backend; its own file, `tests/work/test_part_elsewhere.py`):
  `planning` (epic `<e>`, item `<o>`) and `app`; from `planning`, `tcw -C
  ../app work new 'Add export' --parent planning.work/<e> --blocked-by
  planning.work/<o> --priority high` exits 0, prints
  `app.work/<date>-add-export`, and the state file holds the three values;
  with `--nest` for a second part: exit 0, `not nested:`, folder at the top
  of `app`'s store. `planning`'s files unchanged.

**Changes**

- `tcw/work/jira/backend.py`:
  - `ticket_key` (`:578-588`) and `_parent` (`:617-623`) are replaced by
    `_place(value, what) -> Linked(key) | Recorded(full_id)`: the value's
    project is the backend's own → its folder's key (as today); otherwise
    `Locator.of(<this project's root>).owner_root(project, named_by=root)`
    (its outcomes propagate: exit 5, 1, 1, and nothing is written), then
    the owner's configuration (`load_config`, no personal layers, as
    TCW-110 Step 13 reads another project's) gives its backend and site;
    a Jira owner on this site → `Linked(<key of its folder>)`; anything
    else → `Recorded(<full id>)`. The message `Jira links only tickets on
    one site` is removed.
  - `create` (`:654-738`): a `Recorded` parent → no parent field, the
    project's default issue type (`meta.issue_type`) rather than
    `child_issue_type` (`:598-615`); recorded blockers → no link. Both go
    into `_item_file` (`:641-650`), which writes `parent` and `blocked-by`
    when given. Standard error says Design 3.3's sentence for each
    recorded value.
  - `update` (`:793-847`): per value, Jira first: a `Recorded` parent →
    clear any Jira parent (the edit `:826-834` makes), then write the state
    file's `parent`; a `Linked` parent → set the parent field, then remove
    any recorded `parent`; `none` → both. Blockers per value the same way,
    `Recorded` ones never reaching `_add_links` (`:849-860`) or
    `delete_link`. The state file is written with `state_text` (TCW-111),
    replacing only the changed keys.
  - `_item_file_problems` (`:146-167`, as TCW-111 leaves it): accepts
    `parent` (one full identifier) and `blocked-by` (a list), each only
    when present.
- `tcw/work/model.py` `validate_changes` (`:188-233`): unchanged; its
  cycle check sees only the item's own project.
- `tcw/serve/work.py` `create` and `edit` reach the same code through the
  backend; no change beyond Step 8.

**Proves it:** the tests above; `tests/work/jira/test_jira_write.py`,
`test_jira_guards.py`; the full suite.

## Step 14 — Jira: reading recorded references

**Tests first**, in `tests/work/jira/test_jira_recorded.py` (AC 7's reading
half):

- `tcw work show` of the item from Step 13's first bullet prints both
  recorded values; `tcw work list --parent files.work/<f>` prints it;
  `tcw work list --parent <site A ticket's item>` uses the JQL parent clause
  (the fake records it), as today.
- `--json` of `show` and `list` gives the recorded values under `parent`
  and `blocked-by`, as a files item's are.
- An item with both a recorded `parent` and no Jira parent reads as that
  parent; TCW-111 Design 3.2's folder-and-parent warning is computed for it
  without `--remote`.

**Changes** `tcw/work/jira/backend.py`:

- `_items` (`:360-381`): after the Jira keys are resolved, each item's
  recorded `parent` and `blocked-by`, read from its state file with
  `read_state` (no network), are added: `parent` is the Jira one or the
  recorded one (there is never both after a TCW write; `tcw validate`
  reports both, Step 15), `blocked_by` is both lists.
- `list` (`:433-482`), the parent clause (`:452-456`): when
  `query.parent` is a ticket on this site (`_place` → `Linked`), today's
  JQL; otherwise today's search without the parent clause, keeping the
  items whose recorded `parent` equals `query.parent`, where today it
  answers `[]` (`:456`).

**Proves it:** the tests above; the full suite.

## Step 15 — `tcw validate` of recorded references

**Tests first**, in `tests/work/jira/test_jira_recorded.py` (AC 27):

- In AC 7's `app`: a recorded `parent` naming `files.work/<f>` passes; one
  naming an item `files` does not have is a warning naming it; `files`
  removed (manifest entry kept): "could not check"; a recorded `parent`
  naming a ticket of a TCW project on site A is an error with `<state
  file>: parent <full id> is a ticket on <site>; run tcw work edit <item>
  --parent <full id> to make it a Jira link`.
- `tcw validate` without `--remote` makes no request to the fake.
- With the fake giving the item's ticket a Jira parent while its state file
  records a `parent`, `tcw validate --remote` reports an error naming both.

**Changes**

- `tcw/validate.py` `_work_findings` (`:548-617`), the Jira branch
  (`:583-588`): beside `jira_store_problems`, the recorded references of
  every Jira item folder (folder scan, `read_state`) as `(item, field,
  value)` triples go through `reference_problems` (Step 10 item 3) with
  `reference_resolver(project_root)` (`tcw/work/open.py:210-241`), each
  finding at the item's state file.
- `tcw/work/jira/backend.py` `jira_store_problems` (`:112-143`): for each
  recorded value, `_place`'s offline decision; a `Linked` answer is
  Design 3.3's error. A `_place` that cannot locate the project reports
  nothing here: `reference_problems` already reports it.
- `tcw/work/jira/remote.py` `_items_and_tickets` (`:458-…`): a ticket with
  a Jira parent whose folder's state file records a `parent` is an error
  naming both values and the command to keep one.

**Proves it:** the tests above; `tests/work/jira/test_jira_remote*.py`; the
full suite.

## Step 16 — the repository's references are rewritten, and mentions listed

The model code that Design 5.8 step 2.3 calls back, tested on its own
before any move uses it.

**Tests first**, new `tests/test_rewrite.py`:

- `rewrite_references(active_root, changes)` with `changes` a list of
  `(old FullId, new FullId)`: in a fixture holding every row of `FIELDS`
  (Step 9's fixtures), each value equal to an old identifier is replaced;
  `!` kept on `Roles` and `When`; every other byte of each file unchanged
  (the test compares each file to its expected text exactly); a value
  equal to `demo.work/2026-10-22-old-two` is left when `…-old` changes
  (Design 6.2); a link inside a fenced block or inline code is left; a
  link keeps its text and everything around the address.
- It returns, per file, the fields and links changed, and separately the
  ones that already named a new identifier (counted as done by an earlier
  run, Design 5.8).
- Running it twice changes nothing the second time and reports everything
  as already done.
- A file that cannot be written: it raises `OSError` carrying the files
  written so far (for the stop message).
- `field_problems(active_root, changes)` (Design 5.4 f): moving
  `roles/owner` to `cli/owner` while `cli/y`'s `Roles` names it returns
  the problem naming `Roles` and `cli/y`.
- `unreadable_records(active_root)` (Design 5.4 e): a capability state file
  with an unparsable `tcw-version`, and a `capabilities.yaml` that is not
  YAML, are each named.
- `mentions(active_root, changes)` (Design 6.4): a prose line naming
  `demo.work/<date>-old-words/P`, and a link in a code block, are each
  reported as `<file>:<line>: names <old>, not rewritten`; a line naming
  `<other-epic>/P` is not; a file that is not UTF-8 is skipped.

**Creates** `tcw/rewrite.py`, with those four functions. It reads the
active project's three stores (their roots from the store locations), the
records of each with `walk` and `read_state` (TCW-111), each item's
`capabilities.yaml` (`parse_declarations`), and every `.md` file under the
three stores, `resources/` included, for links (`links_outside_code`,
Step 11). YAML values are replaced by position (choice 6). It never reads
outside the three stores, nor another project's files (Design 6.5).
Configuration files are not read: Step 21's sweep confirms no
configuration key holds an object reference.

**Proves it:** `tests/test_rewrite.py`; the full suite.

## Step 17 — the work backend's `move`, and `tcw work rename` and `tcw work move` (files backend)

**Tests first**, new `tests/work/test_move.py` (AC 11, AC 13 files, AC 14,
AC 18 files, AC 25 work, and the stop tests):

- AC 11 as written: the epic `<date>-old-words` holding `P` holding `Q`;
  `R` with `blocked-by` naming `P` and the four kinds of text in its spec.
  `tcw work rename <date>-old-words new-words`: exit 0, exactly three lines
  `<old> -> <new>` in the order epic, `P`, `Q`; the references and the
  first link rewritten; the code link, the `-two` link and the prose
  unchanged; standard error names the prose line and the code line, not the
  `-two` link, and ends with `references in other projects are not
  rewritten`. `tcw validate` passes. `--json`: `"schema": 2` and the three
  pairs under `moved`. With the epic's state file holding `id:
  <date>-old-words`: afterwards `id: <date>-new-words`; `P`'s `id: P`
  unchanged. With `R`'s state file unwritable: exit 1, nothing on standard
  output, standard error names `R`'s state file, the files already
  rewritten and `run the same command again`, the epic's folder still at
  the old place; writable again, the same command exits 0, prints the three
  lines, and every file is as after the first clean run.
- AC 13 (files): `move <a> --into <e>`, one line, no folder-and-parent
  warning in `tcw validate`; `move <e>/<a> --top` back; `move <b> --into
  <e>` says `parent: decides` and `<b>`'s `parent` unchanged; `move <b>
  --into 2026/q4` creates `2026/` and `2026/q4/`, moving back with `--top`
  removes both and names them; with `os.rename` patched to fail, `move <b>
  --into 2026/q4` exits 1 and neither folder is left; each of `--into
  <e>/drafts`, `--into <e>/plan`, `--into resources`, `--into <a>` for `<a>`,
  both and neither of `--into` and `--top` exits 2 with nothing changed;
  with a folder named like `<b>` in another letter case inside `<e>`, exit 3.
- AC 14: TCW-111 AC 16a's layout; `move <date>-old-words/<part> --into
  <date>-new-words` exits 0 and removes the emptied `<date>-old-words/`;
  after `edit … --parent <date>-new-words`, `tcw validate` passes.
- AC 18 (files): an epic holding a part whose full identifier is 250
  characters; a rename making it 256 exits 2 naming the part's new
  identifier and 255, and moves nothing.
- The renamed item's own `id`; a case-only rename refused with `already
  exists`; a rename to the same name refused with `already has that name`.
- AC 25 (work half): with a `post` hook and a `pre` check bound to every
  stage, `tcw work rename` and `tcw work move` exit 0 and start no process
  (Step 0 item 4's rule for TCW-107's probe).
- AC 1's `move` row loses its `xfail` mark (Step 3).
- AC 26's rename half for the `work-item` rows (Step 10).
- **Every stop** (`tests/move_stops.py`, choice 10): for `tcw work rename
  <epic> new-words` in AC 11's fixture, each write of a clean run in turn
  fails (a state file write, a repository file write, the folder's
  `os.rename`): each stop exits 1 with nothing on standard output, says
  the folder is still at the old place and `run the same command again`,
  names every file written so far, including on a second stop those the
  first run wrote; the healthy re-run exits 0 and the result equals the
  clean run's byte for byte. A failure in the tidy step (`rmdir` patched to
  fail) exits 0 with a warning, and the move stands.

**Changes**

- `tcw/work/backend.py` (`:69-113`): `rename(self, folder, title_words)`
  (`:95`) becomes `move(self, id_path, new_id_path, before_folder) ->
  list[tuple[FullId, FullId]]`; the docstring keeps "Twelve operations".
- `tcw/work/fs_backend.py` `rename` (`:424-477`) becomes `move`, in Design
  5.8's order: every item's state file read (`read_all`, `:193`; today's
  check `:443-447`); `parent` and `blocked-by` naming a changed identifier
  rewritten in every item's state file, and a renamed item's own `id`
  (Design 5.2), each written with `_replace_file` (`:187`), skipping a value
  that already names the new identifier; `before_folder()`; then
  `move_object_folder` (choice 7), the last write. The `report_mentions`
  call and the "other projects" line (`:474-476`) go: `tcw/move.py` prints
  them. TCW-111's refusal of an item with nested items goes. Returns the
  pairs, the item first, then `objects_below` in the walk's order.
  `report_mentions` (`:211-223`) is removed once nothing calls it (Step 18
  removes the Jira call).
- `tcw/object_folders.py`: `move_object_folder` (choice 7).
- **Creates** `tcw/move.py`: `move_object(namespace, source_text, *,
  new_name=None, into=None, top=False, root) -> int`, which runs Design
  5.4 a to h in order (a: `resolve_work_input` or `find_tree` then
  `check_owned`; 5.5's grammar-breaking source accepted when the walk lists
  exactly that folder; b: the name rules of 5.1 (work words as today,
  `fitted_words`, a tree name one id-part and not reserved) and the
  destination rules of 5.3; c: no entry of the destination folder with the
  same name ignoring letter case, and not the same identifier; d:
  `length_problem` of every changed identifier, nested ones included; e:
  `unreadable_records`; f: `field_problems`; g: in Step 19; h: the backend's
  own read, Step 18), then the backend's or store's `move` with
  `before_folder = lambda: rewrite_references(root, changes)`, then the tidy
  step (empty folders above the old place removed and named; `mentions`;
  TCW-111's `disagreement` warning for each moved object whose folder parent
  is not its `parent`), then the output (5.6) through `print_json` for
  `--json`. A `TcwError` or `OSError` from step 2 is re-raised with the stop
  message (choice 8).
- `tcw/work/cli.py`: `_rename` (`:406-410`) calls `move_object("work", …,
  new_name=…)`; a new `_move_item` (the name `_move` is the advance helper,
  `:364`) calls it with `into` or `top`; the `move` parser beside `rename`
  (`:805-811`) with a required mutually exclusive `--into`/`--top` group
  (argparse gives exit 2 for both or neither) and `--json`; `rename`'s
  contract `prints=` says one `<old> -> <new>` line per changed identifier
  (Design 9.4); `move`'s contract and examples like its neighbours'.
- `tcw/work/jira/backend.py` `rename` (`:870-909`) is renamed `move` with
  the new signature and today's body, refusing more than one moved item
  with TCW-111's message, so that the interface has one name at this
  boundary; Step 18 replaces the body.
- `tests/work/memory_backend.py` (`:120-125`) and `tests/serve/memory.py`:
  `rename` becomes `move`. `tests/work/test_backend_contract.py:205`,
  `tests/work/test_fs_backend.py:312-347`, `tests/work/jira/test_jira_write.py:264-302`
  and `tests/work/jira/test_jira_guards.py:88` call `move` with the new
  signature (`tests/serve/test_files.py:425` renames a folder on disk, not
  through a backend, and is left). The two tests of mentions printed by a
  backend's rename (`test_rename_reports_other_mentions`,
  `tests/work/jira/test_jira_write.py:296-302`, and its files-backend
  counterpart in `tests/work/test_fs_backend.py`, which Step 0 names)
  become command-level tests in `tests/work/test_move.py`, since
  `tcw/move.py` now prints mentions. Each failing assertion is read before
  it is changed, and the changed or moved test IDs go in
  `allowed-step17.txt`.

**Proves it:** the tests above; `compare_outcomes.py` with
`allowed-step17.txt`; the full suite.

## Step 18 — the Jira backend's `move`

**Tests first**, new `tests/work/jira/test_jira_move.py` (AC 12, AC 13
Jira, AC 18 Jira):

- AC 12, the clean run: epic `EK` holding `PK` holding `QK`, each
  `TCW Item` its full identifier; `R`'s spec links `PK`'s identifier.
  `tcw work rename <EK-folder> new`: the fake's log shows one search for
  the three keys, then for each of `EK`, `PK`, `QK` a read then an edit;
  then `R`'s link is rewritten and the folder moved (the order of the last
  two checked by recording the times of the rewrite and the `os.rename`
  with spies). Each `TCW Item` is the new identifier.
- AC 12's bullets, each from the same starting state: the second edit
  failing (`fail_edit(2)`), then the third (`fail_edit(1)` on the re-run,
  which edits `PK` first), then healthy, with the messages and the fake's
  records AC 12 lists; the folder's `os.rename` failing, then a re-run with
  no edit; `QK` holding a 3.x value: exit 3 before any edit, naming `QK` and
  `tcw migrate`; `PK` holding another 4.0 identifier: exit 3 naming `PK` and
  `tcw validate --remote`; `fake.hide("PK")`: exit 4, `Jira has no ticket
  PK`; two runs at once: `before_request` changing `EK`'s `TCW Item` after
  the first search and before the first edit: exit 3, no edit, `R` and the
  folder unchanged, message names `EK`, its new value and `another command
  may be moving this item`.
- A ticket gone between the search and its edit (`hide` from
  `before_request`): exit 4, with 5.8's message.
- The connection dropping after the first edit
  (`drop_after_next_write(then_unreachable=True)`): exit 5, the message
  names `EK` as set; a healthy re-run finishes with edits of `PK` and `QK`
  only.
- **Every stop** (`tests/move_stops.py`): each Jira edit, the repository
  rewrite's writes, the state file `id` write and the folder's `os.rename`
  fail in turn; each stop names every ticket set (by this run or an earlier
  one) and every ticket still to be set; each healthy re-run finishes, and
  the fake's tickets and the tree equal the clean run's.
- AC 13 (Jira): `move <a> --into <e>`: `<a>`'s `TCW Item` is the new
  identifier.
- AC 18 (Jira): the 256-character rename exits 2 and the fake records no
  request after the search (no edit).
- No ticket is ever set back: in every test above, the fake records no
  edit that writes an old value.

**Changes** `tcw/work/jira/backend.py` `rename` (`:870-909`) becomes
`move`: the moved keys are the item's and `objects_below`'s
(`folder_key` of each, `:98-101`); **read**: one search by key (as
`resolve_keys`, `:391-…`, searches) reading `TCW Item`, sorting each into
to-be-set, done, 3.x (refused, naming every such key and `run 'tcw migrate'
in this project first`), other (refused, naming key, value and
`tcw validate --remote`) and missing (`NotFound`, today's `_issue` message,
`:344-350`); **set**: for each to-be-set key in order, `_issue` reading
`TCW Item` again, then the edit only if it still holds the old value, done
if it holds the new one, else `Refused` (or `NotFound`) with Design 7.3's
sentence; then the renamed item's own `id` in its state file; then
`before_folder()`; then `move_object_folder`. The set-back (`:894-904`) is
removed. The `report_mentions` call goes; `report_mentions`
(`tcw/work/fs_backend.py:211-223`) is then removed.
`test_a_failed_tcw_item_edit_keeps_the_folder`
(`tests/work/jira/test_jira_write.py:287-292`) still holds and is kept; the
test that a failed folder move sets `TCW Item` back (TCW-111 Step 12's) is
replaced by AC 12's `os.rename` bullet, and listed in `allowed-step18.txt`
with Design 5.8.

**Proves it:** the tests above; `compare_outcomes.py` with
`allowed-step18.txt`; the full suite.

## Step 19 — the tree stores' `move`, and `rename` and `move` for terms and capabilities

**Tests first**, new `tests/test_tree_move.py` (AC 15, AC 16, AC 17, AC 19,
AC 20, AC 21, AC 25's tree half, AC 2's last rows, AC 26's tree rows):

- AC 15, AC 16, AC 17, AC 19, AC 20, AC 21 exactly as the spec writes
  them, including AC 15's "every other line of each file it rewrote is
  unchanged" (each file compared with its expected text), `tcw taxonomy
  show bill` printing the same `name`, `id: invoice` → `id: bill`, and the
  `os.rename` failure and re-run. AC 17's exit 7 with `core`'s folder
  removed comes from inherited-at.
- AC 25 (tree half): `tcw taxonomy rename` and `tcw capabilities move` start
  no process.
- AC 2's `tcw taxonomy rename core.taxonomy/t u` and `tcw capabilities move
  core.capabilities/cli/x --top` rows lose their `xfail` mark.
- AC 26: the rename half of every term, capability, `capabilities-yaml` and
  link row, and of the added `Reviewed by` row.
- **Every stop** (`tests/move_stops.py`): for `tcw taxonomy rename invoice
  bill` in AC 15's fixture, each repository write and the folder's
  `os.rename` fail in turn; each re-run finishes, the result equal to the
  clean run's.

**Changes**

- `tcw/store/base.py`: `TaxonomyStore` (`:346`) and `CapabilitiesStore`
  (`:511`) gain `move(id_path, new_id_path, before_folder) ->
  list[tuple[FullId, FullId]]`.
- `tcw/store/fs.py`: `FsTaxonomyStore` (`:1704`) and `FsCapabilitiesStore`
  (`:2225`) implement it in `FsTreeStore` (`:1250`): the pairs from
  `objects_below`; `before_folder()`; `move_object_folder`. The store writes
  nothing else (Design 8): the references terms and capabilities hold, and a
  renamed object's own `id`, are rewritten by `rewrite_references` (Step
  16), which `tcw/move.py` passes as `before_folder` and extends with the
  own-`id` write for a tree rename (Design 5.8 step 2.3).
- `tcw/move.py`: check 5.4 g for taxonomy and capabilities: inherited-at
  for the object's own path (not none → refused, naming the inherited
  object) and for each new path (not none → refused); `InheritedUnavailable`
  propagates (exit 7).
- `tcw/taxonomy/cli.py` `add_subparser` (`:137-201`) and
  `tcw/capabilities/cli.py` `add_subparser` (`:221-315`): `rename <term>
  <name>` and `move <term> (--into <id-path> | --top)` (and the same for
  capabilities), each calling `move_object`, with `--json`, contracts and
  examples like their neighbours'.

**Proves it:** the tests above; the full suite.

## Step 20 — shipped text

**Tests first** (AC 23):

- `tests/test_shipped_prompts.py`: `tcw work stage prompt plan <item>`
  contains `tcw -C tcw://<id>.path/ work new`, `--parent <slug> --nest` and
  `TCW records it in the part's folder`, and not `--project`, `uncommitted`
  or `only a ticket on its own site`.
  `test_plan_says_how_to_file_a_part_into_another_project` (`:331-341`) is
  rewritten to check the new paragraph's order (`--nest`, `tcw -C`,
  `--blocked-by`, `records it`), and listed in `allowed-step20.txt` under its
  old ID if renamed.
- `tcw work procedure audit-backlog` contains `tcw -C` and not `--project`.
- `tests/test_docs_describe_3_0.py`: `docs/lifecycle/abstraction.md`'s
  interface list has a **move** entry, no **rename** entry, and not
  `uncommitted changes before creating an item in another project`;
  `test_the_backend_interface_names_exactly_twelve_operations` still passes.
- `tests/test_shipped_text.py`: the accepted-commands list (`:336-339`)
  loses `'tcw work new "<title>" --project <id>'` and gains `tcw -C
  tcw://<id>.path/ work new "<title>" --parent <slug> --nest`.

**Changes**

- `tcw/work/prompts/plan.md` step 6 (`:38-46`, as TCW-111 Step 15 leaves
  it), replaced by Design 9.1's paragraph, which combines TCW-111's `--nest`
  sentence with this item's:

  > 6. **Too large for one item?** Split it here: `tcw work new "<title>"
  >    --parent <slug> --nest` per part, its request on stdin; this item is
  >    the parent, and `--nest` puts the part's folder inside the parent's
  >    folder (where it cannot, the command says so and makes it at the
  >    top). A part for another project is made in that project:
  >    `tcw -C tcw://<id>.path/ work new "<title>" --parent <slug> --nest`
  >    (`--nest` then makes it at the top of that project's store and says
  >    so); set `--blocked-by` the same way. When Jira cannot link the
  >    parent (an epic kept in files, or on another Jira site), TCW records
  >    it in the part's folder and says so, and Jira itself does not show it.

  The wording of TCW-111's own sentence is kept as TCW-111 wrote it if it
  differs from the above in words, not meaning; Step 0 copies it in.
- `tcw/work/procedures/audit-backlog.md:27-29`: Design 9.2's sentence.
- `docs/lifecycle/abstraction.md`: the **rename** entry (`:55-56`, as
  TCW-111 leaves it) becomes Design 9.3's **move** entry; the git-reads
  list (`:101-104`) loses the uncommitted-changes clause.
- `tests/fixtures/prompt_fallback/unconfigured.json` regenerated with
  `tests/fixtures/prompt_fallback/capture.py`, and the difference read: only
  step 6 changes.

**The combined change is reviewed once both items have landed** (TCW-111
Risks; spec 9.1): the implement round of this item records a review of
`git diff <TCW-111's last commit> -- tcw/work/prompts/plan.md` covering both
items' edits together.

**Proves it:** the tests above; the full suite.

## Step 21 — the sweep, and guards that keep it swept

**The site list**, written into the implement round, one line per site with
its file and line after Steps 2 to 20, from a fresh search over `tcw/`,
`web/client/src/`, `scripts/` and `evals/`:

1. Every write site of Design 1.2, with its call of the ownership check:
   the work CLI's eight (Step 3, `new` through `tickets adopt`, `move` from
   Step 17), the tree CLI's ten (Steps 3, 19), the web's eleven routes
   (Step 4), and every `generate:` binding and hook (none write outside the
   item's folder; each named).
2. No comparison of `.project` with another ID used to refuse a write:
   `grep -rn "\.project != \|\.project == " tcw/` read site by site, the
   ones left being reads (`_own`, `tcw/work/cli.py:71`, and
   `tcw/serve/work.py:454`, `:484` gone).
3. No caller of the removed functions (Step 7's grep), no route ending
   `/blocks`, no `Jira links only tickets on one site`, no backend method
   `rename` (`grep -rn "def rename" tcw/`), no reader of `read-only` or
   `readOnly`.
4. Every reader of a reference field reads `FIELDS` (Step 10's list, plus
   any the search finds).
5. Every reader and writer of a Jira item's `parent` and `blocked-by` uses
   `_place` and the recorded values (Steps 13, 14).
6. The ten current-folder reads (Step 5).
7. Every configuration key, confirmed to hold no object reference: the keys
   of `tcw-config.yaml`'s schema read one by one (Design 6.5).

**Tests first**, new `tests/test_ownership_sweep.py` (AC 24):

- A search of `tcw/`, `web/client/src/`, `scripts/` and `evals/` finds no
  definition or call of `delegate`, `open_for_update`, `blocks_target`,
  `delegate_to_jira`, `uncommitted_changes`, `_cannot_make_item`, no `def
  rename` in a backend or store class, no route pattern ending `/blocks`,
  and no `Jira links only tickets on one site`.
- Every function under `tcw/` that calls a backend's `create`, `update`,
  `set_stage`, `comment` or `move`, or a tree store's `add`, `set`,
  `reset`, `remove`, `update_term`, `update_capability` or `move`, is in a
  list kept in the test, each with the name of the function on its path
  that calls `check_owned`; a new caller fails the test until it is added
  with its check. Found by an `ast` walk, as `tests/test_static_guards.py`
  walks today.
- No `Path.cwd()` or `os.getcwd()` under `tcw/` outside Step 5's list.

**Proves it:** the tests; the list in the implement round, which the
reviewer checks against a fresh search (AC 24); the full suite.

## Step 22 — this repository's records

In this repository's ledgers in their **3.x form** (`meta.yaml` and
`description.md`), because the lifecycle `tcw` reads them and TCW-116
converts them, as TCW-111 Step 18 does. From `capabilities.yaml`:

- New capabilities, status `Supported`, `Subject` naming the new term:
  `docs/capabilities/cli/change-objects-only-in-the-project-that-owns-them/`,
  `docs/capabilities/cli/run-a-command-as-if-started-in-another-folder/`,
  `docs/capabilities/work/move-a-work-item/`,
  `docs/capabilities/taxonomy/rename-or-move-a-term/`,
  `docs/capabilities/capabilities/rename-or-move-a-capability/`.
- The twelve changed capabilities: the sentence the spec's "Capability
  changes" gives each, in its `description.md`.
- Removed: `docs/capabilities/work/delegate-a-work-item-to-another-project/`,
  its status set to the 3.x form for a removed capability that the other
  removed ones in this ledger use (Step 0 reads one), with `Superseded by`
  naming `cli/run-a-command-as-if-started-in-another-folder`.
- Taxonomy: new `docs/taxonomy/owning-project/`; `reference` and `project`
  descriptions updated.

The new text names only commands that exist after Step 19
(`tests/test_documented_cli_surface.py` checks every `tcw …` span, `-C`
included after Step 6).

**Proves it:** with the lifecycle `tcw` from the worktree: `tcw validate`;
`tcw work advance TCW-114 --dry-run` at the end of implement (the records
gate); `tests/test_documented_cli_surface.py` with the suite.

## Step 23 — notes for the later children

The spec's handoffs (after Risks) were to be recorded on each ticket when
the spec was accepted. The dispatching session checks each is on its
ticket and posts any that is missing, and posts what planning added (the
text goes in the implement round first):

- **TCW-113:** every write route is marked in the route table with
  `writes`, and the router checks it (Step 4); a route TCW-113 adds is
  marked the same way. The connected-project rows of `GET /api/project`
  no longer carry `readOnly` (and possibly no `projects` key at all, Step
  8); TCW-113's views of other projects bring back whatever they need.
- **TCW-115:** the refusal's tail for a project not on this machine can add
  `tcw project provision <id>` in `check_owned` (`tcw/ownership.py`), its
  one place.
- **TCW-116:** a move refuses while a ticket holds a 3.x `TCW Item` (Step
  18); this repository's own tickets will be refused until migrated.
- **TCW-117:** beyond the spec's list: `tcw -C` in `docs/guide/cli.md` and
  the CLI guide's global options; `tcw work move`, `tcw taxonomy
  rename|move`, `tcw capabilities rename|move`; that a Jira-mode create
  form now accepts blockers in other projects (Step 8); the removal of
  `report_mentions` changes nothing a user sees.

## Step 24 — Documentation Sync

Each documentation entry (`tcw work docs`), evaluated with the
`documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: `-C`, the move commands, `--project` and `--blocks` removed (`README.md:608`) | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99, "How 4.0 is built"); the spec's TCW-117 handoff and Step 23 say what. Recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | yes: recorded parents and blockers; a move edits `TCW Item` per ticket; delegation gone (`:235`) | Deferred to TCW-117, as above. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/cli.md:150`, `work.md:332`, `:351`, `multi-repo.md:141-187` | Deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written (below). |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written (below). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: `skills/work/SKILL.md:94`, `:107-112`, `skills/capabilities/SKILL.md:153`, `:181`, `skills/work/references/commands.md:11`, `:19` | Deferred to TCW-117 (spec handoff). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no key changes; `projects.md:170`, `:199` teach `--project` | No configuration key is added or changed; the two lines are TCW-117's (spec handoff). |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-3 and UC-4's filing requirements | Deferred to TCW-117 (spec handoff). |

The two entry files are named
`TCW-114-tcw-4-0-changes-only-in-the-owning-project-and-moving-or-renaming-objects.md`
(the item's folder name), checked by `tests/test_upcoming_entries.py`, and
formatted with `prettier`. Their content, in plain language and with no
module names in the release note:

**`docs/release-notes/upcoming/<folder>.md`:**

- Only the project that owns a record can change it. A command run in one
  project that would change another project's work item, term or
  capability stops and says which folder to run it in; overriding an
  inherited capability is still allowed.
- New: `tcw -C <folder or tcw://<id>.path/> <command>` runs any command as
  if it had been started in that folder, as that project, with its
  settings, checks and hooks.
- `tcw work new --project` and `tcw work edit --blocks` are removed. Create
  a part in its own project with `tcw -C … work new "<title>" --parent
  <epic>`, and record a blocker on the blocked item with `--blocked-by`.
  The web app's project choice on the create form and its "Blocks (add)"
  section are gone.
- New: `tcw work move`, `tcw taxonomy rename|move` and `tcw capabilities
  rename|move`; `tcw work rename` now works on an item with items inside it.
  A move or rename updates every reference in this project, lists the
  places it could not update, and, if it stops partway, says what it did and
  that running the same command again finishes it.
- In a Jira project, a parent or blocker that Jira cannot link (an item kept
  in files, or a ticket on another Jira site) is now kept in the item's
  folder rather than refused, and TCW says Jira will not show it.

**`docs/changelogs/upcoming/<folder>.md`:** Added (`tcw/ownership.py`
`check_owned`; the route table's `writes`; `tcw -C`; `tcw/move.py`,
`tcw/rewrite.py`, `tcw/reference_fields.py`; `move_object_folder`;
`code_spans` and `links_outside_code`; the `move` and `rename` commands;
recorded `parent` and `blocked-by` in a Jira item's state file; the fake
Jira's three switches); Changed (the backend operation `rename` became
`move(id_path, new_id_path, before_folder)`; the files backend writes
references before the folder; the Jira move reads each ticket before its
edit and never sets one back; every reference checker reads the one list of
fields; `reference_problems` takes triples; `tcw validate` checks recorded
references; the plan stage prompt's step 6, `audit-backlog`,
`abstraction.md`); Removed (`--project` and `--blocks`, kept only to give a
message; `delegate`, `open_for_update`, `uncommitted_changes`,
`_check_declared`, `_check_target`, `_uncommitted_in`, `blocks_target`,
`delegate_to_jira` and its helpers, the server's `delegate` service, the
`/blocks` route, `BlocksForm`, the create form's project selector,
`read_only_reason`, `read-only`, `readOnly`, `_own`, `report_mentions`,
`_strip_code`, TCW-111's refusal to rename an item with nested items and its
delegation length fitting); Internal (`tests/move_stops.py`, the sweep
guard, the `-C`-aware command checkers).

## Step 25 — the suite as CI runs it

What `.github/workflows/test.yml` runs (AC 28), done locally, since CI does
not run on `v4`:

- the `pytest` job: bare `.venv/bin/pytest` from the worktree's root, never
  `python -m pytest`;
- the `web-build` job: `pnpm install --frozen-lockfile` and `pnpm
  check:build`;

and, beyond CI, `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint`, and
`pnpm exec prettier --check` over every file this item changed or created
that `.prettierignore` does not exclude. Last, `compare_outcomes.py
<outcomes-step1.xml> <final.xml> <every allowed-step*.txt joined>` passes:
every test that disappeared over the whole item is listed with its reason. A
failure is fixed in the step it belongs to, not with a skip.

## Verification the tests cannot do

- **The QA plan's six scenarios** (ticket comment of 2026-10-22), run by
  hand in throwaway projects under the scratchpad with `.venv/bin/tcw`, the
  current folder set there: ownership refusals read well and the `tcw -C`
  they print works when pasted; filing replaced by `-C … --parent`; a
  blocker in another project allowed; a Jira parent recorded (with the
  suite's Jira launcher, `tests.serve.jira_launcher`, never the live board);
  `-C` with a path and an address; a move and a rename of a nested item, and
  one stopped by making a file unwritable, then finished.
- **The web app**, served from a scratchpad fixture with `.venv/bin/tcw
  serve` (current folder there) in the dedicated Chrome profile: the create
  form has no project choice, the item page has no "Blocks (add)" and still
  lists what the item blocks; a Jira-mode form accepts a blocker in another
  project with the warning.
- **The messages read as plain language** at their length: the stop message
  of a Jira move with three tickets, read in a terminal.
- **The combined step 6 of the plan prompt** (Step 20), read once in full as
  an agent would see it.

## Self-review against the spec

**Every criterion has a step:**

| AC | Step |
| --- | --- |
| 1 work writes refused, four locate outcomes | 2, 3 (`move` row: 17) |
| 2 tree writes refused, override allowed, one shape | 3 (`rename`, `move` rows: 19) |
| 3 planning workspace | 3, 6 |
| 4 web app: create, `/blocks`, PATCH, route table, router test, client | 4, 7 (create, `/blocks`), 8 (client) |
| 5 removed options | 7 |
| 6 a part in another project, files | 13 (with `-C` from 5) |
| 7 Jira recorded references: write, read, exit 5, stop and re-run | 13, 14 |
| 8 `-C` path | 5 |
| 9 `-C` address | 5 (3.x start with a path), 6 |
| 10 `-C` runs as there | 5 (`init`), 6 |
| 11 rename with nested items, files, and its stop | 17 |
| 12 rename with nested items, Jira, every stop | 12, 18 |
| 13 moving work items | 17, 18 (Jira) |
| 14 repairing a merge | 17 |
| 15 taxonomy rename and move | 19 |
| 16 capabilities rename and move | 16 (5.4 f), 19 |
| 17 overrides | 19 |
| 18 length | 17, 18 |
| 19 unreadable records | 16, 19 |
| 20 grammar-breaking folder | 17 (5.5 in `tcw/move.py`), 19 |
| 21 other projects' references | 19 |
| 22 no `read-only`, no `readOnly` | 7, 8 |
| 23 shipped text | 20 |
| 24 the sweep | 7, 21 |
| 25 no hooks, no git | 17, 19 (Step 0 item 4's rule) |
| 26 one definition | 9, 10, 17, 19 |
| 27 validate of recorded references | 15 |
| 28 suite as CI runs it | 25 |

**Every Design rule has a step:** 1.1-1.3 → 2, 3; 1.4 → 4; 1.5 → 3; 1.6 →
3, 6; 1.7 → 13; 1.8 → 7, 8; 2.1-2.2 → 7; 2.3 → 7, 8; 2.4 → 7; 3.1-3.2 → 13
(AC 6); 3.3 → 13, 14, 15; 4.1-4.2 → 5; 4.3-4.4 → 6; 4.5 → 5; 4.6 → 6; 5.1-5.6
→ 17, 19; 5.7 → 17, 19 (AC 25); 5.8 → 17, 18, 19 (every stop); 6.1-6.2,
6.4-6.6 → 16; 6.3 → 9, 10; 7.1-7.2 → 17; 7.3 → 18; 7.4 → unchanged, covered by
TCW-111; 8 → 19; 9.1-9.3 → 20; 9.4 → 17, 19; 10 → "What this plan relies
on", Step 0; 11 → 21.

**The suite at each step boundary.** Each step adds its tests and the code
they need together, and removes a test only in the step that removes its
behaviour, listed in that step's `allowed` file:

- Step 3's rows for commands that do not exist yet (`tcw work move`; `tcw
  taxonomy rename`, `tcw capabilities move`) are `xfail(strict=True)` until
  Steps 17 and 19 add them, so they pass (as expected failures) at every
  boundary between, and a strict mark fails the suite if one starts passing
  while still marked.
- Step 4's route-table test lists `/blocks` as a write until Step 7 removes
  the route.
- Step 7 removes every caller of the removed functions in the same step,
  the server's `/blocks` route and create branch included, so nothing calls
  a function that is gone at its boundary; the client keeps its selector
  for one step and gets a usage error if a person picks another project,
  which no test exercises against a real server. Step 8 removes the
  selector.
- Step 10 changes no behaviour; each commit is compared with an empty
  allowed list.
- Step 17 changes the backend interface, both memory backends and the Jira
  backend's method name together (the Jira `move` running today's rename
  body), so `tcw work rename` in a Jira project works at the Step 17
  boundary; Step 18 replaces the Jira body. The Jira rename tests pass at
  that boundary on the renamed method, called with the new signature.
- Step 20 changes the prompt text and its tests together, and regenerates
  the fallback fixture in the same step.

**Citations.** Every `file:line` above was read at `d2d02829`; Step 0
re-checks them all after TCW-112 lands, and the earlier items' plans name
most of these places as changing.

**No placeholders.** Every message is given in full or by the Design rule
that gives it in full; the one name taken from another item's plan
(inherited-at, TCW-112) is recorded in Step 0 before it is used.

## Spec issues found while planning

1. **AC 9 and AC 25 may ask for something TCW-107 makes impossible.** AC 9
   says none of its commands "starts a `git` process", and AC 25 that a move
   "starts no process". Design 4.6 claims only that `-C` itself runs no git.
   But a project lookup on TCW-107's registry probes for a linked git
   worktree (`worktree_anchors`, `tcw/store/project.py:67-79`, running `git
   -C <folder> rev-parse` through `_git_lines`, `:119-128`), and the
   fixtures are git repositories. If Step 0 item 4 finds that probe running
   in `tcw work list` or `tcw work rename`, the tests allow exactly that
   read-only probe and nothing else. AC 9's sentence should then say "no git
   process other than TCW-107's read-only worktree check", and AC 25's "no
   process other than…" the same.
2. **A Jira-mode project whose Jira settings come from a missing parent.**
   TCW-109's handoff to TCW-117 notes that such a project cannot open its
   backend (exit 7). That makes Design 5.4 g's reading, "a work move needs
   no other project", false for that setup: `tcw work move` stops with exit
   7 before any check. This is not a defect in this item's design, since
   every command in that project stops the same way, but the spec's
   sentence overstates. It is worth one clause in 5.4 g.
3. **Design 2.2 says "nothing reads their values", but the `--blocks`
   message depends on the value**: it omits `-C` for a target in the
   active project and names "its project's folder" otherwise (AC 5 tests
   both). The plan reads the value only to word the message (Step 7). The
   sentence should say the value is read only for the message.
4. **The Jira-mode web form refuses a blocker in another project today**
   (`web/client/src/ui/work-forms.tsx:600-606`, "in Jira mode a blocker must
   be one of this project's items"). Design 3.3 makes the backend record
   one, and says the web routes send each value to its place, but 2.3 does
   not mention the client. The plan changes it (Step 8); the spec could
   name it in 2.3.
5. **`tickets adopt` has no ownership call today** and always writes the
   active project's item. Design 1.2 lists it as a writer; the plan gives it
   a call that always passes (choice 2), so that the sweep finds every
   writer calling the check. Not a defect, recorded so the reviewer is not
   surprised.
