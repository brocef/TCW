# Plan — TCW 4.0: the `tcw project` command group

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`).

**Where the references point.** File and line references are to commit
`62e41ec5` on `v4`. Its committed `tcw/`, `tests/`, `evals/` and `scripts/`
are identical to `d2d02829`, the commit the spec cites, so the spec's line
numbers and this plan's agree. At that commit only TCW-106's code has
landed. This item lands tenth and last of the code items, after TCW-106,
TCW-107, TCW-110, TCW-108, TCW-111, TCW-109, TCW-112, TCW-114 and TCW-113
(the spec's Notes and the epic's order), so almost every piece of code it
changes will look different by the time it starts. Where a step uses code an
earlier item writes, it names that code by the name the earlier item's plan
or spec gives it, cited by step or by design rule, never by line number; for
TCW-113, which has no plan yet, by its spec. **Step 0 re-reads every
citation on the merged `v4` and corrects this plan before Step 1.** A
citation that cannot be found then is fixed in this plan, never worked
around in the code.

**The gate at every step boundary.** Every step writes its tests first and
sees them fail for the reason they name, then makes the change, and ends with
the named tests passing and the **whole Python suite** passing:
`.venv/bin/pytest` with no arguments, from the worktree's root, as CI runs it
(bare `pytest`, not `python -m pytest`). This item changes no web client
code, so TCW-110's web gate (`pnpm exec tsc --noEmit`, `pnpm test`,
`pnpm lint`, `pnpm exec prettier --check …`, `pnpm build`) is run only if
Step 6's check of `_projects` finds a client change is needed, which it
expects not to. A step that cannot end green is two steps.

**Which `tcw` drives this repository's lifecycle.** The `tcw` first on
`PATH`, the primary checkout's install of `main` (3.x), exactly as TCW-110's
plan header and TCW-114's say: the 4.0 code is run only by the suite (whose
projects are under `tmp_path`) and in throwaway project folders under the
scratchpad, with the current folder set there; never from a folder inside
the worktree, never with `.venv/bin` first on `PATH` in a shell that runs a
lifecycle command. While `tcw/` is being edited in the worktree, this item's
lifecycle moves are made by hand (CLAUDE.md's exception), and the implement
round says so.

**No network in any test.** Every remote is a git repository the test makes
in `tmp_path` (a bare repository, `git init --bare`, pushed to from a work
folder), named in a manifest entry by its path. **The stand-in `git`**
(spec, Acceptance criteria preamble) is built once, in Step 11, as a pytest
fixture.

---

## Decided while planning, each with its reason

These are choices the spec leaves to the plan. Each is the simpler or safer
option of those the TCW-99 design and the sibling specs allow.

1. **Where the code goes.** The group is registered from a new module,
   `tcw/project_cli.py`, which owns `add_subparser` for `tcw project` and its
   six verbs. The code of the verbs that exist today stays where it is:
   `run_init` and `run_provision` in `tcw/cli.py`, `connected` and `_list` in
   `tcw/projects_cli.py`, `render` and `_show` in `tcw/config_cli.py`. Those
   two modules lose only their `add_subparser`. *Reason:* the tests import
   `render`, `_scalar` and `_entry` from `tcw/config_cli.py`
   (`tests/config/test_config_show.py:11`, `:250-254`,
   `tests/config/test_config_edges.py:9`,
   `tests/config/test_personal_merge.py:193`) and the web app imports
   `connected` (`tcw/serve/work.py:146`, `:549`); TCW-114's guard on reads of
   the current folder lists `tcw/projects_cli.py:56` and
   `tcw/config_cli.py:254` (TCW-114 plan, Step 5's list of ten reads, kept
   by its Step 21). Moving the code would change all of those for no gain.
   The project rounds of provisioning go in a new `tcw/provision.py`; the
   clone, staging and move go in `tcw/store/fs.py`, beside
   `FsStoreProvisioner` (`:3389`), reusing `_git` (`:147`),
   `_no_prompt_env` (`:164`) and `_git_reason` (`:3094`).
2. **The old commands stay registered until the tests have moved.** Step 2
   adds the group beside the old commands, Step 3 moves every test and
   document to the new names mechanically (with an inventory, an outcome
   comparison and a mutation check), and only Step 4 removes the old
   commands. *Reason:* the removal then changes no test that was not read by
   hand, and the mechanical rename is checked against a suite in which both
   names work, so any changed outcome is the rename's fault.
3. **Documents that name a removed command get the new command's name in
   this item, and nothing else.** The spec (Design 1.4) leaves
   `docs/guide/`, `README.md`, `AGENTS.md`, `skills/` and `docs/use-cases.md`
   to TCW-117, but `tests/test_documented_cli_surface.py` checks every `tcw`
   command written in every Markdown file outside its `ARCHIVAL` list
   (`:38-43`), so the suite cannot pass at Step 4 while those files name
   `tcw init`. Following TCW-114's precedent (its plan, Step 23's note to
   TCW-117: "the passages Step 7 changed only as far as naming a working
   command"), Step 3 replaces the command names only; TCW-117 rewrites the
   prose. This is reported as a spec defect (below).
4. **The removed-command table is checked first, at the top level only.**
   In `SuggestingParser._hint` (`tcw/cli_suggest.py:126-145`), which
   `_check_value` (`:106-124`) calls for the added line, the first test is:
   the parser is the top-level one (`here == ()`) and the word is a key of
   `REMOVED_COMMANDS`; then the line is the table's line and nothing else.
   `_check_value` already appends whatever `_hint` returns to argparse's
   invalid-choice message, so it is unchanged. *Reason:* Design 1.2
   says "checked before every other rule"; a second hint would only dilute
   it.
5. **The method of Design 8.1** is `FsProjectRegistry.placement(project_id,
   named_by=None) -> Placement | None`, on `FsProjectRegistry` only
   (`tcw/store/project.py`), with `Placement(id, asked_by, folder, entry,
   owner, entry_folder, repository_folder)`: `asked_by` the root of the
   project whose lookup decided; `folder` the folder found, or `None`;
   `entry` the deciding `ManifestEntry` (TCW-107 plan, its manifest parser in
   `tcw/store/manifest.py`) or `None`; `owner` the root of the project whose
   `.tcw/` holds that manifest (for a personal file a worktree borrows,
   TCW-107 Design 4.2, the worktree's root, since that is the project that
   reads it); `entry_folder` the entry's `path` resolved (TCW-107 Design 2.3,
   4.3); `repository_folder` that with `subfolder` removed (TCW-107 Design
   1.6). Without `named_by` it returns the first answer this registry
   recorded for the ID (TCW-107 plan, Step 3, `_answers`) and looks nothing
   up; with `named_by` it looks up exactly as `project_folder` does,
   raising `UnknownProject` or `ProjectGraphError` the same way. *Reason:*
   Design 8.1 asks for "a project ID and the root of the project that names
   it"; provisioning also needs who asked (for 7.8's way out) and who owns
   the manifest (for 7.8's bound), which the answer already holds. Reported
   as a spec defect in that it names fewer fields than the command needs.
6. **Which projects each form fetches.** No argument: `registry.unreachable()`
   (TCW-108 plan, its walk order, one record per ID). `<id>`:
   `project_folder(<id>, <active root>)` first (its four outcomes), then
   `load_order(<id>).missing` (TCW-108 Design 4.6). Each round's IDs are
   those, less the IDs this run already attempted.
7. **The order of the checks before any contact**, per project of a round:
   (1) no deciding entry, or an entry with no repository: reported, not a
   failure (7.5); (2) a URL or branch beginning with `-` (7.9); (3) the bound
   (7.8); (4) the repository folder's state, `.git`-only then occupied
   (7.6); then, across the round, (5) grouping by repository folder (7.7).
   *Reason:* each check needs only what the earlier ones passed, and the
   cheapest come first; the first that fails names the project's refusal.
8. **The bound, exactly.** Every folder compared is `Path(os.path.realpath(…))`.
   A bounded entry's `path` written as absolute or beginning with `~` is
   refused before any resolving, with 7.8's first message (Design 7.8 lists
   both as refused; resolving alone would let an absolute path that happens
   to land directly inside the bound through). Allowed means
   `target.parent == bound` and `not target.name.startswith(".")`. Refused
   outright when `Path.home()` resolved is the bound or inside it
   (`home == bound or home.is_relative_to(bound)`), or the bound is the
   filesystem root. The owner's repository folder is, in order: the folder
   this run cloned it into; `git_root(owner)` (`tcw/store/fs.py:240-255`);
   the owner's root. "Trusted" means the entry's file is one of the active
   project's own two manifests (TCW-107 plan, `personal_file` for the
   borrowed one). *Reason:* this is Design 7.8 word for word, with the one
   sentence the resolved rule would not enforce made a separate check.
9. **The git calls.** `git clone --quiet -- <url> <staging>/<name>`, then,
   with a branch, `git -C <staging>/<name> checkout --quiet <branch>`. The
   staging parent `<parent>/.tcw-staging-<8 hex>` is made with
   `os.mkdir(…)` (which fails if the name exists), retried with a new name
   on `FileExistsError` up to five times. The move is `os.rename` onto an
   absent folder, or onto an empty one (POSIX `rename` replaces an empty
   folder); the staging parent is removed in a `finally`. Missing parent
   folders of the repository folder are made only for a trusted entry
   (7.6), and never in a dry run. *Reason:* `os.rename` is one system call
   with no partial state, and `mkdir` failing on an existing name is the
   exclusive creation 7.9 asks for.
10. **The store clone gets `--` too.** `_obtain` (`tcw/store/fs.py:3477-3497`)
    runs `git clone --quiet <url> <staging>`; this item adds `--` before the
    URL there as well, since the reason is the same. A store `ref`
    beginning with `-` is not refused here (the spec's 7.9 is about
    projects; the store's `repository` is parsed by `parse_repository`,
    which TCW-107's handoff (2) may tighten); recorded as a possible
    follow-up, not done.
11. **Graph validity is checked first** for the no-argument and `<id>` forms
    (`require_valid`, `tcw/store/project.py:453`), before the stores pass.
    The `--component` form keeps exactly today's checks, so the store tests
    of AC 33 run unchanged. The stores pass's early return when no store
    declares a repository (`tcw/cli.py:160-163`) no longer ends the command:
    the projects pass follows it.
12. **Design 7.2's message.** `StoreNotProvisioned`'s text
    (`tcw/store/fs.py:3314-3318`) names `tcw -C <project root> project
    provision --component <axis>` when the store's project root resolves to
    a folder other than `find_project_root()`'s answer for the current
    folder, and `tcw project provision --component <axis>` otherwise.
    `resolve_store` (`:3182`) already has the store's project root.
13. **`tcw project path`** calls `require_valid()` first (as `list` does,
    `tcw/projects_cli.py:28`), prints the folder as `print`-ed text of the
    resolved absolute path (the same form `list --json`'s `path` holds), and
    turns `validate_project_id`'s `ValueError` into `UsageError` (exit 2).
    *Reason:* without the graph check a sibling found by the search could be
    answered while two folders claim it.
14. **`tcw project info` does not set `own_config`**, so the configuration
    check every command makes first (`tcw/cli.py:655-661`) stops it on a
    problem in the active project's own files (Design 6.2). `config`
    keeps `own_config=True` as `config show` has it (`tcw/config_cli.py:272-287`),
    and `new` as `init` has it (`tcw/cli.py:557-568`).
15. **`info`'s settings when `work.jira` is withheld.** When
    `Config.withheld["work.jira"]` is set (TCW-109 plan, Step 7b), both
    `work.jira.site` and `work.jira.project` read `undecided: <message>` or
    `broken: <message>` with that one message, matching what the commands
    that read them do. Outside Jira mode neither line is printed (AC 12).
16. **`info`'s overrides.** Per axis: call the tree store's `view_warnings()`
    (TCW-112 plan, its store method list, "Design 2.5's warnings"); if it
    raises `InheritedUnavailable`, the axis reads `could not check: <its
    message>` and its count `?` (JSON `null`); otherwise list
    `list_all(local_only=True)` (TCW-112 plan, Step 13's records) entries
    whose `overrides` is set, and count the warnings. A missing store reads
    `none` and count 0. *Reason:* these are exactly the inputs TCW-112's
    plan names for this item (its Step 22 note, "Design 3.7's inputs").
17. **`info`'s stores.** Per axis, the same call `tcw <axis> path` makes
    (`_store().root` in `tcw/taxonomy/cli.py` and `tcw/capabilities/cli.py`;
    `open_backend(project_root())` in `tcw/work/cli.py:314-325`), factored
    into one helper `store_folder(axis, root) -> Path` in
    `tcw/project_cli.py` that the three `path` verbs do not change; any
    `TcwError` or `ValueError` is caught and its text is the reason.
18. **7.4's message names the new answer's deciding manifest file.** A new
    answer that differs with no deciding entry cannot arise (only a
    manifest fetched in the run can change an answer, and it then decides);
    if it does, the message reads `this run's fetches` in place of the file,
    and a unit test pins that fallback.
