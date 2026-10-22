# Plan — TCW 4.0: `--scope`, `--project` and a project's whole family in the CLI and the web app

Child 8 of 13 of TCW-99. The spec (`spec/spec.md` beside this folder, 41
criteria, revised after review) and `capabilities.yaml` are the inputs.
"Design n" and "AC n" are the spec's; "TCW-1nn Step n" is a step of that
item's plan; "TCW-1nn Design n" a rule of that item's spec.

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`).

**Landing order and where the references point.** TCW-106, TCW-107, TCW-110,
TCW-108, TCW-111, TCW-109, TCW-112, TCW-114, then this item, then TCW-115.
File and line references to code are to commit `62e41ec5` on `v4`, where
only TCW-106's code has landed in `tcw/` and `web/` (the uncommitted edits in
the worktree belong to another session and are not cited). Every other item
before this one rewrites much of what is cited, so each step names the code
by function as well as by line, and names what an earlier item adds by the
name that item's plan gives it. **Step 0 re-finds every citation** on the
tree those items leave, and a citation that cannot be found is corrected in
this plan before Step 1, never worked around in the code. TCW-114's spec and
plan were being revised while this plan was written, so names from them are
cited by name only.

**The gate at every step boundary.** Every step writes its tests first and
sees them fail for the reason they name, then makes the change, and ends
with the named tests passing and the **whole Python suite** passing:
`.venv/bin/pytest` with no arguments, from the worktree's root, as CI runs
it. A step that touches the web client also ends with, from the worktree's
root: `pnpm exec tsc --noEmit`, `pnpm test`, `pnpm lint`,
`pnpm exec prettier --check <every file the step changed or created that
.prettierignore does not exclude>`, and `pnpm build` (which rewrites the
committed `tcw/serve/dist`). Not `pnpm typecheck`, for the reason TCW-110's
plan gives (it runs `prettier --check .` over the whole repository first).
A step that cannot end green is two steps.

**Which `tcw` drives this repository's lifecycle.** TCW-110's eight rules,
adopted unchanged, as every sibling plan does: lifecycle commands
(`show`, `advance`, `comment`) use the `tcw` first on `PATH` (the primary
checkout's install of `main`, 3.x), checked with `which tcw`; `.venv/bin` is
never put first on `PATH` in a shell that runs one; the 4.0 code is run only
by the suite (projects under `tmp_path`) and in throwaway projects under the
session's scratchpad, with the current folder set there; `tcw serve` is
never run from the worktree. This repository's records stay in the 3.x
format until TCW-116 (Step 18).

## How the steps are grouped

| Part | What | Steps |
| --- | --- | --- |
| 0 | the starting state, the inventory, the outcome record, the family fixture | 0, 1, 2 |
| 1 | the model: which projects a scope covers, and reading them | 3, 4 |
| 2 | work across a scope, and the Jira search kept for one command | 5, 6, 7 |
| 3 | taxonomy and capabilities across a scope; the default becomes `own`; `--local` goes | 8, 9, 10, 11, 12a, 12b |
| 4 | the web app | 13, 14, 15, 16 |
| 5 | shipped text, records, documentation, notes, CI | 17-21 |

23 steps in all. **The mass test conversions** are Steps 10 and 12a. Each is
split from the behaviour change it serves (Steps 11 and 12b), so that a
failure can only come from one of the two, and each uses TCW-107's and
TCW-108's safeguards as TCW-112's plan collects them (its "The conversion
safeguards"): an inventory, the outcome comparison, a mutation check, a
mechanical commit apart from the hand edits, and a failure list found
before the change exists.

## What this plan relies on

Each name below is confirmed in Step 0 against what the item landed.

**TCW-106** (landed): `.tcw/tcw-config.yaml`, `tcw-version` on every file;
`tests/projectfiles.py`'s `write_config(root, text)`,
`write_config_file(path, text)`, `write_local_config(root, text)`.

**TCW-107** (its plan): `FsProjectRegistry.open(root)` returning the
command's one registry for that root (TCW-107 Design 2.13; its Step 5, with
`begin_command`, `end_command`, `forget_registries`);
`FsProjectRegistry.project_folder(project_id, named_by)` and its four
outcomes (a folder; `Unreachable`, exit 5; `UnknownProject`, exit 1;
`ProjectGraphError`, exit 1) (its Step 3); `UnreachableProject.message`,
Design 6.2's sentence that names `tcw project provision <id>` when the
deciding manifest entry gives a repository, and
`registry.unreachable_project(project_id)` (its Step 3); `write_manifest(root,
entries)` and the `tmp_path` guard in `tests/conftest.py` (its Step 2);
`_read_text`, the module-level function every registry read goes through,
which a test replaces to count reads (its Step 3, choice 3); the
inventory, search-off and mutation-check safeguards (its Step 9).

**TCW-110** (its plan): `tcw/ids.py` (`FullId`, `parse_full_id`,
`sort_input` and its forms a to d, `looks_full`, the project-ID rule) (its
Step 1); `tests/fullids.py` (`fid`, `wid`) (its Step 3); the item record's
`full-id` and `owner` keys and `"schema": 2` from `print_json` (its Step 4);
`Term.owner`, `Capability.owner`, `full_id`, the tree records' `full-id`
and `owner` keys, `route_key(obj, project_id)` in `tcw/refs.py` and the
client's `itemKey` and `keySegments` (its Step 6); `tcw/locate.py`'s
`Locator.of(active_root)`, `owner_root(project_id, named_by)`,
`read(full_id, named_by)`, `outcome_of(error)` and `Outcome` (its Step 7);
`find_tree(store, namespace, text)` and `resolve_work_input(text, active,
root)` (its Step 8, the second argument a function after TCW-109 Step 6);
`resolve_address(project_root, uri) -> ResolveResult` (its Step 10); the
web client's `web/client/src/model/identifier.ts` (`parseFullId`,
`fullIdText`, `objectAddress`) (its Steps 2, 10).

**TCW-108** (its plan): `ProjectRegistry.load_order(project_id=None)`
returning a `LoadOrder` whose `ids` include missing ancestors and whose
`missing` and `unreadable` name them (its Steps 2, 7b, 10);
`declared_child_ids(project_id)` (the active project's list with its
personal additions, a descendant's committed list, an ancestor's names);
`descendants()` breadth first; `get(id)` answering only for family members
on this machine (its Step 7b); `sources(axis, project_id=None)` raising
`InheritedUnavailable` (exit 7, `tcw/errors.py`) for the first missing or
unreadable project that passes the axis (its Step 10);
`connect_projects(root, relation, *ids, inherit=...)` in
`tests/projectfiles.py` (its Step 8a); `compare_outcomes.py` as its Step 7
describes it.

**TCW-111** (its plan): `tests/statefiles.py`'s `write_state(folder, data)`
and `CAPABILITY_STATE`, `TAXONOMY_STATE` (its Step 3), so a fixture writes
objects in the 4.0 layout; `StateFileProblem` (exit 1) for an unreadable
state file (its Step 5); both backends find items by id-path (its Step 8).

**TCW-109** (its plan, revised): a project read for itself is
`load_config(root, personal=False, registry=<the command's registry>)`, and
the registry is required when that project declares `parents:` (its choice
3, the revised handoff to this item); `open_backend`, `read_work_config`,
`project_facts` and `_layered` in `tcw/work/open.py` take `registry=None`
and pass it on (its Step 7a); an undecided `work.jira` raises
`InheritedUnavailable` with a message naming the project (its Step 7c).

**TCW-112** (its plan, and its handoff to this item): the view is
`get_view(id_path)` and `list_all()`; `list_all(local_only=True)` is the own
objects, each combined as its owner sees it, and degrades to
`declaration()` marked `partial` on `InheritedUnavailable` (its Step 13);
`get_local(id_path)`, `has_own(id_path)`, `declaration(id_path)`,
`own_paths()`, `chain(id_path) -> list[FullId]` nearest first (its choice
1, Step 7); `Term.overrides`, `Capability.overrides`, `partial`, and the
`overrides` key in every record (its choice 7, Step 7); a source's store is
opened as another project's with `STORE_CLASSES[axis].open(root,
as_other=True)` (its choice 4); `Locator.exists(full_id, named_by)` (its
Step 13); `CapabilityDetail.declared_description` and the detail answer's
`declaredDescription` (its Step 17b, AC 44); `InheritedUnavailable`
answered `503` `{"code": "inherited-unavailable"}` by `error_answer` (its
Step 17a); `unreviewed_inherited` for drift (its Step 16), which this item
leaves alone.

**TCW-114** (its plan, being revised; names only): `Route.writes`, a
function from the request to a list of `Written(full_id, hint)`, and the
router's call of `check_owned` (`tcw/ownership.py`) before a write route's
handler (its Step 4); the 403 `read-only` refusal whose message holds
`belongs to project '<owner>'`; the work and files write routes' `writes`
answering "the item the path names (`item_folder`, made into the active
project's full identifier)" (its Step 4); the route-table test
`tests/serve/test_route_writes.py` (its Step 4); `work new --project` and
`edit --blocks` refused and hidden (its Step 7); `GET /api/project` without
the connected-project rows (its Steps 7, 8); `_place` and the Jira
backend's recorded `parent` and `blocked-by`, which `list` reads for a
parent in another project (its Steps 13, 14); `tcw/work/procedures/audit-backlog.md`'s
"Wrong project" line naming `tcw -C` (its Steps 7, 20), and its test that
the procedure contains no `--project`.

## Choices this plan makes where the spec leaves room

Each is "decided while planning", with its reason.

1. **Where the code lives.** The model: `ProjectRegistry.scope_members` and
   `covering_scope` (Design 1.3, 1.4, 2.2), `UNAVAILABILITY_ERRORS` and
   `is_unavailability` (Design 1.6), `text_matches` (Design 4.5), and
   `scope_rows` with its records (Design 4.10), all in `tcw/store/base.py`.
   What the CLI and the web app share above the model is two new modules:
   `tcw/scope.py` (the covered projects of one command, the `--project`
   check, reading each other project inside the catch, the `projects`
   array and the warnings) and `tcw/tree_scope.py` (taxonomy and capability
   rows across a scope, built from stores and handed to `scope_rows`); and
   one for work, `tcw/work/scoped.py` (items across a scope). Reason: the
   CLI and `tcw serve` must give the same rows (Design 6.2), so neither
   computes them itself.
2. **The unavailability catch is a tuple and one test.** A tuple cannot say
   "every `TcwError` except `UsageError`", so `UNAVAILABILITY_ERRORS =
   (TcwError, StoreLocationUnusable, StoreDeclarationError,
   StoreNotProvisioned, yaml.YAMLError, OSError)` is caught and
   `is_unavailability(error)` returns false for a `UsageError` (and its
   subclasses), which the catch then raises again. Both live beside
   `scope_rows`, as Design 1.6 asks.
3. **How another project is located and named when it is missing.** A
   covered project other than `P` is found with `registry.get(id)` (TCW-108:
   family members on this machine). When `get` answers `None`, the reason is
   `registry.unreachable_project(id).message` (TCW-107's Design 6.2
   sentence, kept once per ID by TCW-108 Step 7b), raised as `Unreachable`
   inside the catch, so it takes the same path as any other reason. No new
   lookup is made, so a project with no family opens nothing (Design 1.9).
4. **Another project's work backend** is `open_backend(root, personal=False,
   registry=<the command's registry>)` (TCW-109 Step 7a), its stages from
   `read_work_config(root, personal=False, registry=...)`. Its tree stores
   are `Locator.of(P's root)`'s cached stores, opened as another project's
   (TCW-112 choice 4), so one command opens each store once.
5. **`--mine` across projects.** A files-backend project other than `P` is
   given `P`'s `user.name` (`effective(P's root).user_name`), a Jira one
   its own `current_user()`. The test is `isinstance(backend, JiraBackend)`,
   as `_person` already makes it (`tcw/work/cli.py:265-270`). A project that
   can name nobody raises `ConfigError` with `_me`'s message inside the
   catch (Design 3.2, 1.6 f).
6. **The warning a `show` gives** (spec gap G8). Design 1.8 says "A `show`
   says `… so its status is not shown`". That is true only of `tcw
   capabilities show`. `tcw work show` says `warning: '<Q>' is unavailable,
   so its work items are not included: <reason>`, and `tcw taxonomy show`
   `… so its taxonomy entries are not included: <reason>`. Reason: a status
   is a capability's; the other two shows leave out items and entries.
7. **`--project` on taxonomy and capabilities never groups**, so its
   records carry no `statuses` and no `overridden-by`, under any scope
   (spec gap G10). Reason: Design 2.1 says its rows are one owner's own
   objects, "never combined into another project's row", and a group is
   what those two keys describe.
8. **The `status by project:` block** goes after the record's fields and
   before `body:`; `overridden by:` goes on the line after `overrides:`
   (spec gap G13). Reason: Design 4.6 says "after the record's fields",
   and the body is not a field.
9. **The web app's list and detail records** are the server's objects
   today (`jsonable` of each `Term` or `Capability`), with the CLI record's
   keys added and taking precedence (spec defect D1). AC 33 is checked as:
   the same rows, in the same order, and each web record holding the CLI
   record's keys and values. Reason: the client reads `description`,
   `body`, `fields`, `modified`, `relates_to` and `vocabulary` from list
   rows (`web/client/src/ui/content-views.tsx:215-276`,
   `web/client/src/ui/shared-components.tsx:414-429`), which the CLI's
   list records do not carry; making the answer "exactly" the CLI records
   would break the page.
10. **The search kept for one command is thread-local** (spec gap G11).
    `tcw/config.py` gains `command_state() -> dict | None`, backed by a
    `threading.local`, created by `begin_command()` and dropped by
    `end_command()`, and a context manager `command_span()` that creates
    and drops only that state. `tcw serve`'s `_api` wraps each request in
    `command_span()`. Reason: `ThreadingHTTPServer` answers requests on
    several threads, and `_EFFECTIVE` (`tcw/config.py:657-665`) is one
    global; making each request a full `begin_command()` would let one
    request's `end_command()` drop another's cache. The server's promise
    that each request reads the configuration again (`WorkContext`'s
    docstring, `tcw/serve/work.py:48-50`) is kept.
11. **A kept search is answered with a deep copy** (`copy.deepcopy`), so no
    caller can change what another caller is given (Design 3.5, "none
    changes it").
12. **The interim default between Step 9 and Step 11.** Step 9 adds
    `--scope` to the six tree commands with an internal default, `None`,
    meaning "what the command does today" (the view, and no `projects`
    key), so no existing test changes in Step 9; Step 10 converts the tests
    that rely on it; Step 11 makes the default `own` and deletes `None`.
    Reason: an explicit `--scope up` adds `projects` to `--json` (Design
    1.8), so a default of `up` would change every `--json` test at once.
13. **Help strings.** `--scope`: "which projects to cover: own (this
    project, the default), up (adds its ancestors), down (adds its
    descendants), all (both); never a sibling". `--project`: "keep only this
    project's own objects; it must be one the scope covers". The `--json`
    helps add "and `projects` when the scope is not own".
14. **The client's scope state** is read from and written to the URL's
    query string with react-router's `useSearchParams`, so a reload or a
    copied link reproduces it (Design 6.6).

## Step 0 — start from what the earlier items left

No code changes.

1. `git log --oneline` shows the TCW-114 implement and review commits; the
   lifecycle `tcw work show TCW-114` is at `completed`.
2. Every file and line this plan cites is re-found on the tree, and each that
   moved is noted in the implement round with its new place. Most likely
   moved: everything in `tcw/work/cli.py`, `tcw/work/open.py`,
   `tcw/work/record.py`, `tcw/work/jira/backend.py`, `tcw/serve/work.py`,
   `tcw/serve/records.py`, `tcw/serve/files.py`, `tcw/serve/server.py`,
   `tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`, `tcw/store/base.py`,
   `tcw/store/fs.py`, `tcw/config.py`, `tcw/cli.py`, and the client files of
   Steps 13-16.
3. Each name in "What this plan relies on" is confirmed. In particular:
   whether `FsProjectRegistry.open(root)` is itself the command's one
   registry or `Locator.of(root)` exposes it (the plan uses whichever
   TCW-107 Step 5 and TCW-110 Step 7 landed, and names it in the round);
   the attribute names of `LoadOrder` (`ids`, `missing`, `unreadable`);
   `unreachable_project`; `open_backend(..., personal=False, registry=...)`;
   the `as_other` store opening and `Locator`'s store cache; `chain`,
   `declaration`, `own_paths`, `has_own`; `Route.writes`, `Written` and the
   router's call; how `tcw serve` builds a `Locator` per request (TCW-110
   Step 7: "a fresh one per request").
4. **Whether `tcw serve` already brackets requests.** If TCW-107 or TCW-110
   made `_api` call `begin_command()`, choice 10 still holds: Step 7 adds
   only the thread-local state, and the round says what was found.
5. **The tests that read inherited content through `list`, `show` or
   `search` with no option**: `grep -rln "taxonomy\", \"list\"\|capabilities\", \"list\"\|\"show\"\|\"search\"" tests/`
   gives the starting list; Step 10 finds the exact set by running the
   suite.
6. **Every `--local` in tests, evals and shipped text**:
   `grep -rn -- "--local\b\|local_only=args.local" tests/ evals/ tcw/ skills/ agents/ docs/guide docs/capabilities README.md`
   (ignoring `tcw-config.local` and `manifest.local`), kept for Steps 12a
   and 12b.
7. The suite passes: `.venv/bin/pytest`, and the web gate.

**Proves it:** the notes in the implement round; the suite green.

## Step 1 — the inventory, the outcome record and the comparison script

Before any test is added or changed, in the style of TCW-114 Step 1 and
TCW-112's safeguards. All scripts are one-off and kept in the session's
scratchpad, never in the repository.

- **The inventory**: `.venv/bin/pytest --collect-only -q` saved to
  `<scratchpad>/inventory-step1.txt`; and from a script walking each test
  function's syntax tree, its count of `assert` statements and
  `pytest.raises` blocks, and `ast.dump` of each, saved beside it.
- **The outcome record**: `.venv/bin/pytest -q
  --junitxml=<scratchpad>/outcomes-step1.xml`, from the worktree's root.
- **The comparison script**, `compare_outcomes.py <before.xml> <after.xml>
  <allowed.txt>`, copied unchanged from TCW-112's or TCW-114's scratchpad
  when it is still there, or written again from TCW-112's description (its
  "The conversion safeguards"): it exits non-zero, printing each offending
  test ID, when an ID in `before` is missing from `after` and not in
  `allowed.txt`; an ID in both has a different outcome and is not in
  `allowed.txt`; an ID in `allowed.txt` is still present with its old
  outcome; or any ID in `after` has outcome `failed` or `error`. A new ID
  must be `passed`. An ID listed with `assertion:` before it may keep
  `passed` with a rewritten assertion, checked against the inventory's
  dumps.

**The record is saved again at the end of every step** as
`outcomes-step<N>.xml`, so each comparison is against the step before it.

**Proves it:** the four scratchpad files exist; nothing in the repository
changed.

## Step 2 — the family fixture

**Creates** `tests/families.py`, the one place this item's tests build
the spec's family `F` (spec, Acceptance criteria, the opening list), in the
4.0 layout, with TCW-106's, TCW-107's, TCW-108's and TCW-111's helpers:

- `build_family(tmp_path, *, server_backend="files", docs_passes=None,
  extra=None) -> Family`: folders `docs`, `shared`, `desktop`, `server`,
  `other` side by side under `tmp_path`, each a git repository (TCW-108
  AC 26's way, `git init`), each with `.tcw/tcw-config.yaml` written with
  `write_config` holding its `id`, its `parents:` and its `children:` as
  the spec lists them (`shared`'s link to `docs` is `inherit: none` unless
  `docs_passes` names axes), and each located by `write_manifest` entries;
  `mobile` named in `shared`'s manifest at a folder that does not exist,
  with `repository: https://example.invalid/mobile.git`. Objects with
  `write_state`: `shared`'s capabilities `abc` (`name: Abc`, `Status:
  Missing`) and `ghi` (`Status: Missing`) and term `invoice`; `desktop`'s
  `abc` holding only `Status: Supported` and complete `def` (`Status:
  Supported`); `server`'s `abc` holding only `Status: Omitted`; `docs`'s
  term `plan`. One unfinished work item `2026-10-01-<id>-item` in each of
  `docs`, `shared`, `desktop`, `server` and `other`, written with
  `tests/work/projects.py`'s `write_item`.
- `Family`: the roots by ID, and `run(project_id, *argv) -> Result` running
  `tcw` in that folder in process through `tcw.cli.main` with standard
  output and standard error captured (as the `run` fixture of
  `tests/serve/conftest.py:183-185` runs it, re-checked in Step 0; in process
  so a test can wrap a function and count its calls), returning `code`, `out`, `err`, and
  `json` parsed when `--json` was given.
- `jira_mode(family, project_id, fake, *, jira_project="APP", email=...)`:
  switches one project to `work.backend: jira` against a `FakeJira`
  (`tests/work/jira/fake.py:155`) installed with `install_sites`
  (`:761`), seeding one ticket per item, with the field ids and stage
  statuses every project of the fixture shares unless given.

**Tests first**, `tests/test_families.py`: the fixture as written passes
`tcw validate` in each of `docs`, `shared`, `desktop`, `server` and
`other` (no error finding), and `tcw projects list --json` in `shared`
names `docs` as a parent and `desktop`, `server`, `mobile` as children, with
`mobile` `present: false`. So every later test starts from a family the
earlier items accept.

**Proves it:** that test; the full suite.

## Step 3 — which projects a scope covers (the model)

Design 1.2, 1.3, 1.4, 1.9 (the registry part), 2.2 (which scope covers a
project).

**Tests first**, new `tests/test_scope_members.py`, calling the registry
directly (`FsProjectRegistry.open(<root>)`) on `build_family`:

- In `shared`: `scope_members("own")` is `[("shared", "current")]`;
  `"down"` is `shared, desktop, server, mobile` with relations `current,
  descendant, descendant, descendant`; `"all"` is `docs, shared, desktop,
  server, mobile` (AC 3's order, at the registry level); `"up"` is `docs,
  shared`. No scope names `other` (AC 4's registry half).
- In `desktop`: `"up"` is `docs, shared, desktop`, relations `ancestor,
  ancestor, current` (AC 10's `projects` order), whatever `inherit` says.
- Breadth first: a fixture where `desktop` lists a child `kid`: in
  `shared`, `"down"` is `shared, desktop, server, mobile, kid`.
- A listed child not on this machine is covered and its own children are
  not looked for: `mobile` is in `"down"`, and `_read_text` (TCW-107's
  counting hook) records no read under `mobile`'s manifest folder.
- A personal child: `shared`'s `.tcw/tcw-config.local.yaml` (personal
  files turned on for that test, since `tests/conftest.py:167-178` turns
  them off) lists `extra`; `"down"` includes it after the committed
  children.
- `covering_scope("desktop")` in `shared` is `"down"`; of `docs` is
  `"up"`; of `other` is `None`.
- A project with no family (Design 1.9): in a lone project `solo`, each
  scope is `[("solo", "current")]`, and a wrapper of `project_folder`
  records no call.
- `UNAVAILABILITY_ERRORS` and `is_unavailability`: a row per class of
  Design 1.6 (a `TcwError`, `Unreachable`, `InheritedUnavailable`,
  `ConfigError`, the three store `ValueError`s, `yaml.YAMLError`,
  `OSError`) is an unavailability; `UsageError` and a plain `ValueError`
  are not.

**Changes**, `tcw/store/base.py`:

- `SCOPES = ("own", "up", "down", "all")` and `RELATIONS`.
- `@dataclass(frozen=True) class ScopeMember: id: str; relation: str`.
- Concrete `ProjectRegistry.scope_members(scope, project_id=None) ->
  list[ScopeMember]` beside `ancestors` and `descendants`
  (`tcw/store/base.py:281-290` at `62e41ec5`): `own` is the project alone,
  asking the registry nothing; `up` and `all` take the ancestors from
  `load_order(project_id).ids` without the project itself (missing ones
  included); `down` and `all` take the descendants breadth first over
  `declared_child_ids(x)` for the project and for each descendant `x` that
  `get(x)` answers, each ID once; the order is ancestors, the project,
  descendants (Design 1.4). A docstring states Design 1.3's sentence on
  `inherit` and siblings.
- Concrete `covering_scope(project_id) -> str | None`: the first of `up`,
  `down`, `all` whose members hold it.
- `UNAVAILABILITY_ERRORS` and `is_unavailability(error) -> bool` (choice 2),
  with a docstring naming Design 1.6's cases a to h. `tcw/store/base.py`
  imports `yaml` and `TcwError`, `UsageError` (`:22` already imports from
  `tcw.errors`).

Litmus: every answer comes from `load_order`, `declared_child_ids` and
`get`, which any registry implements (spec, Abstraction litmus test, first
row).

**Proves it:** the tests above; the full suite.

## Step 4 — reading the covered projects (`tcw/scope.py`)

Design 1.5, 1.6 (what the catch surrounds), 1.7 (`P` outside the catch),
1.8, 2.2.

**Tests first**, new `tests/test_scope_reader.py`, on `build_family`,
calling `tcw.scope` directly:

- `cover(root, "own", None)` in `shared` asks the registry nothing (a
  wrapped `FsProjectRegistry.open` counts no `scope_members` call beyond
  `own`'s), and `covered.projects_json()` is `None` (Design 1.8: under
  `own` the document is unchanged).
- AC 6's and AC 4's refusals as messages, exactly Design 2.2's form:
  `cover(shared, "own", "desktop")` raises `UsageError` whose message is
  `--project desktop: 'desktop' is not covered by --scope own in 'shared',
  which covers shared; --scope down covers it`; `cover(shared, "all",
  "other")` ends `; it is neither an ancestor nor a descendant of
  'shared'`; `cover(shared, "down", "Bad_Id")` raises `UsageError` naming
  the ID rule (`tcw.ids`' project rule); each before any store or backend
  is opened (a wrapped `open_backend` and `FsTreeStore.__init__` record
  nothing).
- `covered.read("mobile", fn)` returns the sentinel `UNAVAILABLE`, does not
  call `fn`, and records `mobile`'s reason, which contains `tcw project
  provision mobile`; `covered.warn("work items", say)` says exactly one
  line, `warning: 'mobile' is unavailable, so its work items are not
  listed: <reason>`.
- A read raising each unavailability class records a reason; one raising
  `UsageError` or `ValueError("x")` propagates; a project read twice in one
  command after it failed is not read again (its first reason stands).
- `projects_json()` under `down`: one object per member in scope order,
  `{"id", "relation"}`, with `"unavailable": <reason>` only for a project
  a read failed for; `desktop`, never read, has no `unavailable` key even
  when its folder is removed (Design 1.8, "only what is left out").
- `covered.root_of("desktop")` is `desktop`'s folder from `registry.get`.

**Creates** `tcw/scope.py`:

- `UNAVAILABLE`, a sentinel.
- `@dataclass class Covered`: `scope`, `active` (P's ID), `root` (P's
  folder), `registry`, `members: list[ScopeMember]`, `only: str | None`
  (the `--project` value), `reasons: dict[str, str]` (insertion order).
- `cover(root, scope, project) -> Covered`: the registry is the command's
  one (Step 0, item 3); for `own` without `--project`, `members` is `[P]`
  and the registry is not asked (Design 1.9). `--project` is checked
  against the project-ID rule, then against `members`; when not covered,
  `covering_scope` words the tail (Design 2.2).
- `Covered.wanted() -> list[ScopeMember]`: the members `--project` keeps
  (all of them without it).
- `Covered.root_of(project_id) -> Path`: `P`'s root, or `registry.get(id)`'s
  folder, or raises `Unreachable(registry.unreachable_project(id).message)`
  (choice 3).
- `Covered.read(project_id, fn)`: calls `fn(self.root_of(project_id))`
  inside `try`/`except UNAVAILABILITY_ERRORS`, re-raising when
  `is_unavailability` is false; on a reason, records it and returns
  `UNAVAILABLE`. Never called for `P` (Design 1.7): `P` is read by the
  caller outside any catch, first.
- `Covered.warn(what, say, *, show=False)`: one line per recorded reason,
  in scope order (Design 1.8; choice 6 for a `show`).
- `Covered.projects_json() -> list[dict] | None`.

**Proves it:** the tests above; the full suite.

## Step 5 — `tcw work list` across a scope

Design 1.1 (work list), 1.5, 1.6, 1.8, 2.1, 2.2, 3.1, 3.2, 7.2 (its help);
AC 1 (its work-list sentences), 2 (work), 3, 4 (list), 5, 6, 22 (list),
23, 26, 27, 38.

**Tests first**, new `tests/work/test_scope_work_list.py`, on
`build_family` (each criterion one test, named by its number):

- AC 1's `tcw work list --scope sideways` exits 2; AC 2's work sentence
  (`tcw work list` in `desktop` prints exactly
  `desktop.work/2026-10-01-desktop-item`, its `--json` has no `projects`).
- AC 3, AC 4 (the list and `--project other` sentences), AC 5, AC 6.
- AC 22's list sentences (`server` in Jira mode with `work.jira` from a
  second parent `cfg` that passes `config` and is not on this machine:
  exit 0, `shared`'s and `desktop`'s items, the warning with TCW-109's
  message naming `server`; in `server`, `tcw work list` exits 7).
- AC 23 (`server`'s personal file not valid YAML: listed from `shared`;
  exit 1 in `server`).
- AC 26 (`server` in a fake Jira not enabling `review`): `--stage review`
  exits 0, no warning naming `server`, `fake.requests("POST", "search")`
  (the shape Step 0 confirms) records nothing; `--stage review --stage spec`
  records one search whose status clause names `spec`'s status alone; in
  `server`, `--stage review` exits 2.
- AC 27 (`--mine`: `shared`'s personal file sets `user.name: ann`,
  personal files turned on for the test; `desktop`'s item assigned to
  `ann`; `server` in a fake Jira signing in as `a-1`, its item assigned to
  `a-1`).
- AC 38 (`--tag ui` and its one warning line, `--assignee ann` in both
  backends, `--all`).
- A covered project with an unreadable item file prints the existing
  "could not be read" warning for that project and still lists the rest
  (the `_readable` path, `tcw/work/cli.py:136-142`), under `--json`.

**Creates** `tcw/work/scoped.py`:

- `ScopedItems`: `by_project: list[tuple[str, list[Item], WorkBackend]]`
  in scope order, and `every: list[Item]` (the readable items of every
  covered project that is not unavailable, for `children` and `blocks`,
  Design 3.3, used from Step 6).
- `list_scope(covered, query, *, mine, assignee, need_every) ->
  ScopedItems`: `P`'s backend read first, outside the catch, with the
  query unchanged (Design 1.7; `P`'s Jira stage refusal stays, AC 26's
  last sentence). Then for each other wanted member `Q`, inside
  `covered.read`: `read_work_config(Q root, personal=False,
  registry=covered.registry)`; the query's stages narrowed to `Q`'s
  `enabled` (Design 3.2), and when none remains `Q` gives `[]` without its
  backend opened; otherwise `open_backend(Q root, personal=False,
  registry=covered.registry)` (choice 4); the assignee for `--mine` by
  choice 5; `backend.list(query)`; with `need_every`, `readable(backend)`
  (`tcw/work/record.py:14-22`).

**Changes**

- `tcw/work/cli.py`, the `list` parser (`:719-735` at `62e41ec5`): `--scope`
  (`choices=SCOPES`, default `own`) and `--project` (choice 13's helps);
  one new example, `list --scope down --json`; the `--json` help names
  `projects`.
- `_list` (`:235-258`): with scope `own` and no `--project`, today's code,
  unchanged. Otherwise `covered = cover(root, args.scope, args.project)`
  first (so a refused `--project` reads nothing); the tag warning
  (`:245-247`) is kept, checking `P`'s registry only; the parent is parsed
  from `P` as today (`resolve_work_input`, TCW-110 Step 8); `list_scope`;
  `covered.warn("work items", _say)` before any row; then each project's
  items in scope order, or `print_json(None, {"items": [...], "projects":
  covered.projects_json()})` with each record built by `item_record(i,
  <P's readable items when the scope is own, else scoped.every>,
  _layout(<the item's own backend>))`. Until Step 6, `every` under a wider
  scope is the item's own project's, as today; Step 6 widens it.

**Proves it:** the tests above; `tests/work/test_cli_items.py`,
`tests/test_cli_contract.py`, `tests/test_cli_help_standard.py`; the full
suite.

## Step 6 — `tcw work show` across a scope, and `children` and `blocks`

Design 1.1 (work show), 1.7 (an object named by its full identifier), 2.3
(work), 3.3, 3.4; AC 4 (show), 22 (show), 24, 25.

**Tests first**, in `tests/work/test_scope_work_list.py` (renamed
`test_scope_work.py` here, since it now holds both; the rename is listed in
`allowed-step6.txt`):

- AC 4's last sentence (`tcw work show other.work/2026-10-01-other-item` in
  `shared` exits 0).
- AC 22's show sentence (exit 7 for `server.work/...` by full identifier).
- AC 24 (a folder name exits 4 under `own` with today's message; found in
  `desktop` under `down`; the same folder name in `server` too: exit 2
  naming both full identifiers, Design 3.4's message).
- AC 25, with `desktop` in a second git repository beside `shared`'s
  (`build_family` already makes each a repository), `part`'s state file
  holding `parent: shared.work/<epic>` written with `write_state`: `show
  <epic> --json` has `children` `[]`; with `--scope down`,
  `["desktop.work/<part>"]`; `list --scope down --parent shared.work/<epic>`
  prints exactly `desktop.work/<part>`; and `list --scope down --json`
  gives the epic's record `children` with the part.
- Design 2.3: `show 2026-10-01-desktop-item --scope down --project
  desktop` finds it in `desktop` only; `show shared.work/<x> --scope down
  --project desktop` exits 2 naming both projects.
- A ticket key under `down` (`server` in a fake Jira): `show <its key>
  --scope down` in `shared` finds `server`'s item.
- An unavailable project under `show --scope down`: `mobile`'s warning in
  choice 6's wording; exit 0.

**Changes**

- `tcw/work/cli.py`, the `show` parser (`:737-747`): `--scope`, `--project`,
  one example `show <folder> --scope down`.
- `_show` (`:277-311`): input sorted with `sort_input(text, "work", KEY)`.
  A full identifier (form a or c) goes to `resolve_item` as today, outside
  any catch (Design 1.7, 3.4). A folder name or key (forms b, d) under
  `own` with no `--project`: today's `resolve_item`. Otherwise
  `cover(...)`, then the lookup in `P` first, outside the catch
  (`backend.lookup` for a key, `backend.read(folder)` catching only
  `NotFound` for a folder), then in each other wanted member in scope order
  inside `covered.read`; one match is the item, none is `NotFound` (exit
  4), several is `UsageError` with Design 3.4's message. With `--project`
  only that project is looked in, and a full identifier naming another
  project is a `UsageError` naming both (Design 2.3).
- `children` and `blocks` (Design 3.3): under `own`, `item_record(item,
  _readable(<the item's backend>), ...)` as today; under a wider scope,
  `list_scope(covered, Query(all=True), need_every=True).every` read for
  the record, so `children` and `blocks` cover every covered project that
  is not unavailable. `_list --json` under a wider scope passes the same
  `every` (finishing Step 5's last bullet).
- `covered.warn("work items", _say, show=True)` before the record.

**Proves it:** the tests above; `compare_outcomes.py outcomes-step5.xml
outcomes-step6.xml allowed-step6.txt`; `tests/work/` green; the full
suite.

## Step 7 — a search kept for one command

Design 3.5; AC 28, and AC 26's "one search".

**Tests first**:

- New `tests/work/jira/test_kept_search.py`, on `build_family` with
  `jira_mode` for `shared`, `desktop`, `server` and `other` (one fake,
  Jira project `APP`, one email for all): AC 28 every sentence: one search
  naming `project = "APP"` that is not a key search for `tcw work list
  --scope down` in `shared`; the items printed project by project equal
  what `tcw work list` prints in each of the three; no item of `other`;
  `desktop` moved to `DESK`: two such searches, one per Jira project;
  `desktop` back in `APP` with its email variable holding another
  account's email: two searches naming `APP`, the second sent with
  `desktop`'s credentials (the fake records the account per request); a
  second command makes its own search.
- In `tests/test_config_command_state.py` (new): `command_state()` is
  `None` outside a command; a dict inside `begin_command()`…`end_command()`;
  `None` again after; two threads each inside `command_span()` see
  different dicts, and one thread leaving its span does not drop the
  other's.
- A unit test of `_kept_search`: called twice with the same key inside a
  span it calls the search once and returns equal values that are not the
  same object (choice 11); a different site, account, text or field list
  each calls again; outside a span it always calls.

**Changes**

- `tcw/config.py` (`:657-665`): `_COMMAND = threading.local()`;
  `begin_command()` also sets `_COMMAND.state = {}`; `end_command()` sets
  it to `None`; new `command_state()` and `command_span()` (choice 10).
- `tcw/work/jira/backend.py`, `list` (`:433-482`): the line
  `issues = self.client.search(text, read_fields(meta.field_ids))`
  (`:466`) becomes `issues = _kept_search(self, text,
  read_fields(meta.field_ids))`. `_kept_search(backend, text, fields)`:
  the key is `(backend.jira.site, os.environ.get(backend.jira.email_env,
  "").strip(), text, tuple(fields))`, its result kept under
  `command_state()["jira-searches"]` and answered with `copy.deepcopy`
  (choice 11); with no command state it calls the search. The `TCW
  Project` filter that follows (`:470`) is unchanged, so each project keeps
  only its own tickets. Only `list`'s search goes through it; key searches
  and every write path are untouched.
- `tcw/work/jira/jql.py`'s module docstring (`:1-10`) gains one sentence:
  the same search text in one command is sent once (Design 3.5).

Litmus: no backend operation changes (spec, Abstraction litmus test, the
"search kept for one command" row).

**Proves it:** the tests above; `tests/work/jira/` green; the full suite.

## Step 8 — groups, rows, `statuses` and `overridden-by` (one store-neutral function)

Design 4.1-4.7, 4.10 at the function level; AC 12, 13, 15, 18, 19 (their
rows, statuses and `overridden-by`, as data).

**Tests first**, new `tests/test_scope_rows.py`, giving `scope_rows` plain
data (no files):

- AC 12 and 13 (`down` in `shared`): at `abc`, the scope objects
  `shared.capabilities/abc`, `desktop.capabilities/abc` (overrides
  `shared`'s), `server.capabilities/abc` (overrides `shared`'s) make one
  row shown as `shared`'s, `statuses` `[shared Missing false, desktop
  Supported false, server Omitted false]`, `overridden-by` of the shown
  object `[desktop…abc, server…abc]`; at `ghi`, one row with `shared`
  `Missing` false and `desktop`, `server` `Missing` true (each with no own
  object, its view object `shared.capabilities/ghi`); at `def`, one row,
  `desktop` `Supported` false.
- AC 15: `server`'s own `abc` declares no `Status`: its entry is
  `server` `Missing` `inherited: true`.
- AC 18: two descendants' new objects at `zz` make two rows, ordered by
  owner in scope order (AC 32's `desktop` before `server`).
- AC 19 under `down`: `P` has no own `xyz`, so each descendant's override
  of `docs.capabilities/xyz` is its own row; under `all`, with `V(X)` =
  `docs.capabilities/xyz` and its chain `[docs…xyz]`, one row shown as
  `docs`'s, whose `statuses` name `docs`, `shared` (inherited), `desktop`
  and `server`, in that order.
- A group held only by `overrides` links (two descendants, the second
  overriding the first's): one row, shown as the object that overrides no
  other of the group.
- Taxonomy (no statuses): `statuses` is `None`; `overridden-by` computed
  the same way.

**Changes**, `tcw/store/base.py`, beside TCW-112's `combine`:

- `@dataclass(frozen=True) class ScopeObject: full_id: FullId; overrides:
  FullId | None`.
- `@dataclass(frozen=True) class ProjectView: project: str; view_object:
  FullId | None; status: str | None; sets_status: bool` (one covered
  project's answer at the id-path, for `statuses`).
- `@dataclass(frozen=True) class ScopeRow: shown: FullId; group:
  frozenset[FullId]; statuses: list[dict] | None; overridden_by:
  dict[FullId, list[FullId]]`.
- `scope_rows(id_path, *, order, own, v, chain, views) -> list[ScopeRow]`:
  `order` is the scope order of project IDs; `own` the descendants' own
  objects at the id-path (and, under `down`, `P`'s own object, passed as
  `v`); `v` is `V(X)` as Design 4.1 defines it for the scope, or `None`;
  `chain` the full identifiers `P`'s view combined at `X` under `all`
  (empty under `down`); `views` the `ProjectView`s for capabilities, or
  `None` for taxonomy. Groups by Design 4.2 (union of `overrides` links
  among scope objects, plus `V(X)`'s chain under `all`), rows by Design 4.3,
  `statuses` by Design 4.6 (an entry for each `ProjectView` whose
  `view_object` is in the group, `inherited` = not `sets_status`), and
  `overridden-by` by Design 4.7, each list in its owners' scope order. It
  reads no file.
- `row_order(rows, order)`: Design 4.4's order (id-path compared folder by
  folder, then the shown object's owner's place in `order`).
- `text_matches(name, body, query) -> bool`: today's rule, a
  case-insensitive substring of the name or the body
  (`tcw/store/fs.py:1823-1826`, `:2465-2468`), moved here so the rows of a
  scope and the stores' own `search` use one rule; both stores' `search`
  call it.

**Proves it:** the tests above; `tests/test_taxonomy.py`,
`tests/test_capabilities.py` (search unchanged); the full suite.

## Step 9 — the six tree commands take `--scope` and `--project`

Design 1.1 (the six), 1.6 b-e, g, h for trees, 1.8, 2.1-2.3 (trees), 4.1-4.9
(all but the `own` default and its hint, Step 11), 7.2 (their helps); AC 1,
8, 9, 10, 11, 12, 13, 14 (its first part), 15, 16 (its `down` part), 18,
19, 20, 21 (its `up`, `down`, `all` sentences), 29, 31 (its `--scope up`
part), 32, 40.

Every test here passes `--scope` explicitly; the default stays "what the
command does today" (choice 12) until Step 11, so no existing test changes.

**Tests first**, new `tests/test_scope_trees.py`, on `build_family`, one
test per criterion and sentence named above, with these notes:

- AC 1 (all eight commands accept `--scope down`, each `show` given an
  object it names; `tcw work tickets list --scope up`, `tcw work tags list
  --scope up` and `tcw capabilities drift --scope up` exit 2).
- AC 10 builds `docs` without its folder (manifest entry kept) for its last
  two sentences.
- AC 20 adds a second parent `ext` to `desktop` with `inherit:
  [capabilities]`, at a manifest folder that does not exist.
- AC 21's sentences on `up`, `down`, `all` exiting 7 in `desktop` with
  `shared` removed, and the second half (`docs` passing `all` and removed:
  exit 7 in `shared` under `down`, no line containing `is unavailable`).
- AC 29: `server`'s capabilities store declared at
  `https://example.invalid/server-caps.git` and not provisioned (TCW-107's
  provisioning declaration, the form Step 0 confirms); then `desktop`'s
  `def` state file holding text that is not valid YAML.
- A count, in AC 12's command, that each covered project's store is opened
  once (`FsTreeStore.__init__` wrapped).

**Creates** `tcw/tree_scope.py`:

- `@dataclass class TreeRow: obj (Term | Capability); statuses; overridden_by`.
- `list_rows(covered, axis, *, status=None, namespace=None, query=None) ->
  list[TreeRow]`:
  - `own`, or `--project P`: `P`'s store `list_all(local_only=True)` (its
    partial behaviour kept, TCW-112 Step 13), no grouping.
  - `--project Q` (`Q` not `P`): inside `covered.read`, `Q`'s store opened
    as another project's, `list_all(local_only=True)`; no grouping (choice 7).
  - `up`: `P`'s store `list_all()`, the view (outside any catch: its
    `InheritedUnavailable` stops the command, Design 4.9).
  - `down` and `all`: first `P`'s view, `list_all()`, outside any catch
    (Design 4.9, so a failure on `P`'s side stops before any other project
    is read, AC 21); then `P`'s own objects (`list_all(local_only=True)`,
    which no longer degrades since the view is built); then for each other
    member in `views_needed` (descendants; under `all` on capabilities also
    ancestors, Design 1.8), inside `covered.read`: its store's
    `list_all(local_only=True)` (descendants only), and on capabilities its
    view `list_all()` and `declaration(x)` for each of its `own_paths()`,
    for `ProjectView.sets_status`. Then for each id-path any of them has:
    `scope_rows` with `v` and `chain` (`P`'s `get_view(x)` and `chain(x)`
    under `all`; `P`'s own object under `down`).
  - Filters (Design 4.5): `--namespace` on the id-path's first folder;
    `--status` on the combined status under `own` and `up`, on any
    `statuses` entry under `down` and `all`; `search`'s query with
    `text_matches` on each row's own object. Order: `row_order`.
- `show_row(covered, axis, text) -> TreeRow` (Design 4.8, 2.3): a full
  identifier goes to `find_tree` (TCW-110 Step 8) whatever the scope, and
  under `down` and `all` its group's `statuses` and `overridden-by` are
  attached when it is a scope object or `V(X)` (computed with the same
  rows at its id-path); an id-path under `up` is `find_tree`'s form d
  (`P`'s view object); under `down` and `all` it is the row at the id-path:
  one row, `NotFound` for none, `UsageError` with Design 4.8's message for
  several; with `--project` the id-path names `<id>.<axis>/X` read with
  `find_tree`, and a full identifier of another project is a `UsageError`
  naming both. Under the interim default, today's `find_tree` call.

**Changes**

- `tcw/taxonomy/cli.py` (`list` `:141-147`, `show` `:164-171`, `search`
  `:182-188`) and `tcw/capabilities/cli.py` (`list` `:225-236` area, `show`,
  `search`, re-found in Step 0): each parser gains `--scope`
  (`choices=SCOPES`, `default=None`, with choice 13's help naming `own` as
  the default it will have from Step 11) and `--project`; one `--scope`
  example each; the `--json` helps name `projects`. `_list`, `_search`,
  `_show` (`tcw/taxonomy/cli.py:68-92`, `tcw/capabilities/cli.py:59-83`):
  with `args.scope is None` and no `--project`, today's code; otherwise
  `cover(...)`, `list_rows` or `show_row`, `covered.warn(<what>, ...)`
  before any row (`taxonomy entries`, `capabilities`; for `capabilities
  show`, Design 1.8's status wording; for `taxonomy show`, choice 6), and
  the records: `_record(obj)` plus `statuses` (capabilities, when not
  `None`) and `overridden-by` (when the scope is `down` or `all`), with
  `projects` in the document from `covered.projects_json()`.
- Text `show` (Design 4.6, 4.7; choice 8): `overridden by: <ids>` after
  the `overrides:` line when any; for capabilities under `down` and `all`,
  the block `status by project:`, one line per status in first-appearance
  order, `(no status)` for `null`, `(inherited)` after a project marked so,
  and `unavailable: <ids>` when any project was unavailable.

**Proves it:** the tests above (AC 14's last sentence and AC 16's, 17's,
21's and 31's `own` sentences wait for Step 11); `compare_outcomes.py
outcomes-step8.xml outcomes-step9.xml` (new IDs only); the full suite.

## Step 10 — the tests that rely on today's default say `--scope up` (conversion)

No production code changes. Design 4.8's last paragraph and spec Risks
("TCW-112's tests that read the view through `list` or `show <id-path>` …
gain `--scope up` here; the plan reads each failure rather than editing its
assertion").

1. **The failure list, before the change exists** (TCW-112's safeguard).
   Step 11's default change is written in the working tree as one patch:
   `None` read as `own` in the six commands, and the web routes untouched.
   The suite is run once; the failing test IDs are saved to
   `<scratchpad>/step10-fails.txt`; the patch is saved with `git diff --
   tcw/taxonomy/cli.py tcw/capabilities/cli.py tcw/tree_scope.py >
   <scratchpad>/step11-default.patch` and undone with `git apply -R` of
   that patch (never `git stash`, whose stack other sessions share).
2. **Every failure is read.** For each, the round records why it failed. A
   failure whose cause is a `list`, `show` or `search` of a taxonomy or
   capabilities command that relied on inherited content is converted; any
   other cause is a defect of Step 9 or of the patch, fixed before going on.
3. **The mechanical commit.** A one-off script walks each listed test
   function's syntax tree and, in every argument list given to `tcw`
   (`main([...])`, `run([...])`, `Family.run`, the subprocess calls Step 0
   lists) whose first two strings are `taxonomy` or `capabilities` and
   `list`, `show` or `search`, appends `"--scope", "up"`, leaving every
   other byte as it was. A call built in any other way is listed for the
   hand commit.
4. **The hand commit**: the calls the script listed, each changed to say
   `--scope up`, and nothing else.
5. **Proofs**: the inventory's assertion dumps are identical before and
   after the mechanical commit (no assertion changed); `compare_outcomes.py
   outcomes-step9.xml outcomes-step10.xml` exits 0 with an empty allowed
   list (no outcome changed, since `--scope up` lists the view as the
   default does); `git apply <scratchpad>/step11-default.patch`, the suite
   run again, and every ID in `step10-fails.txt` now passes (then `git
   apply -R`).
6. **The mutation check.** With a second scratchpad patch making `--scope
   up` behave as `own` in `tcw/tree_scope.py`, every converted test that
   asserts inherited content goes red; one that stays green is listed with
   its reason (for example, it asserts only an exit code), and the list is
   read. The failure reasons of at least ten red tests across different
   files are read and confirmed to be the missing inherited rows.

**Proves it:** the five proofs; the full suite.

## Step 11 — `own` is the default, and `show` by id-path names the project's own object

Design 1.2 (the default), 1.9 (its last sentence), 4.8 (`own` and the
hint), 4.9 (`own` keeps working); AC 2 (trees), 7, 14 (last sentence), 16
(own), 17, 21 (own), 31 (own).

**Tests first**, in `tests/test_scope_trees.py`:

- AC 2's tree sentences (in `desktop`, `tcw capabilities list` prints
  exactly `desktop.capabilities/abc` and `desktop.capabilities/def`, the
  same as `--scope own`; `tcw taxonomy list` prints nothing; no
  `projects`).
- AC 7: in `solo`, each of the eight commands with each scope prints the
  same standard output as with `--scope own`, and a test wrapping
  `project_folder` and `FsTreeStore.__init__` sees only `solo`'s.
- AC 14's last sentence, AC 16's `own` sentence, AC 17 (the hint, then
  `shared` removed: exit 4, not 7), AC 21's first sentence (`"partial":
  true`), AC 31's first sentence.

**Changes**

- `git apply <scratchpad>/step11-default.patch`, then: the six parsers'
  `--scope` default `own`; the `None` branches and `TODAY` comments of
  Step 9 deleted.
- `show_row` under `own` (Design 4.8): an id-path names `P`'s own object
  only: `has_own(x)` then `find_tree` (the own object, partial on
  `InheritedUnavailable` as TCW-112 Step 13 keeps it); when `P` has none,
  `NotFound` whose message adds, when `P`'s `get_view(x)` answers inside a
  `try` catching `UNAVAILABILITY_ERRORS` (and nothing is added on any of
  them), `; '<P>' inherits <full id> there: add --scope up, or name it by
  that full identifier`. A full identifier stays `find_tree`'s.

**Proves it:** the tests above; `compare_outcomes.py outcomes-step10.xml
outcomes-step11.xml` (new IDs only, every other outcome unchanged, which
Step 10 made true); `grep -n "TODAY\|scope is None" tcw/taxonomy/cli.py
tcw/capabilities/cli.py tcw/tree_scope.py` finds nothing; the full suite.

## Step 12a — tests stop passing `--local` (conversion)

No production code changes. With `own` the default, `--local` and no option
are the same command, so dropping it changes no outcome.

- The `--local` list of Step 0 item 6, in `tests/` and `evals/`: a one-off
  script removes the `"--local"` string from each argument list (and
  `local_only=True` stays where a test calls the store directly: that is
  the store's API, not the option). Calls built otherwise are done by hand,
  in a second commit.
- **Proofs**: the assertion dumps are identical across the mechanical
  commit; `compare_outcomes.py outcomes-step11.xml outcomes-step12a.xml`
  exits 0 with an empty allowed list; `grep -rn -- '"--local"' tests/
  evals/` finds only the tests Step 12b adds.

## Step 12b — `--local` is refused, and the passages that name it change

Design 5.1, 5.2, 7.2 (`--local` absent from help); AC 30, 39 (the sweep).

**Tests first**, in `tests/test_scope_trees.py`: AC 30 (`tcw taxonomy list
--local` and `tcw capabilities list --local` exit 2 with a message holding
`--scope own` and `drop --local`; neither `--help` contains `--local`); and
nothing is read first (a wrapped `FsTreeStore.__init__` records nothing).

**Changes**

- `tcw/taxonomy/cli.py` (`:143-144`) and `tcw/capabilities/cli.py`
  (`:232-233`): `--local` kept with `help=argparse.SUPPRESS`; given, `_list`
  raises `UsageError("list --local is removed in TCW 4: --scope own, the
  default, already lists only this project's own objects; drop --local")`
  as its first line. The taxonomy example `taxonomy list --local --json`
  (`:143`) becomes `taxonomy list --scope up --json`.
- The passages (Design 5.2), each changed only as far as saying that the
  default lists the project's own objects and `--scope up` adds the
  inherited ones: `README.md:413`, `skills/capabilities/SKILL.md:176`,
  `docs/guide/taxonomy-and-capabilities.md:32` and `:98`, and this
  repository's 3.x records
  `docs/capabilities/taxonomy/browse-the-term-forest/description.md` and
  `docs/capabilities/capabilities/browse-capabilities-by-status/description.md`
  (Step 18 writes the rest of those records' changes).

**Proves it:** the tests above;
`tests/test_documented_cli_surface.py` (`test_documented_verbs_and_flags_exist`,
`test_every_command_named_in_shipped_text_exists`) and
`tests/test_shipped_text.py`; Design 5.2's sweep, `grep -rn -- '--local'
skills/ agents/ tcw/ README.md docs/guide docs/capabilities | grep -v
"tcw-config.local\|manifest.local"`, finds only the hidden option and its
refusal in the two CLI files; the full suite.

## Step 13 — the web server: scope and project, answers, `scopes`

Design 3.5 (a request is one command), 6.1, 6.2; AC 33; TCW-112's handoff
(`declaredDescription` for another project's capability). Choices 9, 10.

**Tests first**, new `tests/serve/test_scope.py`, `tcw serve` started in
`shared` of `build_family` (`tests/serve/conftest.py:97`'s `start`):

- AC 33, every sentence (the `capabilities` equality read as choice 9).
- `GET /api/taxonomy?scope=up` from `desktop` lists `shared.taxonomy/invoice`;
  `GET /api/taxonomy` answers `{"terms": [...]}` with `desktop`'s own only.
- `GET /api/capabilities/abc?scope=down` answers the record with
  `statuses` and `overridden-by` as AC 13 gives them, and `projects`.
- `GET /api/capabilities/desktop.capabilities%2Fabc?scope=down` answers
  `declaredDescription` equal to `desktop`'s own `description.md` text, or
  `null` when `desktop` declares none (TCW-112 AC 44, the handoff; spec
  gap G1).
- `GET /api/work/<shared's folder>?scope=down` gives `children` across the
  scope (Design 3.3).
- Two concurrent `GET /api/work?scope=down` requests against a fake Jira
  each make their own search (choice 10: nothing is kept across requests),
  and one request listing two projects that share a search key makes one.

**Changes**

- `tcw/serve/server.py`, `_api` (`:299-311`): the handler call is wrapped
  in `command_span()` (choice 10).
- New `scope_of(request) -> Covered` in `tcw/serve/records.py` (beside
  `jsonable`): reads `scope` (default `own`) and `project` from
  `request.query`, calls `cover(request.root, ...)`, and turns its
  `UsageError`, or an unknown scope, into `usage(...)` (400 `{"code":
  "usage"}`).
- `tcw/serve/records.py`, `list_terms` (`:70-71`) and `list_capabilities`
  (`:149-150`): `list_rows(scope_of(request), axis)`; the answer is
  `{"terms": [<jsonable(row.obj) with the CLI record's keys, choice 9>],
  "projects": ...}` (and `"capabilities"` for the other); `projects` only
  when the scope is not `own`. `get_term` and `get_capability`: `show_row`
  for the route key and scope; today's envelope (`term` or `capability`,
  `coreRevision`, and `declaredDescription` from
  `get_capability_detail(row.obj.full_id)`, TCW-112 Step 17b) plus
  `projects`. The CLI record functions `_record` of
  `tcw/taxonomy/cli.py` and `tcw/capabilities/cli.py` are moved to
  `tcw/tree_scope.py` as `term_record` and `capability_record`, which both
  the CLI and the server import, so the two cannot drift.
- `tcw/serve/work.py`, `board` (`:203-234`): with scope `own` and no
  `project`, today's code. Otherwise `list_scope` with `need_every`
  (Step 5), the served project read first with today's fallback
  (`:216-226`) kept for it alone (Design 6.2); every other project
  unavailable through `covered.read`; `items` the records of
  `item_record(i, scoped.every, <owner's layout>)`; `people` merged from
  each project's backend; `projects` added. `detail` (`:249-294`): the
  `scope` query decides `children` and `blocks` as `tcw work show` does
  (Step 6).
- `tcw/serve/work.py`, `project` (`:150-181`): gains `"scopes": {s: [m.id
  for m in registry.scope_members(s)] for s in SCOPES}` (Design 6.2).
- `web/client/src/model/types.ts`: `TProject.scopes`, `TBoard.projects`,
  `TScopeProject`; `TaxonomyItem` and `CapabilityItem` gain `statuses?`,
  `"overridden-by"?`; new `TaxonomyList`, `CapabilityList` answer types.
  `web/client/src/ui/app.tsx`, `loadRecords` (`:267-279`): reads
  `.terms` and `.capabilities` from the new answers. No scope control yet,
  so the page asks with no `scope` and shows the served project's own
  objects, which is Design 6.1's default.
- The serve tests that read inherited entries from `GET /api/taxonomy` or
  `GET /api/capabilities` (found by running the suite; expected in
  `tests/serve/test_records.py`, TCW-110's `tests/serve/test_full_identifiers.py`
  and TCW-112's `tests/serve/test_overrides.py`) gain `?scope=up` and read
  the object answer; each is listed in `allowed-step13.txt` with Design 6.1
  and 6.2. `pnpm build`.

**Proves it:** the tests above; `tests/serve/` green; `compare_outcomes.py
outcomes-step12b.xml outcomes-step13.xml allowed-step13.txt`; the web gate;
the full suite.

## Step 14 — the web server: another project's object, read-only

Design 6.3, 6.4, 6.5; AC 34. TCW-114's router check is relied on; this
step changes only what the work and files write routes name.

**Tests first**, new `tests/serve/test_other_project.py`, `tcw serve` in
`shared`, `K` = `desktop.work%2F2026-10-01-desktop-item`:

- AC 34, every sentence: the three reads answer 200 with what `desktop`'s
  folder holds; each of the five writes (`PATCH /api/work/K`, `POST
  /api/work/K/comments`, `PUT /api/work/K/files/<a file>`, `POST
  /api/work/K/files`, `PUT /api/work/K/declaration`) answers 403 with
  `code` `read-only` and `belongs to project 'desktop'`, and every file
  under `desktop`'s folder is byte for byte what it was (a snapshot of
  paths and bytes before and after); so does `PATCH` of
  `desktop.work%2Fno-such-item`; `GET
  /api/capabilities/desktop.capabilities%2Fabc?scope=down` answers 200;
  `POST /api/resolve` with `tcw://desktop.work/2026-10-01-desktop-item`
  answers `ok` with that full identifier as `key`, and with
  `tcw://mobile.work/x` answers `other-project`.
- The work route key rule as a unit (`work_key`): `desktop.work/x` names
  owner `desktop` without opening anything (a wrapped `open_backend`
  records nothing); `x` and a ticket key name the served project.
- A write handler reached directly with another project's full
  identifier (the route's `writes` patched out, the way TCW-114 Step 4's
  extra-route test registers a route): 404, nothing written (Design 6.5's
  second paragraph).
- TCW-114's `tests/serve/test_route_writes.py` stays green: the same routes
  are marked writes.

**Changes**

- `tcw/serve/work.py`: new `work_key(request, text) -> WorkKey(project,
  name, full: FullId | None)`: `sort_input(text, "work", KEY)`; form a gives
  the identifier's project and folder; anything else the served project
  and the text (Design 6.4). New `context_for(request, project_id) ->
  WorkContext`: the served project → `context(request)`; another → its
  root from `Locator.of(request.root).owner_root(project_id,
  named_by=request.root)` (its outcomes propagate: `Unreachable` → 503,
  `UnknownProject` → 500 as any `TcwError`), its configuration with
  `read_work_config(root, personal=False, registry=...)` and its backend
  with `request.services.open_project(project_id, request.root)` (choice 4).
- `item_folder(ctx, name)` (`:237-246`): a full identifier naming `ctx`'s
  project gives its folder by today's rule; one naming another project is
  `not_found` (Design 6.5's second paragraph).
- `detail` (`:249-294`) and `tcw/serve/files.py`'s `_target` (`:168-172`)
  for the read routes (`get_file`, `get_declaration`): `work_key`, then
  `context_for(request, key.project)`, then `item_folder` on that context.
  The write routes keep `context(request)` (the served project only).
- Every work and files write route's `writes` (TCW-114 Step 4; `PATCH
  /api/work/<key>`, `POST .../comments`, `PUT .../files/<path>`, `POST
  .../files`, `PUT .../declaration`): a full identifier key → `[Written(key.full,
  None)]`, read from the identifier alone; otherwise TCW-114's answer
  (`item_folder` made into the served project's full identifier). One
  helper, `writes_item(request)`, shared by the five routes.
- `tcw/serve/records.py`, `resolve` (`:210-241`, as TCW-110 Step 10 leaves
  it): an address whose owner is another project that `Locator.exists`
  (TCW-112 Step 13) finds answers `{"ok": true, "axis": <namespace>, "key":
  <the full identifier>}`; `other-project` stays only for an `unresolved`
  outcome (a project not on this machine), Design 6.4.

**Proves it:** the tests above; `tests/serve/test_route_writes.py`,
`tests/serve/test_work_write.py`, `tests/serve/test_files.py`,
`tests/serve/test_no_process.py`; the full suite.

## Step 15 — the client: the scope control and the project filter

Design 6.6; AC 35 (its scope-control sentences). Choice 14.

**Tests first**:

- New `web/client/src/model/scope.test.ts`: `scopeParams("?scope=down&project=desktop")`
  is `{scope: "down", project: "desktop"}`; an unknown value reads as
  `own`; `withScope("/api/work?all=1", {scope: "down"})` is
  `/api/work?all=1&scope=down`; `own` with no project adds nothing.
- New `web/client/src/ui/scope-control.test.tsx`: hidden when
  `scopes.all` has one project; otherwise offers `own`, `up`, `down`,
  `all`, each labelled with what it covers, `own` chosen by default; the
  project filter offers the current scope's projects and "all of them".
- `web/client/src/ui/app.test.tsx`: choosing `down` requests
  `/api/work`, `/api/taxonomy` and `/api/capabilities` each with
  `scope=down`, and the location's search becomes `?scope=down`; opening
  the app at `/?scope=down&project=desktop` requests with both.

**Changes**

- New `web/client/src/model/scope.ts`: `SCOPES`, `scopeParams(search)`,
  `withScope(path, scope)`.
- New `web/client/src/ui/scope-control.tsx`: the two selects, from
  `project.scopes`.
- `web/client/src/ui/app.tsx`: the scope and project read with
  `useSearchParams` (choice 14) and kept on every path the app navigates
  to; `loadBoard` (`:257-265`) and `loadRecords` (`:267-279`) request
  through `withScope`, and reload when either changes; the header renders
  `ScopeControl`.
- `web/client/src/test-fixtures.ts`: the project fixture gains `scopes`.
- `pnpm build`.

**Proves it:** the tests above; the web gate; the full suite.

## Step 16 — the client: read-only display, followed links, notices, mixed status

Design 6.3 (client route keys), 6.7, 6.8, 6.9, 6.10; AC 35 (the rest), 36.

**Tests first**:

- `web/client/src/ui/content-views.test.tsx`: a capability whose `owner` is
  not the served project shows `owned by <owner>` and no Edit button; one
  the project owns shows Edit.
- `web/client/src/ui/work-views.test.tsx` and
  `web/client/src/ui/shared-components.test.tsx`: a board row and a tree
  row of another project's object show the same badge; `SlugLink` for
  another project's item that the resolver answers `ok` is a link to
  `/work/<encoded full id>`, and for one it answers `other-project` stays a
  labelled name.
- `web/client/src/ui/app.test.tsx`: another project's work item page has no
  property form, comment box, file editing, new-file action or declaration
  editing; a list answer naming an unavailable project shows one notice
  with its reason (containing `tcw project provision mobile` in the
  fixture); a capability row under `down` with AC 13's `abc` statuses
  shows `Missing(1), Supported(1), Omitted(1)`, and its page lists each
  status with its projects, `inherited` marked, each project with an own
  object linked to it, and an `unavailable` line.
- `web/client/src/ui/route-utils.test.ts`: `itemKey` of `desktop.work/x`
  served from `shared` is the whole full identifier; of `shared.work/x`,
  `x` (Design 6.3 for work).
- `web/client/src/model/scope.test.ts`: `statusSummary(statuses)` gives
  each status with its count, in first-appearance order (Design 6.9).

**Changes**

- `web/client/src/ui/content-views.tsx`: `EditOrInherited` (`:167-191`)
  becomes `EditOrOwned`, showing `owned by <owner>` when `owner !==
  project.id`, else the Edit button; the capability page gains the status
  block (Design 6.9).
- `web/client/src/ui/work-views.tsx`: `SlugLink` (`:53-84`) asks the link
  resolver the Markdown links use (`web/client/src/ui/link-context.ts`)
  with `objectAddress(fullId)` and links to the answered key when `ok`;
  board rows show the badge.
- `web/client/src/ui/shared-components.tsx`: tree rows show the badge and,
  under `down` and `all`, the status summary.
- `web/client/src/ui/app.tsx`: the item page's forms, comment box, file
  editing, new-file action and declaration editing are rendered only when
  the item's `owner` is the served project; the unavailable notices above
  each list from `projects`.
- `web/client/src/ui/route-utils.ts`: `itemKey`'s work branch keeps the
  folder only for the served project's item.
- `web/client/src/model/scope.ts`: `statusSummary`.
- `pnpm build`; `pnpm check:build` (AC 36: `tcw/serve/dist` equal to what
  is committed).

**Proves it:** the tests above; the web gate; `pnpm check:build`; the full
suite.

## Step 17 — the audit procedure covers the family

Design 7.1; AC 37.

**Tests first**, in `tests/test_shipped_procedures.py`: `tcw work procedure
audit-backlog` prints text containing `tcw work list --scope down --json`,
`unavailable` and `tcw work list --scope down --all --json`, no line telling
the agent to start from a bare `tcw work list`, and (TCW-114 Step 7's
test, kept) no `--project`.

**Changes**, `tcw/work/procedures/audit-backlog.md` (as TCW-114 leaves it):
the start (`:7-12` at `62e41ec5`) becomes Design 7.1's: start with `tcw work
list --scope down --json`; name every project in its `projects`; report each
marked `unavailable` as not audited, with its reason, never as clean; the
per-item reports grouped under one heading per project, in scope order; a
blocker in another project looked up with `tcw work show <its full
identifier>` (the "Blocked" bullet, `:33-35`); the across-items agent reads
`tcw work list --scope down --all` (`:72`); the final check compares `tcw
work list --scope down --all --json` before and after (`:118-120`).
`tests/fixtures/prompt_fallback/` is regenerated if it holds the
procedure's text (Step 0 checks).

**Proves it:** the test above; `tests/test_shipped_text.py`,
`tests/test_documented_cli_surface.py`; the full suite.

## Step 18 — this repository's records

With the lifecycle `tcw` (the header), in this repository's 3.x layout, as
TCW-108 Step 14 and TCW-112 Step 21 do, so the records gate passes for
every entry of `capabilities.yaml`:

- **New**, with `tcw capabilities add`, status `Supported`:
  `cli/choose-which-projects-a-list-or-show-command-covers` and
  `capabilities/see-each-projects-status-for-a-capability`, each with the
  spec's Capability changes sentence.
- **Changed**: the `description.md` of each record in `capabilities.yaml`'s
  `changed:` list, with its sentence from the spec; the two `--local`
  records of Step 12b get the rest of their sentence here; `cli/reference-a-tcw-object`'s
  description (`:6-8`) no longer says `tcw serve` shows another project's
  object as a labelled name.
- **Taxonomy**: new term `scope` (`tcw taxonomy add Scope`) relating to
  `project`; `local-web-app`'s description gains the scope control and the
  read-only display.

The descriptions are Markdown outside `docs/work/`, so
`tests/test_documented_cli_surface.py` checks every `tcw …` command they
name in backticks.

**Proves it:** with the lifecycle `tcw`: `tcw validate`, and `tcw work
advance TCW-113 --dry-run` at the end of implement (the records gate);
`tests/test_documented_cli_surface.py` in the full suite.

## Step 19 — Documentation Sync

Each documentation entry (`tcw work docs`), evaluated with the
`documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: `--scope`, `--project`, `--local` removed, the web app's scope control | `README.md:413` changed in Step 12b (Design 5.2, the passage the scans would fail on); the rest deferred to TCW-117 (spec Design 7.3, decided by the dispatching session on 2026-10-22), with Step 20's note. |
| `docs/guide/jira.md` [Jira-Change] | yes: a scope's projects sharing one Jira project are read with one search | Deferred to TCW-117 (Design 7.3), with Step 20's note. |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `cli.md`, `web-viewer.md`, `taxonomy-and-capabilities.md`, `multi-repo.md` | `taxonomy-and-capabilities.md:32`, `:98` changed in Step 12b; the rest deferred to TCW-117, with Step 20's note. |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written in implement, in plain language, as `docs/release-notes/upcoming/TCW-113-tcw-4-0-scope-project-and-a-project-s-whole-family-in-the-cli-and-the-web-app.md`: every list and show command takes `--scope own|up|down|all` (the project alone, the default; with the projects above it; with the projects below it; both), never a sibling; `--project <id>` keeps one project's results; `tcw taxonomy list` and `tcw capabilities list` now list only the project's own entries, and `--scope up` adds the inherited ones; `show` of an inherited entry by its path needs `--scope up` and says so; `--local` is removed; a related project that is not on this machine or cannot be read is named in a warning, with the command that fetches it, and in the JSON's `projects`, and the command still succeeds; under `--scope down` or `all` each capability is listed once, with the status each project gives it, in the JSON and in `show`; an epic's parts in other projects show as its children with `--scope down`; projects sharing one Jira project and account are read with one search; the backlog audit covers the child projects; the web app has a scope control and a project filter, shows other projects' objects read-only and follows links to them. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written in implement, same file name under `docs/changelogs/upcoming/`, grouped: **Added** (`ProjectRegistry.scope_members`, `covering_scope`, `SCOPES`, `ScopeMember`, `UNAVAILABILITY_ERRORS`, `is_unavailability`, `scope_rows`, `ScopeObject`, `ProjectView`, `ScopeRow`, `row_order`, `text_matches`; `tcw/scope.py`, `tcw/tree_scope.py`, `tcw/work/scoped.py`; `--scope` and `--project` on the eight commands; `projects`, `statuses`, `overridden-by` in `--json`; `command_state`, `command_span`; `GET /api/project`'s `scopes`; the client's scope control), **Changed** (the default of the six tree commands is `own`; `show` by id-path; `children` and `blocks` across a scope; the Jira backend's `list` keeps a search for one command; `GET /api/taxonomy` and `GET /api/capabilities` answer an object; work route keys and the write routes' `writes`; `/api/resolve` answers `ok` for another project's object; `audit-backlog`), **Removed** (`--local`, refused with a message) and **Internal** (`tests/families.py`; the tests converted to `--scope up` and off `--local`). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: `work`, `taxonomy`, `capabilities` | `skills/capabilities/SKILL.md:176` changed in Step 12b (Design 5.2); the rest deferred to TCW-117 (Design 7.3), with Step 20's note. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no: no configuration key is added, removed or changed (Non-goals, "A configured default scope") | Nothing. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: UC-3, UC-4, UC-5, UC-6 | Deferred to TCW-117 (Design 7.3), with the spec's Notes list. |

Both `upcoming/` files are formatted with `prettier`, and
`tests/test_upcoming_entries.py` checks their names and headings.

**Proves it:** both files exist and pass `tests/test_upcoming_entries.py`;
the documentation gate when the item leaves implementation.

## Step 20 — notes for the later children

Comments the dispatching session posts (the text goes in the implement round
first): the spec's Handoffs (its Notes) as written, plus what planning
added:

- **TCW-115:** `--project`'s refusal (Design 2.2) is built in one place,
  `tcw/scope.py`'s `cover`, where `tcw project path <id>` can be added.
- **TCW-117:** the spec's Notes list, plus: the warning wording of a
  `show` (choice 6); the web app's list records are the server's full
  objects with the CLI record's keys (choice 9); `--project` never groups
  (choice 7); the README's table row for `tcw capabilities list` (changed
  only as far as `--local` in Step 12b).
- **TCW-50:** ordering is `row_order` (trees) and scope order then each
  backend's order (work); limits apply per project.

## Step 21 — the suite as CI runs it

AC 41, done locally as TCW-110 Step 19 and TCW-108 Step 17 do, since CI does
not run on `v4`: bare `.venv/bin/pytest` from the worktree's root, never
`python -m pytest`; `pnpm install --frozen-lockfile` and `pnpm check:build`;
and beyond CI, `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint` and
`pnpm exec prettier --check` over every file this item changed or created
that `.prettierignore` does not exclude. A failure is fixed in the step it
belongs to, not with a skip.

## Verification the tests cannot do

- **The QA plan's scenarios** (the ticket's QA plan comment, scenarios 1-10)
  are run by hand at qa with `.venv/bin/tcw` in throwaway projects under the
  scratchpad, with the current folder set there, never inside the worktree.
  Scenario 6 uses the fake Jira through the suite's AC 28 test, or a Jira
  test project if the person running qa has one; never this repository's
  board.
- **The web app in a browser** (scenario 8): `tcw serve` on a scratchpad
  family, in the dedicated Claude Chrome profile, never the default one;
  scenario 8's extra step with `curl` against the running server.
- **Concurrent requests** under a real browser (several lists loading at
  once after a scope change) cannot be timed in a test; scenario 8 is
  watched for a request answered with another request's projects.

## Self-review against the spec

**Every criterion to its step.**

| AC | Step(s) | AC | Step(s) |
| --- | --- | --- | --- |
| 1 | 5 (work list), 9 (all eight) | 22 | 5 (list), 6 (show) |
| 2 | 5 (work), 11 (trees) | 23 | 5 |
| 3 | 3 (registry), 5 | 24 | 6 |
| 4 | 3, 4 (refusal), 5 (list), 6 (show) | 25 | 6 |
| 5 | 5 | 26 | 5 |
| 6 | 4 (refusal), 5 | 27 | 5 |
| 7 | 3 (registry), 11 (commands) | 28 | 7 |
| 8 | 9 | 29 | 9 |
| 9 | 9 | 30 | 12b |
| 10 | 3, 9 | 31 | 9 (`up`), 11 (`own`) |
| 11 | 9 | 32 | 8, 9 |
| 12 | 8, 9 | 33 | 13 |
| 13 | 8, 9 | 34 | 14 |
| 14 | 9, 11 (last sentence) | 35 | 15, 16 |
| 15 | 8, 9 | 36 | 16 |
| 16 | 9 (`down`), 11 (`own`) | 37 | 17 |
| 17 | 11 | 38 | 5 |
| 18 | 8, 9 | 39 | 12b, 18, 21 |
| 19 | 8, 9 | 40 | 9 |
| 20 | 9 | 41 | 21 |
| 21 | 9 (`up`, `down`, `all`), 11 (`own`) | | |

**Every design rule to its step.** 1.1-1.4: 3, 5, 9; 1.5-1.8: 4, 5, 6, 9;
1.9: 3, 11; 2.1-2.3: 4, 5, 6, 9; 3.1-3.4: 5, 6; 3.5: 7, 13; 4.1-4.7, 4.10:
8, 9; 4.8: 9, 11; 4.9: 9, 11; 5.1-5.2: 12a, 12b; 6.1-6.2: 13; 6.3-6.5: 14,
16; 6.6: 15; 6.7-6.10: 16; 7.1: 17; 7.2: 5, 6, 9, 12b; 7.3: 12b, 18, 19.

**Every step traces back.** Steps 0-2 and 10, 12a are the safeguards and
conversions the Risks and the brief ask for; 18-21 are the records, the
documentation entries, the notes and CI.

**The suite stays runnable at every boundary.** The options arrive with the
code that serves them (work in 5-6, trees in 9); the tree default keeps
today's behaviour until the tests that rely on it say `--scope up` (9, 10,
11); `--local` keeps working until its callers stop passing it (11, 12a,
12b); the web answer's shape changes with the client's reader in one step
(13); the write routes' `writes` change in the same step as the reads that
make another project's key reachable (14).

**Names are consistent**: `scope_members`, `covering_scope`, `cover`,
`Covered`, `list_scope`, `list_rows`, `show_row`, `scope_rows`, `work_key`,
`context_for`, `writes_item`, `command_state`, `command_span`,
`_kept_search` each appear in one step that creates it and the steps that
use it.

## Spec gaps found while planning

Each handoff the spec does not yet reflect, and each gap, with how the plan
handles it.

- **G1. TCW-112's AC 44, `declaredDescription`** (its plan's revised
  handoff, which arrived after this spec's revision). A web body edit
  writes only the declared description. The plan: the detail answer for
  another project's capability carries the **owner's** declared
  description (Step 13's test), and since that page has no Edit button
  (Step 16), the field is display only there.
- **G2. TCW-112's `Locator.exists(full_id, named_by)`** for an existence
  check without a view: `/api/resolve`'s `ok` for another project's object
  uses it (Step 14), so resolving a link never builds another project's
  view.
- **G3. TCW-112's `chain(id_path)`** is `V(X)`'s chain under `all` (Step 9,
  feeding Step 8).
- **G4. TCW-112's handoff that `--project <id>` reads `get_local` of that
  project's store**: the listing uses `list_all(local_only=True)` of that
  store and `show` uses `find_tree` on `<id>.<axis>/X`, which reads the
  owner's `get_local` (Steps 9, 11).
- **G5. TCW-109's revised handoff**: a project read for itself needs the
  command's registry; every read of another project passes it (choice 4,
  Steps 5, 13, 14).
- **G6. TCW-114's handoff**: `GET /api/project` no longer carries the
  connected-project rows, so `scopes` (Design 6.2) is the client's only list
  of the family's projects (Steps 13, 15).
- **G7. TCW-114 Step 7's test** that `audit-backlog` names no `--project`:
  kept, and Step 17's text names none.
- **G8. The warning a `show` gives** (Design 1.8): choice 6.
- **G9. "Exactly the records"** for the web list answers (Design 6.2, AC
  33): choice 9, and defect D1 below.
- **G10. `--project` with `down` or `all`** on the trees: choice 7.
- **G11. A request is one command** under a threaded server: choice 10.
- **G12. AC 36 says `pnpm build` in `web/client`**: the build and its check
  run from the repository root (`package.json`'s `build` and
  `check:build`), as every sibling plan runs them; Step 16 does so.
- **G13. Where the status block goes in `show`**: choice 8.

## Spec defects found while planning

- **D1. Design 6.2 and AC 33: the web list answers cannot be exactly the
  CLI's `--json` records.** The client reads `description`, `body`,
  `fields`, `modified`, `relates_to` and `vocabulary` from list rows, which
  the CLI records do not carry. The plan keeps the server's full objects
  with the CLI record's keys added (choice 9) and asserts AC 33 as "same
  rows, same order, each holding the CLI record". Suggested spec wording:
  "each array holds one object per record `tcw <axis> list --scope …
  --json` prints, in the same order, each holding that record's keys and
  values".
- **D2. Design 1.8's `show` wording** ("so its status is not shown") is
  wrong for `tcw work show` and `tcw taxonomy show`. The plan's wording is
  choice 6. Suggested spec wording: "`tcw capabilities show` says `… so its
  status is not shown`; the other two shows say `… so its <what> are not
  included`".

Neither changes what the spec asks for, so the item stays at plan; the
dispatching session decides whether the spec is amended before implement.

## Decisions taken while planning

Choices 1-14 above, each with its reason. The two with the most effect on
behaviour are choice 9 (the web records) and choice 10 (the per-request
state is thread-local); the one with the most effect on the work is choice
12 (an interim default so the conversion and the default change are
separate steps).
