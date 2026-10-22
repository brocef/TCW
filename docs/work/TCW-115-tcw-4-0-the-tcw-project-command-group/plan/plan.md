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
option of those the TCW-99 design and the sibling specs allow. Choices 2, 3, 5, 7-10, 12, 18 and 20-22 were revised, and 23-27 added,
after the plan review of 2026-10-22 (its finding is named in each); each of
those was decided by the dispatching session, 2026-10-22, for the reason it
gives.

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
   comparison, a mutation check and a check with the old commands
   unregistered), and only Step 4 removes the old commands. *Reason:* the
   removal then changes no test that was not read by hand or named in Step
   3's list for Step 4, and the mechanical rename is checked against a suite
   in which both names work, so any changed outcome is the rename's fault.
3. **Documents that name a removed command get the new command's name in
   this item, and nothing else** (spec Design 1.6, AC 40, which the spec now
   states after the plan review). Step 3 replaces the command names only,
   keeps every `tcw -C` target one token, and the implement round lists each
   changed passage as TCW-117's list; TCW-117 rewrites the prose.
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
   as a spec defect at the first draft; spec Design 8.1 now lists these
   fields. Every folder in a `Placement` is resolved (`os.path.realpath`),
   so the bound and the record of clones (choice 8) never inherit a path
   as written, with one addition kept unresolved on purpose:
   `repository_path`, the entry's path joined to the folder TCW-107
   Design 2.3 and 4.3 resolve it from, with `subfolder` removed, before any
   link is followed, which choice 8 resolves again, completely, at each
   check.
6. **Which projects each form fetches.** No argument: `registry.unreachable()`
   (TCW-108 plan, its walk order, one record per ID). `<id>`:
   `project_folder(<id>, <active root>)` first (its four outcomes), then
   `load_order(<id>).missing` (TCW-108 Design 4.6). Each round's IDs are
   those, less the IDs this run already attempted.