19. **Rounds re-read with `forget_registries()`** (TCW-107 plan, Step 5)
    and then a fresh `FsProjectRegistry` for the active root. Each kept
    answer is looked up again with `placement(id, asked_by)` from its
    recorded `asked_by`; when that root is no longer a project here (it
    cannot vanish in a run that only adds folders, but a race could), with
    `placement(id)` from the active root.
20. **The static guards.** `tests/test_static_guards.py`'s `EXEMPT`
    (`:33-42`) gains the new functions whose messages name git or `.git`
    (`("provision.py", …)` for 7.6's `.git` message and the round runner,
    `("store/fs.py", "fetch_project")`) and loses `("cli.py",
    "_provision_projects")` once TCW-107 has removed it (its existence test,
    `:108`, fails otherwise). `tests/test_subprocess_stdin.py` passes
    because every new git call goes through `_git`.
21. **The help-standard lists.** `tests/test_cli_help_standard.py`'s
    `SURFACE` (`:23`) gains `project new`, `project list`, `project config`,
    `project provision`, `project path`, `project info` in Step 2 and loses
    `init`, `provision`, `projects list`, `config show` in Step 4, where
    `REMOVED` gains them; the choices check (`:139`) names
    `project provision` from Step 4.
22. **TCW-114's note on `check_owned`.** If TCW-114's refusal for a project
    not on this machine (`tcw/ownership.py`, `check_owned`) does not already
    name `tcw project provision <id>`, Step 11 adds it, with a test. If any
    provisioning code still calls `reached_by_both_sides` (TCW-114 plan,
    Step 23's note), it is removed with the 3.x provisioning, since 4.0's
    walk never reaches a sibling (Design 7.3 (a)).

---

## Step 0 — start from what the earlier items left

No code changes. Results go in the implement round.

1. **Every citation, re-read on the merged `v4`.** For each name below,
   `grep -n` finds it and its behavior is what this plan says; any that
   differs is corrected in this plan before Step 1, and any that is missing
   is reported to the dispatching session rather than built here.
   - TCW-106: `.tcw/` layout, `TCW_FOLDER`, `legacy_message`
     (`tcw/project_files.py`), `version_problem`, `refuse_legacy_project`.
   - TCW-107: `FsProjectRegistry.project_folder`, `UnknownProject` (its
     message), `ProjectGraphError`, `Unreachable` and
     `UnreachableProject.message` / `decided_by` (Design 6.2's text naming
     `tcw project provision <id>`), `found(id)`'s four shapes, `_answers` and
     `_Answer` (folder, how found, deciding entry, problem), `_returned`,
     `begin_command`, `end_command`, `forget_registries`, `_read_text`,
     `_list_folder`, `_search`, `ManifestEntry`, `tcw/store/manifest.py`,
     `personal_file`, `validate_project_id` in `tcw/project_files.py`, and
     that `_declared_projects_in_graph`, `_provision_projects` and
     `declared_connected_projects` are gone while the `PROJECT_TARGET`
     branch of `FsStoreProvisioner` remains (TCW-107 plan, Step 7).
   - TCW-108: `ParentLink`, `LoadOrder(ids, missing, unreadable, warning)`,
     `parents()`, `declared_child_ids()`, `children()`, `load_order(id=None,
     root=…)`, `availability()`, `unreachable()`'s walk order, exit 7 in
     `EXIT_CODES`, `InheritedUnavailable`, and `tcw projects list --json`'s
     document (`load-order`, `load-order-complete`, `load-order-warning`,
     `inherit`, `personal`, `found`).
   - TCW-110: `print_json` writes `"schema": 2`; `tcw/locate.py`'s `Locator`.
   - TCW-109: `INHERITED_KEYS`, `Withheld`, `Config.withheld`,
     `Config.require`, `Origin.project` / `variable` / `position` / `root`,
     the `environment` layer, `_Writer.comment`'s labels (its plan, Step 9),
     `tcw config show`'s exits 7 and 1, the `TCW_<KEY>__<PROJECT>` names.
   - TCW-112: `view_warnings()`, `list_all(local_only=True)` and its records'
     `overrides` and `partial`, `ProjectRegistry.unavailable(…,
     store_message=…)`, and whether its Step 18 built anything for `info`.
   - TCW-114: `-C` (`_enter` in `_dispatch`, `main` restoring the folder),
     the ten listed reads of the current folder and the guard that keeps
     them, the removal of `read-only` and `readOnly`, whether `_projects`
     (`tcw/serve/work.py`) still exists, `check_owned`.
   - TCW-113 (spec): its AC 29's test asserting a reason containing
     `tcw provision`, and any other test it added that matches the
     `StoreNotProvisioned` text or a removed command.
   - This repository at `62e41ec5`: every `file:line` in this plan.
2. **The inventories**, saved in the scratchpad:
   - `tests-before.txt`: `.venv/bin/pytest --collect-only -q` (every test ID).
   - `sites-before.txt`: every line under `tests/`, `evals/`, `scripts/` and
     `tcw/` that runs or names a removed command, from
     `grep -rnE "tcw (init|projects|config show|provision)\b"` plus
     `grep -rnE "[\"'](init|provision)[\"']|[\"']projects[\"'], *[\"']list[\"']|[\"']config[\"'], *[\"']show[\"']"`
     with the `git init` lines (`"git", "init"`, `git(…, "init"`, `_git(…,
     "init"`) removed by a second filter and the filter's removals listed
     too. At `62e41ec5` that is 77 lines of text naming a command, 159
     string literals `"init"` (most of them `git init`), 61 `"provision"`,
     26 `"projects", "list"` and 25 `"config", "show"`, across 75 files.
   - `docs-before.txt`: every Markdown file outside `ARCHIVAL` naming a
     removed command, with its count (42 at `62e41ec5`: `README.md`, 18
     capability descriptions, two taxonomy descriptions, four guides,
     `docs/use-cases.md`, 15 files under `skills/`,
     `tcw/work/procedures/search.md`, `tests/cli/scenarios/13-release-integrity.md`).
3. **The outcome record:** `.venv/bin/pytest -q
   --junitxml=<scratchpad>/outcomes-step0.xml`, all passing. The
   scratchpad's `compare_outcomes.py <before.xml> <after.xml> <allowed.txt>`
   is TCW-108's (its plan, the paragraph "The outcome comparison", before
   its Step 8a), rebuilt if the scratchpad no longer holds it.

