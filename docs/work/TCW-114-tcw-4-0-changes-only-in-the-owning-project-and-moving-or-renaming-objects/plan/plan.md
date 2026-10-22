# Plan — TCW 4.0: changes only in the owning project, and moving or renaming objects

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). File and
line references are to commit `d2d02829` on `v4`, where only TCW-106's code
has landed, and were re-checked at `965f2bff` for this revision (the plan's
review round, see "Revised after the plan review" at the end). This item lands eighth, after TCW-106, TCW-107, TCW-110,
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
- **TCW-109** (plan): personal files and environment variables are chosen by
  the active project's ID and folder; a project read for itself is
  `load_config(root, personal=False, registry=<the command's registry>)`
  (TCW-109 plan, choice 3), which raises `InheritedUnavailable` (exit 7)
  when a key it needs (`work.jira` in Jira mode, `work.tags`) is undecided
  (its choice 4 and Step 7c). Step 13's `_place` reads the named project's
  backend and site that way.
- **TCW-112** (plan): `inherited_at(id_path) -> FullId | None` on both tree
  stores (its Design 2.7, plan Step 8), raising `InheritedUnavailable` (exit
  7) when the view cannot be built; `get_inherited` deleted; `tcw
  capabilities set` on an inherited capability writes the active project's
  own object at the same id-path (its Design 4.2), written by
  `_write_target`; `chain(id_path)`; `override_target(target) -> FullId`
  and `removal_target(target) -> FullId` on the stores, which hold its only
  two refusals of another project's object (Design 4.2's for `set` and
  `reset`, Design 4.4's for `rm`), and which this item rewords (TCW-112
  plan, choice 9 and its handoff to TCW-114); `find_tree_writable(store,
  namespace, text, *, removing: bool) -> FullId` (no default, TCW-112's
  final plan), which calls one of them
  and refuses nothing itself; `extends` gone. Step 0 item 3 confirms these
  against what TCW-112 landed.

## Choices this plan makes where the spec leaves room

1. **Where the ownership check lives.** A new module, `tcw/ownership.py`,
   with one function, `check_owned(full_id, active_root, *, reason=None,
   hint=None)`. It is model code that asks the deployment layer
   (`tcw/locate.py`) for the owner's folder only to word the refusal.
   TCW-112's `override_target` and `removal_target`, where its two
   refusals of another project's object live, become calls of it.
