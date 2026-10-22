# Plan — TCW 4.0: inherited configuration, personal settings and environment overrides

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`).

**Where the references point.** File and line references to `tcw/` and
`tests/` are to commit `d2d02829` on `v4`, where TCW-106 is built and
TCW-107, TCW-110, TCW-108 and TCW-111 are not. (The spec's references are to
`67c4c15a`; TCW-106's review commits since then moved some lines of
`tcw/config.py` and `tcw/work/config.py` by a few lines, so the numbers here
differ from the spec's in places, for the same code.) Those four items land
first, in the order TCW-106, TCW-107, TCW-110, TCW-108, TCW-111. Where a step
changes code one of them writes, it names that code by the name their plans
give it, cited by plan step, and Step 0 re-reads every citation on the
merged `v4` and corrects this plan before Step 1. A citation that cannot be
found then is fixed in this plan, never worked around in the code.

**The gate at every step boundary.** Every step writes its tests first and
sees them fail for the reason they name, then makes the change, and ends with
the named tests passing and the **whole Python suite** passing:
`.venv/bin/pytest` with no arguments, from the worktree's root, as CI runs it
(`.github/workflows/test.yml`). A step that touches the web client also ends
with TCW-110's web gate (`pnpm exec tsc --noEmit`, `pnpm test`, `pnpm lint`,
`pnpm exec prettier --check <the files it changed>`, `pnpm build`). No step of
this plan is expected to change the client; Step 11 changes only the server.
A step that cannot end green is two steps.

**Which `tcw` drives this repository's lifecycle.** This item follows the
header of TCW-110's plan, rules 1-8, as TCW-108's plan does: the lifecycle is
driven with the `tcw` first on `PATH` (the primary checkout's editable
install, 3.x), never `.venv/bin/tcw`; `.venv/bin` is never put first on
`PATH` in a shell that runs a lifecycle command; the 4.0 code is run only by
the suite and in throwaway project folders under the scratchpad, with the
current folder set there. This repository's own records stay in the 3.x
format until TCW-116. While `tcw/` is being changed in the worktree, the
item's own lifecycle moves are made by hand in Jira, as `CLAUDE.md` says.

## What this plan relies on

From **TCW-106** (built on `v4`):

- `tcw/project_files.py`: `SENTINEL`, `LOCAL_SENTINEL`, `KEY_PATTERN`
  (`:42`), `key_problems` (`:143`), `root_of`, `version_problem`,
  `without_version`.
- `tcw/config.py`: `_file_problems` (`:273-288`), the version and naming
  checks on one file, and `Origin.folder` (`:72-82`) giving the project root
  for the `project` and `local` layers.
- `tests/projectfiles.py`: `write_config`, `write_config_file`,
  `write_local_config`, which write the version line on every file.

From **TCW-107** (its plan, steps named):

- `SKIP_VARIABLE` moved to `tcw/project_files.py` with
  `personal_files_skipped()` (Step 1); `tcw/config.py` imports both.
- `personal_file(root, name)` in `tcw/store/project.py` (Step 6): the main
  checkout's personal file read from a linked worktree that has none, and
  `Origin.root` (Step 6), so a borrowed file's bindings and `TCW_CONFIG_DIR`
  are the worktree's. Spec AC 33 relies on both.
- One registry per command: `begin_command`, `end_command`,
  `forget_registries` (Step 5), so the fold of Step 7 reads the command's one
  registry and adds no walk of its own. Outside a command (a library caller,
  a test, and every request of `tcw serve`, whose `end_command()` runs once
  at start, `tcw/cli.py:545`), each `open` builds a new registry.
- What the registry raises. `current` and `require_valid` still raise
  `ValueError` (`tcw/store/project.py:241`, `:455`); `tcw/work/open.py:73-74`
  turns it into `BackendError`. `project_folder` raises `Unreachable`
  (exit 5), `UnknownProject` or `ProjectGraphError` (both `TcwError`, exit 1,
  in `tcw/errors.py`), Step 3.
- `_read_text`, the module-level function every registry read goes through,
  which tests replace to count reads (Step 3); AC 27's test counts with it.
- `TCW_PROJECT_<ID>` unchanged (spec Design 2.1 of TCW-107); the suite-wide
  `_no_project_overrides` fixture (`tests/conftest.py:126-145`).

From **TCW-110** (its plan, steps named):

- `sort_input(text, "work", KEY)` and its forms `a`-`d` (Step 1), and
  `resolve_work_input(text, backend, root)` in `tcw/work/open.py`, which
  `resolve_item` calls (Step 8). Step 6 of this plan reorders `resolve_item`
  around it.
- `open_project` locating any project with `project_folder` (Step 7), so
  `tcw work show <lib's item>` in AC 14 reaches `lib`.
- `_store_location_problems` in `load_config` (Step 12), which stays where it
  is: store locations are not inherited and not overridable (spec Design 5.1).

From **TCW-108** (its plan, steps named):

- `ParentLink(id, inherit)`, `LoadOrder(ids, missing, unreadable, warning)`,
  `AXES` and `passing(axis, project_id, links)` in `tcw/store/base.py`
  (Steps 1 and 2).
- `ProjectRegistry.load_order(project_id=None, *, root=None)`,
  `parents(project_id=None, *, root=None)` and `link_state(project_id)`
  (Step 7b), and `sources(axis, project_id=None)` with its two messages,
  `absent_note(project_id)` and `link_problem(project_id)` (Step 10).
  `sources` keeps that signature; only `load_order` and `parents` take
  `root=` (re-check R4).
- What fails while the order is computed: `load_order_of` raises
  `ValueError` past its depth limit rather than recursing without end
  (Step 2), and a loop found for a descendant's order or an outside
  project's raises `ProjectGraphError` (choice 5). In the `active` role a
  `parents:` problem is a graph problem and `link_state` stays `here`
  (TCW-108 Step 7b), so `load_order()` may answer an order holding the
  project alone without raising; choice 11 therefore reads the project's own
  `parents:` itself, with TCW-108's `parse_parents` (Step 1), and looks for a
  loop with its `find_loop` (Step 2).
- `InheritedUnavailable` (exit 7) carrying `project`, `axis` and `reason`
  (Step 3).
- `_read_config`'s roles (`active`, `ancestor`, `descendant`, `outside`) and
  `link_problem` for an ancestor whose `parents:` cannot be read (Step 7b).
- `_cmd_validate`'s one finding per missing or unreadable project from
  `availability()`, with row suffixes (Step 7d), and the `unavailable` list
  `validate()` takes (Step 11).
- `LOCAL_ONLY_KEYS = ("children",)` beside `PERSONAL_KEYS`, and `children`'s
  merge in `_merge` (Step 9).