**Proves it:** the implement round lists each citation with its file and
line on `v4` and "as planned" or the correction; the three inventories and
the outcome file exist.

## Step 1 — the deciding entry, readable (Design 8.1)

**Tests first**, new `tests/test_project_placement.py` (library level, no
CLI):

- A project found by its manifest entry: `placement("core")` after
  `project_folder("core", app)` gives `folder` = `<tmp>/core`, `entry.file`
  = app's `.tcw/tcw-manifest.yaml`, `owner` = app's root, `asked_by` =
  app's root.
- Not on this machine with an entry giving `repository: <remote>#main` and
  `subfolder: apps/x`: `folder is None`, `entry.url == <remote>`,
  `entry.branch == "main"`, `entry_folder` = the resolved `path`,
  `repository_folder` = that with `apps/x` removed.
- Found by the search, and by `TCW_PROJECT_CORE`: `entry is None`,
  `folder` set.
- An entry in an ancestor's manifest (TCW-108 Design 3.4 (b)): `owner` is
  the ancestor's root, `asked_by` the active root.
- A personal manifest borrowed by a linked worktree: `owner` is the
  worktree's root, `entry.file` the main checkout's file.
- Without `named_by`, no file is read (the `_read_text` hook replaced by
  one that fails) and the first recorded answer is returned; an ID never
  looked up gives `None`.
- With `named_by`, an unknown ID raises `UnknownProject`, a graph problem
  `ProjectGraphError`.

**Changes:** `tcw/store/project.py`: the frozen dataclass `Placement` and
`FsProjectRegistry.placement` (choice 5), reading `_answers`; the owner is
recorded in `_Answer` by `_locate` if TCW-107 did not already keep it.
Nothing on `ProjectRegistry` (`tcw/store/base.py:184`).

**Proves it:** the new file; the full suite.

## Step 2 — the group, beside the old commands (Design 1.1, 2, 3, 4 names)

**Tests first**, new `tests/test_project_group.py`:

- `tcw project --help` lists `new`, `list`, `config`, `provision`, `path`,
  `info`; `tcw project` alone exits 2; `tcw --help` lists `project` after
  `work`.
- `tcw project new --id demo`, `tcw project list`, `tcw project config` and
  `tcw project provision --dry-run` each give the same exit code, standard
  output and files as `tcw init --id demo`, `tcw projects list`,
  `tcw config show` and `tcw provision --dry-run` in the same fixture (a
  side-by-side check, removed in Step 4 once the old names are gone).

This step registers only the four verbs that replace a command; `path` and
`info` are added in Steps 8 and 9 with their tests, and `tcw project --help`'s
list is extended there.

`tests/test_cli_help_standard.py`: `SURFACE` gains the four new leaves
(choice 21); the existing walk then checks each has `Prints:`, `Writes:`
and an example.

**Changes:**

- New `tcw/project_cli.py`: `add_subparser(sub)` registering `project` with
  the help of Design 1.1, and under it `new` (the arguments of
  `tcw/cli.py:557-568`, help of Design 2.2, `own_config=True`, handler
  `_cmd_init`), `list` (the arguments and handler of
  `tcw/projects_cli.py:68-77`), `config` (those of
  `tcw/config_cli.py:272-287`, `own_config=True`), `provision` (those of
  `tcw/cli.py:570-581`, handler `_cmd_provision`). Each verb's help through
  `cli_help.command` (`tcw/cli_help.py:15-27`) and the group's through
  `cli_help.group` (`:30-35`).
- `tcw/cli.py` `build_parser` (`:549-613`): `project_cli.add_subparser(sub)`
  after the loop over `_BUILT` (`:606-607`), so `project` is registered
  after `work`.
- The messages the verbs print keep their current prefixes and texts in
  this step ("tcw provision:", `tcw/cli.py:111`, `:134`, `:150`, `:158`,
  `:186`), so the outcome comparison of Step 3 is exact; Step 5 changes them.

**Proves it:** the new file; `tests/test_cli_help_standard.py`; the full
suite.

## Step 3 — the tests and documents move to the new names, mechanically

No behavior changes. Every change in this step is made by one script, kept
in the scratchpad as `rename_commands.py`, and nothing by hand except where
the script's report says so.

**The script**, over the files of `sites-before.txt` and `docs-before.txt`:

- In Python source under `tests/` and `evals/` and in
  `tests/fixtures/prompt_fallback/capture.py`, a TCW argument list: the
  string literal `"init"` (or `'init'`) as the first command word of a
  call that runs TCW (`main([…`, `cli(capsys, …`, `run(…, `, `_tcw(…, `,
  `tcw(…, `, `_run(dest, …`, and `["tcw", "init", …]`) becomes `"project",
  "new"`; `"provision"` becomes `"project", "provision"`; `"projects",
  "list"` becomes `"project", "list"`; `"config", "show"` becomes
  `"project", "config"`. A literal preceded by `"git", `, or inside a call
  of `git(`, `_git(` or `subprocess.run(["git"`, is never changed. Every
  candidate the script skips, and why, is printed.
- In text (docstrings, comments, Markdown, YAML), the whole words
  `tcw init` → `tcw project new`, `tcw projects list` → `tcw project list`,
  `tcw projects` → `tcw project list` only where followed by a backtick or
  end of command, `tcw config show` → `tcw project config`,
  `tcw provision` → `tcw project provision`. `tcw initial…` and
  `tcw provisioning` are not matched (`\b` after the word).
- Not touched: `docs/work/`, `docs/changelogs/`, `docs/release-notes/`,
  `docs/migration-guide-*` and the other `ARCHIVAL` trees
  (`tests/test_documented_cli_surface.py:38-43`); assertions on message
  text (`"tcw provision:"` prefixes, `tcw provision` inside an expected
  message), which change with the messages in Step 5. The script lists each
  assertion it left.
- Changed by hand, because the script's patterns do not match them and
  each is listed in the report: `tests/test_projects_list.py:118` (the
  argument tuple `("provision",)`) and `:128` (the expected prefix built from
  it). Left as they are on purpose: `tests/work/test_cli_surface.py:138`
  (`tcw work init`, a removed `work` verb that still exits 2) and every
  `git init`.

**Checks, in order:**

1. **The inventory:** the script's report (every changed line, every
   skipped candidate with its reason) is saved as `rename-report.txt` and
   read whole by hand; every skipped `"init"` is confirmed to be `git init`
   or not a TCW command.
2. **The outcome comparison:** `.venv/bin/pytest -q
   --junitxml=<scratchpad>/outcomes-step3.xml`, then `compare_outcomes.py
   outcomes-step0.xml outcomes-step3.xml empty.txt` (plus the tests Steps 1
   and 2 added, which are new IDs and allowed as additions): no test ID
   disappears and no outcome changes. The test IDs do not change, since
   the script changes arguments, not function names.
3. **The mutation check:** with `run_init` called from `project new` made to
   raise `TcwError("mutated")` (and only from there: the old `init` still
   works), the converted tests that build projects through the CLI go red,
   and the count is recorded; reverted. The same for `project provision`.
   This proves the tests now run the new names and not the old ones.
4. `tests/test_documented_cli_surface.py` passes with the documents now
   naming `tcw project …`.

**Proves it:** the four checks above; the full suite.

## Step 4 — the old commands removed; the table; the suggestions (Design 1.2, 1.3)

**Tests first:**

- `tests/test_project_group.py`: AC 1 (`tcw --help` lists `project` and not
  `init`, `projects`, `config`, `provision`); AC 2, each of the four
  invocations exits 2, writes nothing (the folder's listing before and
  after), and prints its table line; the side-by-side tests of Step 2 are
  removed.