2. **The writers call it through the shared code they already use**, as the
   spec's first Risk asks: work commands through `resolve_item(...,
   writing=True)` (`tcw/work/cli.py:50-66`), tree commands through
   `find_tree_writable`, web routes through the router. Both make the check
   on the project the text names **before** anything of that project is
   opened (spec 1.1): `resolve_item` sorts the text with `sort_input` and,
   for forms `a` and `c`, calls `check_owned` before `resolve_work_input`
   opens the named project's backend; for the trees, TCW-112's
   `removal_target` already refuses another project's full identifier
   before reading anything, and its refusal becomes `check_owned`. The creators (`new`, `tickets adopt`, the tree `add`
   commands, the web create and adopt routes) make no call (spec 1.2, the
   dispatching session's decision on the review's U2), and the sweep lists
   them as creators.
3. **The route table marks a write by a function, not a flag.** `Route`
   (`tcw/serve/server.py:193-197`) gains `writes`, a function from the
   request to the existing objects it writes (a list of `Written(full_id,
   hint)`), or `None` for a read. A create route answers `[]`: it makes a
   new object of the active project and names no existing one, so the
   router makes no call for it (spec 1.2), but it is still marked a
   write. This lets AC 4's test read the table and
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
6. **Values in YAML are replaced by their position in the text, at the
   fields the definition names.** For a state file or a `capabilities.yaml`,
   the rewrite reads the file with `yaml.parse`'s events (mapping and
   sequence starts and ends, and scalars, each with its start and end in
   the text) and keeps a **key path** as it goes: the mapping keys above the
   current value, and a marker for a sequence item under a key. A scalar is
   replaced only when its key path is one that `FIELDS` names for that
   record (for `capabilities.yaml`: `new[]`, `changed[]`, `removed[]`,
   `taxonomy.new[]`, `taxonomy.changed[]`, `taxonomy.removed[]`; for a
   capability: `Subject[]`, `Feature`, `Superseded by`, `Blocked by`,
   `Roles[]`, `When[]`, `parent`; and so on) and its parsed value, with a
   `!` taken off where the row allows one, equals an old identifier. Its
   quoting style is kept; a value needing quotes it did not have is written
   in single quotes. A scalar equal to an old identifier at any other path
   is a mention (spec 6.3, 6.4): left, and listed. Every other byte stays
   (Design 6.6). The same function, `rewrite_yaml(text, fields, changes)`,
   is used by the files work backend for its state files (choice 12).
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
   5), with the message replaced and the original error's `name` kept
   (`_dispatch` prints `error.name` when it is set). Where the folder is,
   the message checks when it is built (`old_path.is_dir()`), and the
   advice it ends with is chosen by why the run stopped (spec 5.8): "run the
   same command again" for every stop except a ticket found holding a third
   value (exit 3, the clash with another command) and a folder already gone
   (exit 4), each of which gets the spec's own advice. An `OSError` from
   `os.rename` whose source no longer exists is raised as `NotFound`
   (exit 4).
9. **A Jira item's recorded references are read in the folder scan** by
   `object_folders.read_state`, so reading them never needs the network.
10. **Partial failure is tested by stopping at every write in turn.** A test
   helper, `tests/move_stops.py`, counts the writes a clean run makes, then,
   for each write `k`, runs the command with write `k` failing, checks the
   stop, runs it again healthy, and compares the result with the clean
   run's, byte for byte, including the fake's tickets. This covers "stop a
   move at each point and show that a re-run finishes it" without writing
   one test per point by hand. Its rules:
   - **What it counts.** Every target of `_atomic_write_all`
     (`tcw/store/fs.py:1149`; one count per `(path, content)` pair, failing
     before that pair's file is put in place), `Path.write_text`,
     `Path.write_bytes`, `os.replace`, `Path.replace`, `os.rename`,
     `Path.rename`, `shutil.move`, `os.mkdir`, `Path.mkdir`, `os.rmdir`,
     `Path.rmdir`, `os.remove`, `Path.unlink`, and each fake Jira `PUT
     /issue/<key>`. The writes `_atomic_write_all` itself makes to its
     temporary files are not counted separately; they are inside its one
     count. **Counting pauses inside a counted call**: while
     `_atomic_write_all`, `Path.write_text`, `Path.write_bytes`,
     `Path.mkdir`, `Path.rename`, `Path.replace`, `Path.rmdir`,
     `Path.unlink` or `shutil.move` runs, the `os` functions it calls
     (`os.mkdir`, `os.rename`, `os.replace`, `os.unlink` and so on) are not
     counted again, so each write is counted once and the counts read as
     the command's own writes. (`Path.unlink` calls `os.unlink`, which is not
     on the list while `os.remove` is; the rule below catches any primitive
     that is missed, so that is not a hole.)
   - **Every change must be explained.** Before and after the clean run the
     helper takes a snapshot of every file and folder under the fixture
     (path, kind, bytes) and of the fake's tickets. Every path whose bytes or
     existence changed, and every ticket that changed, must be the target of
     a counted write; otherwise the helper fails, naming the path, so a write
     through a primitive it does not patch cannot pass unnoticed. **A folder
     rename explains what is under it**: after a counted `os.rename(old,
     new)` or `Path.rename` of a folder, every path under `old` that is gone
     and every path under `new` that appeared is explained by that rename,
     provided its kind and bytes under `new` equal what it had under `old`
     or are the target of a later counted write. Without this clause every
     clean run would fail, since only the two folder paths are the rename's
     own targets.
   - **Which commands.** A rename (files and Jira), a move that creates two
     organising folders (`--into 2026/q4`, so that a failing second `mkdir`
     after a first that succeeded is exercised), a taxonomy rename and a
     capabilities move.
11. **The process rule is decided now** (review M5). A move, `-C` and the
   commands of AC 9 start no process other than read-only `git rev-parse`.
   The rule is `_allowed` (`tests/serve/test_no_process.py:77-91`) with its
   `git --no-optional-locks status` branch left out, moved to a shared test
   helper, `tests/processes.py` (`allowed_read_only_git(argv)` and a
   `recorded_processes` fixture recording every `subprocess.run` and
   `subprocess.Popen`), which `tests/serve/test_no_process.py` then imports
   for its own wider rule. Step 1 creates it.
12. **One rewrite of a YAML field for every writer.** The files work backend's
   `move` rewrites its state files' reference fields (`fields_of("work-item")`)
   with choice 6's `rewrite_yaml`, not through the `Item` model's `parent`
   and `blocked_by` attributes, so a work-item row added to `FIELDS` is
   rewritten as well as checked (spec 6.3, review S9). The backend still
   owns the write: it calls a pure function of text, and writes the result
   with `_replace_file`.
13. **The documents that write a removed option are changed in Step 7**
   (spec 9.5, review M1), together with hiding the options. The other way,
   keeping `--project` and `--blocks` visible in `--help` until TCW-117,
   would keep `tests/test_documented_cli_surface.py` green only because the
   documents name an option that still parses while it no longer does what
   they say. Each passage is changed only as far as naming a working
   command.

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
   confirmed against what they landed: `inherited_at(id_path)` and
   `chain(id_path)`; `override_target` and `removal_target`, which word
   TCW-112's two refusals; `find_tree_writable(..., removing: bool)`, with
   no default,
   calling them and refusing nothing itself; where TCW-112's `set` writes
   an override (`_write_target`); `load_config(root, personal=False,
   registry=...)`. Step 3 is written against TCW-112's plan; a difference
   found here is resolved by spec 1.1's rule (Step 3's last paragraph).
4. **The git processes a plain command starts, measured.** The rule is
   already decided (choice 11, spec 4.6): nothing but read-only `git
   rev-parse`. In a scratchpad fixture of two git repositories side by side,
   `tcw work list`, `tcw work rename`, `tcw taxonomy rm` and `tcw
   capabilities set` are each run with every `subprocess.run` and
   `subprocess.Popen` call recorded (the recording plugin of Step 1), to
   confirm that what TCW-107 to TCW-112 landed starts nothing else (TCW-107's
   search may probe more folders' worktrees, `_worktree_copy`, which only
   adds `git rev-parse` calls). Anything else found is a defect of the item
   that added it, reported to the dispatching session before Step 2.
5. The repository URL a `project_folder` refusal can name: Step 0 finds how
   TCW-107 exposes the deciding manifest entry's `repository` to a caller
   (an attribute of the raised `Unreachable`, or a registry method). If it
   is only inside the message text, Step 2 adds a `repository` attribute to
   the `Unreachable` that `project_folder` raises, set where TCW-107 builds
   that message.
6. The suite passes: `.venv/bin/pytest`, and the web checks of the gate.
7. **The documents of choice 13, found again.** The documented-command
   check itself finds them: `tests/test_documented_cli_surface.py` is run
   with a one-off scratchpad patch that hides `--project` and `--blocks`
   from `--help` (as Step 7 will), and every failure it reports is compared
   with Step 7's list. Earlier items (TCW-108, TCW-112) changed some passages only enough
   to name no command they removed; whatever they left is Step 7's. The
   check fails only on a `tcw` code span, so prose that says a removed
   option works (such as "file it with `--project`") is found by a grep as
   well: `grep -rn -- "--project\b\|--blocks\b" README.md docs/guide
   docs/use-cases.md skills tcw/work/prompts tcw/work/procedures
   docs/capabilities`, each line compared with Step 7's list. At planning
   time it finds, besides the check's own failures,
   `docs/guide/multi-repo.md:179`, `docs/use-cases.md:216`,
   `docs/guide/work.md:332`, `README.md:608` and the ledger records that
   Step 7 and Step 22 change.
8. **The callers of `read_only_reason`,** as TCW-108 left them: at
   `965f2bff` they are `_check_declared` (`tcw/work/open.py:134`),
   `_connected_declarations` (`tcw/cli.py:222`, provisioning), the interface
   method (`tcw/store/base.py:223`) and `_validate_upstreams`
   (`tcw/store/project.py:955`, which TCW-108 removes). Step 7 handles each.
9. **TCW-108 and TCW-111 are past their records gate.** Both declare
   `work/delegate-a-work-item-to-another-project` under `changed`
   (`docs/work/TCW-108-…/capabilities.yaml:15`,
   `docs/work/TCW-111-…/capabilities.yaml:14`). Once Step 7 deletes that
   record, the records gate of an item that has not yet passed it reports
   "declared changed but not in the ledger" (`tcw/work/gates.py:184-185`,
   with `finished=True`), and `tcw validate` would not warn first, since it
   checks an unfinished item with `finished=False` (`tcw/validate.py:528-532`,
   `:603-611`). `tcw work show TCW-108` and `tcw work show TCW-111` must be at
   `completed`; if either is not, that is reported to the dispatching
   session before Step 7, which then waits for it.

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
- **The shared process rule** (choice 11), in the suite: new
  `tests/processes.py` with `allowed_read_only_git(argv)` (the `rev-parse`
  half of `_allowed`, `tests/serve/test_no_process.py:77-91`, taking the
  same `-C <folder>` and other options before the command) and a
  `recorded_processes` fixture that records every `subprocess.run` and
  `subprocess.Popen` call for one test and returns the argument lists.
  `tests/serve/test_no_process.py`'s `_allowed` becomes
  `allowed_read_only_git(argv) or <its status branch>`, and its
  `test_the_git_rule` gains rows for the shared function. Tests first: the
  shared function's own rows (accepts `git -C /x rev-parse
  --show-toplevel`, refuses `git status`, `git -C /x add .`, `git commit`).

**Proves it:** the four scratchpad files exist; `tests/processes.py`'s rows
and `tests/serve/test_no_process.py` pass; the suite's outcomes are
otherwise unchanged.

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
- Unknown (nothing names `core`): exit 3, `is not on this machine`. A graph
  problem (two folders beside `app` both declaring `core`): exit 3,
  `belongs to project 'core'; project 'core' cannot be located: ` followed
  by the `ProjectGraphError`'s own message (Design 1.3, review S11). In
  every case the error is `Refused`, never `Unreachable`, `UnknownProject`
  or `ProjectGraphError`: locating never changes the exit.
- `check_owned` opens no backend and no store of the owner's: with
  `tcw.work.open.open_project` and `FsTreeStore.__init__` patched to fail,
  every case above gives the same answer.
- With `hint="; or override it …"`, the hint ends the message.

**Creates** `tcw/ownership.py`: `check_owned(full_id, active_root, *,
reason=None, hint=None) -> None`. It compares `full_id.project` with the
active project's ID (read from the `Locator`'s registry, `current.id`); on a
match it returns. Otherwise it asks `Locator.of(active_root).owner_root(
full_id.project, named_by=active_root)` inside a `try`, with both the
`Locator.of(...)` call and `owner_root` inside it: a returned folder
gives the `tcw -C <folder>` tail. The `except` clauses come in this order,
because in TCW-107's plan `UnknownProject` is a subclass of
`ProjectGraphError` (`UnknownProject(ProjectGraphError)`), so a clause for
`ProjectGraphError` placed first would also catch an unknown project:
first `UnknownProject` and `Unreachable`, which give "not on this machine",
reading the repository as Step 0 item 5 found; then `ProjectGraphError`,
which gives the "cannot be located: <its message>" tail; then every other
`TcwError`, which gives "not on this machine". Step 0 item 3 confirms the
class order TCW-107 landed. Then it raises `Refused` with Design
1.3's text. It writes nothing and reads no file of the owner's.

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
  row is `xfail(strict=True)`, reason "tcw work move arrives in Step 18",
  until Step 18 adds the command and removes the mark. The
  not-on-this-machine, unknown and graph-problem variants as AC 1 states
  them, each also with `tcw.work.open.open_project` patched to fail if
  called: the check comes before the lookup (review M4).
- AC 2: `app` with parent `core` passing taxonomy and capabilities.
  `tcw taxonomy rm core.taxonomy/t`, `tcw capabilities rm
  core.capabilities/cli/x` exit 3 naming core's folder; the `rename` and
  `move` rows marked `xfail(strict=True)` until Step 19 adds those
  commands. `tcw capabilities
  set core.capabilities/cli/x --status Supported` exits 0, writes `app`'s own
  `cli/x` and leaves `core`'s files unchanged. In `other` (no parent),
  the same `set` exits 3 with `belongs to project 'core', and 'other' does
  not inherit it, so it cannot be overridden here; run the command there:
  tcw -C`. Neither message contains `change it in`. With `core`'s folder
  removed and its manifest entry kept, `tcw capabilities rm
  core.capabilities/cli/x` and `tcw taxonomy rm core.taxonomy/t` exit 3 and
  say `is not on this machine` (review M4: before this change they would
  exit 4 or 5 from `find_tree`), while `tcw capabilities set
  core.capabilities/cli/x --status Supported` exits 7 in `app`, since
  `core` is one of `app`'s sources and deciding that it is an override
  needs `core`'s content (spec 1.5, TCW-112), and exits 3 in `other`,
  where `core` is no source and is refused before anything is read
  (TCW-112's order, step 2 of `override_target`).
- AC 3: `workspace` and `app`, `app` with `work.path:
  tcw://workspace.path/docs/app/work`. In `workspace`, `comment`, `edit
  --priority low` and `advance` of `app.work/<a>` exit 3 naming `app`'s
  folder, and nothing under `<workspace>/docs/app/work` changes. The `-C`
  half of AC 3 is in Step 6.
- TCW-112's two message tests (Step 0 item 3 names them) change to Design
  1.3's text; each failure is read before its assertion is changed.

**Changes**

- `tcw/work/cli.py`: `_own` (`:69-74`) is removed; `resolve_item`
  (`:50-66`) gains `writing: bool = False`. When true, before anything
  else is opened for the text, it sorts the text with `sort_input(arg,
  "work", KEY)` (TCW-110 Step 1) and, for form `a` (a full identifier) or
  form `c` (`<project>.work/<KEY>`), calls `check_owned(<that project's
  identifier for the text>, root)`; only then does it call
  `resolve_work_input`, which for another project would open that
  project's backend (`open_project`, `tcw/work/open.py:86-97`, exit 4 or 5).
  Forms `b` and `d` name the active project's own items and are looked up
  there; nothing of another project is reached. Every writer passes
  `writing=True`: `_edit` (`:328-361`), `_move` (the advance helper,
  `:364-371`), `_discard` (`:389-394`), `_comment` (`:397-403`),
  `_rename` (`:406-410`). `_new` (`:186-232`) and `_tickets_adopt`
  (`:427-433`) make no call (spec 1.2: creators; choice 2).
- `tcw/locate.py` and the tree stores, as TCW-112's revised plan leaves
  them (its choice 9): `find_tree_writable(store, namespace, text, *,
  removing: bool) -> FullId` sorts the text and calls the store's
  `removal_target` (for `rm`, and for Step 19's `rename` and `move`) or
  `override_target` (for `set` and `reset`); it refuses nothing itself,
  and always returns the active project's own full identifier, so a
  `check_owned` placed after it would always pass. The two refusals of
  another project's object live only in those two methods, and this step
  replaces each with a call of `check_owned`:
  - `removal_target`: for a full identifier naming another project, it
    refuses at once, before any view or store is read (TCW-112 choice 9),
    now with `check_owned(<that identifier>, active_root)` (no reason); for
    an id-path the view shows as another project's, `check_owned` of the
    object the view shows. So `rm core.capabilities/cli/x` exits 3 whether
    or not `core` is on this machine (review M4).
  - `override_target`, which decides in TCW-112's order (its handoff to
    this item, "plan, final"): (1) the active project's own full
    identifier gives its own object, or `NotFound` (exit 4) when it has
    none there; (2) a project that is not one of the active project's
    sources for the namespace (`source_entries`) is refused before
    anything is read, exit 3 even with an ancestor missing; (3) an id-path
    with an own object needs no view; (4) otherwise the view decides: a
    source's identifier not in the id-path's `chain()` is refused, and with
    a source missing that is TCW-108's exit 7, not a refusal (spec 1.1,
    1.5). The refusals of (2) and (4) become `check_owned(<identifier>,
    active_root, reason=", and '<active>' does not inherit it, so it
    cannot be overridden here")`, each in its own branch, so the order is
    kept; nothing else moves.
  - `find_tree_writable`'s `removing` keyword has no default after TCW-112
    (`find_tree_writable(store, namespace, text, *, removing: bool)`);
    every call this item adds or changes passes it.

  If the landed code differs from TCW-112's plan (Step 0 item 3), the rule
  that decides is spec 1.1: the refusal for a full identifier naming
  another project comes before that project is read, and one function
  words it.
- `tcw/taxonomy/cli.py` `_rm` and `tcw/capabilities/cli.py` `_set`
  (`:119`), `_reset` (`:127`), `_rm` (`:137`) reach the check through
  `find_tree_writable` (`removing=True` for `rm`, as TCW-112 leaves it). The `add`
  commands (`tcw/taxonomy/cli.py:100`, `tcw/capabilities/cli.py:91`) take an
  id-path in the active project's own store and make no call (spec 1.2).

**Proves it:** the tests above; `tests/test_capabilities_federation.py` and
TCW-112's override tests, unchanged except the two messages; the full suite.

## Step 4 — the web router makes the check

**Tests first**, new `tests/serve/test_route_writes.py` (AC 4, the server
half):

- Reading `tcw.serve.server._routes()`: the routes whose `writes` is not
  `None` are exactly Design 1.2's web column and its four web creators,
  and each creator's `writes` answers `[]` for any request (spec 1.2: the
  router makes no call for it): `POST /api/work`, `PATCH
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
  write whose function sorts the key with `sort_input`: a full identifier
  is answered as it is, without reading any store, so the check comes
  before the lookup (spec 1.1, review M4); an id-path is resolved with
  `find_tree` in the served project's view (as TCW-110 Step 8 makes the
  route key do) and its full identifier answered; for a
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
- The process rule of AC 9 (choice 11): every command of this list, run
  under `recorded_processes` (`tests/processes.py`), starts only processes
  that `allowed_read_only_git` accepts. The rule is not "none": building
  the registry that an address's lookup needs runs TCW-107's worktree
  probe (`git rev-parse`) for each folder not yet probed in the process
  (`_ANCHOR_CACHE`, `tcw/store/project.py:64`), so whether `_enter` itself
  starts one depends on what ran before it. The test therefore clears
  `_ANCHOR_CACHE` before each command, so that the probe runs and the rule
  is checked against it, rather than passing by accident.
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
  <target> work new --no-such-flag` (the `--project` rejection case needs
  the option hidden, so it is in Step 7, review M1);
  `test_shipped_text.command_problem` accepts `tcw -C tcw://<id>.path/ work
  new "<title>" --parent <slug> --nest`; `tests/test_docs_describe_3_0.py`
  `command_problems` likewise.

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
  reading the group, skip each `-C <target>` pair after `tcw`. The target
  is exactly one whitespace-separated token, so the check stays strict: a
  document must write a one-token placeholder (`<folder>`,
  `tcw://<id>.path/`), and one written as a phrase (`<its folder>`) fails,
  as Step 7's rows show.

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
- `test_documented_cli_surface._check` rejects `tcw -C <target> work new
  --project x` (moved here from Step 6, review M1).