7. **The order of the checks before any contact**, per project of a round:
   (1) no deciding entry, or an entry with no repository: reported, not a
   failure (7.5); (2) a URL or branch beginning with `-` (7.9); (3) the bound
   (7.8, choice 8); (4) the repository folder's state, `.git`-only then
   occupied (7.6); then, across the round, (5) grouping by repository folder
   (7.7). *Reason:* each check needs only what the earlier ones passed, and
   the cheapest come first; the first that fails names the project's
   refusal. Checks (2) to (4) are made **again for each project immediately
   before its clone writes anything** (spec 7.3, 7.8 "The folder checked is
   the folder written"), on folders resolved again, and the repository
   folder must resolve to the same folder as at the round's check, or the
   project is refused with 7.8's "now leads to" message.
8. **The bound, exactly** (spec 7.8, as corrected after the plan review).
   All of it is one function, `tcw/provision.py`
   `_bound_problem(placement, active_root, cloned, home) -> str | None`,
   with these parts, in order:
   - **Trusted** means `same_folder(placement.owner, active_root)`; such an
     entry has no bound (the rest is skipped).
   - **As written:** a bounded entry's `path` that is absolute or begins
     with `~` is refused with 7.8's first message, before anything is
     resolved.
   - **The owner's repository folder** `R`: `cloned[owner_id]` when this run
     fetched the owner (recorded resolved); otherwise `repository_top(owner)`
     (choice 24); otherwise the owner's root. `R` is resolved. **The bound**
     is `B = Path(os.path.realpath(R)).parent`.
   - **The target** `T`: with `W = placement.repository_path`, `W.name`
     must be a plain name (not `.` or `..`), and
     `P = realpath(W.parent, strict=True)` must succeed; an `OSError` (a
     part that does not exist, a link loop) refuses with 7.8's first
     message, naming `W` as written. Then `T = P / W.name`, and
     `same_folder(T.parent, B)` and `not T.name.startswith(".")` must hold.
     A trusted entry's `T` is `realpath(W)` without `strict`, since its
     missing parent folders are made (choice 9).
   - **The home rule:** `H = realpath(Path.home())`. Refused with 7.8's
     second message when `same_folder(B, a)` for `a` in `[H, *H.parents]`,
     or `B` is the filesystem root, or `B` lies below `H` (some ancestor of
     `B` is the same folder as `H`) and any folder from just below `H` down
     to `B`, `B` included, has a name beginning with `.`.
   - `same_folder(a, b)` (new, `tcw/provision.py`) is `os.path.samefile`
     when both exist, and comparison of `realpath` texts, by whole
     components, when either does not; `Path.home()` is read through the
     `home` argument so tests set it.
   *Reason:* this is spec 7.8 word for word; identity closes the
   letter-case and Unicode bypass on macOS (review S2), the strict
   resolution closes the review's reproduced escape at the round's check
   (M1), and the definitions of `R` and `B` are the review's S1.
9. **The git calls, staging, and the move** (spec 7.6, 7.9, 7.10). For each
   project, after choice 7's checks pass again (immediately before it
   writes), in `tcw/store/fs.py` `fetch_project`:
   1. For a trusted entry whose `T.parent` does not exist: each missing
      folder from the deepest existing ancestor down is made with
      `os.mkdir` (never `makedirs`, never `exist_ok`), recorded in `made`,
      and `realpath(T.parent, strict=True)` is then required to be `T.parent`
      (a link appearing would change it).
   2. `parent_fd = os.open(T.parent, os.O_RDONLY | os.O_DIRECTORY)`; its
      `os.fstat` is recorded, and for a bounded entry must be the same file
      as `B` (device and inode).
   3. The staging parent: `os.mkdir(".tcw-staging-<8 hex>", dir_fd=parent_fd)`
      (`secrets.token_hex(4)`), which fails on any existing name, a symbolic
      link included, and never follows one; on `FileExistsError` a new name,
      up to five in all, then 7.9's "five names" refusal.
   4. `git clone --quiet [--branch <branch>] -- <url> <T.parent>/<staging>/<T.name>`
      through `_git` with `_no_prompt_env`; no separate `checkout`.
   5. The clone's checks (7.9): the `subfolder`, resolved, is inside the
      staging clone (`same_folder` on its ancestors); the configuration at
      `subfolder` or the top (`version_problem`, `legacy_message`, the
      declared `id`); with a `subfolder`, the top folder's declared ID
      against the run's kept answers (choice 18).
   6. Just before the move: the entry's path is resolved again (as in
      choice 8) and must give `T`; `os.stat(T.parent)` must be the same file
      as `os.fstat(parent_fd)`; `os.lstat(T)` must raise `FileNotFoundError`
      or show a real folder (not a link) with no entries; otherwise refused
      as occupied (7.10).
   7. `os.rename(f"{staging}/{T.name}", T.name, src_dir_fd=parent_fd,
      dst_dir_fd=parent_fd)`; an `OSError` is 7.10's "could not move".
   8. In a `finally`: the staging parent removed (`shutil.rmtree` of
      `<T.parent>/<staging>` after checking that `os.stat` of `T.parent` is
      still `parent_fd`'s file); when the project was refused, each folder in
      `made` removed deepest first with `os.rmdir`, stopping at the first
      that is not empty; `parent_fd` closed. A failure to remove the staging
      parent prints 7.9's warning and never replaces the project's own
      outcome.
   *Reason:* `os.rename` within one held-open folder is one system call with
   no partial state and writes into the folder that was checked even if a
   path to it changes; `mkdir` failing on an existing name is the exclusive
   creation 7.9 asks for; `git clone --branch` fails on a branch the remote
   lacks, where `git checkout <branch>` read a matching file name as a file
   and exited 0 (checked in the review; `clone --branch` on a present and a
   missing branch checked while revising this plan, the missing one leaving
   no folder).
   A second program on this machine changing folders while the run works is
   outside what this defends against (spec 7.8). Python 3.11, the oldest
   this project supports (`pyproject.toml:10`), has `dir_fd` for `mkdir` and
   `rename` on Linux and macOS.
10. **The store clone gets `--` too** (spec 7.2). `_obtain`
    (`tcw/store/fs.py:3477-3497`) runs `git clone --quiet <url> <staging>`
    and `git -C <staging> checkout --quiet <ref>`; this item adds `--` before
    the URL and after the `ref` (`checkout --quiet <ref> --`), since the
    reason is the same; the store keeps its separate checkout, because a
    store's `ref` may name a commit, which `clone --branch` does not take. A store `ref`
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
    *Kept after the review's note:* `find_project_root()` is how every
    command finds the active project, and after `-C` it reads the folder
    `-C` entered, so it is the active root; passing the root into
    `resolve_store` would change every one of its callers for no difference
    in behavior.
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
18. **7.4's message names the new answer's deciding manifest file**, and
    the one case without one is stopped before it happens (spec 7.4, 7.9,
    corrected after the plan review): a clone with a `subfolder` whose top
    folder declares an ID with a kept answer at another folder, and which is
    not one of the projects of its group (7.7), is refused in
    `fetch_project`'s step 5 (choice 9) before the move. For anything else,
    the message reads `this run's fetches` in place of the file; a unit test
    pins that fallback, and AC 35's last case tests the real one.
19. **Rounds re-read with `forget_registries()`** (TCW-107 plan, Step 5)
    and then a fresh `FsProjectRegistry` for the active root. Each kept
    answer is looked up again with `placement(id, asked_by)` from its
    recorded `asked_by`; when that root is no longer a project here (it
    cannot vanish in a run that only adds folders, but a race could), with
    `placement(id)` from the active root.
20. **The static guards.** `tests/test_static_guards.py`'s `EXEMPT`
    (`:33-42`) gains the new functions whose messages name git or `.git`
    (`("provision.py", …)` for 7.6's `.git` message and the round runner,
    `("store/fs.py", "fetch_project")`, and `repository_top` for 7.8's third
    message). TCW-107 Step 7 already removes `("cli.py",
    "_provision_projects")` from it (TCW-107 plan:550); Step 0 confirms, and
    removes it here only if it is still there (its existence test, `:108`,
    fails otherwise). `tests/test_subprocess_stdin.py` passes
    because every new git call goes through `_git`.
21. **The help-standard and contract lists** change in the step that
    changes the leaves, so each step ends green:
    - `tests/test_cli_help_standard.py`: `SURFACE` (`:22`) and its count
      (`assert len(SURFACE) == 43`, `:70`; the review cited `:84`) go to 47 in
      Step 2 (the four new leaves), 43 in Step 4 (the four old ones out, into
      `REMOVED`, `:35`), 44 in Step 8 (`project path`) and 45 in Step 9
      (`project info`); the choices check names `project provision` from
      Step 4.
    - `tests/test_cli_contract.py`: `ROWS` (`:48-54`), which
      `test_every_leaf_command_has_a_row` (`:214`) requires to name every
      leaf, gains `"project new": (["project", "new", "--id", "fx"], 0)`,
      `"project list": (["project", "list"], 1)`, `"project config":
      (["project", "config"], 1)` and `"project provision": (["project",
      "provision", "--dry-run"], 1)` in Step 2, and the outside-a-project
      run (`:229`, `set(ROWS) - {"init"}`) leaves out `project new` as it
      leaves out `init`; Step 4 removes the four old rows and `"init"` from
      that set; Step 8 adds `"project path": (["project", "path"], 1)` and
      Step 9 `"project info": (["project", "info"], 1)`, each exiting 1
      outside a project.
22. **TCW-114's note on `check_owned`.** If TCW-114's refusal for a project
    not on this machine (`tcw/ownership.py`, `check_owned`) does not already
    name `tcw project provision <id>`, Step 11 adds it, with a test. If any
    provisioning code still calls `reached_by_both_sides` (TCW-114 plan,
    Step 23's note), it is removed in Step 11 with the 3.x provisioning
    that calls it (`_connected_declarations`, if TCW-107 left it), since
    4.0's walk never reaches a sibling (Design 7.3 (a)): the method on
    `FsProjectRegistry` and on `ProjectRegistry` (`tcw/store/base.py`), and
    its tests (TCW-114's renamed Design 7.1 cases), whose IDs Step 18 lists
    as removed. If anything else still calls it, it stays and the implement
    round says what.
23. **An error line's prefix follows the command typed** (review M2). The
    dispatcher prints `<command>: ` from the parser path that was typed
    (`parser.set_defaults(_command=…)`, `tcw/cli_suggest.py:195`; printed at
    `tcw/cli.py:672`, `:676`, `:683`, `:689`). Five lines of `run_provision`
    (`tcw/cli.py:111`, `:134`, `:150`, `:158`, `:186`) and one of `_show`
    (`tcw/config_cli.py:267`) instead write `tcw provision:` and
    `tcw config show:` as fixed text. Step 2 makes those six take the typed
    command (`args._command`, passed down as `prefix`), so the old names
    print exactly what they print today and the new names print
    `tcw project provision:` and `tcw project config:`. Then an assertion
    on `tcw init:`, `tcw provision:`, `tcw projects list:` or
    `tcw config show:` at the start of an expected error is the command's
    name, not message text, and Step 3's script renames it with the
    command's arguments.
24. **The owner's repository folder** (spec 7.8, review D2):
    `repository_top(root) -> Path | None`, in `tcw/provision.py`. When
    neither `root` nor any folder above it holds a `.git` entry
    (`os.path.lexists`), `None` (the owner's root is used). Otherwise
    `git -C <root> rev-parse --show-toplevel` through `_git`; its answer,
    resolved; any failure (a non-zero exit, `FileNotFoundError` for a
    missing `git`) raises `RepositoryUnknown(reason)`, which
    `_bound_problem` turns into 7.8's third message for every bounded entry
    of that manifest. `git_root` (`tcw/store/fs.py:240-255`) is not used:
    it returns `None` for every failure.
25. **A failed store does not stop the projects pass** (spec 7.2, 7.13;
    review S12), as in 3.x (`tcw/cli.py:165-191` at `62e41ec5`): the stores
    pass returns its counts (`fetched`, `failed`) and the projects pass
    adds its own; the last line counts both. A configuration that cannot
    be read still returns 1 before either pass (`:106-112`).
26. **A dry run never fetches, from the step that builds the projects
    pass** (review S13). Step 12's `provision_projects` takes `dry_run`
    from its first version: the first round is planned with the checks that
    exist at that step, its `→` and `would fetch` lines printed, and the run
    stops; Step 16 adds the rest of 7.12. So no step leaves a `--dry-run`
    that clones.
27. **Every provisioning test sets `HOME`** (spec AC preamble): the
    fixture of Step 11 sets it to `tmp_path_factory.mktemp("home")`, outside
    `<tmp>`, unless a test sets its own.

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
     (`tcw/serve/work.py`) still exists, `check_owned`; that the `-C`
     skip in `_check`, `command_problem` and `command_problems` takes exactly
     one token (Design 1.6 relies on it); and every caller of
     `reached_by_both_sides` and whether `_connected_declarations` survived
     TCW-107 (choice 22).
   - TCW-107's handoff (2): whether a `repository` or branch beginning with
     `-` is now a manifest problem; if so, AC 37's two CLI cases assert
     TCW-107's message through 7.14 and 7.9's own check is pinned in
     `tests/test_fetch_project.py` only (spec AC 37).
   - TCW-113 (its plan and its landed tests): whether its AC 29 test took
     the handoff (asserting `has not been provisioned here` and `provision`,
     not `tcw provision`); if not, Step 5 changes that one assertion and the
     implement round says so. Any other test it added that matches the
     `StoreNotProvisioned` text or runs a removed command.
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
     removed command, with its count (43 at `62e41ec5`: `README.md`, 18
     capability descriptions, two taxonomy descriptions, four guides,
     `docs/use-cases.md`, 15 files under `skills/`,
     `tcw/work/procedures/search.md`, `tests/cli/scenarios/13-release-integrity.md`;
     1 + 18 + 2 + 4 + 1 + 15 + 1 + 1, rechecked while revising this plan).
   - `argv-sites.txt`: every list or tuple literal under `tests/` and
     `evals/` that holds a removed command's words outside a call the script
     of Step 3 recognises, from `git grep -nE` for `[(\[] *["'](init|provision)["']`,
     `["']projects["'], *["']list` and `["']config["'], *["']show` less the
     `git` lines. At `62e41ec5` these are
     `tests/test_project_files_cli.py:186-187` (`("init", "--id", "x")`,
     `("config", "show")`), `tests/test_cli_handler.py:109`
     (`["projects", "list"]`, `:108-109`), `tests/test_store_provisioning.py:780`
     (`[["provision"], ["init"]]`, whose expected text at `:792` is built
     from `command[0]`), `tests/test_projects_list.py:118` (`("provision",)`,
     with the prefix built from it at `:128`), and `ROWS` in
     `tests/test_cli_contract.py:48-54`; `tests/work/test_cli_surface.py:138`
     (`["init"]`, the removed `tcw work init`) is not a site.
3. **The comparison script:** the scratchpad's `compare_outcomes.py
   <before.xml> <after.xml> <allowed.txt>` is TCW-108's (its plan, the
   paragraph "The outcome comparison", before its Step 8a), rebuilt if the
   scratchpad no longer holds it. Its rules: a test ID missing from `after`
   must be in `allowed.txt`, which must list exactly those; an ID in both
   must keep its outcome; a new ID must pass. The record it compares
   against is taken at the end of Step 2, not here, so that Steps 1 and 2's
   own changes are never blamed on the rename.

**Proves it:** the implement round lists each citation with its file and
line on `v4` and "as planned" or the correction; the four inventories
exist.

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

`tests/test_cli_help_standard.py`: `SURFACE` gains the four new leaves and
its count goes to 47 (choice 21); the existing walk then checks each has
`Prints:`, `Writes:` and an example. `tests/test_cli_contract.py`: `ROWS`
gains the four rows of choice 21, and the outside-a-project run leaves out
`project new`.

The prefix (choice 23): `tcw project provision` with a configuration that
cannot be read prints `tcw project provision: …`, and `tcw provision` the
same case prints `tcw provision: …`, byte for byte as before; likewise
`tcw project config` and `tcw config show` for a problem in the active
project's own file.

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
- The six fixed prefixes of choice 23 (`tcw/cli.py:111`, `:134`, `:150`,
  `:158`, `:186`; `tcw/config_cli.py:267`) take the typed command, passed
  from each handler as `prefix=args._command`. The messages' texts are
  unchanged in this step ("run `tcw provision`" and the like), so Step 3's
  outcome comparison is exact; Step 5 changes them.
- At the end of the step, the outcome record Step 3 compares against:
  `.venv/bin/pytest -q --junitxml=<scratchpad>/outcomes-step2.xml`, all
  passing.

**Proves it:** the new file; `tests/test_cli_help_standard.py`;
`tests/test_cli_contract.py`; the full suite.

## Step 3 — the tests and documents move to the new names, mechanically

No behavior changes. Every change in this step is made by one script, kept
in the scratchpad as `rename_commands.py`, and nothing by hand except the
sites listed below.

**The script**, over the files of `sites-before.txt` and `docs-before.txt`:

- **Argument lists**, in Python source under `tests/` and `evals/` and in
  `tests/fixtures/prompt_fallback/capture.py`: the string literal `"init"`
  (or `'init'`) as the first command word of a call that runs TCW
  (`main([…`, `cli(capsys, …`, `run(…, `, `_tcw(…, `, `tcw(…, `,
  `_run(dest, …`, and `["tcw", "init", …]`) becomes `"project", "new"`;
  `"provision"` becomes `"project", "provision"`; `"projects", "list"`
  becomes `"project", "list"`; `"config", "show"` becomes `"project",
  "config"`. A literal preceded by `"git", `, or inside a call of `git(`,
  `_git(` or `subprocess.run(["git"`, is never changed. Every candidate the
  script skips, and why, is printed.
- **Error prefixes**, in the same files: the text `tcw init:`,
  `tcw provision:`, `tcw projects list:` and `tcw config show:` inside a
  string literal, which since Step 2 is always the typed command's name
  (choice 23), becomes `tcw project new:`, `tcw project provision:`,
  `tcw project list:` and `tcw project config:`. A mention of a command
  inside message text, such as "run `tcw provision` to obtain it", with no
  colon after the name, is left for Step 5.
- **Text**, in Markdown and YAML anywhere outside the archives, and in
  docstrings and comments under `tests/` and `evals/`: the whole words
  `tcw init` → `tcw project new`, `tcw projects list` → `tcw project list`,
  `tcw projects` → `tcw project list` only where followed by a backtick or
  end of command, `tcw config show` → `tcw project config`,
  `tcw provision` → `tcw project provision`. `tcw initial…` and
  `tcw provisioning` are not matched (`\b` after the word). **Python under
  `tcw/` is not touched** (review S6): a script cannot tell a docstring from
  a message there, and those are Step 5's, by hand; Markdown under `tcw/`
  (`tcw/work/procedures/search.md`) is a document and is renamed here.
- **Not touched:** `docs/work/`, `docs/changelogs/`, `docs/release-notes/`,
  `docs/migration-guide-*` and the other `ARCHIVAL` trees
  (`tests/test_documented_cli_surface.py:38-53`); a command named inside an
  expected message's text, which changes with the messages in Step 5. The
  script lists each such assertion it left.
- **No new `-C` text:** the script writes no `tcw -C`; any passage in
  `docs-before.txt` that already writes one keeps a one-token target (spec
  Design 1.6), checked by reading `rename-report.txt`.

**Changed by hand**, each listed in the report, because the script's
patterns do not reach them (`argv-sites.txt`, Step 0):
`tests/test_project_files_cli.py:186-187`; `tests/test_cli_handler.py:108-109`;
`tests/test_store_provisioning.py:780` and the expected text built from
`command[0]` at `:792` (it becomes `" ".join(command)`, with the
parametrized lists `["project", "provision"]` and `["project", "new"]`);
`tests/test_projects_list.py:118` and the prefix built from it at `:128`.
`ROWS` and `SURFACE` are not changed here: they list the old leaves, which
still exist until Step 4 removes them. Left as they are on purpose:
`tests/work/test_cli_surface.py:138` (`tcw work init`, a removed `work` verb
that still exits 2) and every `git init`.

**Checks, in order:**

1. **The inventory:** the script's report (every changed line, every
   skipped candidate with its reason, every hand change) is saved as
   `rename-report.txt` and read whole by hand; every skipped `"init"` is
   confirmed to be `git init` or not a TCW command. The Markdown part of
   that report, each passage with what it now says, is copied into the
   implement round as the list TCW-117's handoff names (spec Design 1.6).
2. **The outcome comparison:** `.venv/bin/pytest -q
   --junitxml=<scratchpad>/outcomes-step3.xml`, then `compare_outcomes.py
   outcomes-step2.xml outcomes-step3.xml empty.txt`: no test ID disappears
   and no outcome changes, with an empty allowed list (the baseline already
   holds Steps 1 and 2's tests, so nothing is added either). The test IDs
   do not change, since the script changes arguments and text, not function
   names or parametrize IDs taken from them; if one does change, it is a
   finding, not something to list.
3. **The mutation check:** with `run_init` called from `project new` made to
   raise `TcwError("mutated")` (and only from there: the old `init` still
   works), the converted tests that build projects through the CLI go red,
   and the count is recorded; reverted. The same for `project provision`.
   This proves the tests now run the new names.
4. **The old commands unregistered** (review M4): with the four old
   subparsers taken out of `build_parser` in the working tree only, the
   suite is run, and the failing IDs must be exactly the list Step 4 says it
   changes (`step4-changes.txt`: the side-by-side tests of Step 2, the
   `SURFACE` count and walk, `ROWS`'s four old rows and the IDs keyed by
   them, the suggestion cases that name a removed command); the change is
   then reverted. A failure outside that list is a test still running an
   old command, which is renamed here and the check run again. This is the
   check the mutation check cannot make: that no test still runs an old
   name.
5. `tests/test_documented_cli_surface.py` and `tests/test_shipped_text.py`
   pass with the documents now naming `tcw project …`.

**Proves it:** the five checks above; the full suite.

## Step 4 — the old commands removed; the table; the suggestions (Design 1.2, 1.3)

**Tests first:**

- `tests/test_project_group.py`: AC 1 (`tcw --help` lists `project` and not
  `init`, `projects`, `config`, `provision`); AC 2, each of the four
  invocations exits 2, writes nothing (the folder's listing before and
  after), and prints its table line; the side-by-side tests of Step 2 are
  removed.
- `tests/test_command_suggestions.py`: AC 3's rows for `tcw list` and
  `tcw new`, the two whose answer this step settles (`tcw path` waits for
  Step 8, which adds `project path`, and `tcw work info x` and `tcw info`
  for Step 9, which adds `info`; review M5); and a guard that no **key** of
  `SYNONYMS` (`tcw/cli_suggest.py:27-39`) other than `info` is a subcommand
  anywhere in the tree (Design 1.3's "this rule changes no other
  suggestion"). The guard is on the words typed, not on their targets:
  the targets `show`, `list` and `advance` are subcommands everywhere
  (review S7). Until Step 9 the guard holds with `info` as well; Step 9
  adds the exception.
- `tests/work/test_cli_surface.py` and `tests/test_command_suggestions.py`:
  every existing case passes; any case that named a removed command is
  changed and listed in the implement round (at `62e41ec5` there is none:
  `tests/work/test_cli_surface.py:138` checks only that `tcw work init`
  exits 2, which still holds, since the table applies at the top level
  only and `init` is then a subcommand nowhere).
- `tests/test_cli_help_standard.py` and `tests/test_cli_contract.py`
  (choice 21): `SURFACE` loses the four and its count goes to 43, `REMOVED`
  gains them, the choices check names `project provision`; `ROWS` loses the
  four old rows and the outside-a-project run no longer names `init`. The
  IDs this removes (`test_every_command_outside_a_project[provision]`,
  `[projects list]`, `[config show]`, and the side-by-side tests) are the
  ones `step4-changes.txt` (Step 3, check 4) listed, and Step 18 lists them
  again.

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
  parser is the top-level one (choice 4), and then puts a synonym whose
  target is valid at the level typed before the commands found elsewhere,
  then fills up to `_MAX` (`:47`). The synonym-first order has no visible
  effect until Step 9 registers `info`; its tests are there.

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
  `StoreNotProvisioned` text in TCW-112's tests changes to
  `tcw project provision`, and in TCW-113's only if Step 0 found it did not
  take the handoff (spec, Handoffs back to earlier items).

**Changes**, each a message, help text or comment naming a removed command:

- `tcw/cli.py`: `_cmd_validate`'s "run `tcw provision`" (`:432`). The
  error prefixes already follow the typed command since Step 2 (choice
  23).
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
depth, Design 2.6, which this item relies on). AC 3's `tcw path` row
(`tests/test_command_suggestions.py`): still the three axis `path` verbs,
`tcw project path` being the fourth and dropped.

**Changes:** `tcw/project_cli.py`: the `path` verb, `[<id>]`, help per the
standard; handler: `validate_project_id` (`tcw/project_files.py`, after
TCW-107) with `ValueError` → `UsageError`; the command's registry
(`begin_command`'s), `require_valid()`, then `project_folder(<id>, root)`;
`Unreachable` → exit 5 with its `message` (TCW-107 Design 6.2);
`UnknownProject` / `ProjectGraphError` → exit 1 (choice 13). No `<id>`:
prints `find_project_root()`.

**Proves it:** the new file; `tests/test_cli_help_standard.py` (`SURFACE`
gains `project path`, count 44) and `tests/test_cli_contract.py` (`ROWS`
gains `project path`, exit 1 outside a project), choice 21; the full
suite.

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
AC 3's rows for `tcw work info x` (`` did you mean `tcw work show` or
`tcw project info`? ``) and `tcw info` (`` `tcw project info` ``), in
`tests/test_command_suggestions.py`, now that `info` is a verb (review M5);
the synonym-key guard of Step 4 gains `info` as its one exception.

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

**Proves it:** the new file; `SURFACE` gains `project info` (count 45) and
`ROWS` gains `project info` (exit 1 outside a project), choice 21; AC 3's
two rows; the full suite.

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
  `stand_in_git(tmp_path, tmp_path_factory, monkeypatch)`, which also sets
  `HOME` to `tmp_path_factory.mktemp("home")` (choice 27): a script in
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
  clone's argv is `["git", "clone", "--quiet", "--", url, staging]`, and
  with a `ref` the checkout's is `["git", "-C", staging, "checkout",
  "--quiet", ref, "--"]` (choice 10); a store `ref` naming a file of the
  repository and no branch fails, where it passed before.
- AC 26's store part (choice 25): a store that fails, then the projects
  pass still runs (here, with nothing to fetch, `nothing to fetch` is still
  printed), and the run exits 1; the counts are completed in Step 12.
- If choice 22 applies: the tests of `reached_by_both_sides` are removed
  with it, each ID listed in the implement round and in Step 18.

**Changes:**

- `tcw/cli.py` `run_provision` (`:86-192`): takes `project_id` and the
  components; `<id>` with components → `UsageError`; for the no-argument and
  `<id>` forms, `registry.require_valid()` first (choice 11); the stores
  pass only for the no-argument and `--component` forms; the early return
  at `:160-163` becomes "continue to the projects pass" for the no-argument
  form; then `tcw.provision.provision_projects(…)` (Step 12) for the
  no-argument and `<id>` forms. The `TCW_PROJECT_<ID>` refusal (`:127-135`)
  is what TCW-107 Step 7 kept (its choice 6); unchanged. A store that fails
  no longer ends the command: the stores pass returns `(fetched, failed)`
  and the projects pass follows (choice 25).
- `tcw/cli.py` (or wherever TCW-107 left them): `_connected_declarations`,
  if still there, and `reached_by_both_sides` on `FsProjectRegistry` and
  `ProjectRegistry` (`tcw/store/base.py`), when Step 0 found no other
  caller (choice 22).
- `tcw/project_cli.py`: `provision` gains the optional positional `<id>`.
- `tcw/store/fs.py` `_obtain` (`:3477-3497`): `--` before the URL and
  after the `ref` (choice 10).
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
AC 22's `--dry-run` cases run against the dry run this step builds
(choice 26), so none of them can clone; AC 26's last sentence (a failed
store counted with the projects: `fetched 1, failed 2`).

**Changes:** new `tcw/provision.py`:

- `provision_projects(root, project_id=None, *, dry_run, out, stores=(0,
  0)) -> int` (returns the exit code; prints to standard error only;
  `stores` is the stores pass's `(fetched, failed)`, added to the last
  line's counts, choice 25). With `dry_run`, from this first version, the
  first round is planned with the checks that exist so far, its `→` and
  `would fetch` lines are printed, and the run stops with nothing fetched
  (choice 26).
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
- `tcw/store/fs.py`: `fetch_project(url, branch, target, *, project_id,
  subfolder) -> None`, raising `FetchRefused(message)` (a `TcwError`),
  first version: `git clone --quiet [--branch <branch>] -- <url>` into a
  staging folder beside `target`, then `os.rename`; `target` is already
  resolved (choice 8). Step 13 completes it to choice 9.
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
`<tmp>`; `.DS_Store` beside `.git`: occupied), AC 25 (the four remotes, the
unreadable path and the missing branch `#nosuch`: exit 1, each message,
nothing at `<tmp>/core` and no `.tcw-staging-*` in `<tmp>`; the same with
`app`'s entry at `../new/core`, leaving no `<tmp>/new`), AC 26 completed,
AC 36 (g) (a committed link at the `subfolder`: `leads outside the clone`,
nothing at `<tmp>/mono`), AC 37 (the leftover
`<tmp>/.tcw-staging-0123abcd/core` left as it was while `core` is fetched
into `<tmp>/core`; `--template=<tmp>/t` and `<remote>#--orphan` refused with
`beginning with '-'`, no `clone`, or through 7.14 if Step 0 found TCW-107
refuses them).

Library tests in new `tests/test_fetch_project.py`, each naming the step of
choice 9 it pins:

- step 7: the move raising `OSError` (`os.rename` patched) refuses with
  `<id>: could not move the clone into <folder>: <reason>`, leaves no
  staging folder and nothing at the folder;
- step 6: a file appearing in the folder between the check and the move
  (the check's second call patched to see it) refuses as occupied; a
  symbolic link put at the folder's name after the first check refuses as
  occupied and nothing is written through it; the entry's path resolving
  elsewhere just before the move (the resolver patched) refuses with 7.8's
  "now leads to" message and leaves nothing at either folder;
- step 3: the staging name colliding (an existing `.tcw-staging-<hex>`,
  `secrets.token_hex` patched to return it first) is retried, never written
  into; five collisions in a row refuse with 7.9's "five names" message;
- step 8: removing the staging parent failing (`shutil.rmtree` patched)
  prints 7.9's warning naming it, and the project's own outcome (fetched,
  or the refusal) is reported unchanged;
- step 1 and 8: a trusted entry's missing parents are made one at a time
  and, when the clone then fails, removed deepest first, a parent that has
  meanwhile gained an entry being left;
- step 4: the argv of the clone is `["git", "clone", "--quiet", "--branch",
  "<b>", "--", url, …]` with a branch and without `--branch` otherwise, and
  no `checkout` call is made;
- step 5: a `subfolder` link leading outside the staging clone is refused
  without reading the configuration it leads to (the reader patched to
  fail if called); 7.9's `-` check, unit-tested here whatever TCW-107 does
  (spec AC 37).

**Changes:**

- `tcw/provision.py` `_plan_round`: checks (2), (4) and (5) of choice 7 —
  the `-` check (`<id>: <file> gives a repository beginning with '-'`), the
  folder state (`_folder_state(folder) -> "absent" | "empty" | "git-only" |
  "occupied"`, read with `os.lstat` and `os.scandir`, so a link at the
  folder's name is occupied, with 7.6's two messages), and the grouping by
  resolved repository folder with `normalized_url`
  (`tcw/store/checkouts.py:21-57`) and branch (7.7's conflict message; the
  second and later projects of a group are `Comes-with(first)`).
- `tcw/provision.py` `_run_round`: before each project's `fetch_project`,
  checks (2) to (4) again on folders resolved again, and the "now leads to"
  refusal when the repository folder differs from the round's (choice 7).
- `tcw/store/fs.py` `fetch_project`, full: steps 1 to 8 of choice 9. Its
  checks of the clone are new code, each tested by AC 25 (review S9): the
  `PROJECT_TARGET` branch of `_is_store_layout` checks only that the
  configuration file exists (`:3150-3153`), so nothing of it is reused but
  the pattern of cloning beside the target and renaming in. `git`'s failure
  text goes through `_git_reason`.
- `tcw/store/fs.py`: the `PROJECT_TARGET` branch of `FsStoreProvisioner`
  and `_is_store_layout` (`:3121`, `:3150`, `:3467`), now unused by any
  caller (Step 0 confirms), is removed. If something still calls it, it
  stays and the implement round says why.
- After a round, Design 7.11's first rule: each fetched project must be
  found at its entry's folder; otherwise refused as 7.7's "has no TCW project
  at" when it came with another's clone.

**Proves it:** the tests above; `tests/test_static_guards.py`;
`tests/test_subprocess_stdin.py`; the full suite.

## Step 14 — provision: the bound (Design 7.8)

**Tests first**, `tests/test_project_provision.py`, each with `HOME` set by
the fixture outside `<tmp>` unless the case sets its own (choice 27):

- AC 27 whole: each of `../../base-far`, `../x/base`, `vendor/base`,
  `../.base`, and the absolute path `<tmp>/repos/base` in a personal
  manifest committed into `core`'s remote (directly inside the bound, so
  only the as-written rule refuses it; review S8), refused before contact,
  the stand-in saw one `clone`, 7.8's first message naming `<tmp>/repos`,
  nothing made, `core` stays, exit 1; `../base` fetched into
  `<tmp>/repos/base`; a second run refuses `../../base-far` the same way;
  the way out names `tcw -C <tmp>/repos/core project provision base` and
  `<tmp>/repos/core/.tcw/tcw-manifest.local.yaml` and not app's personal
  manifest; running that `-C` command fetches `base` into `<tmp>/base-far`,
  then `provision` in `app` prints `nothing to fetch`; a fresh fixture with
  `base: <tmp>/elsewhere/base` in core's personal manifest, then the `-C`
  command; trusted entries in app's own manifests honoured with missing
  parent folders made; the `ws` / `wp` case naming `<tmp>` and app's own
  manifests, then fixed by app's personal manifest.
- AC 36 whole: (a) the committed links `up -> ../..` refused naming
  `<tmp>/base`, `lnk -> ..` fetched; (b) `<tmp>/repos-x`; (c)
  `HOME=<tmp>/home` and `HOME=<tmp>/home/inner`, 7.8's second message,
  nothing at `<tmp>/home/base`, while `core` from app's own entry is
  fetched, and the hidden case with `app` at `<tmp>/home/.local/app`; (d)
  the review's layout, `aa` at `../aa` and `bb` at `../aa/l/../../bb` with
  `aa` committing `l -> ../../far/x`: `bb` refused at the round's check,
  `aa` fetched, nothing outside `<tmp>/repos`; (e) letter case, skipped
  where the file system tells `a` from `A`, and run on macOS in the
  implement round; (f) `<tmp>/ws/.git` reading `gitdir: <tmp>/nowhere`:
  7.8's third message.
- Library tests of `_bound_problem` in `tests/test_fetch_project.py`, each
  part of choice 8 with a mutation check (the part removed, the test seen
  red, restored): the as-written rule; the strict resolution; the hidden
  folders below home; `repository_top`'s three outcomes (no `.git` above;
  git answers; git fails, including `git` missing from `PATH`). For
  `same_folder`, the mutation (identity replaced by comparing text) is seen
  red only by AC 36 (e), since only a file system that ignores letter case
  or Unicode spelling has two spellings for one folder: the implement round
  runs that test and its mutation on macOS and records both; on Linux, and
  so in CI, it is skipped.
- The re-check before each clone (choice 7): a library test of `_run_round`
  in which the resolver returns a different folder on its second call
  refuses with 7.8's "now leads to" message and runs no `clone`.

**Changes:** `tcw/provision.py`: `_bound_problem` and `same_folder`
(choice 8), `repository_top` and `RepositoryUnknown` (choice 24), check (3)
of choice 7, with the three messages and the way out of 7.8 (the asking
project is the active one, or not; the `-C` sentence only when `<file>` is
the asking project's own manifest); `cloned` maps each project fetched in
this run to its resolved repository folder, for the owner's repository
folder. Missing parent folders are made for trusted entries before the
staging folder, by `fetch_project`'s step 1, and removed on a refusal
(choice 9; review M6).

**Proves it:** the tests above; the full suite.

## Step 15 — provision: answers kept for the run, and a fetched project's own problems (Design 7.4 second half, 7.11)

**Tests first**, `tests/test_project_provision.py`: AC 35 (`core` fetched,
`lib` refused with 7.4's message naming `<tmp>/lib`, `<tmp>/repos/lib` and
core's manifest, one `clone`, nothing at `<tmp>/repos/lib`, exit 1; with
`lib: ../lib` in app's personal manifest, the next run prints `nothing to
fetch`), AC 32 (core's remote holding a manifest with a TCW-107 Design 1.8
problem: fetched and kept, 7.11's message naming its manifest and saying to
remove `<tmp>/core`, no further round, `base` not attempted, exit 1; a
malformed `parents:` in the remote: fetched, a warning, exit 0). AC 35's
last case, the real one of choice 18: `server`'s remote with `id: lib` at
its top refused before the move, nothing at `<tmp>/mono`, `tcw project path
lib` still `<tmp>/lib`; with `id: mono` there, fetched. A unit test of 7.4's
fallback text (choice 18).

**Changes:** `fetch_project` takes the run's kept answers, as a mapping
from ID to resolved folder, for its step 5 (choice 18). `tcw/provision.py`:
before the first clone, `kept` records
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

**Changes:** `tcw/provision.py`: the dry run of choice 26 completed: the
first round's plan is printed (the `→` line, `would fetch`, the "cannot be
listed" line, `would come with`) after every check a real run makes before
contact, the bound included, and the run stops there; no `mkdir`, no
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
- Every description written here that names `tcw -C` gives its target as
  one token (`tcw -C <folder> project provision <id>`, spec Design 1.6), so
  the document checks read it; the new provisioning capability's
  description states the bound as spec 7.8 has it, the hidden folders below
  the home folder and the refusal when git cannot say included.
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
it: the side-by-side tests of Step 2; the IDs keyed by the four old
`ROWS` entries, `test_every_command_outside_a_project[provision]`,
`[projects list]` and `[config show]`; any help-standard or suggestion ID
keyed by an old command's name; and, under choice 22, the tests of
`reached_by_both_sides`), and the sweep greps of Step 0 showing only
`REMOVED_COMMANDS` and the archival trees. AC 40: the documents' greps of
Step 0 find no removed command outside the archives. The CI workflow
runs bare `pytest` (`.github/workflows/test.yml`), so the run is bare
`pytest`, not `python -m pytest`.

**Proves it:** AC 39, AC 40.

## Step 19 — Documentation Sync

The `documentation-sync` skill is invoked, as this repository's CLAUDE.md
requires before any code change is reported complete, and its verdict per
entry is recorded in the implement round; the table below is what this
plan expects it to find.

| Entry | Fires? | What this item does |
| --- | --- | --- |
| `README.md` [Public-API] | yes | Command names only (Step 3, spec Design 1.6). The prose for the `tcw project` group is TCW-117's (spec Non-goals, Design 1.6). |
| `docs/guide/jira.md` [Jira-Change] | no | No `tcw work` command, `work.jira` key or stage status changes. Step 3 renames any removed command it names (none at `62e41ec5`). |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes | Command names only (Step 3: `cli.md`, `configuration.md`, `multi-repo.md`, `work.md`). The rewrite — the group, the bound, the `.git`-only refusal, staging folders — is TCW-117's (spec, Handoffs to later items). |
| `docs/release-notes/upcoming/TCW-115-tcw-4-0-the-tcw-project-command-group.md` [Public-API] | yes | Written at implement: the `tcw project` group and its six verbs; the four removed commands and their replacements; `--origin`'s new label; provisioning fetches parents and children in turn, places a clone from another project's manifest only directly beside that project and never at or above the home folder or inside a hidden folder below it, refuses a folder holding only `.git`, and `--component` fetches no project; a store whose `ref` names no branch, tag or commit now fails. Under `## New` and `## Changed`, plain language. |
| `docs/changelogs/upcoming/TCW-115-tcw-4-0-the-tcw-project-command-group.md` [Any-Code-Change] | yes | Written at implement: Added (`tcw/project_cli.py`; `tcw/provision.py` with `_bound_problem`, `same_folder`, `repository_top`; `FsProjectRegistry.placement` and `Placement`; `fetch_project`, `FetchRefused`; `REMOVED_COMMANDS`; `origin_label`, `origin_json`), Changed (the suggester's synonym order; `_Writer.comment`'s shape; `run_provision`'s forms, graph check and store-failure handling; error prefixes follow the typed command; `StoreNotProvisioned`'s `-C` form; `--` before every clone URL and after a store's `ref`; every message naming a removed command), Removed (`tcw init`, `tcw projects`, `tcw config`, `tcw provision`; the `PROJECT_TARGET` branch; `reached_by_both_sides` if no caller remained), Internal (`tests/provision_support.py`'s stand-in `git`; the test rename). |
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
7. On macOS, AC 36 (e) (letter case) run, and run again with
   `same_folder` replaced by a comparison of text, to see it go red for
   that reason; both results recorded, since CI on Linux skips it.

## Self-review

**Every criterion to a step:**

| AC | Step |
| --- | --- |
| 1 | 2 (four verbs, help), 8 and 9 (`path`, `info` added to `tcw project --help`), 4 (`tcw --help` without the old ones) |
| 2 | 4 |
| 3 | 4 (`tcw list`, `tcw new`, the synonym-key guard), 8 (`tcw path`), 9 (`tcw work info x`, `tcw info`) |
| 4 | 5 (test, messages), 3 (argument lists in `evals/seed_fixture.py`, `capture.py`), Verification 4 |
| 5 | 3 (the existing `init` tests run as `project new`), 2 |
| 6 | 6 |
| 7, 8 | 7 |
| 9, 10, 11 | 8 |
| 12-16, 18 | 9 |
| 17 | 10 |
| 19, 20, 21 (first part), 22, 26, 28 | 12 (26's store part begun in 11, its occupied case completed in 13) |
| 21 (`--component`, exit 2) | 11 |
| 23, 24, 25, 37 | 13 (37's `path` half in 8) |
| 27, 36 (a)-(f) | 14 |
| 36 (g) | 13 |
| 29, 30 | 16 |
| 31, 33, 38 | 11 |
| 32, 35 | 15 |
| 34 | 6 (`list`), 9 (`info`), 11 (`provision`) |
| 39 | 18 |
| 40 | 3 (the rename, the list for TCW-117), 18 (the greps) |

TCW-107's handoff, item by item (spec Notes): fetching and following
declarations — 12; a project already here not fetched — 12 (AC 22); still
read — 12; the dry run — 16; two entries one working copy — 13; no project
at the expected folder — 13; occupied refused before contact — 13;
malformed declaration and a fetched project's error — 11 (AC 31), 15 (AC
32); reader-only checkout, nothing written — 12 (AC 19); `TCW_PROJECT_<ID>`
never fetched — 12 (AC 22); clone into the entry's folder with `subfolder`
removed — 1, 13; empty folder and `.git`-only — 13; `forget_registries()` —
12, 15; `found` in `list` — 6; the `PROJECT_TARGET` branch's pattern
reused and the branch removed — 13.

**The suite at every boundary.** Step 2 adds verbs beside the old ones,
with their `ROWS` and `SURFACE` entries (choice 21), and makes six fixed
error prefixes follow the typed command, which leaves every old command's
output as it was (choice 23). Step 3 changes only arguments, error
prefixes and text, checked by an exact outcome comparison against Step 2's
record with an empty allowed list, by a mutation check, and by a run with
the old commands unregistered whose failures must be exactly Step 4's
list. Step 4 removes the old commands, their `ROWS` and `SURFACE` entries,
and changes exactly those tests; `tests/test_documented_cli_surface.py` is
green because Step 3 renamed the documents. Step 5 changes messages and
the assertions on them together. Steps 6-10 add behavior with their tests;
Steps 8 and 9 add their `ROWS` and `SURFACE` entries and the AC 3 rows that
need their verbs. Step 11 changes the stores pass under its existing tests.
Steps 12-16 add the projects pass one rule at a time; each test needs only
the steps before it, and the dry run never clones at any of them (choice
26).

**Citations.** Every `file:line` is at `62e41ec5`, re-checked while writing
this plan; every earlier item's code is named, not numbered, and Step 0
re-checks both.

## Spec defects found while planning

All six were folded into the spec after the plan review, as TCW-114 did
with its Design 9.5 (spec Notes, "Corrected after the plan review"):

1. Design 1.4's narrowing for documents could not hold with the suite: now
   spec Design 1.6 and AC 40 (choice 3).
2. Design 8.1 named fewer fields than the command needs: now lists
   `asked_by`, `owner` and `repository_folder` (choice 5).
3. Design 7.8's refusal of absolute and `~` paths is a separate rule, made
   before resolving (choice 8).
4. TCW-113's AC 29 asserts `tcw provision`: a handoff to TCW-113 in the
   spec; Step 0 checks whether it was taken, and Step 5 changes the one
   assertion if not.
5. Design 7.4's changed answer without a deciding manifest can arise,
   through a clone's top folder; spec 7.9 now refuses it before the move
   (choice 18, AC 35's last case), with the fallback text kept.
6. `AGENTS.md` names no removed command: dropped from the spec.