- Its test tooling: the inventory method (Step 0: test IDs, and the count of
  `assert` statements and `pytest.raises` blocks per test function), the
  outcome record taken with `--junitxml` and `compare_outcomes.py <before>
  <after> <allowed.txt>` (Step 7f's last paragraph), both kept in the
  scratchpad. This plan reuses the script unchanged.
- Its tests of AC 18, 20, 26 and 31 in `tests/test_parent_links_cli.py`
  (Step 10), and of AC 19 with its "what lies above is unknown" sentences
  (Step 11), which this item must leave passing (spec Design 3.5). Those of
  AC 19, 20 and 31 gain the suffix of spec 3.6 and are amended at Step 7c if
  they compare the whole text. Also the two-repository fixture of AC 26,
  which AC 29 here repeats.

From **TCW-111**: `link_exists`, which Step 6 calls to answer a reference
into a Jira-mode project from its folders, and which TCW-111 changes to take
an id-path (TCW-111 spec, the `link_exists` paragraph of its Design; its
plan's change to `tcw/work/jira/backend.py:104-109`). Step 6 passes whatever
form TCW-111 leaves, as the existing callers in `tcw/refs.py` and
`reference_resolver` already do. TCW-111 also renames `item.yaml` to a state
file and changes `create`'s signature (its Steps 5 and 9); Step 0 re-reads
`tcw/work/fs_backend.py` and `tcw/work/jira/backend.py` for the two places
that read `work.tags` on every create and edit.

## Readings and choices where the spec leaves room

1. **"A value that cannot be used" (spec Design 3.4).** A withheld key is held
   in the parsed configuration as a `Withheld` object (`tcw/config.py`) that
   carries the error to raise. For `work.tags`, `WorkConfig.tags` holds it,
   and its `__iter__`, `__contains__`, `__len__` and `__bool__` raise that
   error, so every reader that uses the tags today (`set(config.tags)`,
   `t in config.tags`, `list(config.tags)`, `for t in ...`) raises without
   being rewritten, and passing the object along does not. For `work.jira`,
   `Config.jira` holds it, and `open_backend` calls `Config.require(key)`
   before building a `JiraBackend`, so it raises before any request. Neither
   is ever in `Config.problems`, which is what the check every command makes
   first reads (`tcw/cli.py:657-661`, spec 3.7).
2. **Where the fold gets its order.** A new concrete
   `ProjectRegistry.source_entries(axis, project_id=None, *, root=None) ->
   list[SourceEntry]` in `tcw/store/base.py` returns TCW-108's load order kept
   to the projects that pass `axis`, ending with the project, each entry
   `SourceEntry(id, project, state)` with `state` one of `here`, `missing`,
   `unreadable` and `project` the `Project` when here. It never raises for a
   gap. TCW-108's `sources` is rewritten to call it and raise for the first
   gap, so the two cannot disagree. The registry is opened by `load_config`
   only when the project's own shared file declares `parents:`, so a single
   project (UC-1) reads nothing new.
3. **A project read for itself** (spec Design 5.2) is `load_config(root,
   personal=False, registry=<the command's registry>)`, which now folds that
   project's own configuration sources and applies the variables naming each
   of them, with no personal file. The project's order comes from TCW-108's
   `load_order(id, root=root)` on that registry (TCW-108 plan, re-check R4).
   **The registry is required** when `personal=False` and the project's
   shared file declares `parents:`. Without it, `load_config` raises
   `TypeError` naming the missing argument. That is a mistake in the call,
   not a configuration problem, so it does not go into `Config.problems`. A
   fallback registry opened at `root` would treat that project as the active
   one. It would then read the project's personal `children` (TCW-108 Step 9)
   and could place an ancestor in another folder (spec 5.2). Every caller in
   `tcw/` passes the registry it already holds (Step 7a lists them). A
   library caller opens one at the active project's root and passes it.
4. **When a key is undecided.** A key `K` of Design 1.1 is undecided exactly
   when no layer after the last gap in the order declares `K`, or a key above
   it, with a value that replaces it whole (spec 3.1: the latest gap is the
   strictest of the "for some gap" cases). The gap a message names is the
   first gap after the last such declaration, or the first gap in the order
   when there is none.
5. **Opening a Jira-mode store requires `work.jira`, then `work.tags`.** Every
   command that opens a Jira-mode store reads tickets, and reading a ticket
   reads `work.tags` (`read_props`, `tcw/work/jira/backend.py:354`). Requiring
   both at the open, before the `JiraBackend` exists, is what makes "no
   network request is made before the command stops" (spec 3.3) hold.
6. **`work.jira: null` in a filesystem project.** By Design 2.5 the `null`
   removes the key, so it is absent when the parser runs, and today's "'jira'
   is only read with `backend: jira`" problem is not reported for it. A
   mapping value at `work.jira` without Jira mode still gets it (AC 9).
7. **An ancestor's unreadable shared file** (spec Design 1.6). Built in the
   `ancestor` and `outside` roles of TCW-108's `_read_config`, as the revised
   spec says. A descendant's unreadable file stays a graph problem, as the
   spec now states. A file that reads but has no valid `id` stays a graph
   problem in every role (`tcw/store/project.py:607-618`).
8. **Commands that need no inherited key and open the store today** (spec
   Design 3.4). The seven places in `tcw/work/cli.py`, and the two readers of
   a reference into a Jira-mode project. Those are `tcw/refs.py:139`, where a
   gap would give a false `error` finding, since `resolve_tcw_ref` catches
   every exception (`:123-124`). And `reference_resolver`
   (`tcw/work/open.py:210-241`), where an `InheritedUnavailable` would escape
   and stop `tcw validate` with exit 7. Both answer from the item folders,
   which need no Jira setting. Each place keeps the checks `open_backend`
   makes before it builds a backend (Step 6's `project_facts`).
9. **The environment is read once per command.** Every override is decoded
   and checked once while a command runs, kept beside `_EFFECTIVE`
   (`tcw/config.py:654`) and dropped by `end_command`; a library caller reads
   it afresh. So each problem of Design 4 is reported once.
10. **What an origin records.** `Origin` gains `project` (the declaring
    project's ID, None for `built-in`), `variable` (the name, for the new
    `environment` layer) and `position` (the source's index in the fold), and
    keeps TCW-107's `root`. `rank`, used by `_origin_for`
    (`tcw/config.py:559-571`) to blame a mapping's problem on its highest
    layer, becomes `(position, layer)`, so a later project outranks an earlier
    one.
11. **A registry that cannot answer** (spec Design 1.3, Decisions 25 and
    30). The order cannot be had in any of three cases, checked in this
    order once `P`'s shared file declares `parents:`:
    - **`P`'s own `parents:` is refused**: TCW-108's `parse_parents(<P's
      value>, <P's file>)` returns no links. The loader reads the value from
      the shared file it has already read. This is needed because in the
      `active` role TCW-108 makes the problem a graph problem and leaves
      `link_state` at `here`, so the registry may answer `[P]` without
      raising (the re-check's B1).
    - **A loop through `P`'s ancestors**: TCW-108's `find_loop` over
      `registry.parents(q)` for `P` and each project reached from it through
      parent links (each visited once), found before `source_entries` is
      asked, so the outcome does not depend on whether TCW-108's order
      computation raises for a loop.
    - **A raise**: opening the registry, `current` or `source_entries` raises
      `ValueError` or a `TcwError`. That covers `current`'s `ValueError`,
      `load_order_of`'s depth guard, `ProjectGraphError` (TCW-108 choice 5),
      and TCW-107's `Unreachable` and `UnknownProject`. `InheritedUnavailable`
      is a `TcwError` too (TCW-108 Step 3); the `try` re-raises it before its
      `TcwError` clause, so it is never swallowed, though `source_entries`
      is not expected to raise it. Catching `Unreachable` turns its exit 5
      into exit 1; no path reaches that today, since the walk records a
      missing project rather than raising and a project read for itself is
      asked for with `root=`, so it costs nothing now.
    It is not had when `P` is in the order's `unreadable` either (a
    backstop: TCW-108's active role does not put it there).
    Then `load_config` folds the project alone and keeps the **withheld
    error**: the text `registry.require_valid()` raises (the registry's
    graph problems joined with `; `, `tcw/store/project.py:455`), which is
    exactly what `tcw work list` prints for the same project through
    `open_backend`; only when it raises nothing, or no registry could be
    opened, the caught error's text, or for a loop the registry did not
    record, `loop_message(<the loop>)`. So a loop is named by TCW-108's
    `loop in parents: …`, never by the depth guard's words. A narrower
    trigger than "any graph problem" is kept on purpose: a descendant that
    does not name `P` back is a graph problem too, and withholding on it
    would newly stop `tcw work tags list`, which reads no graph today.
    At Step 7a nothing is withheld (the interim rule). From Step 7c, each
    key of Design 1.1 that the project does not decide itself is withheld
    with `BackendError(<the withheld error>)`, exit 1. That is the
    conversion `open_backend` already makes (`tcw/work/open.py:73-74`), so
    `tcw validate`'s `_work_findings` reports it through its existing
    `BackendError` branch (`tcw/validate.py:571-575`). The error is never
    put in `Config.problems`. So `tcw validate`, which loads the
    configuration before its own checks (`own_config`, `tcw/cli.py:592`;
    `config_findings`, `tcw/validate.py:366`), still runs every check and
    lists the graph problem as a finding. Every other command that reads no
    inherited key reaches `open_backend`'s `require_valid`, and fails there
    as it does today.
12. **The user-wide file is checked once** (spec 1.6, 2.1; Decision 26). It
    is read and checked at `P`'s position, against the whole allowed list,
    and its problems, `refused` and `skipped` records are `P`'s. What passed
    is kept. At each other source it is applied cut to Design 1.1, with no
    check, no problem and no `Setting` record.
13. **Variable problems go into the active project's configuration only**
    (spec 4.4; Decision 27): `load_config(personal=True)`. A reading with
    `personal=False` applies only the variables that passed every check, and
    reports none. What this protects is the `tcw://` link check, which
    `validate()` runs whatever the configuration holds
    (`tcw/validate.py:327-348`), and the web app's reads of another project:
    a `ConfigError` from opening another project would be a false `error`
    finding for every link into it (`tcw/refs.py:158`). An item's reference
    into another project is not reached in that case, because
    `_work_findings` returns at the active project's `ConfigError`
    (`:571-573`).
14. **Guards on `Withheld`** (the review's answer 6). It stores a function
    that builds its error, and raises a new error at each use, so one
    exception object never collects traceback frames from many places. It
    subclasses neither `tuple` nor `list`, so `asdict` and `deepcopy` never
    iterate it. `isinstance(x, Withheld)` is used only in
    `work_store_problems` (7b), `tcw/serve/work.py`'s summary (Step 11),
    `config_cli._show` (Step 9) and `Config.require`. Each of those carries
    a comment saying that `config.tags or ()` is not a safe test.
15. **One registry, passed along, for the fold only.** `project_facts`
    takes `registry=None`. For the active project (`personal=True`) it
    opens one at `root` when none is passed, and that registry answers
    `require_valid()`, `current.id` and the fold, so a call outside a
    command builds one registry, not two (the review's answer 7c). It is
    passed to `_layered`, and through a new `registry=None` keyword on
    `effective(root, registry=None)` (`tcw/config.py:667-675`) to
    `load_config`; `effective` uses it on the call that fills its cache.
    For a project read for itself (`personal=False`) the passed registry,
    the command's, is used for the fold alone. Its `current` is the
    **active** project, so the read project's ID never comes from it
    (spec Decision 31): it comes from `FsProjectRegistry.open(root).current.id`,
    as `open_backend` reads it today (`tcw/work/open.py:65-71`), which
    TCW-107 Step 5 keeps to one registry per root per command. That
    per-root registry is never passed to `load_config`. With
    `personal=False` and no registry passed, `project_facts` opens none for
    the fold; `load_config`'s `TypeError` (choice 3) is the one check, so no
    fallback slips past it. A `tcw serve` request runs outside a command,
    so `context` still builds two: one in `read_work_config` and one in
    `open_backend` (`tcw/serve/work.py:68-69`). That is 3.x's cost plus
    nothing for a project with no `parents:`, and it is left as it is.

## Step 0 — start from what the earlier items left

Checks, before any change:

- TCW-106, TCW-107, TCW-110, TCW-108 and TCW-111 are completed and on `v4`;
  none of this item's code is (`grep -n "INHERITED_KEYS\|Withheld"
  tcw/config.py` finds nothing).
- Every name and line this plan cites is re-read on the merged tree and
  corrected here: in particular `sources`, `load_order`, `link_state`,
  `absent_note`, `link_problem`, `availability()`, the role argument of
  `_read_config`, `LOCAL_ONLY_KEYS`, `personal_file`, `Origin.root`,
  `personal_files_skipped`, `resolve_work_input`, `_store_location_problems`,
  and the seven lines of spec Design 3.4 (`tcw/work/cli.py:56`, `:71`, `:318`,
  `:441`, `:455`, `:567`, `:596`).
- **What the registry raises, as landed** (choice 11): `grep -n "raise "
  tcw/store/project.py tcw/store/base.py`, each raise on the path from
  `FsProjectRegistry.open`, `current`, `load_order` and `parents` recorded with
  its exception class. Also, by a throwaway script in the scratchpad, what
  `load_order()` answers for an active project whose own file holds
  `parents: notalist`, and for `app: [lib]`, `lib: [top]`, `top: [lib]`: an
  order, or which exception; and what `require_valid()` raises in each, which
  is the withheld error's text. Choice 11 does not depend on the first answer
  (it reads `P`'s own `parents:` and looks for the loop itself); its list of
  caught errors is corrected here if anything else can be raised, and
  `parse_parents`, `find_loop` and `loop_message` are confirmed by name.
- **Every reader of an inherited key**, by `grep -rn "\.tags\b"` and
  `grep -rn "\.jira\b\|layered\.jira\|config\.jira"` over `tcw/`, compared
  with this list at `d2d02829`: `tcw/work/fs_backend.py:286`, `:536`;
  `tcw/work/cli.py:245`, `:621`, `:632`; `tcw/work/jira/backend.py:354`,
  `:437`, `:628`; `tcw/serve/work.py:173`; `tcw/work/open.py:75-77`;
  `tcw/validate.py:505`, `:580`. A new one found is added to Step 6 or 9.
- **Every opener of a work store**, by `grep -rn "open_backend(\|read_work_config("
  tcw`, each recorded as reading an inherited key (spec 3.4 rows a-c) or not.
  At `d2d02829`: `tcw/capabilities/cli.py:201` (`tcw capabilities drift`,
  which lists completed items, row a of spec 3.4), `tcw/validate.py:496`,
  `:570`, `tcw/refs.py:139`, `tcw/cli.py:518` (`--remote`, row a),
  `tcw/work/jira/tickets.py:339`, `tcw/serve/services.py:26`,
  `tcw/serve/work.py:68-69`, `:559`, `tcw/work/open.py:99`, `:177`, `:183`,
  `:198`. (`--remote` catches every `TcwError` from `open_backend`,
  `tcw/cli.py:518-519`, so `tcw validate --remote` still never stops on a
  gap, as spec 3.6 asks.)
- **Every reading of a project for itself**, by `grep -rn "personal=False"
  tcw tests` (the tests too: a test that calls `load_config(...,
  personal=False)` or `read_work_config(..., personal=False)` directly on a
  project with `parents:` meets the new `TypeError` at Step 7a, and is listed
  there and given a registry). At `d2d02829`, in `tcw`: `tcw/work/open.py:42` (`_layered`), `:99`
  (`open_project`), `:178` and `:184` (`delegate`), `:199`
  (`open_for_update`), `tcw/work/jira/tickets.py:339` (`delegate_to_jira`
  with `root=`, reached from `delegate`, which holds a registry), and
  `tcw/serve/work.py:559` (`_other_items`, which holds `registry`). Each is
  recorded with the registry it will pass at Step 7a (choice 3). One that
  holds none is given one, never left to fail.
- **The tests this item changes.** Searched on the merged tree, each file
  read and the list written into the implement round:
  1. Tests that run a tag command (`grep -rlnE "\"tags\", \"(add|rm|list)\"|tags (add|rm|list)|--tag|--untag" tests`),
     a Jira-mode work command (`grep -rlnE "backend: jira|\"backend\": \"jira\"" tests`)
     or `tcw config show` (`grep -rln "config\", \"show\"\|config show" tests`),
     intersected with the files whose fixtures write a parent link
     (`grep -rlnE "parents:|\"parents\"|connect_projects\(|connect\(" tests`).
     Each test in the intersection is read for a parent that passes `config`
     (any link but `inherit: none` or one leaving `config` out) and that is
     missing, unreadable, or sets `work.tags` or `work.jira`. Such a test sees
     inheritance or a withheld key for the first time and is expected to fail
     at Step 7a or 7c; it is listed there.
  2. **TCW-108's tests of AC 18, 19, 20, 26 and 31** in
     `tests/test_parent_links_cli.py` (its Steps 10 and 11). The `tcw work
     list` sentences run in filesystem projects with no tag option and must
     pass unchanged (spec 3.5). Some `tcw validate` sentences have a parent
     that passes `config` missing or unreadable and a child that sets no
     `work.tags`. Their `unresolved` finding gains `; could not check the
     configuration inherited from it` at Step 7c (spec 3.6). Those are:
     - AC 19's, `app: [core]`, `core` missing, with `taxonomy.extends`; its
       finding already holds row (a)'s and row (c)'s text;
     - Step 11's "when what lies above is unknown" tests, `lib` missing, and
       again unreadable;
     - AC 20's;
     - AC 31's, and its `projects:` variant.
     Each one that compares the finding's whole text, or the whole list of
     findings, rather than testing for words in it, is amended at Step 7c to
     the new text and listed with Design 3.6 (spec Decision 24). AC 18 (`ws`
     behind `inherit: none`) and AC 26 (`inherit: none`) have no
     configuration gap and are unaffected.
  3. Tests that pin a behaviour Design 2.4 or 2.5 changes:
     `grep -rn "allowed only in a stage\|is allowed only" tests` (at
     `d2d02829`, `tests/config/test_personal_merge.py:102-108`, which uses
     `work.tags` as the list that refuses `inherit`), and
     `grep -rnE "(tags|jira)\"?: *(None|null)" tests`.
  4. Tests that construct `Origin` or read `LAYERS`, `PERSONAL_LAYERS` or
     `rank` (`grep -rn "Origin(\|LAYERS\|\.rank\b" tests`; at `d2d02829`
     none outside `tests/config/test_personal_merge.py:180`'s
     `personal_files`, which keeps its signature).
  5. **Every `tcw validate` test that a parent link can reach.** Tests that
     run `tcw validate`, call `_cmd_validate` or call `validate(`
     (`grep -rlnE "\"validate\"|_cmd_validate|validate\(" tests`), and the
     tests of the unregistered-tag warnings: `work_store_problems`'s, and the
     `--tag` warning `is not in this project's registry`
     (`tcw/work/cli.py:244-246`; `grep -rlnE "not in this project's
     registry|is not registered|unregistered" tests`). Each set is intersected
     with the parent-link grep of list 1 (the grep itself, not list 1's
     result, so that TCW-108's validate tests in files that run no tag
     command are included). That includes every
     3.x-era fixture TCW-108 Step 8a rewrote from `projects.parent` to
     `parents:`, which passes `config` by default. Each test in the
     intersection is read and sorted:
     - **7a**: a parent passes `config` and is here, and its tags now reach
       the child. The unregistered-tag warnings or `--tag`'s warning change.
     - **7c**: a parent passes `config` and is missing or unreadable, the
       child sets no `work.tags`, and the test asserts an `unresolved`
       finding's text or the whole list of findings.
     Each is named in that step's list of expected failures in the implement
     round, before the step's change is made.
  6. **Tests whose active project's own `parents:` is wrong, or whose
     ancestors loop**, and that run a tag command, `tcw config show`, or a
     Jira-mode work command (list 1's command greps, intersected with
     `grep -rlnE "parents: *[^\[{ ]|loop in parents|find_loop" tests`, and
     TCW-108's tests of its AC 2 and AC 15 read by hand). From Step 7c such a
     command newly exits 1 (choice 11). Each is named in Step 7c's list of
     expected failures.
- **Inventories**, taken now and kept in the scratchpad (not the
  repository), by TCW-108 Step 0's method: `pytest --collect-only -q`, and the
  per-function counts of `assert` statements and `pytest.raises` blocks.
- **Outcome record**: `.venv/bin/pytest -q --junitxml=<scratchpad>/outcomes-step0.xml`
  from the worktree's root, and TCW-108's `compare_outcomes.py` copied into
  the scratchpad if it is not there.

**Proves it:** bare `.venv/bin/pytest` passes on the merged `v4`; its count
is recorded in the implement round as the baseline.

## Step 1 — the key table and the variable names, not yet used

Spec Design 1.1, 4.1, 4.3, AC 26.

**Tests first.** New `tests/test_config_keys.py`, on the functions alone:

- `INHERITED_KEYS == ("work.tags", "work.jira")`, in that order.
- AC 26: every entry of `known_keys()`, with every stage of `STAGES`, every
  procedure of `PROCEDURE_IDS` and every priority of `PRIORITIES` filled in,
  encodes to a distinct name for a project `p`, and `decode_key(<its key
  part>)` gives back that entry; the side stage has only `enabled` and
  `prompt` (`SIDE_STAGE_KEYS`, `tcw/work/config.py:44`).
- `override_name(("work", "jira", "credentials", "email-env"), "my-proj") ==
  "TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__MY_PROJ"` and
  `override_name(("user", "name"), "tcw") == "TCW_USER_NAME__TCW"` (4.1).
- `decode_key` gives None for `WORK_STAGES_SPEC_PROMPTS`, `TCW_VERSION` and
  `WORK_STAGES_DESIGN_PROMPT` (AC 20's three), and for any key of a list
  entry (`WORK_STAGES_SPEC_PROMPT_BLOB`, 4.3's last paragraph).
- Each entry's kind: `mapping` for a key with keys under it, `text` for
  `user.name` and the two credential names, `list` for a stage's `prompt`,
  `pre`, `post` and a procedure, and the rest by what the parser reads
  (`work.hooks.timeout` a number, a stage's `enabled` a boolean, …).

**Creates** `tcw/config_keys.py`, pure functions with lazy imports of the
constants (as `built_in_values` does, `tcw/config.py:208-221`, since
`tcw/work/config.py` imports `tcw.config`):

- `known_keys() -> dict[KeyPath, str]`: every key reachable through mappings
  in `.tcw/tcw-config.yaml` and its kind: `id`, `parents`, `children`,
  `user.name`, `taxonomy` and `capabilities` with `path`, `repository` and
  `extends` (and the keys of a `repository` mapping, as the merged tree's
  `parse_repository_declaration` accepts them; Step 0 reads it), and under
  `work` the keys of `WORK_KEYS`, `STAGE_KEYS` or `SIDE_STAGE_KEYS` for each
  stage of `STAGES`, `HOOK_KEYS`, each procedure of `PROCEDURE_IDS`, and the
  Jira keys (`KEYS`, `CREDENTIAL_KEYS`, `FIELD_KEYS`,
  `tcw/work/jira/config.py:31-36`; `PRIORITIES`, `tcw/work/model.py:98`).
  No `tcw-version` (TCW-106 Design 3.3) and no key inside a list entry.
  The table has two uses only: decoding a variable's key part (Step 2), and,
  restricted to `work.tags` and `work.jira`'s keys, deciding which keys are
  undecided (Step 7c). Nothing reports a key of a file because the table
  lacks it, so TCW-112 Step 5c can take the `extends` entries out without
  any file becoming a problem here (TCW-112's handoff, point 3).
- `override_name(key_path, project_id) -> str` (4.1) and
  `decode_key(key_part) -> KeyPath | None`: the one entry whose encoding is
  the key part (4.3), found by encoding every entry once (a dictionary built
  on first use).

**Changes** `tcw/config.py`: `INHERITED_KEYS = ("work.tags", "work.jira")`
beside `PERSONAL_KEYS` (`:46-53`), with a comment saying the list grows only
in a release and is the order `tcw config show` names an undecided key in
(spec 1.1, 7.1).

**Proves it:** the new test file; the full suite (nothing calls the new code).

## Step 2 — reading the override variables, not yet applied

Spec Design 4.2, 4.3, 4.5, 4.6, 4.7. Pure: given a mapping of variables, it
returns what the variables set and the problems, so every rule is tested
without a project.

**Tests first.** New `tests/test_config_overrides.py`, calling
`read_overrides(environ)` on literal mappings:

- 4.2: `TCW_PROCEDURE_X`, `TCW_PROJECT_CORE`, `TCW_JIRA_EMAIL`,
  `TCW_STDIN_TIMEOUT`, `TCW_CONFIG_DIR` and `TCW_NO_PERSONAL_CONFIG` are not
  overrides (AC 19's last sentence); `TCW__ALL__WORK_TAGS`, `TCW_WORK__`,
  `TCW_WORK___APP` and `TCW_user_NAME__APP` are each one problem starting with
  the name and containing `TCW_<KEY>__<PROJECT>` (AC 20).
- 4.3: AC 20's three unknown keys, each `no configuration key is written`.
- 4.4: the project part `MY_PROJ` read as `my-proj`.
- 4.5: each of AC 21's names is `<NAME>: <dotted key> is a shared key; an
  environment variable cannot set it`, `TCW_CHILDREN__APP` included (5.1: no
  variable sets `children`); `TCW_WORK_STAGES_SPEC__APP='{prompt: [{blob: p}],
  status: x}'` gives one problem, for `work.stages.spec.status`, and keeps the
  `prompt`.
- 4.6: `TCW_USER_NAME__APP=no` and `=null` give the text; AC 22's five
  refusals with their words (`must be a list`, `is not valid YAML`, `null has
  no meaning in an environment variable`, `must be a mapping`, a repeated
  key); `TCW_USER_NAME__APP=' x'` is refused by the `user.name` rule
  (`tcw/config.py:385-389`); a credential name `lower` by `VARIABLE`'s rule;
  and for every refusal of the file, no message contains the value
  (`s3cr3t-token`).
- 4.7: the overrides of one project come back fewest parts first,
  `TCW_WORK_STAGES_SPEC__APP` before `TCW_WORK_STAGES_SPEC_PROMPT__APP`
  whatever order the mapping holds them in.

**Creates** in `tcw/config_keys.py`:

- `Override(name, project, key_path, value)`, frozen.
- `read_overrides(environ) -> tuple[dict[str, list[Override]],
  list[Problem]]`: every name starting `TCW_` and holding `__` is matched
  against 4.2's pattern, its key decoded (4.3), checked against the allowed
  list (4.5, by Step 2's change to `_allowed` below), its value read by the
  key's kind (4.6: text as written; a list or mapping by
  `yaml.load(value, UniqueKeyLoader)`, refusing `null` and the wrong kind),
  and the overrides grouped by project ID, each group sorted by the number of
  parts in its key, stably (4.7). Every problem is a `tcw.config.Problem`
  with no file and no key path, its message starting with the name (so
  `tcw validate` shows it at `environment`, `tcw/validate.py:375`).

**Changes** `tcw/config.py`, `_allowed` (`:371-407`): its three messages and
the way a problem is built come from a small `voice` argument, so the one
allowlist walk serves a file (today's words, the default) and a variable
(`<NAME>: <dotted key> is a shared key; an environment variable cannot set
it`, and the `null` message of 4.6). `LOCAL_ONLY_KEYS` (TCW-108 Step 9) is
allowed only for the file voice of the `local` layer, as now.

**Proves it:** the new test file; `tests/config/test_personal_allowlist.py`
unchanged; the full suite.

## Step 3 — the configuration editor writes an `inherit` entry

Spec Design 6.2 needs `work.tags` written as `[inherit: true, …]`, which the
editor cannot write today: `SetList` holds plain values only
(`tcw/store/config_edit.py:54-57`) and `plan_list` refuses a list holding
anything else (`:458-460`).

**Tests first**, in `tests/test_config_edit.py` and
`tests/test_config_edit_writers.py`: `SetList("work", "tags", ("z",),
inherit=True)` writes `- inherit: true` first in a block list and
`{inherit: true}` first in a flow list; on a file whose list already starts
with `- inherit: true`, adding `y` changes only the new line; a list whose
non-scalar entry is anything but one leading `{inherit: true}` is still
refused with today's message; `intended` puts `{"inherit": True}` first.

**Changes** `tcw/store/config_edit.py`: `SetList` gains `inherit: bool =
False`; `block_value` (`:313-321`), `flow_list` (`:309-311`), `plan_list`
(`:456-470`) and `intended` (`:104-122`) write and accept that one leading
entry. Nothing else in the editor changes.

**Proves it:** the two test files; the full suite.

## Step 4 — the configuration sources, without raising

Spec Design 1.3, and 1.6's last paragraph (an ancestor whose shared file
cannot be read at all).

**Tests first**, in `tests/test_parent_links.py` (TCW-108's file), calling
`FsProjectRegistry.open(<root>)`:

- `source_entries("config")` for AC 1's layout is `[core, app]`, each
  `here`; for AC 16's (`app: [{id: ws, inherit: none}, core]`, `ws` absent)
  `[core, app]`; for AC 13's (`core` absent) `[core (missing), app]`; for AC
  15's (`core` with `parents: notalist`) `[core (unreadable), app]`. It raises
  in none of them.
- `sources("config")` raises for the first gap exactly as before, with the
  same messages, so TCW-108's AC 17-20, 26 and 31 tests stand unchanged.
- **The unreadable file** (spec 1.6): `core`'s shared file not valid YAML, and
  again with `tcw-version: 99.0.0`: from `app: [core]`, `require_valid()`
  passes, `core` is in `load_order().unreadable`, `link_problem("core")`
  names `core`'s file and holds the read problem's text, and nothing above
  `core` is looked up (counted with `_read_text`); `tcw validate` in `app`
  exits 0 with one `unresolved` finding naming `core`, with row (d)'s text
  (TCW-108 Design 6.5) being the read problem. `sources("taxonomy")` from
  `app` raises with the second message of TCW-108 Design 6.2.
- **A descendant's unreadable file** (spec 1.6, AC 15): `app` lists `core`,
  `core: [app]`, `core`'s file not valid YAML. From `app`, `require_valid()`
  raises naming `core`'s file, as before this item.
- **`unavailable`**: `unavailable("app", "core", "config", subject="configuration
  (work.tags)")` has `axis == "config"`, `reason == "missing"` and the
  message of spec 3.3's first line.

**Changes**

- `tcw/store/base.py`: `SourceEntry(id, project, state)`, frozen;
  `ProjectRegistry.source_entries(axis, project_id=None, *, root=None)`
  (choice 2), built from `load_order`, `passing` and `link_state`; `sources`
  rewritten over it. The building of the `InheritedUnavailable` that
  `sources` raises moves into `ProjectRegistry.unavailable(project_id,
  gap_id, axis, *, subject=None) -> InheritedUnavailable`. `axis` is the
  error's `axis` attribute (TCW-108 Step 3): `taxonomy`, `capabilities`, or,
  from this item, `config`. `subject` is the words that stand for the axis in
  the message. It defaults to the axis name, and this item passes
  `configuration (work.tags)` or `configuration (work.jira)`. The `reason`
  (`missing` or `unreadable`) comes from `link_state(gap_id)`, and the text
  after the colon from `absent_note` or `link_problem`, as in `sources`.
  `sources` calls it with the axis alone, so its messages do not change. A
  test asserts that the configuration error's `axis` is `config`, so no
  code that checks the axis meets an unknown value. TCW-112 Step 2 adds its
  third reason here as one more keyword-only argument, `store_message: str |
  None = None` (reason `store`, its `detail` the store's message), so
  `unavailable` stays the one place an `InheritedUnavailable` message is
  built; nothing in this item builds one anywhere else (TCW-112's handoff,
  point 1).
- `tcw/store/project.py`, `_read_config` (as TCW-108 Step 7b leaves it): in
  the `ancestor` and `outside` roles, a file whose read gives a problem (the
  problem `read_project_file` returns, `tcw/config.py:257-270`: not UTF-8,
  not YAML, not a mapping, or a version this TCW cannot read) is recorded as
  `link_problem` with that problem's text and its links as unknown, instead
  of a graph problem. The `active` and `descendant` roles keep TCW-108's
  handling (choice 7). A file that is not there is a missing project, as
  today (`_unreachable_edge`, `tcw/store/project.py:567-587`). A file that
  reads but has no valid `id` stays a graph problem in every role
  (`:607-618`). If TCW-108 as landed already does this, Step 0 records it
  and only the tests are added.

Tests that relied on an ancestor's unreadable file being a graph problem
(found at Step 0 with `grep -rln "not valid YAML\|tcw-version: 99" tests`,
read for an ancestor's file) are amended to the 6.6 outcome and listed with
spec 1.6.

**Proves it:** the tests above; TCW-108's test files unchanged; the full
suite.

## Step 5 — `inherit: true` in `work.tags`, and `null` at an inherited key, within one project

Spec Design 2.4 and 2.5, as far as one project shows them. Done before the
fold so that the rule and its refusals are tested where nothing is
inherited yet.

**Tests first**, in `tests/config/test_personal_merge.py` and a new
`tests/test_inherited_config.py` (this item's CLI and loader tests; the
layouts of the spec's criteria are built there by one helper, `family(tmp_path,
**projects)`, writing each project with `write_config` and placing the others
with TCW-107's `write_manifest`):

- AC 7's single-project sentences: a project with no parents setting
  `work.tags: [{inherit: true}, c]` has tags `c` and `tcw validate` reports no
  problem; `work.documentation: [{inherit: true}]` is refused with a message
  naming `work.tags`; two `inherit: true` entries in `work.tags` are refused
  with `a list may hold one 'inherit' entry`.
- AC 8's single-project sentences: `work.tags: null` in the personal file is
  refused with `null has no meaning in a personal file`; `work.backend: null`
  in the shared file is refused with `must be one of`; `work.tags: null` and
  `work.jira: null` (choice 6) in a filesystem project's shared file give no
  problem and no tags.
- `tests/config/test_personal_merge.py:102-108`
  (`test_inherit_outside_a_chain_list_is_one_problem`) used `work.tags` as the
  list that refuses `inherit`; it is rewritten on `work.documentation`,
  keeping its one-problem assertion, and asserts that the message names
  `work.tags` (AC 7). Listed with Design 2.4.

**Changes** `tcw/config.py`:

- `_takes_inherit(key_path)`: `_is_chain` (`:295-300`) or `("work", "tags")`.
  `_list_problems` (`:313-354`) accepts the entry where `_takes_inherit`
  holds, with every rule it has today; its refusal reads `'inherit' is
  allowed only in work.tags, a stage's prompt, pre or post list, or a
  procedure's list`; the repeated-entry check stays for chain lists only.
- `_merge` (`:487-528`): its first branch resolves the entry where
  `_takes_inherit` holds (`_chain`, `:466-484`); `written` is still recorded
  for chain lists only (it feeds the personal note).
- `_merge`: `null` in the `project` layer at a key of Design 1.1 or below one
  (`_inherited_key(here)`: `here[:2] == ("work", "tags")` or `here[:2] ==
  ("work", "jira")`) removes the key and its origins (`_clear`, `:445-447`)
  instead of storing `None`; at any other key, today's two branches
  (`:510-513`, `:523-526`) are unchanged. The removal is recorded as a
  declaration that replaces the key whole, for Step 7c.

**Proves it:** the tests above; `tests/config/`; `tests/work/test_config.py`;
the full suite.

## Step 6 — what reads an inherited key reads it only when it uses it

Spec Design 3.4, before anything is withheld, so each change is proved by
behaviour that does not change and by a test that would see the store
opened.

**Tests first**, in `tests/test_inherited_config.py`:

- `Withheld`: iterating it, `in`, `len` and `bool` each raise the error it
  carries; passing it as an argument and `repr` do not.
- **The store is not opened**: with `tcw.work.open.open_backend` replaced (in
  the command's process, `monkeypatch` on `tcw.work.cli` and
  `tcw.work.open`) by a function that raises, `tcw work lifecycle`,
  `tcw work docs`, `tcw work stage prompt spec` and `tcw work procedure
  search` with no item, `tcw work path` with no item, and `tcw work show
  <lib's item by full identifier>` from `app` exit 0 with the output they give
  today; the write refusal of `_own` and the note of `_personal_note` still
  appear where they appear today (`tests/config/test_personal_origins.py`'s
  note tests unchanged). Run through `tcw.cli.main` in-process, as
  `tests/test_project_files_cli.py:42-49` does.
- **A tag is read only when one is applied**: with `registered_tags` a
  `Withheld`, `validate_changes` with no `add_tags` returns, and with one
  raises the carried error.
- **The checks the store's opening made are kept** (the review's S3). In a
  project whose work directory cannot be found, `tcw work path` with no item
  exits 1 with today's message. In a project whose graph is invalid (a
  descendant that does not name it back), `tcw work lifecycle`, `tcw work
  docs` and `tcw work stage prompt spec` with no item each exit 1 with the
  message they give today. Each is compared with the output recorded at
  Step 0 for the same fixture.
- **References into a Jira-mode project** (spec 3.4): `reference_resolver`
  and `resolve_tcw_ref` answer a reference to an existing folder `found` and
  to an absent one `missing`, with `open_backend` replaced by a function
  that raises. `reference_resolver` answers `unresolved` for a project
  whose opening raises `InheritedUnavailable`.

**Changes**

- `tcw/config.py`: `Withheld(error)` (choice 1).
- `tcw/work/model.py:188-214` (`validate_changes`): the registered set is
  built only when `changes.add_tags` is not empty. The two callers
  (`tcw/work/fs_backend.py:286`, `tcw/work/jira/backend.py:628`) still pass
  `config.tags`, which is no longer read on a create or edit without a tag.
- `tcw/work/open.py`: `open_backend` (`:54-78`) is split in two.
  `project_facts(root, *, personal=True, registry=None) -> ProjectFacts`
  does everything `open_backend` does today before it builds a backend:
  - the layered configuration, raising `ConfigError` on its problems;
  - with `personal`, the active project's registry (the one passed, which
    must be the one at `root`, or one opened at `root`), with
    `require_valid()`;
  - the ID of the project at `root`: with `personal`, that registry's
    `current.id`; without, `FsProjectRegistry.open(root).current.id`, as
    `open_backend` reads it today (`:65-71`). Never the passed registry's
    `current` when `personal` is false: that is the active project
    (choice 15, spec Decision 31);
  - `work_path(root)`.
  Each `ValueError` is turned into `BackendError`, as now (`:73-74`). It
  returns `ProjectFacts(layered, project, path, registry)`, frozen, where
  `registry` is the one passed, or the one opened for the active project.
  Until Step 7a no caller passes a registry, so the ID is read exactly as
  today.
  `open_backend` calls it and then builds the backend, so its own behaviour
  does not change. `external_stages_of(config)`, also new, answers
  `JiraBackend.external_stages` or `FsWorkBackend.external_stages` by
  `config.backend` (`tcw/work/jira/backend.py:216`, `tcw/work/fs_backend.py:235`).
  Each of the places below calls `project_facts`, so it fails exactly as it
  does today when the graph is invalid or the work path cannot be found (the
  review's S3). It builds no `JiraBackend`, so it never reads `work.jira`.
- `tcw/work/cli.py`:
  - `_own` (`:69-74`): compares with `project_facts(root).project`.
  - `_personal_note(project, root, key_path)` (`:449-460`) takes the ID of
    the project whose list was composed, in place of a backend, and
    compares it with `project_facts(root).project`. Its two callers pass
    `backend.project` with an item, and the facts' `project` without one:
    `_stage_prompt`, `:507`, and `_procedure`, `:539`.
  - `_lifecycle` (`:567`) and `_docs` (`:596`): `project_facts(root).layered.work`.
  - `_path` with no item (`:318`): prints `project_facts(root).path`.
  - `_prompt_target` with no item (`:440-441`) returns the facts' work
    configuration and `external_stages_of(config)` in place of a backend.
    `_stage_prompt` (`:490-519`) and `_procedure` (`:521-546`) read those two
    instead of `backend.config` and `backend.external_stages`.
  - `resolve_item` (`:50-66`, as TCW-110 Step 8 leaves it) passes
    `resolve_work_input` the active backend as a function,
    `lambda: open_backend(root)`, in place of the backend itself.
- `tcw/work/open.py`, `resolve_work_input(text, active, root)` (TCW-110
  Step 8): `active` is a function returning the active project's backend. It
  is called only for form `b` (a Jira key), form `d`, and a form `a` naming
  the active project, whose ID comes from `project_facts(root).project`.
  Forms `a` and `c` naming another project go to `open_project` without
  calling it. So the input is sorted in one place (the review's S4), and the
  web's `parse_changes` (`tcw/serve/work.py:332-362`) and the other callers
  TCW-110 Step 8 lists get the same fix. Callers that already hold a backend
  pass `lambda: backend`. If TCW-110 as landed already takes a function, as
  this item's handoff asks, Step 0 records it and only the tests are added.
- `tcw/refs.py:139` and `reference_resolver` (`tcw/work/open.py:210-241`), for
  a Jira-mode project: answered from the item folders (`link_exists(<the
  facts' path>, folder)`) without building a `JiraBackend`, as they already
  answer it once built (choice 8). `reference_resolver` also turns an
  `InheritedUnavailable` from opening the referenced project into
  `UNRESOLVED`, so a reference into a filesystem project read for itself can
  never stop `tcw validate` (spec 3.6).

**Proves it:** the tests above; `tests/work/` and `tests/config/`
unchanged; the full suite.

## Step 7a — the fold: a project takes the inherited keys from its sources

Spec Design 1.1-1.5, 2.1-2.3, 2.6, 5.2. The riskiest change of the item, put
here so that the order (Step 4), the `inherit` and `null` rules (Step 5) and
the narrow readers (Step 6) exist and are tested before it. The switch is
split three ways, each with one possible cause of failure: 7a folds the
sources that are here, 7b handles a problem in an inherited value, 7c
handles a gap. **Until 7c, a gap contributes nothing and withholds nothing**
(the 3.x behaviour, since nothing was inherited), and **until 7b, a problem
in an inherited value is a problem of the active project** (exit 1 on every
command); both interim rules are stated in the code's comments and replaced
in the next two steps, before the item completes.

**Tests first**, in `tests/test_inherited_config.py`, through
`load_config(<root>)` and the CLI:

- AC 1, AC 2, AC 3 (all three sentences), AC 4, AC 5 (all four orders, and
  the tags of `dd`), AC 6, AC 7's inherited sentences, AC 8's inherited
  sentences, AC 9, AC 11's file sentences (`MINE`, `APPS`, `CORE_EMAIL` with
  `TCW_NO_PERSONAL_CONFIG=1`, and reading `core` for itself with only its
  personal file set), AC 12, AC 16 (with `ws` behind `inherit: none` absent,
  which 7a's interim rule and 7c's final one answer the same).
- AC 33, in a real git repository with a linked worktree (`git worktree
  add`), as TCW-107 Step 6's tests build one.
- **Origins** (Design 2.6): in AC 1's layout, the origin of `work.jira.site`
  in `app`'s configuration has `project == "core"`, layer `project`, and
  `core`'s file; a `file:` binding cannot be inherited (Design 1.2), so the
  folder rule is checked through `Origin.folder` on `core`'s origin being
  `core`'s root (1.4).
- **The user-wide file once** (choice 12, spec AC 12's last sentence):
  `app: [core]`, the user-wide file setting `work.tags: [u]` and
  `work.jira.credentials.email-env: MINE`. `app`'s configuration has exactly
  one problem for `work.tags`, naming the user-wide file. `refused` holds one
  record. `jira.email_env` reaches `app` as `MINE` (in Jira mode).
- **When the order cannot be had** (choice 11, spec AC 15's last sentences),
  7a's half: with `app`'s own `parents: notalist`, and with the loop
  `app: [lib]`, `lib: [top]`, `top: [lib]`, `load_config(<app>)` returns
  without raising. Its sources are `[app]`, and `Config.order_error` holds
  the withheld error of choice 11: for the loop, text containing `loop in
  parents: lib -> top -> lib`, equal to the message `tcw work list` prints
  in `app`. `tcw validate` in `app` exits 1 with TCW-108's graph problem as
  a finding line (the `where` TCW-108's AC 2 test checks) and standard error
  ending with the closing count; with `app` also setting
  `work.hooks.timeout: soon`, that problem is a finding of the same run.
  `tcw work list` exits 1 as before. A unit test of the trigger alone: with
  `source_entries` replaced by one that returns `[app]` without raising,
  `app`'s own `parents: notalist` still sets `order_error` (the re-check's
  B1).
- **A project read for itself needs the registry** (choice 3):
  `load_config(<core>, personal=False)` with `core: [base]` and no registry
  raises `TypeError`; with no `parents:` it does not. Through each caller
  Step 0 listed (`tcw work show <core's item>`, `tcw work new --project core`,
  `tcw work edit --blocks`, the web app's item suggestions), with `core:
  [base]` and `base` setting `work.tags: [b]`, the command reads `core`'s
  configuration with `base`'s tags and does not raise `TypeError`.
- **A project read for itself keeps its own ID** (choice 15, spec Decision
  31, the re-check's B2): from `app`, with `lib: [base]` so the command's
  registry is passed, `tcw work show <lib's item by full identifier>` prints
  the item with `lib` as its project, and `project_facts(<lib's root>,
  personal=False, registry=<app's registry>).project == "lib"`. Mutation
  check, recorded and reverted: reading the ID from the passed registry's
  `current` makes both go red with `app` in place of `lib`.

**Changes** `tcw/config.py`, `load_config` (`:574-645`) and helpers:

- **The order** (choice 2): `P`'s shared file is read first, as now. When it
  declares `parents:`, the sources are `registry.source_entries("config",
  root=root)`. The registry is the one passed, or, when `personal` is true
  and none was passed, `FsProjectRegistry.open(root)`. With `personal=False`
  and none passed, `load_config` raises `TypeError` (choice 3). Without
  `parents:`, the sources are `[P]` and no registry is opened.
- **When the order cannot be had** (choice 11): first `parse_parents` on
  `P`'s own `parents:` value; then opening the registry, the loop search
  with `find_loop`, `current` and `source_entries`, inside one `try` that
  re-raises `InheritedUnavailable` and catches `ValueError` and
  `TcwError`; and `P` in the order's `unreadable` as a backstop. In any of
  these cases the sources are `[P]`, and the withheld error of choice 11
  (built from `require_valid()`'s text when the registry records a
  problem) is kept as `Config.order_error`, for Step 7c. At this step
  nothing is withheld (the interim rule).
- **P's mode** is `P`'s own `work.backend` from its shared file (spec 1.2,
  5.2): it decides whether an ancestor's `work.jira` is taken (1.5) and
  whether credential names are set aside (`_without_credentials`,
  `:419-438`).
- **The fold** (2.1): built-in once. Then, for each source `Q` here, in
  order, at `position` its index:
  - `Q`'s shared file;
  - when personal files apply (`personal=True` and `personal_files_skipped()`
    false), the user-wide file and `personal_file(Q's root,
    LOCAL_CONFIG_NAME)` (TCW-107 Step 6).
  For `Q` other than `P`, each layer's mapping is first cut to the keys of
  Design 1.1 (`_inherited_part`). `work.jira` is dropped from it when `P` is
  not in Jira mode (1.5). Only then is it checked (the naming rule,
  `_list_problems`, and `_allowed` for `Q`'s local file, as `P`'s own are,
  spec 1.6) and merged with today's `_merge`. `P`'s layers are read and
  checked exactly as today. A source not here contributes nothing (the
  interim rule above).
- **The user-wide file** (choice 12) is read, checked against the whole
  allowed list and set aside (`_without_credentials`) once, before the fold,
  as `P`'s own layer. Its problems, `refused` and `skipped` go to `P`'s
  `Config` once. What remains is kept, and at each `Q` other than `P` it is
  cut to Design 1.1 and merged with no further check and no record. A value
  refused in `Q`'s local file is recorded in `Config.inherited_refusals`
  (shown by Step 7b's warning), not in `refused`.
- **Origins** (choice 10): every layer's `Origin` carries `project`,
  `position` and TCW-107's `root`; files of another project are shown by
  their whole path, as another project's files are named today (`shown =
  root if personal else None`, `:588`), with `P`'s own still relative.
- `Config.sources`: the IDs of the sources folded, in order, gaps included
  (read by Step 10).
- **A project read for itself** (`personal=False`, spec 5.2): its own sources
  are folded the same way with no personal file. The docstring of
  `load_config` (`:575-583`) says so, and no longer says "an upstream".
- `tcw/work/open.py`: `_layered` (`:36-45`), `read_work_config` (`:48-51`),
  `project_facts` and `open_backend` take `registry=None` and pass it to
  `load_config`, and `effective` gains `registry=None` for the same purpose
  (choice 15). For the active project `project_facts` opens the registry
  first, when none is passed, and passes it on, so one call builds one
  registry. For a project read for itself it passes on only what it was
  given, and reads the project's ID from the project's own per-root
  registry, never from the passed one (choice 15). Every reading of a
  project for itself that Step 0 listed passes the registry it holds:
  - `open_project` (`:88-99`, as TCW-110 leaves it);
  - `delegate` (`:162-187`), in both its `read_work_config` and its
    `open_backend`;
  - `open_for_update` (`:190-199`);
  - `delegate_to_jira(root=…)` (`tcw/work/jira/tickets.py:339`), which gains
    a `registry` keyword that `delegate` fills;
  - `_other_items` (`tcw/serve/work.py:559`).

**Reading every failure.** The full suite is run, and every failure is read
one by one, as TCW-108 Step 7f does. An assertion is changed only where a
criterion of this spec changes the behaviour it checks, and each change is
listed in the implement round with its design rule. Expected, and named in
the implement round before the change: only the tests from Step 0's list 1
and list 5 (its 7a group) whose parent passes `config` and sets `work.tags`
or `work.jira`. The child now sees them, and the unregistered-tag warnings
change with them. If more than five test files need the
same change, the change is made by hand and checked with the safeguards
below; no test is deleted in this step.

**Proves it:** the tests above; `tests/config/` (spec AC 27's second half:
every test there passes, with Step 5's one listed change); then, from the
worktree's root, `.venv/bin/pytest -q --junitxml=<scratchpad>/outcomes-step7a.xml`
and `compare_outcomes.py <scratchpad>/outcomes-step0.xml
<scratchpad>/outcomes-step7a.xml <scratchpad>/allowed-step7a.txt` exit 0,
`allowed-step7a.txt` being empty (no test ID goes in this step; a changed
test keeps its ID and must pass); the inventory against Step 0's: no test's
count of `assert` statements and `pytest.raises` blocks dropped. **Mutation
check**, recorded in the implement round and reverted: with
`_inherited_part` returning an empty mapping (nothing is taken from an
ancestor), AC 1, 4, 5, 6, 7 and 11's tests go red, and every test amended in
this step for seeing inheritance goes red; the failure reasons of at least
five are read and are the missing inherited value.

## Step 7b — a problem in an inherited value stops only what reads it

Spec Design 1.6 ("broken"), 7.1's exit 1, AC 10, AC 17's last sentence.

**Tests first**, in `tests/test_inherited_config.py`: AC 10, every sentence
(`tcw work tags list` and `tcw work new y --tag t` exit 1 naming `core`'s file
by its whole path and `work.tags`, with no `y`; `tcw work list`,
`tcw work new x` and `tcw taxonomy list` exit 0; `tcw validate` exits 0 with
the `warning`; in `core` it exits 1; `app` setting `work.tags: [x]` clears
both; `core`'s `work.hooks.timeout: soon` never reaches `app`). AC 17's last
sentence (`tcw config show` exits 1) is Step 9's, where `tcw config show`
learns the rule. Also, spec 1.6's refusal: `core`'s `tcw-config.local.yaml`
setting `work.tags: [x]` (refused by the allowlist), in `app`. `tcw work tags
list` prints `core`'s committed tags and exits 0, and `tcw validate` exits 0
with one `warning` at `core`'s local file. The user-wide file's `work.tags`
of Step 7a's test still gives one error and no warning.

**Changes**

- `tcw/config.py`: a problem found in another project's layer by the checks
  of 7a, and a parser problem whose origin (`_origin_for`, `:559-571`, now
  ranking by `(position, layer)`) is another project's, is not put in
  `Config.problems`. The user-wide file is never another project's layer
  (choice 12). A refusal by `_allowed` in another project's local file is
  never merged, so it marks nothing broken; it stays in
  `Config.inherited_refusals`. It is recorded as **broken** at its key of Design 1.1
  (`work.tags`, or `work.jira` for anything under it) with its `position`.
  After the fold, a broken mark stands unless a layer at a later position
  declares the key, or a key above it, with a value that replaces it whole
  (the rule of spec 3.1; Step 5's `null` counts). A standing mark makes the
  key withheld: `Config.withheld[key] = Withheld(ConfigError([<the
  problems>]))`, each problem naming the declaring file by its whole path and
  the key (spec 1.6), and `Config.inherited_problems` keeps them for
  `tcw validate`.
- `parse_work_config` is given the withheld keys (a new keyword,
  `withheld`), and puts the `Withheld` in `WorkConfig.tags` when `work.tags`
  is withheld; `load_config` puts it in `Config.jira` when `work.jira` is
  withheld in Jira mode. `Config.require(key)` raises the withheld error of a
  key, or returns.
- `tcw/work/open.py`, `open_backend`: in Jira mode, `layered.require("work.jira")`
  then `layered.require("work.tags")` before building the `JiraBackend`
  (choice 5).
- `tcw/validate.py`, `config_findings` (`:361-381`): one `warning` per
  problem in `Config.inherited_problems` whose key is still broken, and one
  per record in `Config.inherited_refusals`, `where` the declaring file's
  whole path (spec 1.6, AC 10).
- `tcw/work/fs_backend.py`, `work_store_problems` (`:527-566`): the
  unregistered-tag check is skipped when `config.tags` is a `Withheld`
  (spec 1.6: a broken key is handled as an undecided one). This is one of
  the places choice 14 allows to test `isinstance(…, Withheld)`, with the
  comment it asks for.
- `tcw/validate.py`, `_work_findings` (`:550-600`): a `ConfigError` from
  `open_backend` is already left to `config_findings` (`:571-573`), which now
  reports the broken key as a warning; the code is unchanged, and a test of
  AC 10's `tcw validate` in Jira mode is added to prove it.

**Proves it:** the tests above; the full suite; `compare_outcomes.py` against
Step 7a's record with an empty allowed list.

## Step 7c — a gap: undecided keys, exit 7, and `tcw validate`

Spec Design 3.1-3.3, 3.5-3.7, AC 13, 14, 15, 29, and the configuration
sentences of AC 17.

**Tests first**, in `tests/test_inherited_config.py`:

- AC 13, every sentence, including `tcw work advance <x> --dry-run` exit 0
  and the three variants (`app` setting `work.tags: [t]`; the link written
  `{id: core, inherit: [taxonomy, capabilities]}`).
- AC 14, every sentence, with the Jira client faked by
  `tests/work/jira/conftest.py`'s `fake` fixture (`:78`), which records every
  request: `tcw work list` exits 7 with `(work.jira)` and the fake records
  none; `tcw validate` exits 0 with one `unresolved` finding naming `core`;
  the commands AC 14 lists exit 0, `tcw work show` printing `lib`'s item.
- AC 15, both files (`parents: notalist`; not valid YAML), and TCW-108's AC
  31 test passing, amended only as spec 3.5 says.
- AC 29, with two real git repositories, as TCW-108's AC 26 test builds them.
- `tcw capabilities drift` in AC 14's layout exits 7 naming `(work.jira)`
  (spec 3.4 row a: it lists completed items through the backend), and in AC
  13's layout exits 0.
- AC 14's last two sentences: the `tcw://` link to `app`'s own item gives no
  finding in `tcw validate` in `app` (without Step 6's change,
  `resolve_tcw_ref` would catch the withheld `work.jira`'s error and report
  a false `error`); and with one of `lib`'s items referring to one of
  `app`'s, `tcw validate` in `lib` gives no finding about it (`app`, read for
  itself from `lib`, has an undecided `work.jira`; without Step 6's change
  the `InheritedUnavailable` escapes `reference_resolver` and the run exits
  7). (The re-check's I-1: an `app` item's reference cannot test this,
  because `app` is in Jira mode and `_work_findings` runs no reference check
  for a `JiraBackend`, `tcw/validate.py:576-582`.) Mutation check, recorded
  and reverted: with `reference_resolver` building a `JiraBackend` again,
  the `lib` test goes red with exit 7.
- **When the order cannot be had** (choice 11, AC 15's last sentences), 7c's
  half. With `app`'s own `parents: notalist`, `tcw work tags list` exits 1
  with the message `tcw work list` gives in `app` (compared whole), and
  `tcw work new y --tag t` exits 1 and creates nothing. `tcw validate` still
  exits 1 with the graph problem as a finding line and the closing count on
  standard error, and no traceback. The same holds for the loop, whose
  message contains `loop in parents: lib -> top -> lib` and nothing of the
  depth guard's text. `app` also setting `work.tags: [t]`: `tcw work tags
  list` prints `t` (a key the project decides itself is not withheld). And
  with `app: [core]`, `core` setting `work.tags: [a]`, and `app` listing a
  child `kid` that does not name `app` back (a graph problem of `app`),
  `tcw work tags list` in `app` prints `a` and exits 0; it is not stopped
  today either (the trigger is not "any graph problem"). Mutation check, recorded and
  reverted: with choice 11's `parse_parents` trigger removed, the
  `parents: notalist` test goes red with exit 0 and nothing printed.

**Changes**

- `tcw/config.py`, `load_config`: every source not here is a **gap**, at its
  position. During the fold, each declaration that replaces a key of the key
  table (`known_keys()`, restricted to `work.tags` and `work.jira`'s keys)
  whole is recorded with its position. After the fold, a key is
  **undecided** by choice 4; `work.jira` only in Jira mode (1.5); a mapping
  when any key under it is undecided. An undecided key is withheld with
  `registry.unavailable(<P>, <the gap>, f"configuration ({key})")` (spec 3.3);
  undecided wins over broken for the same key (spec 1.6). `Config` keeps, for
  `tcw validate`, the IDs of the gaps that withheld something, as the
  attribute `Config.gaps_withholding` (a tuple, in load order).
- **When the order could not be had** (choice 11): with `Config.order_error`
  set and `P` declaring `parents:`, each key of Design 1.1 that `P`'s own
  layers do not decide (choice 4's rule, as if one gap stood before `P`) is
  withheld with `BackendError(<order_error's text>)`, the withheld error of
  choice 11, so the message is TCW-108's graph problem as `tcw work list`
  prints it. `gaps_withholding` is not touched, since no gap is known, and
  `tcw validate`'s graph check reports the problem itself.
- **No built-in value and no "required"** (spec 3.2): the built-in layer has
  no value at either key today (`built_in_values`, `:208-221`), so nothing is
  taken from it; `parse_jira_config` (`tcw/work/jira/config.py:175-243`)
  gains `undecided: frozenset[KeyPath]`, skipping `required` for those paths
  (`_missing`, `:101-106`) and `timeout`'s default and check when `timeout` is
  undecided (`_timeout`, `:162-173`); the decided keys keep every other check.
  `_parse_tags` (`tcw/work/config.py:459-475`) is not run for an undecided
  `work.tags`. The checks that depend on the backend (`tcw/work/config.py:382-385`,
  `:416-427`, `:511-512`) run as today (spec 3.2's last sentence).
- `tcw/validate.py`, `_work_findings` (`:570`) and the one-item check
  (`:496`): an `InheritedUnavailable` from `open_backend` skips the store's
  checks and adds no finding (spec 3.6).
- `tcw/cli.py`, `_cmd_validate` (as TCW-108 Steps 7d and 11 leave it): the
  finding made for each project in `effective(root).gaps_withholding` gains
  `; could not check the configuration inherited from it`, after any row (c)
  suffix, once (spec 3.6).
- TCW-108's tests of AC 19 (and Step 11's "what lies above is unknown"
  tests), AC 20 and AC 31 that compare the finding's whole text, if Step 0
  found any, are amended to the new text and listed with Design 3.6.

**Reading every failure**, as in 7a: the failures expected are the tests of
Step 0's list 1 whose parent passes `config` and is missing or unreadable,
the TCW-108 tests of Step 0's list 2 (AC 19, Step 11's "what lies above is
unknown" tests, AC 20, AC 31), list 5's 7c group, and list 6 (a tag command
in a project whose own `parents:` is wrong or whose ancestors loop), each
named in the
implement round before the change. Each change is listed with its rule. No
test is deleted in this step; a test that no longer fits is amended to the
criterion that changed it.

**Proves it:** the tests above; `tests/test_parent_links_cli.py` and
`tests/test_parent_links.py`; the full suite; `compare_outcomes.py` against
Step 7b's record with an empty allowed list; the inventory against Step 0's.
**Mutation check**, recorded and reverted: with `Withheld` replaced by an
empty tuple for `work.tags` (an undecided key read as "no tags"), AC 13's
`tcw work tags list` and `tcw work new y --tag t` tests go red. The reasons
read are exit 0 for `tcw work tags list`, which prints nothing, and exit 2
for `tcw work new y --tag t`, whose `UsageError` "is not registered"
(`tcw/work/model.py:209-211`) exits 2 (`tcw/exit.py:10`), each in place of 7.

## Step 8 — the environment layer

Spec Design 2.1's last layer, 4.4, 4.8, 4.9, 5.3, 7.2; AC 11's variable
sentences, 19-25, 27 (its variable half), 28.

**Tests first**, in a new `tests/test_config_environment.py` (CLI and
loader), with the variables set by `monkeypatch.setenv` after the personal
fixture has removed `TCW_NO_PERSONAL_CONFIG`:

- AC 11's variable sentences: `TCW_WORK_JIRA_CREDENTIALS_EMAIL_ENV__CORE=VAR`
  gives `app` `VAR`; with `app`'s local file `APPS`; with
  `TCW_NO_PERSONAL_CONFIG=1` `CORE_EMAIL`; reading `core` for itself gives
  `VAR` with the variable and `CORE_EMAIL` with `TCW_NO_PERSONAL_CONFIG=1`
  added.
- AC 19, AC 20 and AC 21 through `tcw work list` in `app` (exit 1 and the
  message; `TCW_WORK_TAGS__ELSEWHERE` exits 1 and
  `TCW_USER_NAME__ELSEWHERE` exits 0 changing nothing in `app`).
- AC 22 through `tcw work stage prompt spec <item>` and `load_config`.
- AC 23, all three sentences, the two variables set in both orders, and
  `tcw work lifecycle --stage spec` listing `blob:gate`.
- AC 24: the `file:` binding, the note naming the variable on standard error,
  `../outside.md` refused with `resolves outside`, `TCW_CONFIG_DIR` written by
  `record.sh` equal to `app`'s root, and the failed `post` naming
  `from TCW_WORK_STAGES_SPEC_POST__APP`.
- AC 25, AC 28, both sentences. The second is `TCW_WORK_TAGS__LIB='[a]'`
  and a `tcw://` work link (`tcw://W/lib/<folder>`) from one of `app`'s
  capability descriptions to a `lib` item: one `environment` error, no
  finding about the link. **Mutation check**, recorded and reverted: with the
  problems also put into `personal=False` configurations, the second
  sentence's test goes red on an `error` finding for the link, whose message
  is the `ConfigError` from opening `lib` (`tcw/refs.py:158`). (An item
  reference cannot be used: `tcw validate` never runs the reference check
  while `app`'s own configuration has a problem, `tcw/validate.py:571-573`,
  so such a test could not fail; the re-check's B3.)
- AC 27: a project with no `parents:`, with `TCW_PROJECT_X`, `TCW_JIRA_EMAIL`
  and `TCW_STDIN_TIMEOUT` set, gives the same standard output, standard error
  and exit code for `tcw work list`, `tcw work tags list`, `tcw config show
  --origin` and `tcw validate` as with the three unset; and TCW-107's
  `_read_text` counting shows no registry read in that project for
  `load_config`.

**Changes**

- `tests/conftest.py`, `_no_personal_config` (`:166-177`): also removes every
  variable starting `TCW_` and holding `__`, so no developer's override
  reaches a test that switches personal configuration back on; its docstring
  says so.
- `tcw/config.py`:
  - `LAYERS` (`:55`) ends with `environment`, and `PERSONAL_LAYERS` (`:56`)
    holds it. `Origin` (choice 10): `folder` is the named project's root for
    the `environment` layer (spec 4.8); `__str__` is `environment: <NAME>`.
  - The overrides of the command (choice 9): `read_overrides(os.environ)`
    from Step 2, read only when `TCW_NO_PERSONAL_CONFIG` is unset or empty
    (spec 5.3; TCW-107's `personal_files_skipped()`), and not read or checked
    when it is `1` or any other value, which keeps today's problem
    (`_personal_layers`, `:678-695`). Its problems go into
    `Config.problems` of the active project's configuration only
    (`personal=True`; choice 13, spec 4.4), once per command. A reading with
    `personal=False` applies only the overrides that passed every check and
    adds no problem, so a project read for itself, through
    `_layered(personal=False)` (`tcw/work/open.py:43-44`), never raises
    `ConfigError` because of a variable. Without this, `tcw validate`'s
    `tcw://` link check would give a false `error` for every link into
    another project (`tcw/refs.py:158`), and the web app's reads of another
    project would fail (choice 13).
  - **Who reads variables** (spec 4.4, 5.2): at each source `Q` of the fold,
    after `Q`'s local file, the overrides naming `Q` are merged as one layer
    each, in Step 2's order, with `Origin("environment", variable=<NAME>,
    project=Q, root=Q's root)`. That holds for the active project and each of
    its sources, and for a project read for itself (`personal=False`) and
    each of its sources. For `Q` other than `P` the override's mapping is cut
    to Design 1.1 as every other layer of `Q`'s is, so only credential names
    reach `P` from an ancestor. An override naming a project the command does
    not fold is checked and otherwise does nothing.
  - `_confinement` (`:535-556`): for a binding from a variable, the folder is
    the named project's root and the message starts with the variable's name
    and says "the root of the project it names" in place of "the folder of
    the file that declares it".
  - `Config.personal_variables(key_path)`: the variables that set the chain
    list at `key_path`, from `written` (`:169-170`); `personal_files` keeps
    its signature (`tests/config/test_personal_merge.py:180`).
  - `Setting` (`:149-156`) gains `variable`, so a credential name set aside
    outside Jira mode from a variable is listed by name in `tcw config show
    --origin`'s set-aside block (`tcw/config_cli.py:209-220`).
- `tcw/work/cli.py`, `_personal_note` (`:449-460`): names the files, then the
  variables (spec 4.9).
- `tcw/work/hooks.py:72-73`: `from <NAME>` for a binding whose origin has a
  `variable`; `config_dir` (`:36-42`) needs no change, since
  `Origin.folder` answers the root.
- `tcw/validate.py`, `config_findings` (`:375`): already shows a problem
  with no file at `environment`; nothing changes beyond a test (AC 28).

**Proves it:** the tests above; `tests/config/` unchanged except Step 5's
listed test; the full suite. **Mutation check**, recorded and reverted: with
the overrides never merged (read and checked, but not applied), AC 19's,
AC 22's and AC 23's tests go red and AC 20's and 21's stay green, which shows
the checking and the applying are tested separately.

## Step 9 — `tcw config show`

Spec Design 7.1, AC 17.

**Tests first**, in `tests/config/test_config_show.py`: AC 17, every
sentence: the inherited values printed; `--origin`'s comment on `site`
holding `core`'s file by its whole path; `TCW_USER_NAME__APP=Robin` printed
with `environment: TCW_USER_NAME__APP`; exit 7 with nothing on standard
output in AC 13's first layout, with and without `--origin`; `(work.tags)` in
AC 14's layout, where both keys are undecided; exit 1 with nothing printed in
AC 10's first layout (if not already written at Step 7b). AC 12's last
sentence: with `app: [core]` and the user-wide file setting `work.tags: [u]`,
`--origin`'s set-aside block lists that value once. Every existing test of
the file passes unchanged (AC 27).

**Changes** `tcw/config_cli.py`:

- `_show` (`:251-269`): before anything is printed, with or without
  `--origin`, the first undecided key in `INHERITED_KEYS`' order raises its
  error (exit 7); with none undecided, the first broken key raises its
  error (exit 1) (spec 7.1).
- `_Writer.comment` (`:119-137`): a value whose origin's `project` is not the
  active project's is labelled `<layer>: <the file's whole path>`; a value
  from a variable `environment: <NAME>`; every other label as today.
- The command's help (`:276-282`) says the effective configuration includes
  what the project's parents pass down and the override variables.

**Proves it:** the test file; `tests/test_cli_help_standard.py`; the full
suite.

## Step 10 — `tcw work tags add` and `rm` in a child

Spec Design 6.1-6.3, AC 18.

**Tests first**, in `tests/test_inherited_config.py`: AC 18, every sentence,
each file compared byte for byte where the criterion says it is unchanged;
and in a project with no parents, `tcw work tags add` and `rm` write the same
bytes as before this item (the existing tag tests found by Step 0's list 1,
unchanged).

**Changes** `tcw/work/cli.py`, `_write_tags` (`:626-645`), `_tags_add`
(`:648-650`) and `_tags_rm` (`:653-665`):

- The merged list is `read_work_config(root).tags` (raising exit 7 or 1 when
  withheld, spec 3.4 row b); the project's own list is its shared file's
  `work.tags`, read with `read_project_file` (`tcw/config.py:257-270`) and
  normalized as `_parse_tags` does, with whether it holds `inherit: true`;
  whether the project has a source other than itself comes from
  `Config.sources` (Step 7a).
- `add` (6.2): tags already in the merged list are left alone; the rest are
  added to the own entries, sorted, written with `SetList(..., inherit=True)`
  (Step 3) when the own list holds the entry, or when it is absent and the
  project has another source; otherwise the plain list, as today.
- `rm` (6.3): a tag still registered afterwards because an earlier source
  declares it (the own list absent or holding `inherit: true`, and an entry
  of the merged list whose origin's `project` is another project's) is
  refused with `Refused` (exit 3) and spec 6.3's message, `<project>` the last
  such origin's project; nothing is written. A tag registered nowhere is
  refused as today (exit 4).

**Proves it:** the tests above; `tests/test_config_edit_writers.py`; the full
suite.

## Step 11 — the web app

Spec Design 3.4's last paragraph, AC 32.

**Tests first**, in `tests/serve/test_work_read.py`: AC 32, both layouts:
`GET /api/project` answers 200 with `tags` a mapping whose `unavailable`
holds `(work.tags)` and every other field as in a project whose tags are
decided; `GET /api/work` 200; in AC 14's layout `GET /api/work` 500 with an
`error` holding `(work.jira)`.

**Changes** `tcw/serve/work.py:173`: `"tags"` is `list(ctx.config.tags)`, or
`unavailable(error)` (`:81-82`) when that raises `InheritedUnavailable` or
`ConfigError`. Nothing else: an `InheritedUnavailable` raised by opening a
Jira-mode store already answers 500 (`tcw/serve/server.py:90-91`, TCW-108's
plan, choice 7).

**Proves it:** the test file; `tests/serve/`; the full suite. No client file
changes, so the web gate is not needed; `git status` confirms
`web/` and `tcw/serve/dist` are untouched.

## Step 12 — this repository's records

In this repository's 3.x-format ledgers, with the lifecycle CLI (the header),
as TCW-108 Step 14 does. Spec AC 30.

- New capabilities, with `tcw capabilities add`, status `Supported`:
  `cli/inherit-configuration-from-parents` and
  `cli/override-configuration-from-the-environment`, each `description.md`
  with the spec's Capability changes sentence, and `Subject` naming the terms.
- Changed: the `description.md` of each of `cli/override-the-team-configuration-for-myself`,
  `cli/show-the-effective-configuration`, `cli/validate-a-project`,
  `work/tag-a-work-item` and `work/keep-work-items-in-jira`, with the
  sentence the spec's Capability changes gives it.
- Taxonomy: new term `environment-override` (`tcw taxonomy add`), related to
  `config-layer` and `personal-configuration`; the descriptions of
  `docs/taxonomy/config-layer/` and `docs/taxonomy/personal-configuration/`
  name the environment layer, the inherited keys and whose personal settings
  apply.

The descriptions never put a command that does not exist yet (`tcw project
config`, `tcw project provision`) in backticks, since
`tests/test_documented_cli_surface.py` checks every `tcw …` command they put
in backticks.

**Proves it:** with the lifecycle CLI, from the worktree: `tcw validate`; and
at the end of implement `tcw work advance TCW-109 --dry-run` (the records
gate); `tests/test_documented_cli_surface.py` in the full suite.

## Step 13 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: settings shared down a family, the override variables | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (spec Non-goals); what it must say is in Step 14's note. |
| `docs/guide/jira.md` [Jira-Change] | yes: `work.jira` may come from a parent, `work.backend: jira` is always the project's own, a credential name may come from a variable | Deferred to TCW-117 (spec Non-goals and Notes). |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: `docs/guide/configuration.md` (the inherited keys, `null`, `inherit: true` in `work.tags`, the environment layer, the allowed list, exit 7 for configuration), `docs/guide/multi-repo.md` | Deferred to TCW-117 (spec Notes list). |
| `docs/release-notes/upcoming/<folder>.md` [Public-API] | yes | Written, in plain language: a project takes its parents' tags and Jira settings, except which backend it uses; how a child changes what it inherits (its own value, `inherit: true` in its tags, `null`); a missing parent stops only a command that needs a setting it could have given, with exit code 7, and `tcw validate` says "could not check"; a mistake in a parent's shared settings stops only what reads them; any setting a personal file may set can be set from an environment variable named `TCW_<KEY>__<PROJECT>`, with examples, and a variable naming a stage changes only what it names; `TCW_NO_PERSONAL_CONFIG=1` turns the variables off too; `tcw work tags add` in a child keeps following its parents. |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`INHERITED_KEYS`, `tcw/config_keys.py` with `known_keys`, `override_name`, `decode_key`, `read_overrides`; the `environment` layer; `Withheld`, `Config.withheld`, `Config.require`, `Config.inherited_problems`, `Config.inherited_refusals`, `Config.gaps_withholding`, `Config.order_error`, `Config.sources`, `Config.personal_variables`; `ProjectRegistry.source_entries`, `SourceEntry`, `ProjectRegistry.unavailable`; `SetList(inherit=)`; `project_facts`, `ProjectFacts`, `external_stages_of`), Changed (`load_config` folds the configuration sources; `Origin` carries `project`, `variable`, `position`; `inherit: true` accepted in `work.tags`; `null` at `work.tags` and `work.jira` removes; `_allowed`'s voice; `parse_jira_config(undecided=)`; `parse_work_config(withheld=)`; `validate_changes` reads the tags only when one is added; `open_backend` requires the inherited keys in Jira mode, and is built on `project_facts`; `load_config(personal=False)` needs the command's registry for a project with `parents:`; `delegate_to_jira(registry=)`; `resolve_work_input` takes the active backend as a function; the commands that no longer open the store; `resolve_item` for another project's item; references into a Jira-mode project answered without opening its store; `tcw config show`'s exit codes and labels; `tcw work tags add` and `rm`; `_cmd_validate`'s suffix; an ancestor's unreadable shared file is unreadable, not a graph problem, while a descendant's stays one; `/api/project`'s `tags`) and Internal (the suite strips override variables). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: `skills/work/SKILL.md` (exit 7 for a configuration setting, `tcw work tags` in a child) | Deferred to TCW-117, as TCW-108 decided for its own skill passages (spec Non-goals); the text is in Step 14's note. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | yes: the inherited keys, `null`, `inherit: true` in `work.tags`, the override variables and the allowed list | Deferred to TCW-117 (spec Notes: "document Design 1.1's list where the configuration keys are documented (`skills/configure/references/`, `docs/guide/configuration.md`)"). |
| `docs/use-cases.md` [Project-Setup-Change] | yes: S-5, UC-5, UC-6 | Deferred to TCW-117, with the spec Notes' wording. |

The two `upcoming/` files are named
`TCW-109-tcw-4-0-inherited-configuration-personal-settings-and-environment-overrides.md`
(the item's folder name, never its full slug), with `##` headings only as the
folder's `README.md` says, and are formatted with `prettier`.

## Step 14 — notes for the later children

Comments the dispatching session posts (the text is in the implement round):
the spec's handoffs (Notes, "Handoffs to later items") plus what planning
added:

- The handoff texts are in the revise report of 2026-10-22, one block per
  ticket; this list is their summary.
- **TCW-108:** its tests of AC 19, 20 and 31, and Step 11's "what lies above
  is unknown" tests, gain spec 3.6's suffix; written as "contains" checks,
  they need no change here.
- **TCW-110:** `resolve_work_input` takes the active backend as a function
  (Step 6).
- **TCW-112:** `source_entries` and `unavailable(project_id, gap_id, axis, *,
  subject=None)` are the non-raising form of `sources` and the one place its
  messages are built; TCW-112's `store_message=` keyword goes there too
  (Step 4). The configuration's `axis` is `config`. An ancestor whose shared
  file cannot be read is unreadable in the `ancestor` and `outside` roles
  (Step 4), and a descendant's stays a graph problem. `taxonomy.extends` and
  `capabilities.extends` are in `known_keys()` and come out when TCW-112
  removes them. `known_keys()` is used only to decode variables and to
  decide undecided keys under `work.tags` and `work.jira` (Step 1); the
  loader never reports a file's key for being missing from it, and reads
  only Design 1.1's keys from another project's file, so an `extends` there
  is never read and never makes that project unreadable.
- **TCW-113:** a project read for itself is `load_config(root,
  personal=False, registry=<the command's registry>)`. The registry is
  required for a project with `parents:`, and is used for the fold only:
  the project's ID comes from `project_facts`, never from the registry's
  `current` (choice 15). Such a reading reports no variable problem. A gap
  in its configuration sources makes it unavailable in a scoped listing
  (exit 0, this item's message as the reason, spec Design 5.2 as amended at
  TCW-113's handoff), and still stops with exit 7 a command that reads its
  object by full identifier or runs in it.
- **TCW-115:** `tcw project config` takes `tcw config show`'s rule (Step 9):
  exit 7 for the first undecided key in `INHERITED_KEYS`' order, exit 1 for a
  broken one, nothing printed; each value's origin carries `project`,
  `variable` and `position` for `--origin`.
- **TCW-116:** the two reports the spec's Notes name (a credential variable
  name starting `TCW_` and holding `__`; a `null` at `work.tags` or
  `work.jira`).
- **TCW-117:** the spec's Notes list, and for `skills/work/SKILL.md`: "On exit
  7 naming a configuration setting (`work.tags`, `work.jira`), report which
  project it comes from and its two remedies, fetch the project or leave
  `config` out of that link; do not retry", and that `tcw work tags add` in a
  child writes `inherit: true` first.
- **TCW-99:** the departures the spec's Notes list. The four spec defects
  planning found have been fixed in the spec (below).

## Step 15 — the suite as CI runs it

Spec AC 31, done locally as TCW-108 Step 17 does, since CI does not run on
`v4`: bare `.venv/bin/pytest` from the worktree's root, never `python -m
pytest`; `pnpm install --frozen-lockfile` and `pnpm check:build`. A failure
is fixed in the step it belongs to, not with a skip.

## Verification the tests cannot do

- **The QA plan's scenarios** (the ticket's QA plan comment, sections 1-8)
  are run by hand at qa with `.venv/bin/tcw` in throwaway folders under the
  scratchpad, with the current folder set there, never inside the worktree.
  Scenario 6 uses two real git repositories; scenario 3's web half opens
  `tcw serve` in the dedicated Claude Chrome profile, never the default one.
- **No request reaches a real Jira site**: the tests use the fake client; at
  qa, a Jira-mode scenario is checked with a site name that does not resolve
  (`https://core.example.net`), so an accidental request fails loudly rather
  than reaching anything.
- **The released 3.x CLI still reads this repository** after Step 12 changes
  the ledgers: `which tcw` first, then `tcw work show TCW-109` and
  `tcw validate` with the lifecycle CLI.
- **A developer's own overrides**: whether a shell that exports a
  `TCW_..__..` variable for real work disturbs the suite cannot be tested from
  inside it; Step 8's conftest change is read in review, and qa runs the suite
  once with `TCW_USER_NAME__TCW=someone` exported.

## Self-review against the spec

| AC | Step |
| --- | --- |
| 1 | 7a |
| 2 | 7a (and 6: `tcw work docs` and the stage prompt read no store) |
| 3 | 7a |
| 4, 5, 6 | 7a |
| 7 | 5 (one project, refusals), 7a (inherited) |
| 8 | 5 (personal `null`, `work.backend: null`, one project), 7a (inherited) |
| 9 | 7a |
| 10 | 7b |
| 11 | 7a (files), 8 (variables, `personal=False`) |
| 12 | 7a (the user-wide file once), 9 (`--origin`'s set-aside list) |
| 13 | 6 (the store is not opened, tags read only when applied), 7c |
| 14 | 6 (the commands that no longer open the store, the two references), 7a (`lib`'s item shown with `lib` as its project), 7c (exit 7, no request, `tcw validate` in `app` and in `lib`, `tcw capabilities drift`) |
| 15 | 4 (registry, the unreadable file, the descendant), 7a (the order cannot be had: no raise), 7c (commands, `tcw validate`, withholding when the order cannot be had) |
| 16 | 7a, 7c |
| 17 | 9 |
| 18 | 3 (the editor), 10 |
| 19, 20, 21 | 2 (rules), 8 (commands) |
| 22, 23 | 2 (rules), 8 (commands) |
| 24, 25 | 8 |
| 26 | 1 |
| 27 | 8 (commands, the single project), 7a and 8 (`tests/config/` passing, the one listed change from Step 5) |
| 28 | 8 (both sentences) |
| 29 | 7c |
| 30 | 12 |
| 31 | 15 |
| 32 | 11 |
| 33 | 7a |

Every design rule of the spec's Coverage table falls in a step through these
criteria; 1.4 has no test of its own, as the spec's Coverage table says, and
7a checks the declaring project's root in an origin. Steps that trace to no
single criterion: 0 (the starting point), 13 (documentation), 14 (handoffs).
No step appears twice; the names `INHERITED_KEYS`, `Withheld`,
`source_entries`, `read_overrides`, `known_keys` are used with one meaning
throughout.

**The suite at each step boundary**, each claim checked against what it
depends on:

- 0→1, 1→2, 2→3: runnable; each adds code nothing calls yet (Step 2's
  `_allowed` change keeps the file voice's words, so the personal-file tests
  are unchanged).
- 3→4: runnable; `SetList`'s new field defaults to today's behaviour.
- 4→5: runnable; `sources` keeps its messages and outcomes over
  `source_entries`; the unreadable-file change touches only the `ancestor`
  and `outside` roles, and any test that relied on the old outcome is
  amended in Step 4 itself.
- 5→6: runnable; within one project `inherit: true` in `work.tags` was a
  problem before and is accepted now, and the one test that pinned the
  refusal moves to `work.documentation` in the same step; `null` at the two
  keys gives the same parsed result in one project (no tags; no `work.jira`).
- 6→7a: runnable. Step 6 changes only which code opens the store and when
  the tags are read. Each changed place keeps the checks the store's opening
  made (`project_facts`), and nothing is withheld yet, so every command
  answers as before.
- 7a→7b: runnable. 7a's interim rules keep every 3.x outcome for a gap
  (nothing contributed) and make an inherited problem stricter, not looser.
  A registry that cannot answer is caught from 7a on, so `load_config` never
  raises for it. The failures 7a reads are only tests whose parents now pass
  a value.
- 7b→7c: runnable; 7b only moves inherited problems out of
  `Config.problems`.
- 7c→8: runnable; `tcw validate` skips rather than stops (7c's own change),
  and TCW-108's validate tests are amended in 7c if their text changes. The
  web app's `/api/project` would answer 500 for an undecided `work.tags`
  until Step 11, and no existing test builds that layout (Step 0's list 1).
- 8→9: runnable; the suite strips override variables from the first change
  of Step 8, and with none set the fold is 7c's.
- 9→10, 10→11, 11→12: runnable; each changes one command's output and its own
  tests.

## Spec defects found while planning, and how they were resolved

The plan review of 2026-10-22 confirmed the four defects this section first
listed, and the item went back to spec. Each is now fixed in the spec, and
this plan follows the fixed text.

1. **Design 3.4's list of commands that must stop opening the store was
   incomplete.** It missed `tcw work path` with no item
   (`tcw/work/cli.py:318`) and the two readers of a reference into a
   Jira-mode project. The first draft of this plan overstated their effect.
   `tcw/refs.py:139` would not stop anything, because `resolve_tcw_ref`
   catches every exception (`:123-124`). It would give a false `error`
   finding in `tcw validate`'s link check and a false answer from
   `/api/resolve`. No `tcw taxonomy` or `tcw capabilities` command calls it.
   `reference_resolver` would let an `InheritedUnavailable` escape, so
   `tcw validate` would exit 7. The spec's 3.4, its Risks bullet and Decision
   19 now name all three, with these effects. Row (b) no longer lists
   `--untag`, which reads no tag list in a filesystem project.
2. **`tcw capabilities drift` reads `work.jira` in Jira mode.** It is now
   in the spec's row (a), with an exception in 3.4's last paragraph, and in
   AC 14.
3. **"No TCW-108 criterion or test changes" (Design 3.5).** It now says that
   no criterion changes. The `tcw validate` tests of TCW-108's AC 19 (with
   its "what lies above is unknown" sentences), AC 20 and AC 31 gain the
   suffix, and Decision 24 says so.
4. **Design 1.6 and descendants.** The first draft of this plan said that
   TCW-108 Design 6.6 applies only to ancestors and lookups. That was wrong
   for `parents:` problems, which 6.6 also takes out of the graph problems
   for a descendant. What 6.6 keeps as a descendant's graph problems is its
   `children:` problems and its name-back check. The spec now says that a
   whole unreadable file is a gap for an ancestor and a project read for a
   lookup, and stays a graph problem for a descendant. The reason is 6.6's
   reason for a descendant's `children:` problems (decided by the
   dispatching session).

## Re-check findings (2026-10-22), and how they were resolved

The re-check of the revised spec and plan found three things to fix before
implement and seven smaller ones. All are fixed in the spec and in this plan.

- **B1, the active project's own bad `parents:`.** Choice 11 now reads the
  project's own `parents:` with `parse_parents` and looks for an ancestor
  loop with `find_loop`, instead of waiting for the registry to raise or to
  call the project unreadable, which TCW-108 does not do in the `active`
  role. The withheld error is the text `tcw work list` gives, so a loop is
  named by TCW-108's message (spec 1.3, Decision 30, AC 15; Steps 7a, 7c).
- **B2, the project ID of a project read for itself.** `project_facts`
  reads that ID from the project's own per-root registry, as `open_backend`
  does today, and uses the command's registry only for the fold; with
  `personal=False` it opens no fallback, so `load_config`'s `TypeError`
  stands (choice 15, Step 6, Step 7a's new test; spec Decision 31, AC 14).
- **B3, AC 28 could not fail.** It now uses a `tcw://` link into `lib`, which
  `tcw validate` checks whatever the configuration holds, and the reasoning
  in spec 4.4, Decision 27, choice 13 and Step 8 says so.
- **I-1**: AC 14's reference half now runs `tcw validate` in `lib`, a
  filesystem project, with a reference into `app` (Step 7c).
- **I-2**: `effective` takes `registry=None` (choice 15).
- **I-3**: Step 0's list 5 uses the parent-link grep itself; list 6 is new;
  the `personal=False` search covers `tests`.
- **I-4**: the TCW-111 paragraph names `link_exists`.
- **I-5**: spec 1.6 lists a duplicate key among unreadable files.
- **I-6**: choice 11 re-raises `InheritedUnavailable` and says why exit 5
  turning into exit 1 costs nothing today.
- **I-7**: AC 15 asserts the finding line and the closing count, plus a
  second problem of `app`'s own in the same run.