- `_check` accepts, with both options hidden, each `tcw` span of the
  replacement texts below, as rows of one parametrized test:
  `tcw -C <folder> work new --parent`, `tcw -C <folder> work new "<title>"
  --parent <slug>`, `tcw -C <folder> work new "<title>" --parent <full
  id>`, `tcw -C <folder>`, `tcw -C tcw://<parent>.path/ work new
  "capability wording: <name>"` and `tcw -C tcw://<id>.path/ work new
  "<title>" --parent <slug>`. And it rejects the two forms the rules below
  forbid, so that the rows prove the rules: `tcw -C <its folder> work new
  --parent` ("no such flag: --parent on tcw") and `tcw -C <its folder or
  tcw://<id>.path/> work new "<title>" --parent <slug>` ("no such verb: tcw
  folder").
- `tests/test_documented_cli_surface.py` as a whole passes with both options
  hidden: no live document writes either one in a `tcw` command (AC 23's
  last sentence, choice 13).
- `docs/capabilities/work/delegate-a-work-item-to-another-project/` does not
  exist, and `tcw validate` (the lifecycle `tcw`, which reads this
  repository's 3.x ledger) reports no dangling `tcw://` link in the four
  records that linked to it.
- `tests/test_shipped_prompts.py` and `tests/test_shipped_text.py`: the plan
  stage prompt and `tcw work procedure audit-backlog` contain no
  `--project`; the prompt's step 6 names `tcw -C tcw://<id>.path/ work new`.
  `test_plan_says_how_to_file_a_part_into_another_project` (`:331-341`) and
  the accepted-commands list of `tests/test_shipped_text.py` (`:336-339`)
  change here, not in Step 20; Step 20 checks the paragraph's final form.
- `tests/test_provision*.py`: their outcomes are unchanged by the renamed
  provisioning predicate (no test is added; the comparison below shows it).

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
  `tcw://<id>.path/`, with every error of the lookup caught, so it never
  changes exit 2 (spec 2.2); for this project no `-C`. A test of each:
  `<b>` in a project not on this machine still exits 2, naming
  `tcw://<id>.path/`.
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
- TCW-108's interim rule (Design 1.8): its write refusal goes with
  `_check_declared` (above), and the `read-only` field of `tcw projects
  list --json` (`tcw/projects_cli.py`, TCW-108 Step 12) is removed, with
  whatever only they use. `read_only_reason` itself has one caller left
  that is not about writing, provisioning's `_connected_declarations`
  (`tcw/cli.py:222`, Step 0 item 8): it is renamed
  `reached_by_both_sides(project_id) -> bool` (true where
  `read_only_reason` returned `None`), in `tcw/store/project.py` and the
  interface (`tcw/store/base.py:223`), with its body and that caller's
  behaviour unchanged (spec 1.8). Its own tests (TCW-108's Design 7.1
  cases) are renamed with it and listed in `allowed-step7.txt` under their
  old IDs; their assertions change only from "reason is None" to "true".
- **The documents** (choice 13, spec 9.5). Each passage below, as Step 0
  item 7 found it again, is changed only as far as naming a working
  command, and nothing else in its file. **Two rules for every replacement
  text**, because `_check` (`tests/test_documented_cli_surface.py:197-219`)
  splits a span on whitespace and Step 6's skip takes exactly one token as
  the `-C` target: (1) the target is always one token, `<folder>` or
  `tcw://<id>.path/`, never a phrase such as `<its folder>`, whose second
  word would be read as a verb or end the command path, so that `--parent`
  is checked against `tcw` itself; (2) a removed option is named only
  outside a `tcw …` code span (as "the `--project` option of `tcw work
  new`"), since any `tcw` span containing it fails once it is hidden. Where
  a sentence needs to say what `<folder>` is, it says so in prose after the
  span. The texts:
  - `skills/work/SKILL.md:4` (the `when_to_use` line): "file work into
    another project (`tcw work new --project`)" becomes "make a part in
    another project (`tcw -C <folder> work new --parent`)";
  - `skills/work/SKILL.md:93-100` (the "Delegation is filing into another
    project" bullet) becomes "**A part for another project is made in that
    project**, with `tcw -C <folder> work new "<title>" --parent <full id>`,
    where `<folder>` is that project's folder or `tcw://<id>.path/`;
    `tcw projects list` names the projects this one declares under
    `projects:` (the configure skill's reference on projects explains the
    key). The plan prompt's step 6 gives the order for an epic's parts." The
    sentences about setting the parent afterwards, uncommitted changes and a
    printed ticket key are dropped, since they describe the removed option;
  - `skills/work/SKILL.md:107-110` (the bullet starting "`tcw work new
    --project` into a project nothing declares exits 3") becomes "- The
    `--project` option of `tcw work new` and the `--blocks` option of
    `tcw work edit` are removed in TCW 4: each exits 2 and names the command
    to run instead.";
  - `skills/work/SKILL.md:111-112` (the bullet starting "Filing into an
    upstream project") becomes "- A change to another project's item, term
    or capability exits 3 and names its folder: run it there, with
    `tcw -C <folder>`.";
  - `skills/work/references/commands.md:11`: the row becomes "| a part for
    another project | `tcw -C <folder> work new "<title>" --parent <slug>`,
    where `<folder>` is its folder or `tcw://<id>.path/` |"; and `:19`:
    `[--blocks <slug>]` is dropped from the `edit` row;
  - `skills/capabilities/SKILL.md:153` and `:181` (`tcw -C
    tcw://<parent>.path/ work new "capability wording: <name>"`);
  - `skills/configure/references/projects.md:170` and `:199`;
  - `docs/guide/cli.md:150`, `docs/guide/jira.md:235`,
    `docs/guide/multi-repo.md:141` and `:187`, `docs/guide/work.md:332` and
    `:351`, and `README.md:608` (the last three name the removed options in
    prose or a table cell outside a `tcw` command, so the check does not
    fail on them; they are changed because they say a removed option works,
    one cell or sentence each);
  - `docs/guide/multi-repo.md:179-184`, prose that the check does not fail
    on (no `tcw` in its span) but which says the removed option works: the
    paragraph "To file an epic's part into another project, file it with
    `--project`. …" becomes "An epic's part in another project is made in
    that project, with `tcw -C <folder> work new "<title>" --parent <full
    id>`; the `--project` option that filed it from here is removed in 4.0.";
  - `docs/use-cases.md:161`, which states a requirement: "(including `tcw
    work new --project` and `tcw work edit --blocks`)" becomes "(in 3.x,
    also through the `--project` option of `tcw work new` and the
    `--blocks` option of `tcw work edit`, both removed in 4.0)";
  - `docs/use-cases.md:213-216`: "Filing a part into a child is a
    cross-project filing (`tcw work new --project`). It refuses every
    property flag except `--priority`, so the parent is set afterwards with
    `tcw work edit` from inside the child (`tcw/work/cli.py`, the
    `--project` checks; the plan prompt's step 6)." becomes "In 3.x, filing
    a part into a child went through the `--project` option of `tcw work
    new`, which is removed in 4.0; a part is made in the child, with
    `tcw -C <folder> work new "<title>" --parent <full id>` (the plan
    prompt's step 6)." The rest of each requirement stays for TCW-117 to
    rewrite;
  - this repository's ledger, in its 3.x form: `docs/capabilities/skills/work/description.md:3`
    (its last clause becomes "a part for another project is made there,
    through `tcw -C`"; `skills/work` is declared changed in
    `capabilities.yaml`), and `docs/capabilities/cli/read-from-an-upstream-project/description.md:16`
    if TCW-108 has not already removed that record (its `capabilities.yaml`
    removes it);
  - the removed capability's record,
    `docs/capabilities/work/delegate-a-work-item-to-another-project/`, is
    deleted once Step 0 item 9 has found TCW-108 and TCW-111 completed (a removed capability is deleted from the ledger,
    `tcw/work/gates.py:172`), and the four records that link to it lose
    the link, each with the sentence around it changed only as far as the
    link: `docs/capabilities/cli/list-connected-projects/description.md:20`,
    `docs/capabilities/work/open-a-work-item/description.md:5`,
    `docs/capabilities/work/manage-blocking-relations/description.md:1`,
    `docs/capabilities/work/manage-the-work-inbox/description.md:5`. Step
    22 writes the rest of those records' changes;
  - the shipped text: `tcw/work/prompts/plan.md:40`, the sentence naming
    `tcw work new "<title>" --project <id>` and the two sentences after it
    (a ticket key printed instead of a slug; setting `--parent` from inside
    the other project; recording uncommitted changes), replaced by "A part
    for another project is made in that project: `tcw -C tcw://<id>.path/
    work new "<title>" --parent <slug>`"; and
    `tcw/work/procedures/audit-backlog.md:28`, Design 9.2's sentence. Step
    20 completes the prompt's paragraph; `tests/fixtures/prompt_fallback/unconfigured.json`
    is regenerated here and again there.

  Each one is listed, with what it now says, in the implement round, which
  is the list TCW-117's handoff names.
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
finds nothing; `tests/test_documented_cli_surface.py` passes; the lifecycle
`tcw validate` passes; the full suite.

## Step 8 — the web client: no project selector, no "Blocks (add)", no `readOnly`

**Tests first** (AC 4's client half):

- `web/client/src/ui/work-forms.test.tsx`: the create form shows no
  "Project" selector; the two `Blocks (add)` tests (`:192-230`, `:529-545`)
  are removed. `web/client/src/ui/app.test.tsx` (`:234-260`): the item page
  has no `Blocks (add)` combobox in either mode, and still lists the item's
  `blocks` (the data of `work-views.test.tsx:38`).
- A Jira-mode create form and edit form accept a blocker in another project
  with the other-project warning, as they accept a parent today (Design 3.3:
  the backend now records it; spec 2.3).

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
  field. (The rename half of each row is added once rename exists: Step 17
  for the work-item rows, Step 19 for the others; the same fixtures, the
  named object renamed, the value rewritten.)
- A test that adds a row to `FIELDS` (monkeypatched) naming a field
  `Reviewed by` of a capability fixture: `tcw validate` reports a dangling
  value in it, with no other change. (Its rename half is in Step 19.)

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
`links_outside_code`; `_strip_code` (`:70-72`), then uncalled, is removed. `tcw/rewrite.py` (Step 16) uses the same two
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
- AC 7, the exit 7 bullet: a fourth project `inh` in Jira mode whose
  `work.jira` comes from a parent not on this machine (TCW-109's fixture
  for its AC 14); `tcw work new 'z' --parent inh.work/<IK>-…` in `app`
  exits 7 with TCW-109's message, and the fake records no request.
- AC 7, the site's letter case: a project `caps` whose `work.jira.site` is
  site A's URL with the host in capital letters; a parent naming one of its
  tickets is a Jira link, and the state file holds no `parent`. A unit row
  of `_same_site`: `https://acme.atlassian.net` and
  `https://ACME.atlassian.net` are one site; `https://acme.atlassian.net`
  and `https://acme2.atlassian.net` are two.
- AC 7, the web bullet (`tests/serve/test_work_write.py`, Jira mode): `POST
  /api/work` with `parent: files.work/<f>` answers success and its
  `warnings` hold one entry whose message contains `Jira shows no link for
  it`; `PATCH /api/work/<item>` setting such a parent the same (review S4).
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
    the owner's configuration, read as a project read for itself,
    `load_config(owner_root, personal=False, registry=<the command's
    registry>)` (TCW-109 plan, choice 3; not TCW-110 Step 13's
    `load_config(root / SENTINEL)`, which reads the raw file and so would
    miss an inherited site, review S5), gives its backend and site; an
    `InheritedUnavailable` from it (an undecided `work.jira`) propagates
    (exit 7, nothing written); a Jira owner whose site is this site by
    `_same_site(a, b)` (the hosts compared ignoring letter case, the scheme
    and path as they are, which TCW's site check already makes `https`
    with none) → `Linked(<key of its folder>)`; anything else →
    `Recorded(<full id>)`. The message `Jira links only tickets on one
    site` is removed.
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
- The note for each recorded value is given to the caller, not only
  printed: the backend's `create` and `update` call their `report` with it
  (as today's reports go), and `tcw/serve/work.py` `create` and `edit` open
  the backend with a `report` that collects lines into the answer's
  `warnings` (`{"severity": "warning", "where": "parent" | "blocked-by",
  "message": <the sentence>}`, the shape `checked_reference` uses,
  `:365-376`) instead of the server's standard error
  (`tcw/serve/services.py:20-26`): every line the backend reports while
  that one request runs is collected (today those are also lines a person
  using the page never sees, such as `not nested:`), with `where` set from
  the field the sentence names, or `null`. Other routes keep reporting to
  standard error.

**Proves it:** the tests above; `tests/work/jira/test_jira_write.py`,
`test_jira_guards.py`, `tests/serve/test_work_write.py`; the full suite.

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
  (Step 9's fixtures) except the work-item state files' rows, each value
  equal to an old identifier is replaced; a work item's state file whose
  `parent` names an old identifier is left byte for byte, since the
  backend rewrites it (choice 12), and is not reported as done;
  `!` kept on `Roles` and `When`; every other byte of each file unchanged
  (the test compares each file to its expected text exactly); a value
  equal to `demo.work/2026-10-22-old-two` is left when `…-old` changes
  (Design 6.2); a link inside a fenced block or inline code is left; a
  link keeps its text and everything around the address.
- **By field, not by value** (choice 6, review M2): in the same fixture, a
  capability whose `name` is the text `demo.capabilities/cli/x`, a
  free-text field of a term holding `demo.taxonomy/invoice`, and a key of
  an item's `capabilities.yaml` outside its lists (`notes:
  demo.capabilities/cli/x`) each keep their value byte for byte, and
  `mentions` reports each as `names <old>, not rewritten`.
- `rewrite_yaml(text, fields, changes)` on its own: a value in a flow
  sequence (`[a, b]`), a block sequence, a quoted and an unquoted scalar,
  a `!`-prefixed scalar under `Roles`, and a nested key (`taxonomy:
  {changed: [...]}`); each comes back with only the value's characters
  changed and its quoting kept. A value under a key not in `fields` is
  never changed, even when it equals an old identifier.
- It returns, per file, the fields and links changed, and separately the
  ones that already named a new identifier (counted as done by an earlier
  run, Design 5.8).
- Running it twice changes nothing the second time and reports everything
  as already done.
- A file that cannot be written: it raises `OSError` carrying the files
  written so far (for the stop message). Each file is written with
  `_atomic_write_all` (spec 6.6): with the promote of the second of two
  files made to fail, the first file holds its new text, the second its
  old text whole, and no temporary file is left beside either.
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

**Creates** `tcw/rewrite.py`, with those four functions and
`rewrite_yaml`. It reads the active project's three stores (their roots
from the store locations): the taxonomy and capabilities records with
`walk` and `read_state` (TCW-111), each item's `capabilities.yaml`
(`parse_declarations`), and every `.md` file under the three stores,
`resources/` included, for links (`links_outside_code`, Step 11). **The
work store is read only for its Markdown files' links and its
`capabilities.yaml` files**, never for the items' state files: those
belong to the backend (spec 6.1), and the files backend rewrites them
itself before it calls `before_folder` (choice 12). Reading them here too
would read each work-item field twice, and the second read would report
it as "already done" in the stop message. YAML
values are replaced by position, at the fields `FIELDS` names (choice 6).
Each file is written with `_atomic_write_all` (`tcw/store/fs.py:1149`),
never with a plain `write_text`. It never reads outside the three stores,
nor another project's files (Design 6.5). Configuration files are not
read: Step 21's sweep confirms no configuration key holds an object
reference.

`tests/test_object_folder_sweep.py` (TCW-111 Step 17, its AC 21) allows only
listed calls of `.iterdir()`, `.rglob(`, `.glob(`, `os.listdir(`,
`os.scandir(` and `os.walk(`. The listing of every `.md` file under a
store, for links and mentions, is one such call in `tcw/rewrite.py`; it is
added to that allowlist with its reason ("every file's text, for links and
mentions, not objects"), the reason `report_mentions`' entry
(`tcw/work/fs_backend.py:214`) gives today. `report_mentions`' entry is
removed in Step 17, when it is.

**Mutation check** (review M2, the rewrite half Step 10's lacked): with a
one-off plugin in the scratchpad removing the `Roles` row from `FIELDS`,
the `Roles` cases of `tests/test_rewrite.py` go red, and the failure is
read and confirmed to be the `Roles` value left unrewritten (and listed as
a mention), not some other error. The same with the `taxonomy.changed`
row removed, for a `capabilities.yaml` case.

**Proves it:** `tests/test_rewrite.py`; the mutation check; the full suite.

## Step 17 — the backend operation `move`, in both backends, and `tcw work rename` through it

The interface, both backends and every caller change in this one step
(review M3): splitting them left a Jira body at the step boundary that took
the new signature but kept today's body, which could not say what to do
with a destination, called `report_mentions` a second time, and did not
call `before_folder`. The new command, `tcw work move`, comes in Step 18,
so this step changes only how `tcw work rename` works.

**Tests first**, new `tests/work/test_move.py` (files: AC 11, AC 18 files,
AC 25's rename half) and `tests/work/jira/test_jira_move.py` (Jira: AC 12,
AC 18 Jira), and new rows in `tests/work/test_backend_contract.py`:

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
  rewritten, `the folder is still at` and `run the same command again`, the
  epic's folder still at the old place; writable again, the same command
  exits 0, prints the three lines, and every file is as after the first
  clean run.
- AC 12, the clean run (Jira): epic `EK` holding `PK` holding `QK`, each
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
  PK`.
- AC 12, two runs at once (review S3): `before_request` changes `EK`'s
  `TCW Item` to another value when the fake is about to answer the `GET`
  of `EK` that comes just before `EK`'s edit (not on the `PUT`, by which
  time the run has read the old value and would edit). Exit 3, no edit,
  `R` and the folder unchanged, and the message names `EK`, its new value,
  `another command may be moving this item` and `tcw validate --remote`
  and does not contain `run the same command again` (review S2). The same
  with `PK`'s value changed on the `GET` before `PK`'s edit: exit 3, the
  message names `EK` as set by this run, contains `pull its commit`,
  `tcw validate --remote` and `in Jira set each ticket it reports to the
  identifier its folder now has`, and does not contain `run the same
  command again`.
- The second way out of that stop (AC 12): the fake and the fixture are
  put in the state the clash leaves once the other command has finished
  (`EK` holding this run's new identifier, `PK` and `QK` the other
  command's, the epic's folder at the other command's place, `R`'s link
  naming it). `tcw work rename <the other place> <this run's words>` exits
  0; the fake records edits of `PK` and `QK` only (`EK` counted as done);
  every `TCW Item`, `R`'s link and the folder name this run's identifiers.
- The folder already gone (review S2's second point): the test removes the
  epic's folder in a `before_folder` spy, after the tickets are set; exit
  4, and the message says `is no longer at`, not `still at`, and names
  `tcw validate --remote`.
- A ticket gone between the search and its edit (`hide` from
  `before_request`, on the `GET` before its edit): exit 4, with 5.8's
  message.
- The connection dropping after the first edit
  (`drop_after_next_write(then_unreachable=True)`): exit 5, the message
  names `EK` as set; a healthy re-run finishes with edits of `PK` and `QK`
  only.
- The search is paged (review S13): with the fake's `page_size` set to 2
  (`tests/work/jira/fake.py:166`, which its search endpoint already honours,
  `:475-482`), an epic holding four nested items is read in three pages
  through the client's paged `search` (`tcw/work/jira/client.py:242-267`)
  and all five tickets are edited.
- The error class and name are kept (choice 8): a stop raised from a
  `NotFound` exits 4, from `Refused` 3, from `Unreachable` 5; a `TcwError`
  with `name` set keeps it.
- AC 18 (files and Jira): an epic holding a part whose full identifier is
  250 characters; a rename making it 256 exits 2 naming the part's new
  identifier and 255, and moves nothing; the fake records no request after
  the search. A rename whose words make only the epic's own identifier too
  long is refused the same way, never shortened (review S8: `fitted_words`
  is not used for a rename).
- The renamed item's own `id`; a case-only rename refused with `already
  exists`; a rename to the same name refused with `already has that name`;
  words that are not a folder name refused with today's `did you mean`
  suggestion; a files rename given `<other date>-<words>` refused with
  today's `a rename keeps the date` message, and a Jira one given another
  key with `a rename keeps the key` (both messages now come from
  `tcw/move.py`, review S8).
- AC 25 (the rename half): with a `post` hook and a `pre` check bound to
  every stage, `tcw work rename` exits 0, runs no hook or check, and starts
  only processes `allowed_read_only_git` accepts (choice 11).
- AC 26's rename half for the `work-item` rows (Step 10), and the files
  backend reading `fields_of("work-item")` (choice 12, review S9): with a
  row `work-item` `reviewed-by` added to `FIELDS` (monkeypatched) and an
  item's state file holding `reviewed-by: <P's id>`, the rename rewrites it.
- The backend contract (`tests/work/test_backend_contract.py`, both the
  files backend and the memory backend): `move(id_path, new_id_path,
  before_folder)` returns the pairs, the item first, then the nested ones
  in the walk's order; calls `before_folder` exactly once, after its own
  writes and before the folder moves; refuses a new last part that does
  not keep the old date or key (`UsageError`).
- **Every stop** (`tests/move_stops.py`, choice 10), for `tcw work rename
  <epic> new-words` in AC 11's fixture and for the same rename in AC 12's
  Jira fixture: each counted write of a clean run in turn fails (a state
  file write, a repository file write, a Jira edit, the folder's
  `os.rename`); each stop exits with its class's code and nothing on
  standard output, says where the folder is and `run the same command
  again`, and names every ticket set and file written so far, including on
  a second stop those the first run wrote; the healthy re-run exits 0 and
  the result (the tree, and the fake's tickets) equals the clean run's
  byte for byte. Every path and ticket that changed in the clean run is
  explained by a counted write. A failure in the tidy step (`rmdir`
  patched to fail) exits 0 with a warning, and the move stands. No ticket
  is ever set back: in every run, the fake records no edit that writes an
  old value.

**Changes**

- `tcw/work/backend.py` (`:69-113`): `rename(self, folder, title_words)`
  (`:95`) becomes `move(self, id_path, new_id_path, before_folder) ->
  list[tuple[FullId, FullId]]`; the docstring keeps "Twelve operations".
  Each backend checks that the last part of `new_id_path` keeps the old
  one's date or key (`UsageError` otherwise, spec 7.1); it does not build
  the name.
- `tcw/work/fs_backend.py` `rename` (`:424-477`) becomes `move`, in Design
  5.8's order: every item's state file read (`read_all`, `:193`; today's
  check `:443-447`); in every item's state file, the fields
  `fields_of("work-item")` names (today `parent` and `blocked-by`) naming a
  changed identifier rewritten with `rewrite_yaml` (choice 12), and a
  renamed item's own `id` (Design 5.2), each written with `_replace_file`
  (`:187`), skipping a value that already names the new identifier;
  `before_folder()`; then `move_object_folder` (choice 7), the last write.
  The `report_mentions` call and the "other projects" line (`:474-476`)
  go: `tcw/move.py` prints them. TCW-111's refusal of an item with nested
  items goes. Returns the pairs, the item first, then `objects_below` in
  the walk's order.
- `tcw/work/jira/backend.py` `rename` (`:870-909`) becomes `move`: the
  moved keys are the item's and `objects_below`'s (`folder_key` of each,
  `:98-101`); **read**: one search by key, paged as `resolve_keys`
  (`:391-…`) pages, reading `TCW Item`, sorting each into to-be-set, done,
  3.x (refused, naming every such key and `run 'tcw migrate' in this
  project first`), other (refused, naming key, value and `tcw validate
  --remote`) and missing (`NotFound`, today's `_issue` message,
  `:344-350`); **set**: for each to-be-set key in order, `_issue` reading
  `TCW Item` again, then the edit only if it still holds the old value,
  done if it holds the new one, else `Refused` (or `NotFound`) with
  Design 7.3's sentence and a marker that this is the clash with another
  command (choice 8 chooses the advice by it); then the renamed item's own
  `id` in its state file; then `before_folder()`; then
  `move_object_folder`. The set-back (`:894-904`) and the `report_mentions`
  call are removed.
- `report_mentions` (`tcw/work/fs_backend.py:211-223`) is removed, with its
  entry in `tests/test_object_folder_sweep.py`'s allowlist (Step 16).
- `tcw/object_folders.py`: `move_object_folder(store_root, old_path,
  new_path) -> created` (choice 7): creates each missing folder of the
  destination in order, remembering each one it created; then the one
  `os.rename`; when any of these fails, it removes, deepest first, each
  folder it created that is still empty, then raises. So a second `mkdir`
  that fails after a first that succeeded leaves neither (review S1 b);
  Step 18's every-stop run exercises it. An `os.rename` failing with
  `FileNotFoundError` for the source is raised as `NotFound` (choice 8).
- **Creates** `tcw/move.py`: `move_object(namespace, source_text, *,
  new_name=None, into=None, top=False, root) -> int`, which runs Design
  5.4 a to h in order:
  - a: `resolve_item(..., writing=True)` for work, `find_tree_writable(...,
    removing=True)` for the trees (Step 3: the check before the lookup); 5.5's
    grammar-breaking source accepted when the walk lists exactly that
    folder;
  - b: the new name (review S8). For work, `tcw/move.py` builds the new last
    part itself: `item_prefix(last_part)` (new, in `tcw/work/model.py`)
    gives the old part's `DATED` date or `KEY_FOLDER` key, whichever it
    starts with; given words that start with a date or key, that prefix
    must match (today's two messages, moved from `fs_backend.py:427-433`
    and `jira/backend.py:873-877`); the words must match `WORDS` (today's
    `did you mean …?` message, moved from `:434-436` and `:878-880`);
    the result is `<prefix>-<words>`. Its length is checked in d, never
    shortened (`fitted_words` is for titles; a rename's words are given
    explicitly). For a tree, the name is one id-part and not reserved.
    For `move`, the destination rules of 5.3 (Step 18);
  - c: no entry of the destination folder with the same name ignoring
    letter case, and not the same identifier;
  - d: `length_problem` (TCW-111, `tcw/ids.py`) of every changed
    identifier, nested ones included, a `UsageError` naming the longest;
  - e: `unreadable_records`; f: `field_problems`; g: Step 19; h: the
    Jira backend's own read, inside its `move`.

  Then the backend's or store's `move` with `before_folder = lambda:
  rewrite_references(root, changes)`, then the tidy step (empty folders
  above the old place removed and named; `mentions`; TCW-111's
  `disagreement` warning for each moved object whose folder parent is not
  its `parent`), then the output (5.6) through `print_json` for `--json`.
  A `TcwError` or `OSError` from step 2 is re-raised with the stop message
  (choice 8). Before any of that it records which counted writes it has
  done, through what the backend's and the rewrite's errors carry (each
  carries the tickets set or files written so far), so the stop message
  can name them.
- `tcw/work/cli.py`: `_rename` (`:406-410`) calls `move_object("work", …,
  new_name=…)`; `rename`'s contract `prints=` says one `<old> -> <new>`
  line per changed identifier (Design 9.4).
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
  `tcw/move.py` now prints mentions; there they also assert that each
  mention is printed exactly once.
  `test_a_failed_tcw_item_edit_keeps_the_folder`
  (`tests/work/jira/test_jira_write.py:287-292`) still holds and is kept.
- **TCW-111's tests that this step replaces** (review S7): its Step 12's
  AC 16 refusal, `tcw work rename <epic> new-words` exiting 3 "renaming it
  waits for TCW-114", in `tests/work/test_nested_items.py` and in
  `tests/work/jira/test_jira_nested.py`, and its Jira set-back case ("with
  the fake set to fail the folder move, it exits 1 and `TCW Item` is set
  back") in `tests/work/jira/test_jira_nested.py`. The first two are
  replaced by AC 11's and AC 12's clean runs, the third by AC 12's
  `os.rename` bullet. `tests/test_object_folder_sweep.py` is read for any
  text naming the refusal, and changed with it. Each changed or removed
  test ID, here and above, is read before it is changed and listed in
  `allowed-step17.txt` with its design rule (5.8, 7.1).

**Proves it:** the tests above; `compare_outcomes.py` with
`allowed-step17.txt`; the full suite.

## Step 18 — `tcw work move`

**Tests first**, in `tests/work/test_move.py` and
`tests/work/jira/test_jira_move.py` (AC 13 files and Jira, AC 14, AC 25's
move half, AC 1's `move` row):

- AC 13 (files): `move <a> --into <e>`, one line, no folder-and-parent
  warning in `tcw validate`; `move <e>/<a> --top` back; `move <b> --into
  <e>` says `parent: decides` and `<b>`'s `parent` unchanged; `move <b>
  --into 2026/q4` creates `2026/` and `2026/q4/`, moving back with `--top`
  removes both and names them; with `os.rename` patched to fail, `move <b>
  --into 2026/q4` exits 1 and neither folder is left; each of `--into
  <e>/drafts`, `--into <e>/plan`, `--into resources`, `--into <a>` for `<a>`,
  both and neither of `--into` and `--top` exits 2 with nothing changed;
  with a folder named like `<b>` in another letter case inside `<e>`, exit 3.
- AC 13 (Jira): `move <a> --into <e>`: `<a>`'s `TCW Item` is the new
  identifier; `move <b> --into 2026/q4` creates the two organising folders
  in the Jira project's folder store and sets `<b>`'s `TCW Item`.
- AC 14: TCW-111 AC 16a's layout; `move <date>-old-words/<part> --into
  <date>-new-words` exits 0 and removes the emptied `<date>-old-words/`;
  after `edit … --parent <date>-new-words`, `tcw validate` passes.
- AC 1's `move` row loses its `xfail` mark (Step 3).
- AC 25 (the move half): `tcw work move` exits 0, runs no hook or check,
  and starts only processes `allowed_read_only_git` accepts.
- **Every stop** (`tests/move_stops.py`, review S1 b), for `tcw work move
  <b> --into 2026/q4`, files and Jira: the counted writes include the two
  `mkdir`s, so one run fails the second `mkdir` after the first has
  succeeded; that stop leaves no `2026/` (`move_object_folder` removed it),
  and its re-run finishes. Every other write fails in turn as in Step 17.

**Changes**

- `tcw/move.py`: the destination rules of 5.3 (check b for `move`):
  exactly one of `--into` and `--top`; `<P>` parsed as an id-path of the
  active project's store of the namespace, or a full identifier of the
  active project's (another project's is refused by `check_owned`, exit
  3); refused as usage errors when `<P>` is the object or below it, is or
  lies inside a fixed folder or `resources/`, has a missing part that would
  lie inside an object's folder, or has a part that breaks the grammar or
  is reserved. The new id-path is `<P>/<last part>` or `<last part>`.
- `tcw/work/cli.py`: a new `_move_item` (the name `_move` is the advance
  helper, `:364`) calls `move_object` with `into` or `top`; the `move`
  parser beside `rename` (`:805-811`) with a required mutually exclusive
  `--into`/`--top` group (argparse gives exit 2 for both or neither) and
  `--json`; `move`'s contract and examples like its neighbours'.

**Proves it:** the tests above; the full suite.

## Step 19 — the tree stores' `move`, and `rename` and `move` for terms and capabilities

**Tests first**, new `tests/test_tree_move.py` (AC 15, AC 16, AC 17, AC 19,
AC 20, AC 21, AC 25's tree half, AC 2's last rows, AC 26's tree rows):

- AC 15, AC 16, AC 17, AC 19, AC 20, AC 21 exactly as the spec writes
  them, including AC 15's "every other line of each file it rewrote is
  unchanged" (each file compared with its expected text), `tcw taxonomy
  show bill` printing the same `name`, `id: invoice` → `id: bill`, and the
  `os.rename` failure and re-run. AC 17's exit 7 with `core`'s folder
  removed comes from `inherited_at`.
- AC 25 (tree half): `tcw taxonomy rename` and `tcw capabilities move`
  start only processes `allowed_read_only_git` accepts, and no hook or
  check (choice 11).
- AC 2's `tcw taxonomy rename core.taxonomy/t u` and `tcw capabilities move
  core.capabilities/cli/x --top` rows lose their `xfail` mark.
- AC 26: the rename half of every term, capability, `capabilities-yaml` and
  link row, and of the added `Reviewed by` row.
- **Every stop** (`tests/move_stops.py`): for `tcw taxonomy rename invoice
  bill` in AC 15's fixture, and for `tcw capabilities move roles/admin
  --into roles/staff` in AC 16's fixture extended with an item whose
  `capabilities.yaml` names `roles/admin` under `changed` (review S1 c:
  the stops then cover a `capabilities.yaml` rewrite, a `Roles` value
  keeping its `!`, and a created organising folder, `roles/staff/`, inside
  `roles/`, itself an organising folder in that fixture; the move keeps `Roles` naming a `roles/` capability so check f allows it), each
  counted write and the folder's `os.rename` fail in turn; each re-run
  finishes, the result equal to the
  clean run's, and every changed path is explained by a counted write.

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
- `tcw/move.py`: check 5.4 g for taxonomy and capabilities: `inherited_at`
  for the object's own path (not none → refused, naming the inherited
  object) and for each new path (not none → refused); `InheritedUnavailable`
  propagates (exit 7). Check a for the trees is `find_tree_writable(...,
  removing=True)` (Step 3: `removal_target`, which answers only the active
  project's own object), so `rename` and `move` of another project's object
  are refused before its store is read; 5.4 g then refuses an override.
  Reusing `removal_target` also brings TCW-112's rule for `rm`: an id-path
  with no own object, whose inherited view cannot be built, is "not found"
  (exit 4), not exit 7. That is accepted for `rename` and `move` as it is
  for `rm`, and a test row records it (`tcw taxonomy rename <id-path with
  no own object> u` with the parent's folder removed: exit 4).
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
  `test_plan_says_how_to_file_a_part_into_another_project` (`:331-341`),
  which Step 7 already changed to the `tcw -C` sentence, now checks the
  final paragraph's order (`--nest`, `tcw -C`, `--blocked-by`, `records
  it`), and is listed in `allowed-step20.txt` under its old ID if renamed.
- `tcw work procedure audit-backlog` contains `tcw -C` and not `--project`
  (already true from Step 7; kept as AC 23's row).
- `tests/test_docs_describe_3_0.py`: `docs/lifecycle/abstraction.md`'s
  interface list has a **move** entry, no **rename** entry, and not
  `uncommitted changes before creating an item in another project`;
  `test_the_backend_interface_names_exactly_twelve_operations` still passes.
- `tests/test_shipped_text.py`: the accepted-commands list (`:336-339`),
  which lost `'tcw work new "<title>" --project <id>'` in Step 7, gains
  `tcw -C tcw://<id>.path/ work new "<title>" --parent <slug> --nest`.

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
- `tcw/work/procedures/audit-backlog.md:27-29`: Design 9.2's sentence,
  already written in Step 7; read again here as part of the combined
  review below.
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
   the work CLI's six (`edit`, `advance`, `discard`, `comment` and `rename`
   from Step 3, `move` from Step 18), the tree CLI's eight (`taxonomy rm`,
   `capabilities set`, `reset` and `rm` from Step 3; `rename` and `move` in
   both from Step 19), the web's seven write routes that name an existing
   object (Step 4), and every `generate:` binding and hook (none write
   outside the item's folder; each named). Then the creators, listed as
   creators with no call (spec 1.2): `tcw work new`, `tcw work tickets
   adopt`, `tcw taxonomy add`, `tcw capabilities add`, and the web's four
   create routes, each with the reason it writes only the active project's
   store.
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
- Every function under `tcw/` that calls a writer of a backend or a tree
  store is in a list kept in the test, each with either the name of the
  function on its path that calls `check_owned`, or the word `creator` and
  its reason; a new caller fails the test until it is added. Found by an
  `ast` walk, as `tests/test_static_guards.py` walks today. **How a call is
  recognised** (review S6: `add`, `set`, `update`, `remove` and `move` are
  also methods of Python's sets, dicts and lists, and an AST walk sees
  names, not types):
  - the writer names are read from the interfaces, not typed in: every
    method of `WorkBackend` (`tcw/work/backend.py`), `TaxonomyStore` and
    `CapabilitiesStore` (`tcw/store/base.py`) that the interface's
    docstring marks as a write, by a `@writes` decorator (defined in
    `tcw/ownership.py`) added to those abstract methods in this step (the decorator does nothing at run time;
    it is a marker the guard reads, and a writer added to an interface
    later joins the list by carrying it);
  - a call `<r>.<m>(…)` with `m` among those names is a writer call unless
    `r` is provably a builtin container: within the same function, `r` is
    a name last bound from a literal (`set()`, `{}`, `[]`, a comprehension,
    `dict(…)`, `list(…)`, `set(…)`, `defaultdict(…)`) or annotated as
    `set`, `dict`, `list`, `frozenset` or one of `typing`'s equivalents;
  - every other such call, including one whose receiver the guard cannot
    resolve, is a writer call and must be on the list. So an unknown
    receiver is listed, never skipped: the guard can be noisy, and the list
    absorbs the noise with a reason per entry, but it has no hole for a
    real backend reached through an unexpected name.
  The guard's own test: a scratch module calling `seen.add(x)` after
  `seen = set()` is not reported; one calling `backend.remove(x)` after
  `backend = open_backend(root)`, and one calling `thing.move(a, b, f)` with
  `thing` a parameter, are.
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
- The thirteen changed capabilities (the twelve of the first draft and
  `skills/work`): the sentence the spec's "Capability changes" gives each,
  in its `description.md`. Step 7 already changed the sentences of five of
  them (`skills/work`, and the link to the removed record in
  `cli/list-connected-projects`, `work/open-a-work-item`,
  `work/manage-blocking-relations` and `work/manage-the-work-inbox`); this
  step writes the rest of each.
- Removed: `docs/capabilities/work/delegate-a-work-item-to-another-project/`
  was deleted in Step 7. A removed capability is deleted from the ledger,
  not kept with a status: the records gate refuses one "declared removed
  but still in the ledger" (`tcw/work/gates.py:172`), and the ledger has no
  removed status (`CAP_STATUSES`, `tcw/store/base.py:455` at `965f2bff`). The first
  draft's "status set to the 3.x form for a removed capability" was wrong,
  found in this revision. Its replacement is named in the new
  `cli/run-a-command-as-if-started-in-another-folder` record's description
  instead.
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
  one place. Provisioning's `_connected_declarations` now calls
  `reached_by_both_sides` (Step 7), the renamed `read_only_reason`; whether
  provisioning keeps that rule is TCW-115's.
- **TCW-116:** a move refuses while a ticket holds a 3.x `TCW Item` (Step
  17); this repository's own tickets will be refused until migrated.
- **TCW-117:** beyond the spec's list: `tcw -C` in `docs/guide/cli.md` and
  the CLI guide's global options; `tcw work move`, `tcw taxonomy
  rename|move`, `tcw capabilities rename|move`; that a Jira-mode create
  form now accepts blockers in other projects (Step 8); the removal of
  `report_mentions` changes nothing a user sees; and the passages Step 7
  changed only as far as naming a working command (the list is in the
  implement round), which TCW-117 rewrites for 4.0 like the rest.

## Step 24 — Documentation Sync

Each documentation entry (`tcw work docs`), evaluated with the
`documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: `-C`, the move commands, `--project` and `--blocks` removed (`README.md:608`) | The one table cell at `:608` that says `--project` creates an item in another project is changed in Step 7, only as far as no longer saying a removed option works (choice 13). Everything else, `-C` and the move commands included, is deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99, "How 4.0 is built"); the spec's TCW-117 handoff and Step 23 say what. Recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | yes: recorded parents and blockers; a move edits `TCW Item` per ticket; delegation gone (`:235`) | `:235` changed in Step 7, as far as naming a working command; the rest deferred to TCW-117, as above. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/cli.md:150`, `work.md:332`, `:351`, `multi-repo.md:141`, `:187` | Each of those passages changed in Step 7, as far as naming a working command; the 4.0 rewrite deferred to TCW-117. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written (below). |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written (below). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: `skills/work/SKILL.md:4`, `:94`, `:107`, `:112`, `skills/capabilities/SKILL.md:153`, `:181`, `skills/work/references/commands.md:11`, `:19` | Each changed in Step 7, as far as naming a working command, because otherwise the documented-command check fails once the options are hidden (spec 9.5); teaching `tcw -C`, `move` and the nested `rename` deferred to TCW-117 (spec handoff). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no key changes; `projects.md:170`, `:199` teach `--project` | No configuration key is added or changed. The two lines are changed in Step 7, as far as naming a working command; the rest is TCW-117's (spec handoff). |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-3 and UC-4's filing requirements (`:161`, `:213`) | The two sentences that write a removed option as a command are changed in Step 7 to say it is removed in 4.0; rewriting the requirements is deferred to TCW-117 (spec handoff). |
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
recorded `parent` and `blocked-by` in a Jira item's state file;
`rewrite_yaml`; `item_prefix`; the `@writes` marker; the fake Jira's three
switches); Changed (the backend operation `rename` became
`move(id_path, new_id_path, before_folder)`; the files backend writes
references before the folder; the Jira move reads each ticket before its
edit and never sets one back; every reference checker reads the one list of
fields; the files backend's rewrite reads the work-item fields from that
list; `reference_problems` takes triples; `tcw validate` checks recorded
references; Jira sites compared by host ignoring letter case; the web
create and edit answers carry the backend's notes as warnings;
`read_only_reason` renamed `reached_by_both_sides`, kept for provisioning
only; the plan stage prompt's step 6, `audit-backlog`, `abstraction.md`;
the passages of the skills, guides, `README.md`, `docs/use-cases.md` and
the ledger that wrote a removed option as a command); Removed (`--project` and `--blocks`, kept only to give a
message; `delegate`, `open_for_update`, `uncommitted_changes`,
`_check_declared`, `_check_target`, `_uncommitted_in`, `blocks_target`,
`delegate_to_jira` and its helpers, the server's `delegate` service, the
`/blocks` route, `BlocksForm`, the create form's project selector,
`read-only`, `readOnly`, `_own`, `report_mentions`,
`_strip_code`, TCW-111's refusal to rename an item with nested items and its
delegation length fitting; the `delegate-a-work-item-to-another-project`
capability record); Internal (`tests/move_stops.py`, `tests/processes.py`,
the sweep guard, the `-C`-aware command checkers).

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
  project with the warning; a Jira-mode create with a parent kept in a
  files-backend project shows, on the page, the note that Jira shows no
  link for it (Step 13).
- **The messages read as plain language** at their length: the stop message
  of a Jira move with three tickets, read in a terminal, both the ordinary
  one ("run the same command again") and the one after a clash with another
  command (with the suite's fake); and the refusal for a graph problem.
- **The combined step 6 of the plan prompt** (Step 20), read once in full as
  an agent would see it.

## Self-review against the spec

**Every criterion has a step:**

| AC | Step |
| --- | --- |
| 1 work writes refused, four locate outcomes, no backend of `core` opened | 2, 3 (`move` row: 18) |
| 2 tree writes refused, override allowed, one shape, `rm` with `core` removed | 3 (`rename`, `move` rows: 19) |
| 3 planning workspace | 3, 6 |
| 4 web app: create, `/blocks`, PATCH, route table, router test, client, Jira-mode blocker | 4, 7 (create, `/blocks`), 8 (client) |
| 5 removed options | 7 |
| 6 a part in another project, files | 13 (with `-C` from 5) |
| 7 Jira recorded references: write, read, exit 5, stop and re-run, exit 7, the site's letter case, the web warning | 13, 14 |
| 8 `-C` path | 5 |
| 9 `-C` address; the process rule | 1 (`tests/processes.py`), 5 (3.x start with a path), 6 |
| 10 `-C` runs as there | 5 (`init`), 6 |
| 11 rename with nested items, files, and its stop | 17 |
| 12 rename with nested items, Jira, every stop, two runs and the way out of their clash, the folder already gone | 12, 17 |
| 13 moving work items | 18 (files and Jira) |
| 14 repairing a merge | 18 |
| 15 taxonomy rename and move | 19 |
| 16 capabilities rename and move | 16 (5.4 f), 19 |
| 17 overrides | 19 |
| 18 length | 17 (files and Jira) |
| 19 unreadable records | 16, 19 |
| 20 grammar-breaking folder | 17 (5.5 in `tcw/move.py`), 19 |
| 21 other projects' references | 19 |
| 22 no `read-only`, no `readOnly` | 7, 8 |
| 23 shipped text; the documents and the removed record | 7 (the documents, the record, the `--project` spans), 20 (the final prompt paragraph, `abstraction.md`) |
| 24 the sweep | 7, 21 |
| 25 no hooks, no git but `rev-parse` | 17 (rename), 18 (move), 19 (trees), by Step 1's rule |
| 26 one definition; by field; a row added is checked and rewritten | 9, 10, 16 (by field, mutation), 17 (work-item rows), 19 |
| 27 validate of recorded references | 15 |
| 28 suite as CI runs it | 25 |

28 criteria; 26 steps (0 to 25).

**Every Design rule has a step:** 1.1-1.3 → 2, 3; 1.4 → 4; 1.5 → 3; 1.6 →
3, 6; 1.7 → 13; 1.8 → 7, 8; 2.1-2.2 → 7; 2.3 → 7, 8; 2.4 → 7; 3.1-3.2 → 13
(AC 6); 3.3 → 13, 14, 15; 4.1-4.2 → 5; 4.3-4.4 → 6; 4.5 → 5; 4.6 → 1, 6;
5.1-5.6 → 17, 18, 19; 5.7 → 17, 18, 19 (AC 25); 5.8 → 17, 18, 19 (every
stop); 6.1-6.2, 6.4-6.6 → 16; 6.3 → 9, 10, 16, 17; 7.1-7.3 → 17; 7.4 →
unchanged, covered by TCW-111; 8 → 19; 9.1-9.3 → 7, 20; 9.4 → 17, 18, 19;
9.5 → 7, 22; 10 → "What this plan relies on", Step 0; 11 → 21.

**The suite at each step boundary.** Each step adds its tests and the code
they need together, and removes a test only in the step that removes its
behaviour, listed in that step's `allowed` file:

- Step 3's rows for commands that do not exist yet (`tcw work move`; `tcw
  taxonomy rename`, `tcw capabilities move`) are `xfail(strict=True)` until
  Steps 18 and 19 add them, so they pass (as expected failures) at every
  boundary between, and a strict mark fails the suite if one starts passing
  while still marked. Each fails as expected because argparse exits 2 for a
  command that does not exist and the row asserts 3.
- Step 4's route-table test lists `/blocks` as a write until Step 7 removes
  the route.
- Step 6 adds no case that needs `--project` hidden; that case is Step 7's
  (review M1).
- Step 7 hides the two options and, in the same step, changes every live
  document that wrote them as a command (choice 13), so
  `tests/test_documented_cli_surface.py` passes at its boundary; it removes
  every caller of the removed functions in the same step, the server's
  `/blocks` route and create branch included, so nothing calls a function
  that is gone; it deletes the removed capability's record together with
  the four links to it, so the lifecycle `tcw validate` reports no dangling
  link. The client keeps its selector for one step and gets a usage error
  if a person picks another project, which no test exercises against a real
  server. Step 8 removes the selector.
- Step 10 changes no behaviour; each commit is compared with an empty
  allowed list.
- Step 17 changes the backend interface, both real backends' bodies, both
  memory backends and `tcw work rename` together (review M3), so no
  boundary has a Jira `move` with the new signature and the old body; the
  rename tests of both backends pass at that boundary on the new method.
  `tcw work move` does not exist until Step 18, so nothing reaches a
  destination in another folder before then.
- Step 20 changes the prompt text and its tests together, and regenerates
  the fallback fixture in the same step (as Step 7 did for its part).

**Citations.** Every `file:line` above was read at `d2d02829` and the ones
this revision added at `965f2bff`; Step 0 re-checks them all after TCW-112
lands, and the earlier items' plans name most of these places as changing.

**No placeholders.** Every message is given in full or by the Design rule
that gives it in full; the names taken from other items' plans
(`inherited_at` and `_write_target` from TCW-112, `load_config(...,
personal=False, registry=...)` from TCW-109) are confirmed in Step 0 before
they are used.

## Spec issues found while planning

All five were taken into the spec in its revision after the plan review:

1. The process rule (now spec 4.6, 5.7, AC 9, AC 25): the worktree probe is
   3.x code that always runs, not TCW-107's, so the rule is "nothing but
   read-only `git rev-parse`", decided now (choice 11).
2. A work move in a project whose `work.jira` comes from a missing ancestor
   (now spec 5.4 g and UC-6), and the Jira backend's decision for a named
   project whose `work.jira` is undecided (now spec 3.3, exit 7).
3. The removed options' values are read only to word the messages (now
   spec 2.2, both options).
4. The Jira-mode web forms' blocker field (now spec 2.3 and AC 4).
5. Creators make no ownership call (now spec 1.2), the dispatching
   session's decision on the review's recommendation; choice 2 and Step 3
   no longer give `new` and `tickets adopt` a call that could never refuse.

## Revised after the plan review (2026-10-22)

The adversarial review returned NOT DONE with five must-fix findings,
thirteen should-fix findings and two for the user. Each was checked against
the repository at `965f2bff` before it was acted on.

- **M1** (Step 7 turns the documented-command check red): confirmed by
  reading `_check` and grepping the live documents. Choice 13 and Step 7
  change each passage only as far as naming a working command; Step 6's
  `--project` case moves to Step 7; the removed capability's record is
  deleted in Step 7 with the four links to it.
- **M2** (the rewrite matched by value): choice 6 now tracks the key path
  and replaces only at fields `FIELDS` names; Step 16 adds the by-field
  negative tests and a rewrite mutation check.
- **M3** (the interim Jira `move`): Steps 17 and 18 are reorganised so the
  interface and both backends change in Step 17, and the `move` command
  comes in Step 18.
- **M4** (the check after the lookup): confirmed at `tcw/work/cli.py:61-63`
  and `tcw/work/open.py:86-97`. Step 3 checks the project the text names
  before anything of it is opened; for the trees, the refusals inside
  TCW-112's `removal_target` and `override_target` become `check_owned`;
  AC 1 and AC 2 gain rows that fail if a backend is opened first.
- **M5** (the process rule): confirmed at `tcw/store/project.py:67-79`,
  `:119-158`, `:229`. Decided now (choice 11, Step 1's shared rule).
- **S1** (the stop helper): the primitives named, the completeness check,
  folder creation in Step 18, capabilities in Step 19, one-step writes in
  Step 16.
- **S2, S3** (the clash between two runs): the stop's advice and the
  folder's place in choice 8 and Step 17; the two-runs test fires on the
  `GET` before the edit.
- **S4** (the web never shows the note): Step 13 collects the backend's
  reports into the answer's warnings.
- **S5** (the owner's configuration and the site): Step 13 reads it with
  TCW-109's `load_config(..., personal=False, registry=...)`, propagates
  exit 7, and compares hosts ignoring case.
- **S6** (the AST guard): Step 21 states the receiver rule and the
  `@writes` marker.
- **S7** (TCW-111's tests): listed in Step 17, with the sweep allowlist's
  `report_mentions` entry (Step 16 and 17).
- **S8** (where the new name is built): `tcw/move.py` with `item_prefix`;
  the length is refused, never shortened.
- **S9** (a checked field is a rewritten field): accepted, not narrowed:
  the files backend rewrites `fields_of("work-item")` (choice 12).
- **S10** (`read_only_reason`'s callers): Step 0 item 8 and Step 7;
  provisioning keeps the test, renamed `reached_by_both_sides`.
- **S11** (the graph-problem message): Step 2's third tail.
- **S12** (TCW-112's names): used throughout, from TCW-112's revised plan
  (`e544fbff`): `inherited_at`, `chain`, `override_target`,
  `removal_target`, and `find_tree_writable(..., removing=False)` (whose
  default TCW-112's final plan removes, Step 3), which
  refuses nothing itself, so Step 3 rewords the refusals inside the two
  target methods rather than adding a check after it.
- **S13** (paging; the error's name): Step 17 and choice 8.
- **Found in this revision:** a removed capability is deleted from this
  ledger, not given a status (Step 22 corrected).

## Revised after the plan re-check (2026-10-22)

- **Step 7's replacement texts** now pass the documented-command check:
  every `-C` target is one token (`<folder>` or `tcw://<id>.path/`), a
  removed option is named only outside a `tcw` code span, the texts for
  `skills/work/SKILL.md:4`, `:93-100`, `:107-110`, `:111-112`,
  `skills/work/references/commands.md:11`, `docs/use-cases.md:161` and
  `:213-216` and `docs/guide/multi-repo.md:179` are written out, and
  Step 7's tests prove each span and the two forms the rule forbids. Step 6
  says the skip takes exactly one token.
- **The clash stop** (spec 5.8, 7.3, AC 12, Step 17) tells the person to
  wait for the other command, pull its commit if it ran in another clone,
  run `tcw validate --remote` and set each ticket it reports to its
  folder's identifier, or run this command again on the item at its new
  place; Step 17 tests that second way out.
- **TCW-112's final handoff**: `removing` has no default; `override_target`'s
  order is kept, with `check_owned` in its branches (Step 3), and a project
  that is no source of the active project exits 3 even with an ancestor
  missing (spec 1.1, AC 2).
- Smaller: `check_owned`'s `except` order (Step 2); `move_stops`' clauses
  for a folder rename and for counting inside a counted call (choice 10);
  `rewrite_references` reads the work store only for Markdown links and
  `capabilities.yaml` (Step 16); the prose grep and the TCW-108 and TCW-111
  records-gate check (Step 0 items 7 and 9); two citations; Step 19's
  exit 4 for an id-path with no own object.