- `tests/test_command_suggestions.py`: AC 3's five rows (`tcw work info x`,
  `tcw info`, `tcw list`, `tcw path`, `tcw new`), and a guard that no
  synonym target in `SYNONYMS` other than `info`'s is a subcommand anywhere
  in the tree (Design 1.3's "this rule changes no other suggestion").
- `tests/work/test_cli_surface.py` and `tests/test_command_suggestions.py`:
  every existing case passes; any case that named a removed command is
  changed and listed in the implement round (at `62e41ec5` there is none:
  `tests/work/test_cli_surface.py:138` checks only that `tcw work init`
  exits 2, which still holds, since the table applies at the top level
  only and `init` is then a subcommand nowhere).
- `tests/test_cli_help_standard.py` (choice 21): `SURFACE` loses the four,
  `REMOVED` gains them, the choices check names `project provision`.

**Changes:**

- `tcw/cli.py` `build_parser`: the `init` and `provision` subparsers
  (`:557-581`) and the calls `projects_cli.add_subparser(sub)` and
  `config_cli.add_subparser(sub)` (`:604-605`) are removed; `_cmd_init` and
  `_cmd_provision` stay as the new verbs' handlers.
- `tcw/projects_cli.py` and `tcw/config_cli.py`: `add_subparser` removed
  (choice 1); module docstrings name `tcw project list` and
  `tcw project config`.
- `tcw/cli_suggest.py`: `REMOVED_COMMANDS`, a mapping from `init`,
  `projects`, `config`, `provision` to Design 1.2's lines, beside
  `REMOVAL` (`:45`); `_hint` (`:126-145`) returns that line first when the
  parser is the top-level one (choice 4), and then puts a synonym whose target is valid at the level typed before the
  commands found elsewhere, then fills up to `_MAX` (`:47`).

**Proves it:** the tests above; the full suite.

## Step 5 — the sweep: messages, help and comments (Design 1.4, 2.2, 7.2's first half)

**Tests first:**

- `tests/test_shipped_text.py`: the AC 4 test. Over `tcw/` (less
  `tcw/serve/dist/`), `evals/`, `scripts/` and `tests/fixtures/`, no file
  contains `\btcw (init|projects|config show|provision)\b` except
  `tcw/cli_suggest.py`'s `REMOVED_COMMANDS`; seen to fail first on the
  current files.
- The three messages of Problem 7, each produced by a test: `tcw work list`
  outside a project names `tcw project new --id <id>` (`NO_PROJECT`,
  `tcw/errors.py:13`); `tcw taxonomy list` in a project with no taxonomy
  store names `tcw project new taxonomy` (`tcw/taxonomy/cli.py:24-28`, and
  `tcw/capabilities/cli.py:26-30` likewise); the init refusal for a store
  with a repository (`tcw/store/fs.py:712-731`) names
  `tcw project provision` and `tcw project new <axes>`.
- Every assertion Step 3 left (its report) is changed to the new text here,
  each listed in the implement round with the message it matches; the
  `StoreNotProvisioned` text in TCW-112's and TCW-113's tests (TCW-113 AC
  29's "containing `tcw provision`") changes to `tcw project provision`.

**Changes**, each a message, help text or comment naming a removed command:

- `tcw/cli.py`: the "tcw provision:" prefixes (`:111`, `:134`, `:150`,
  `:158`, `:186`) become "tcw project provision:"; `_cmd_validate`'s
  "run `tcw provision`" (`:432`).
- `tcw/errors.py:13`; `tcw/taxonomy/cli.py:24-28`;
  `tcw/capabilities/cli.py:26-30`; `tcw/store/project.py:611` (`tcw init
  --id` becomes `tcw project new --id`) and comments at `:219`, `:704`,
  `:1108`; `tcw/store/fs.py` messages at `:712-731`, `:3314-3318` (the
  plain form only here; Step 11 adds the `-C` form), `:3444`, `:3410`'s
  "thing" sentence if it names a command, and the comments at `:53`,
  `:200`, `:362`, `:373`, `:471`, `:486`, `:497`, `:509`, `:636`, `:647`,
  `:718`, `:3207`, `:3272`, `:3506`; `tcw/store/base.py:59`, `:90`;
  `tcw/config.py:18`; `tcw/serve/work.py:144`; `tcw/work/open.py:97` (as
  TCW-107 left it); `tcw/work/procedures/search.md:27`.
- `evals/seed_fixture.py:17` (text) and `:761` (the argument list, changed
  by Step 3's script if it matched `_run(dest, "init", …)`; confirmed here
  by reading it); `tests/fixtures/prompt_fallback/capture.py:64`, `:67`
  likewise. `python evals/seed_fixture.py --customized <scratchpad>/probe`
  is run once to show the builder still builds (Verification).
- `tests/conftest.py:66`, `:84`, `:113` (comments).

**Proves it:** the AC 4 test; the three message tests; the full suite.

## Step 6 — `tcw project list` (Design 3)

**Tests first**, `tests/test_projects_list.py` (renamed by Step 3's
contents, kept at its path): AC 6 whole: the plain listing `app`, `core`,
`k`; `--json` with `schema` 2, `core`'s row `inherit: ["taxonomy"]` and
`found: {"by": "search"}`, `k`'s row `personal: false` and `found: {"by":
"manifest", "file": <app's manifest>}`, the current row `found: null`, no
row with a `read-only` key; with `k` absent, `present: false`, `path:
null`, `found: null`, exit 0. AC 18's half for `list` (a graph problem,
exit 1). AC 34's `list` prints only the ID.

**Changes:** `tcw/projects_cli.py` `connected` (`:21-51`): `found` on every
row if TCW-107 did not add it (TCW-107 Design 6.1), and no `read-only` if
TCW-114 did not remove it (TCW-114 plan, Step 7). **Design 3.3:** Step 0
records whether `_projects` (`tcw/serve/work.py:143-148`) survived TCW-114
(its plan, Step 8). If it did, its docstring names `tcw project list` (Step
5) and nothing else changes; if not, nothing to do. Either way the
`tests/serve/` suite runs it.

**Proves it:** the test file; `tests/serve/`; the full suite.

## Step 7 — `tcw project config` and the origin label (Design 4)

**Tests first**, `tests/config/test_config_show.py` (its contents now
running `project config`): AC 7 whole, each label read off the line it ends
(`# core, project <absolute>`, `# app, project .tcw/tcw-config.yaml`,
`# app, local .tcw/tcw-config.local.yaml`, `# app, environment
TCW_USER_NAME__APP`, `# built-in, tcw/work/prompts/<stage>.md`, `# app,
user <absolute>`), and the plain output reading back with `yaml.safe_load`
as the same values; a borrowed personal file in a linked worktree labelled
with the main checkout's file. AC 8 whole (exit 7 naming `work.jira` and
`core`; exit 1 naming `core`'s file; exit 0 when `app` sets `work.tags`;
`app`'s own problem: plain exit 1, `--origin` prints and exits 1). Every
existing assertion on a label changes to the new shape and is listed.

**Changes:** `tcw/config_cli.py` `_Writer.comment` (`:119-137`, as TCW-109's
Step 9 left it): one shape, `<project>, <layer> <file>` with `<file>` from
`shown_in` (`tcw/config.py:112-120`) against the active root,
`<project>, environment <NAME>`, or `built-in`, then `_packaged`'s file
after a comma (`:104-110`). The project ID comes from `Origin.project`
(TCW-109); a layer applied at the active project's layers with no project
recorded (the user-wide file, Design 4.2) takes the active project's ID.
`_set_aside` (`:209-220`) unchanged. A shared formatter `origin_label(origin,
root, active_id) -> str` is added beside `render`, without the `# `, for
Step 9 to reuse (Design 4.3), with `origin_json(origin, active_id) -> dict`.

**Proves it:** the test file and the other three files under
`tests/config/` that print origins (`test_config_edges.py`,
`test_personal_problems.py`, and `tests/test_cli_contract.py`'s `--origin`
cases); the full suite.

## Step 8 — `tcw project path` (Design 5)

**Tests first**, new `tests/test_project_path.py`: AC 9 (`core`, `k`, no
argument, `app`, from `app/docs`; the sibling `b` from `ws/app2`), AC 10
(exit 5 with `tcw project provision k` and the remote; exit 5 without it
when no repository; `nope` exit 1 `check the spelling`; `Nope` exit 2; two
folders declaring `lib`, exit 1 naming both), AC 11 (a linked worktree: no
argument prints the worktree, `lib` next to the main checkout), outside any
project `NO_PROJECT` exit 1, and nothing written (folder listing before and
after). AC 37's second half: with a leftover
`<tmp>/.tcw-staging-0123abcd/lib` holding a copy of `lib`, `path lib`
prints `<tmp>/lib`, exit 0, no second match (this tests TCW-107's search
depth, Design 2.6, which this item relies on).

**Changes:** `tcw/project_cli.py`: the `path` verb, `[<id>]`, help per the
standard; handler: `validate_project_id` (`tcw/project_files.py`, after
TCW-107) with `ValueError` → `UsageError`; the command's registry
(`begin_command`'s), `require_valid()`, then `project_folder(<id>, root)`;
`Unreachable` → exit 5 with its `message` (TCW-107 Design 6.2);
`UnknownProject` / `ProjectGraphError` → exit 1 (choice 13). No `<id>`:
prints `find_project_root()`.

**Proves it:** the new file; `tests/test_cli_help_standard.py` (`SURFACE`
gains `project path`); the full suite.

## Step 9 — `tcw project info`, text (Design 6.1-6.3, 6.5)

**Tests first**, new `tests/test_project_info.py`: AC 12 (the exact lines, in
order, with personal files turned on), AC 13 (`work.backend: jira (app,
project .tcw/tcw-config.yaml)`, the two `work.jira` lines `(core, project
<file>; inherited)`, `app` setting `work.jira.project` itself, `core`
absent: exit 0, both lines `undecided: ` and TCW-109 Design 3.3's message),
AC 14 (the load-order warning shape and its absence), AC 15 (an override
listed, `taxonomy: none`, the same-path count 1, `core` absent: `could not
check:`, `?`, exit 0), AC 16 (a store not fetched: the `work:` line reads
`tcw work path`'s reason naming `tcw project provision`, exit 0), AC 18
(graph problem exit 1, own configuration problem exit 1, `info core` exit
2), AC 34's `info` (`parents: none`, `children: none`, `load order: <id>`).

**Changes:** `tcw/project_cli.py`: the `info` verb (`--json` added in Step
10), no positional argument (so `info core` is argparse's exit 2), not
`own_config` (choice 14). It builds one `ProjectInfo` record (a plain
dataclass in `tcw/project_cli.py`) from the command's registry —
`require_valid()`; `parents()`; `declared_child_ids()` with each child's
personal flag and `project_folder` outcome; `load_order()`;
the settings of 6.1 (5) from the loaded configuration and its origins
(choice 15), `DEFAULT_BACKEND` (`tcw/work/config.py:27`) as `built-in`
when unset; the stores (choice 17); the overrides (choice 16) — and a
`render_text(info)` writing Design 6.3's lines, with `origin_label` from
Step 7. Every missing or unavailable part is a field of the record, never an
exception past the handler, so the exit code is 0 for all of them.

**Proves it:** the new file; `SURFACE` gains `project info`; the full suite.

## Step 10 — `tcw project info --json` (Design 6.4)

**Tests first**, `tests/test_project_info.py`: AC 17 whole (the `ws` and `p`
rows, `load-order-missing`, `load-order-complete: false`,
`settings["work.jira.site"]` with `inherited: true` and `origin` as Design
4.3, `core` absent: `settings["work.jira.project"] == {"undecided": …}`),
plus `stores` and `overrides` shapes for one present and one unavailable
axis, and `same-path-warnings` `null` for the unavailable one; `schema` is
what `print_json` writes.

**Changes:** `tcw/project_cli.py`: `--json` on `info`; `render_json(info)`
using `origin_json` (Step 7) and `print_json("project", …)`
(`tcw/output.py:53-61`).

**Proves it:** the test file; the full suite.

## Step 11 — provision: the stand-in `git`, the stores pass, and the message for another project's store (Design 7.1, 7.2, 7.14)

**Tests first:**

- New `tests/provision_support.py`: the **stand-in `git`** fixture
  `stand_in_git(tmp_path, monkeypatch)`: a script in
  `tmp_path/stand-in-bin/git`, put first on `PATH`, that appends its
  arguments to a log file and, for `clone`, `fetch`, `ls-remote` or `pull`,
  either exits 97 printing `stand-in git: network call` (the default) or,
  when the fixture is told `allow_clone=True`, passes `clone` through to
  the real git (found by `shutil.which` before `PATH` is changed) and counts
  it; every other call goes to the real git. Helpers `make_remote(tmp_path,
  name, files, branch="main") -> Path` (a bare repository pushed from a
  work folder, both under `tmp_path`) and `calls(kind) -> list[list[str]]`.
  A test of the fixture itself: a `git clone` through it fails the test
  when not allowed; `git rev-parse` passes through.
- New `tests/test_project_provision.py`, this step's part: AC 21's last two
  sentences (`--component work` fetches the store and no project; `core
  --component work` exits 2); an invalid `<id>` exits 2; AC 31 (`ref` key in
  the manifest: exit 1 naming the file and key, no `clone`; with and without
  `--dry-run`; `TCW_PROJECT_CORE` naming a folder that is no project, the
  same naming the variable); AC 34's `provision` (`nothing to fetch`, and the
  stores pass's "Nothing to provision" line); AC 38 (`tcw taxonomy list` in
  `app` exits 7 with `tcw -C <core's root> project provision --component
  taxonomy`; in `core`, without `-C`).
- AC 33: `tests/test_init_provision_contract.py`,
  `tests/work/test_init_provision.py` and the store sections of
  `tests/test_store_provisioning.py` (`:125-1407`, `:1775-2100` at
  `62e41ec5`) pass, running `project provision` since Step 3, their messages
  naming `tcw project provision` since Step 5.
- `tests/test_store_provisioning.py:2071-2072`'s argv check: the store
  clone's argv is `["git", "clone", "--quiet", "--", url, staging]`
  (choice 10).

**Changes:**

- `tcw/cli.py` `run_provision` (`:86-192`): takes `project_id` and the
  components; `<id>` with components → `UsageError`; for the no-argument and
  `<id>` forms, `registry.require_valid()` first (choice 11); the stores
  pass only for the no-argument and `--component` forms; the early return
  at `:160-163` becomes "continue to the projects pass" for the no-argument
  form; then `tcw.provision.provision_projects(…)` (Step 12) for the
  no-argument and `<id>` forms. The `TCW_PROJECT_<ID>` refusal (`:127-135`)
  is what TCW-107 Step 7 kept (its choice 6); unchanged.
- `tcw/project_cli.py`: `provision` gains the optional positional `<id>`.
- `tcw/store/fs.py` `_obtain` (`:3477-3497`): `--` before the URL.
- `tcw/store/fs.py` `resolve_store`'s `StoreNotProvisioned` (`:3314-3318`):
  the `-C` form when the store's project root is not the active one (choice
  12).
- `tcw/ownership.py` `check_owned`: `tcw project provision <id>` in the
  not-on-this-machine tail, with its test in TCW-114's ownership test file,
  if TCW-114 did not add it (choice 22).

**Proves it:** the tests above; the full suite.

## Step 12 — provision: which projects, in rounds, and what is printed (Design 7.3, 7.4 first half, 7.5, 7.13)

A fetch must really happen for these tests to see one, so this step builds
the round runner with the simplest real fetch (clone, check out, rename,
without the checks of Steps 13 and 14), and Step 13 completes it.

**Tests first**, `tests/test_project_provision.py`: AC 19 (exit 0, the `→
core:` line naming the remote before `core: fetched into <tmp>/core`, `list
--json` then shows `core` present with `found.file` app's manifest; a
second run contacts no remote and prints `nothing to fetch`; the stand-in
saw `clone --quiet -- <remote> …`; nothing in the remote or the fetched
`core` changed: `git status --porcelain` empty and its
`.tcw/tcw-config.yaml` byte for byte the remote's), AC 20 (`core` then
`base` in the next round, never `other`; `k` then `kk`), AC 21's first
sentences (`provision core` fetches `core` and `base`, not `k`; `provision
k` fetches `k` and not `kk`; `provision app` fetches ancestors only; a
store with a repository untouched by `provision core`), AC 22 (a), (b),
(c), the variable naming a missing folder, and the last sentence (`base`
reached through a project already here), AC 26 (`fetched 1, failed 1; …`,
exit 1; the second run fetches only `bb`, using an occupied folder, so this
case is completed in Step 13), AC 28 (`no manifest entry gives the
repository` for `nn` and `mm`, exit 0; `provision mm` exit 5; `nope` exit 1
with the spec's longer `check the spelling, or …` text; `Nope` exit 2).

**Changes:** new `tcw/provision.py`:

- `provision_projects(root, project_id=None, *, dry_run, out) -> int`
  (returns the exit code; prints to standard error only).
- `_round_ids(registry, project_id, attempted)` (choice 6).
- `_plan_round(registry, ids, kept, active_root) -> list[Planned | Refused |
  Unfetchable]`, using `placement` (Step 1); in this step only check (1) of
  choice 7.
- `_run_round(planned)`: for each, the `→ <id>: <url>[ at <branch>] →
  <folder>` line, then `fetch_project` (Step 13), then `<id>: fetched into
  <folder>`.
- After each round, `forget_registries()` and a new registry (choice 19);
  the loop ends on an empty round.
- The last line and the exit code of Design 7.13: `nothing to fetch: every
  project it names is on this machine`; `fetched <n>, failed <m>; what was
  fetched stays, and running the command again fetches the rest`; 5 only for
  `<id>` still missing for want of a repository; `<id>: already on this
  machine at <folder>` when `<id>` is already here.
- `tcw/store/fs.py`: `fetch_project(url, branch, repository_folder, *,
  project_id, subfolder) -> None`, raising `FetchRefused(message)` (a
  `TcwError`), first version.
- `tests/test_static_guards.py` `EXEMPT` (choice 20).

**Proves it:** the tests above (AC 26's second half after Step 13); the
full suite.

## Step 13 — provision: the repository folder, one clone per folder, the clone checked, staging and the move (Design 7.6, 7.7, 7.9, 7.10)

**Tests first**, `tests/test_project_provision.py`: AC 23 (one `clone`
counted, `<tmp>/mono` made, both found; a different remote at the same
folder: both refused before any `clone`, each naming the folder, exit 1; the
remote lacking `apps/client`: `server` fetched, `client` refused with `has
no TCW project at apps/client`, exit 1), AC 24 (occupied: exit 1, no
`clone`, `f` unchanged, the message names the folder and app's manifest;
empty: fetched; a `.git` file `gitdir: ../.git/modules/core`, and a `.git`
folder holding `HEAD`: exit 1, no `clone`, 7.6's message, the folder
byte for byte as before (a hash of every file and its mode), nothing new in
`<tmp>`; `.DS_Store` beside `.git`: occupied), AC 25 (the four remotes and
the unreadable path: exit 1, each message, nothing at `<tmp>/core` and no
`.tcw-staging-*` in `<tmp>`), AC 26 completed, AC 37 (the leftover
`<tmp>/.tcw-staging-0123abcd/core` left as it was while `core` is fetched
into `<tmp>/core`; `--template=<tmp>/t` and `<remote>#--orphan` refused with
`beginning with '-'`, no `clone`).
Library tests in new `tests/test_fetch_project.py`: the move raising
`OSError` (the `os.rename` patched) refuses with `<id>: could not move the
clone into <folder>: <reason>`, leaves no staging folder and nothing at the
folder; a file appearing in the folder between the check and the move (the
check's second call patched to see it) refuses as occupied; the staging
name colliding (an existing `.tcw-staging-<hex>` with `uuid`/`secrets`
patched to return it first) is retried, never written into; the argv of the
clone is `["git", "clone", "--quiet", "--", url, …]`.

**Changes:**

- `tcw/provision.py` `_plan_round`: checks (2), (4) and (5) of choice 7 —
  the `-` check (`<id>: <file> gives a repository beginning with '-'`), the
  folder state (`_folder_state(folder) -> "absent" | "empty" | "git-only" |
  "occupied"`, with 7.6's two messages), and the grouping by resolved
  repository folder with `normalized_url` (`tcw/store/checkouts.py:21-57`)
  and branch (7.7's conflict message; the second and later projects of a
  group are `Comes-with(first)`).
- `tcw/store/fs.py` `fetch_project`, full: the staging parent by exclusive
  `mkdir` (choice 9), `git clone --quiet -- <url> <staging>/<name>` and the
  checkout through `_git` with `_no_prompt_env`; the check of
  `<subfolder or top>/.tcw/tcw-config.yaml` with `version_problem`,
  `legacy_message` and the declared `id` (the same checks the
  `PROJECT_TARGET` branch of `_is_store_layout` makes, `:3124-3154`, called
  from here); the second state check; `os.rename`; the staging parent
  removed in a `finally`; `git`'s failure text through `_git_reason`.
- `tcw/store/fs.py`: the `PROJECT_TARGET` branch of `FsStoreProvisioner`
  and `_is_store_layout` (`:3121`, `:3150`, `:3467`), now unused by any
  caller (Step 0 confirms), is removed; `fetch_project` reuses the checks it
  held. If something still calls it, it stays and the implement round says
  why.
- After a round, Design 7.11's first rule: each fetched project must be
  found at its entry's folder; otherwise refused as 7.7's "has no TCW project
  at" when it came with another's clone.

**Proves it:** the tests above; `tests/test_static_guards.py`;
`tests/test_subprocess_stdin.py`; the full suite.

## Step 14 — provision: the bound (Design 7.8)

**Tests first**, `tests/test_project_provision.py`: AC 27 whole (each of
`../../base-far`, `../x/base`, `vendor/base`, `../.base`, and an absolute
path in a personal manifest committed into `core`'s remote, refused before
contact, the stand-in saw one `clone`, 7.8's first message naming
`<tmp>/repos`, nothing made, `core` stays, exit 1; `../base` fetched into
`<tmp>/repos/base`; a second run refuses `../../base-far` the same way; the
way out names `tcw -C <tmp>/repos/core project provision base` and
`<tmp>/repos/core/.tcw/tcw-manifest.local.yaml` and not app's personal
manifest; running that `-C` command fetches `base` into `<tmp>/base-far`,
then `provision` in `app` prints `nothing to fetch`; a fresh fixture with
`base: <tmp>/elsewhere/base` in core's personal manifest, then the `-C`
command; trusted entries in app's own manifests honoured with missing parent
folders made; the `ws` / `wp` case naming `<tmp>` and app's own manifests,
then fixed by app's personal manifest), AC 36 whole ((a) the committed links
`up -> ../..` refused naming `<tmp>/base`, `lnk -> ..` fetched; (b)
`<tmp>/repos-x`; (c) `HOME=<tmp>/home` and `HOME=<tmp>/home/inner`, 7.8's
second message, nothing at `<tmp>/home/base`, while `core` from app's own
entry is fetched). The `-C` runs use TCW-114's `-C`.

**Changes:** `tcw/provision.py`: `_bound_problem(placement, active_root,
cloned) -> str | None` (choice 8), check (3) of choice 7, with the two
messages and the way out of 7.8 (the asking project is the active one, or
not; the `-C` sentence only when `<file>` is the asking project's own
manifest); `cloned` maps each project fetched in this run to its repository
folder, for the owner's repository folder. Missing parent folders made only
for trusted entries, at the move (choice 9).

**Proves it:** the tests above; the full suite.

## Step 15 — provision: answers kept for the run, and a fetched project's own problems (Design 7.4 second half, 7.11)

**Tests first**, `tests/test_project_provision.py`: AC 35 (`core` fetched,
`lib` refused with 7.4's message naming `<tmp>/lib`, `<tmp>/repos/lib` and
core's manifest, one `clone`, nothing at `<tmp>/repos/lib`, exit 1; with
`lib: ../lib` in app's personal manifest, the next run prints `nothing to
fetch`), AC 32 (core's remote holding a manifest with a TCW-107 Design 1.8
problem: fetched and kept, 7.11's message naming its manifest and saying to
remove `<tmp>/core`, no further round, `base` not attempted, exit 1; a
malformed `parents:` in the remote: fetched, a warning, exit 0). A unit test
of 7.4's fallback text (choice 18).

**Changes:** `tcw/provision.py`: before the first clone, `kept` records
`placement(id)` for every ID the registry has an answer for (the walk of
`unreachable()` having run, every project of the family has one), and each
fetched project is added once found; after every reading, each kept ID is
looked up again from its `asked_by` (choice 19), and a changed folder stops
the run with 7.4's message; a graph problem in the new reading
(`require_valid` raising) is turned into 7.11's message naming the fetched
project whose file it is, and stops the run; a warning recorded as
unreadable links (TCW-108 Design 6.6, `load_order().unreadable` or
`availability()`) is printed and the run goes on.

**Proves it:** the tests above; the full suite.

## Step 16 — provision: the dry run and the worktree (Design 7.12, 7.6's worktree)

**Tests first**, `tests/test_project_provision.py`: AC 30 whole (AC 20's
setup: exit 0, no `clone`, no folder made (the listing of `<tmp>` before
and after), `core: would fetch into <tmp>/core` and `core: any projects it
names cannot be listed until it is fetched`, nothing about `base`; AC 23:
`would fetch` for one, `would come with the clone for '<first>'` for the
other; AC 24's occupied and `.git`-only cases, AC 23's conflict and AC 27's
`wp`: exit 1 with the run's messages; every project here: `nothing to
fetch`), AC 29 (a linked worktree of `app` outside the main checkout: the
clone lands next to the main checkout, and `tcw project path core` in the
worktree prints it).

**Changes:** `tcw/provision.py`: with `dry_run`, the first round's plan is
printed (the `→` line, `would fetch`, the "cannot be listed" line, `would
come with`) after the same checks, and the run stops there; no `mkdir`, no
git call that contacts a remote. The worktree case needs no code if
`placement`'s `repository_folder` follows TCW-107 Design 4.3, which Step 1's
tests already pin; if this test fails, the fix is in `placement`, not here.

**Proves it:** the tests above; the full suite.

## Step 17 — this repository's records

**Changes**, from `capabilities.yaml` and `item.yaml`'s taxonomy:

- New capabilities, each with a `description.md` written to the
  capabilities skill's standard: `cli/find-where-a-project-is-on-this-machine`
  (`tcw project path`), `cli/see-how-a-project-is-assembled`
  (`tcw project info`), `cli/fetch-a-project-that-is-not-on-this-machine`
  (`tcw project provision` for projects: rounds, the bound, the dry run).
- Changed capabilities, each description rewritten where it describes the
  command, not only renamed (Step 3 renamed the commands only):
  `cli/scaffold-the-doc-trees`, `cli/list-connected-projects`,
  `cli/show-the-effective-configuration` (the label's new shape),
  `cli/provision-declared-stores` (`--component` fetches no project; the
  `-C` message), `cli/get-a-suggestion-for-a-mistyped-command` (the table,
  synonyms first), `cli/declare-a-connected-projects-home-repository`,
  `cli/point-tcw-at-a-project-i-already-have`,
  `cli/locate-tcw-storage-folders`, `cli/validate-a-project`,
  `cli/override-the-team-configuration-for-myself`,
  `cli/host-multiple-projects-in-one-repo`,
  `cli/read-a-file-by-the-format-version-it-records`, and the six store
  capabilities of `work`, `taxonomy` and `capabilities` (configure the
  location; declare the home repository), each naming
  `tcw project new` / `tcw project provision`.
- Taxonomy: `docs/taxonomy/cli/description.md` (the `project` group) and
  `docs/taxonomy/project-registry/description.md` (path, info, the deciding
  entry).
- `cli/read-from-an-upstream-project` names a removed command too
  (`docs-before.txt`) but is not in `capabilities.yaml`: Step 3 renamed it;
  if it describes 3.x behavior TCW-107 or TCW-108 removed, the implement
  round says so and leaves it to whichever item owns it.

**Proves it:** `tests/test_documented_cli_surface.py` (every command in the
new descriptions exists), `tests/test_capability_ref_wording.py`, and the
full suite. `tcw validate` of this repository's records is not run with
`.venv/bin/tcw`: the records stay in the 3.x format until TCW-116, and the
3.x `tcw` validates them at the `completed` move.

## Step 18 — the suite as CI runs it

`.venv/bin/pytest` with no arguments from the worktree's root, every test
passing; then the inventories again: `tests-after.txt` against
`tests-before.txt` (every removed test ID listed with the rule that removed
it — at most the side-by-side tests of Step 2), and the sweep greps of Step
0 showing only `REMOVED_COMMANDS` and the archival trees. The CI workflow
runs bare `pytest` (`.github/workflows/test.yml`), so the run is bare
`pytest`, not `python -m pytest`.

**Proves it:** AC 39.

## Step 19 — Documentation Sync

| Entry | Fires? | What this item does |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Command names only (Step 3). The prose for the `tcw project` group is TCW-117's (spec Non-goals, Design 1.4). |
| `docs/guide/jira.md` [Jira-Change] | no | No `tcw work` command, `work.jira` key or stage status changes. Step 3 renames any removed command it names (none at `62e41ec5`). |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | Command names only (Step 3: `cli.md`, `configuration.md`, `multi-repo.md`, `work.md`). The rewrite — the group, the bound, the `.git`-only refusal, staging folders — is TCW-117's (spec, Handoffs to later items). |
| `docs/release-notes/upcoming/TCW-115-tcw-4-0-the-tcw-project-command-group.md` [Public-API] | yes | Written at implement: the `tcw project` group and its six verbs; the four removed commands and their replacements; `--origin`'s new label; provisioning fetches parents and children in turn, places a clone from another project's manifest only directly beside that project and never at or above the home folder, refuses a folder holding only `.git`, and `--component` fetches no project. Under `## New` and `## Changed`, plain language. |
| `docs/changelogs/upcoming/TCW-115-tcw-4-0-the-tcw-project-command-group.md` [Any-Code-Change] | yes | Written at implement: Added (`tcw/project_cli.py`; `tcw/provision.py`; `FsProjectRegistry.placement` and `Placement`; `fetch_project`, `FetchRefused`; `REMOVED_COMMANDS`; `origin_label`, `origin_json`), Changed (the suggester's synonym order; `_Writer.comment`'s shape; `run_provision`'s forms and graph check; `StoreNotProvisioned`'s `-C` form; `--` before every clone URL; every message naming a removed command), Removed (`tcw init`, `tcw projects`, `tcw config`, `tcw provision`; the `PROJECT_TARGET` branch), Internal (`tests/provision_support.py`'s stand-in `git`; the test rename). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes | Command names only (Step 3). What the setup, configure and work skills teach about the group is TCW-117's (spec, Handoffs to later items). |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No key or variable is added, removed or changes meaning. Step 3 renames the commands they name. |
| `docs/use-cases.md` [Project-Setup-Change] | yes | Command names only (Step 3). Closing UC-6's known gap "TCW-23 (provision scoping)" is TCW-117's per the spec's handoff; the implement round reminds TCW-117's ticket. |

## Verification the tests cannot do

Each done by hand, in throwaway folders under the scratchpad, with
`.venv/bin/tcw`, the current folder set there, and the result written into
the implement round:

1. `tcw --help`, `tcw project --help` and each verb's `--help`, read whole
   for plain language and for the order of the groups.
2. A real clone over the network is not run (the suite forbids it, and so
   does this plan); instead, a remote that asks for credentials is
   simulated by a `file://` URL to a folder with no read permission, and
   the run is seen to fail at once rather than wait.
3. `tcw project provision` interrupted with Ctrl-C during a clone of a
   large local repository (made by committing many files): the
   `.tcw-staging-<hex>` folder is either removed or left, and in the second
   case `tcw project path <id>` does not find the copy inside it and the
   next run fetches normally.
4. `python evals/seed_fixture.py --customized <scratchpad>/probe` and
   `--bare` build their fixtures with the new commands (the eval builder's
   own runs, AC 4).
5. `tcw project info` read as a person would, in a project with parents
   missing and Jira mode on: every line says what is missing without
   needing the documentation.
6. `git status` and `git rev-parse HEAD` of each fetched project in the
   AC 19 fixture, by hand, to see that nothing beyond the clone was written.

## Self-review

**Every criterion to a step:**

| AC | Step |
| --- | --- |
| 1 | 2 (four verbs, help), 8 and 9 (`path`, `info` added to `tcw project --help`), 4 (`tcw --help` without the old ones) |
| 2 | 4 |
| 3 | 4 |
| 4 | 5 (test, messages), 3 (argument lists in `evals/seed_fixture.py`, `capture.py`), Verification 4 |
| 5 | 3 (the existing `init` tests run as `project new`), 2 |
| 6 | 6 |
| 7, 8 | 7 |
| 9, 10, 11 | 8 |
| 12-16, 18 | 9 |
| 17 | 10 |
| 19, 20, 21 (first part), 22, 26, 28 | 12 (26 completed in 13) |
| 21 (`--component`, exit 2) | 11 |
| 23, 24, 25, 37 | 13 (37's `path` half in 8) |
| 27, 36 | 14 |
| 29, 30 | 16 |
| 31, 33, 38 | 11 |
| 32, 35 | 15 |
| 34 | 6 (`list`), 9 (`info`), 11 (`provision`) |
| 39 | 18 |

TCW-107's handoff, item by item (spec Notes): fetching and following
declarations — 12; a project already here not fetched — 12 (AC 22); still
read — 12; the dry run — 16; two entries one working copy — 13; no project
at the expected folder — 13; occupied refused before contact — 13;
malformed declaration and a fetched project's error — 11 (AC 31), 15 (AC
32); reader-only checkout, nothing written — 12 (AC 19); `TCW_PROJECT_<ID>`
never fetched — 12 (AC 22); clone into the entry's folder with `subfolder`
removed — 1, 13; empty folder and `.git`-only — 13; `forget_registries()` —
12, 15; `found` in `list` — 6; the `PROJECT_TARGET` branch reused — 13.

**The suite at every boundary.** Step 2 adds verbs beside the old ones
(nothing removed). Step 3 changes only arguments and text, checked by an
exact outcome comparison. Step 4 removes the old commands after every test
and document already names the new ones; `tests/test_documented_cli_surface.py`
is green because Step 3 renamed the documents. Step 5 changes messages and
the assertions on them together. Steps 6-10 add behavior with their tests.
Step 11 changes the stores pass under its existing tests. Steps 12-16 add
the projects pass one rule at a time; each test needs only the steps before
it (AC 26's second half waits for Step 13's occupied check, said there).

**Citations.** Every `file:line` is at `62e41ec5`, re-checked while writing
this plan; every earlier item's code is named, not numbered, and Step 0
re-checks both.

## Spec defects found while planning

Reported, not edited:

1. **Design 1.4's narrowing for documents cannot hold with the suite.**
   `tests/test_documented_cli_surface.py` checks every `tcw` command in
   every Markdown file outside its `ARCHIVAL` list, so `README.md`,
   `docs/guide/`, `skills/`, `AGENTS.md` and `docs/use-cases.md` must stop
   naming the removed commands in this item, or AC 39 fails. Choice 3
   renames the commands only and leaves the prose to TCW-117.
2. **Design 8.1 names fewer fields than the command needs.** Design 7.8's
   bound needs the root of the project whose `.tcw/` holds the deciding
   manifest (the owner) and its way out needs the asking project's root;
   Design 8.1 names only the entry's file, path, repository, branch and
   subfolder. Choice 5 adds `asked_by` and `owner`.
3. **Design 7.8's "an absolute path and a `~` path are refused"** is not a
   consequence of the resolved-folder rule (an absolute path can resolve to
   a direct child of the bound). Choice 8 makes it a separate check made
   before resolving.
4. **TCW-113 AC 29** asserts a reason containing `tcw provision`; after this
   item the message names `tcw project provision` (or the `-C` form, Design
   7.2), so TCW-113's test changes here (Step 5). Its spec should say
   `tcw project provision` or not name the command.
5. **Design 7.4's message assumes a deciding `<file>`** for the new answer;
   none exists if the answer changed without a manifest deciding it.
   Choice 18 gives a fallback text and pins it with a unit test.
6. **Design 1.4 lists `AGENTS.md`** among the documents naming a removed
   command; at `62e41ec5` it names none (`docs-before.txt`), so the list in
   the spec's TCW-117 handoff is one file too long. Harmless.
