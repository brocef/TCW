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
  registry and adds no walk of its own.
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
  (Step 10), which this item must leave passing (spec Design 3.5), and the
  two-repository fixture of AC 26, which AC 29 here repeats.

From **TCW-111**: nothing this item calls. It renames `item.yaml` to a state
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
   personal=False)`, which now folds that project's own configuration sources
   and applies the variables naming each of them, with no personal file. A
   caller that holds the command's registry passes it
   (`load_config(root, personal=False, registry=registry)`), so the project's
   order comes from TCW-108's `load_order(id, root=...)` on the command's one
   registry (TCW-108 plan, re-check R4); otherwise the registry opened at
   `root` is used.
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
   `ancestor` and `outside` roles of TCW-108's `_read_config`, as TCW-108's
   Design 6.6 splits roles. A descendant's unreadable file stays what TCW-108
   makes it. The spec's "when it is not the active project" could be read to
   include descendants; reported below.
8. **Commands that need no inherited key and open the store today.** The
   spec's six places (Design 3.4) and three it does not name (spec defect 1):
   `tcw work path` with no item (`tcw/work/cli.py:318`), and the two readers
   of a reference into a Jira-mode project, `tcw/refs.py:139` and
   `reference_resolver` (`tcw/work/open.py:210-241`), which already answer
   from the item folders and need no Jira setting.
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
11. **A registry that cannot answer.** If opening the registry or computing
    the order raises (`ProjectGraphError`, TCW-108 plan choice 5, or another
    `TcwError`), `load_config` folds the project alone and, when it declares
    `parents:`, withholds every key of Design 1.1 it does not decide, with that
    error. So no command runs on a half-inherited value, and one that reads
    no inherited key reaches its own graph check, which reports the problem.

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
  and the six lines of spec Design 3.4 (`tcw/work/cli.py:56`, `:71`, `:318`,
  `:441`, `:455`, `:567`, `:596`).
- **Every reader of an inherited key**, by `grep -rn "\.tags\b"` and
  `grep -rn "\.jira\b\|layered\.jira\|config\.jira"` over `tcw/`, compared
  with this list at `d2d02829`: `tcw/work/fs_backend.py:286`, `:536`;
  `tcw/work/cli.py:245`, `:621`, `:632`; `tcw/work/jira/backend.py:354`,
  `:437`, `:628`; `tcw/serve/work.py:173`; `tcw/work/open.py:75-77`;
  `tcw/validate.py:505`, `:580`. A new one found is added to Step 6 or 9.
- **Every opener of a work store**, by `grep -rn "open_backend(\|read_work_config("
  tcw`, each recorded as reading an inherited key (spec 3.4 rows a-c) or not.
  At `d2d02829`: `tcw/capabilities/cli.py:201` (`tcw capabilities drift`,
  which lists completed items, row a: spec defect 2), `tcw/validate.py:496`,
  `:570`, `tcw/refs.py:139`, `tcw/cli.py:518` (`--remote`, row a),
  `tcw/work/jira/tickets.py:339`, `tcw/serve/services.py:26`,
  `tcw/serve/work.py:68-69`, `:559`, `tcw/work/open.py:99`, `:177`, `:183`,
  `:198`.
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
  2. **TCW-108's AC 18, 20, 26 and 31 tests** in
     `tests/test_parent_links_cli.py`. The `tcw work list` halves run in
     filesystem projects with no tag option and must pass unchanged (spec
     3.5). The `tcw validate` halves of AC 20 and AC 31 have a parent that
     passes `config` missing or unreadable and a child that sets no
     `work.tags`, so their `unresolved` finding gains `; could not check the
     configuration inherited from it` at Step 7c (spec 3.6). If either test
     compares the finding's whole text rather than testing for words in it,
     it is amended at Step 7c to the new text and listed with Design 3.6
     (spec Decision 24 makes that this item's). AC 18 (`ws` behind
     `inherit: none`) and AC 26 (`inherit: none`) have no configuration gap
     and are unaffected.
  3. Tests that pin a behaviour Design 2.4 or 2.5 changes:
     `grep -rn "allowed only in a stage\|is allowed only" tests` (at
     `d2d02829`, `tests/config/test_personal_merge.py:102-108`, which uses
     `work.tags` as the list that refuses `inherit`), and
     `grep -rnE "(tags|jira)\"?: *(None|null)" tests`.
  4. Tests that construct `Origin` or read `LAYERS`, `PERSONAL_LAYERS` or
     `rank` (`grep -rn "Origin(\|LAYERS\|\.rank\b" tests`; at `d2d02829`
     none outside `tests/config/test_personal_merge.py:180`'s
     `personal_files`, which keeps its signature).
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

**Changes**

- `tcw/store/base.py`: `SourceEntry(id, project, state)`, frozen;
  `ProjectRegistry.source_entries(axis, project_id=None, *, root=None)`
  (choice 2), built from `load_order`, `passing` and `link_state`; `sources`
  rewritten over it. The building of the `InheritedUnavailable` that
  `sources` raises moves into `ProjectRegistry.unavailable(project_id,
  gap_id, subject) -> InheritedUnavailable`, where `subject` is the words that
  stand for the axis (`taxonomy`, `capabilities`, or, from this item,
  `configuration (work.tags)`); `sources` calls it with the axis name, so its
  messages do not change.
- `tcw/store/project.py`, `_read_config` (as TCW-108 Step 7b leaves it): in
  the `ancestor` and `outside` roles, a file whose read gives a problem (the
  problem `read_project_file` returns, `tcw/config.py:257-270`: not found
  after it was located, not UTF-8, not YAML, not a mapping, or a version this
  TCW cannot read) is recorded as `link_problem` with that problem's text and
  its links as unknown, instead of a graph problem; the `active` and
  `descendant` roles keep TCW-108's handling (choice 7). If TCW-108 as landed
  already does this, Step 0 records it and only the tests are added.

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

**Changes**

- `tcw/config.py`: `Withheld(error)` (choice 1).
- `tcw/work/model.py:188-214` (`validate_changes`): the registered set is
  built only when `changes.add_tags` is not empty. The two callers
  (`tcw/work/fs_backend.py:286`, `tcw/work/jira/backend.py:628`) still pass
  `config.tags`, which is no longer read on a create or edit without a tag.
- `tcw/work/cli.py`:
  - `_project_id(root)`: `FsProjectRegistry.open(root).current.id`, as
    `open_backend` reads it (`tcw/work/open.py:65-71`).
  - `_own` (`:69-74`) and `_personal_note` (`:449-460`) compare with
    `_project_id(root)`.
  - `_lifecycle` (`:567`) and `_docs` (`:596`): `read_work_config(root)`.
  - `_path` with no item (`:318`): prints `work_path(root)`
    (`tcw/work/open.py:28-33`).
  - `_prompt_target` with no item (`:440-441`) returns the configuration and
    the backend class's fixed `external_stages` (`external_stages_of(config)`,
    a new function in `tcw/work/open.py` answering
    `JiraBackend.external_stages` or `FsWorkBackend.external_stages` by
    `config.backend`, `tcw/work/jira/backend.py:216`,
    `tcw/work/fs_backend.py:235`) in place of a backend; `_stage_prompt`
    (`:490-519`) and `_procedure` (`:521-546`) read those two instead of
    `backend.config` and `backend.external_stages`.
  - `resolve_item` (`:50-66`, as TCW-110 Step 8 leaves it): the argument is
    sorted first (`sort_input(arg, "work", KEY)`); a form `a` or `c` naming a
    project other than `_project_id(root)` opens that project with
    `open_project` and resolves there, without opening the active project's
    store; every other form opens `open_backend(root)` as now (a Jira key,
    form `b`, still needs it, spec 3.4).
- `tcw/refs.py:139` and `reference_resolver` (`tcw/work/open.py:210-241`), for
  a Jira-mode project: answered from the item folders (`link_exists(work_path(root),
  folder)`) without building a `JiraBackend`, as they already answer it once
  built (choice 8).

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

**Changes** `tcw/config.py`, `load_config` (`:574-645`) and helpers:

- **The order** (choice 2): `P`'s shared file is read first, as now. When it
  declares `parents:`, the sources are `registry.source_entries("config",
  root=root)` from the passed registry or `FsProjectRegistry.open(root)`
  (choice 3); otherwise `[P]` and no registry is opened.
- **P's mode** is `P`'s own `work.backend` from its shared file (spec 1.2,
  5.2): it decides whether an ancestor's `work.jira` is taken (1.5) and
  whether credential names are set aside (`_without_credentials`,
  `:419-438`).
- **The fold** (2.1): built-in once; then for each source `Q` here, in order,
  at `position` its index: `Q`'s shared file; when personal files apply
  (`personal=True` and `personal_files_skipped()` false), the user-wide file
  (read once, applied at every `Q`) and `personal_file(Q's root,
  LOCAL_CONFIG_NAME)` (TCW-107 Step 6). For `Q` other than `P`, each layer's
  mapping is first cut to the keys of Design 1.1 (`_inherited_part`), and
  `work.jira` is dropped from it when `P` is not in Jira mode (1.5); only
  then is it checked (naming rule, `_list_problems`, and `_allowed` for a
  personal layer, as `P`'s own are, spec 1.6) and merged with today's
  `_merge`. `P`'s layers are read and checked exactly as today. A source not
  here contributes nothing (the interim rule above).
- **Origins** (choice 10): every layer's `Origin` carries `project`,
  `position` and TCW-107's `root`; files of another project are shown by
  their whole path, as another project's files are named today (`shown =
  root if personal else None`, `:588`), with `P`'s own still relative.
- `Config.sources`: the IDs of the sources folded, in order, gaps included
  (read by Step 10).
- **A project read for itself** (`personal=False`, spec 5.2): its own sources
  are folded the same way with no personal file. The docstring of
  `load_config` (`:575-583`) says so, and no longer says "an upstream".
- `tcw/work/open.py`: `_layered` (`:36-45`), `read_work_config` (`:48-51`)
  and `open_backend` (`:54-78`) take `registry=None` and pass it to
  `load_config`; `open_project` (`:88-99`), `delegate` (`:162-187`) and
  `open_for_update` (`:190-199`) pass the registry they hold.

**Reading every failure.** The full suite is run, and every failure is read
one by one, as TCW-108 Step 7f does. An assertion is changed only where a
criterion of this spec changes the behaviour it checks, and each change is
listed in the implement round with its design rule. Expected: only tests from
Step 0's list 1 whose parent passes `config` and sets `work.tags` or
`work.jira` (the child now sees them). If more than five test files need the
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
learns the rule.

**Changes**

- `tcw/config.py`: a problem found in another project's layer by the checks
  of 7a, and a parser problem whose origin (`_origin_for`, `:559-571`, now
  ranking by `(position, layer)`) is another project's, is not put in
  `Config.problems`. It is recorded as **broken** at its key of Design 1.1
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
  problem in `Config.inherited_problems` whose key is still broken, `where`
  the declaring file's whole path (spec 1.6, AC 10).
- `tcw/work/fs_backend.py`, `work_store_problems` (`:527-566`): the
  unregistered-tag check is skipped when `config.tags` is a `Withheld`
  (spec 1.6: a broken key is handled as an undecided one).
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
  the six commands of AC 14 exit 0, `tcw work show` printing `lib`'s item.
- AC 15, both files (`parents: notalist`; not valid YAML), and TCW-108's AC
  31 test passing unchanged.
- AC 29, with two real git repositories, as TCW-108's AC 26 test builds them.
- `tcw capabilities drift` in AC 14's layout exits 7 naming `(work.jira)`
  (spec defect 2: it lists completed items through the backend), and in AC
  13's layout exits 0.

**Changes**

- `tcw/config.py`, `load_config`: every source not here is a **gap**, at its
  position. During the fold, each declaration that replaces a key of the key
  table (`known_keys()`, restricted to `work.tags` and `work.jira`'s keys)
  whole is recorded with its position. After the fold, a key is
  **undecided** by choice 4; `work.jira` only in Jira mode (1.5); a mapping
  when any key under it is undecided. An undecided key is withheld with
  `registry.unavailable(<P>, <the gap>, f"configuration ({key})")` (spec 3.3);
  undecided wins over broken for the same key (spec 1.6). `Config` keeps, for
  `tcw validate`, the gaps that withheld something (`Config.gaps_withholding`).
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
  finding made for each project in `effective(root).gaps_withholding()` gains
  `; could not check the configuration inherited from it`, after any row (c)
  suffix, once (spec 3.6).
- TCW-108's tests of AC 20 and AC 31 that compare the finding's whole text, if
  Step 0 found any, are amended to the new text and listed with Design 3.6.

**Reading every failure**, as in 7a: the failures expected are the tests of
Step 0's list 1 whose parent passes `config` and is missing or unreadable, and
the TCW-108 tests of Step 0's list 2. Each change is listed with its rule.

**Proves it:** the tests above; `tests/test_parent_links_cli.py` and
`tests/test_parent_links.py`; the full suite; `compare_outcomes.py` against
Step 7b's record with an empty allowed list; the inventory against Step 0's.
**Mutation check**, recorded and reverted: with `Withheld` replaced by an
empty tuple for `work.tags` (an undecided key read as "no tags"), AC 13's
`tcw work tags list` and `tcw work new y --tag t` tests go red, and the
reason read is the exit code 0 or 3 in place of 7.

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
- AC 25, AC 28.
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
    `Config.problems` of every configuration loaded (spec 4.4), each once per
    command.
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
AC 10's first layout (if not already written at Step 7b). Every existing test
of the file passes unchanged (AC 27).

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
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change] | yes | Written, under Added (`INHERITED_KEYS`, `tcw/config_keys.py` with `known_keys`, `override_name`, `decode_key`, `read_overrides`; the `environment` layer; `Withheld`, `Config.withheld`, `Config.require`, `Config.inherited_problems`, `Config.gaps_withholding`, `Config.sources`, `Config.personal_variables`; `ProjectRegistry.source_entries`, `SourceEntry`, `ProjectRegistry.unavailable`; `SetList(inherit=)`; `external_stages_of`), Changed (`load_config` folds the configuration sources; `Origin` carries `project`, `variable`, `position`; `inherit: true` accepted in `work.tags`; `null` at `work.tags` and `work.jira` removes; `_allowed`'s voice; `parse_jira_config(undecided=)`; `parse_work_config(withheld=)`; `validate_changes` reads the tags only when one is added; `open_backend` requires the inherited keys in Jira mode; the commands that no longer open the store; `resolve_item` for another project's item; `tcw config show`'s exit codes and labels; `tcw work tags add` and `rm`; `_cmd_validate`'s suffix; an ancestor's unreadable shared file is unreadable, not a graph problem; `/api/project`'s `tags`) and Internal (the suite strips override variables). |
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

- **TCW-112:** `source_entries` and `unavailable(..., subject)` are the
  non-raising form of `sources` and the one place its messages are built; an
  ancestor whose shared file cannot be read is unreadable in the `ancestor`
  and `outside` roles (Step 4); `taxonomy.extends` and `capabilities.extends`
  are in `known_keys()` and come out when TCW-112 removes them.
- **TCW-113:** a project read for itself is `load_config(root,
  personal=False, registry=<the command's registry>)`.
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
- **TCW-99:** the departures the spec's Notes list, and the two places the
  plan found the spec's command list incomplete (spec defects 1 and 2 below).

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
| 12 | 7a |
| 13 | 6 (the store is not opened, tags read only when applied), 7c |
| 14 | 6 (the six commands), 7c (exit 7, no request, `tcw validate`) |
| 15 | 4 (registry, the unreadable file), 7c (commands, `tcw validate`) |
| 16 | 7a, 7c |
| 17 | 9 |
| 18 | 3 (the editor), 10 |
| 19, 20, 21 | 2 (rules), 8 (commands) |
| 22, 23 | 2 (rules), 8 (commands) |
| 24, 25 | 8 |
| 26 | 1 |
| 27 | 8 (commands, the single project), 7a and 8 (`tests/config/` passing, the one listed change from Step 5) |
| 28 | 8 |
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
- 6→7a: runnable; Step 6 changes only which code opens the store and when the
  tags are read, and nothing is withheld yet, so every command answers as
  before.
- 7a→7b: runnable; 7a's interim rules keep every 3.x outcome for a gap
  (nothing contributed) and make an inherited problem stricter, not looser;
  the failures 7a reads are only tests whose parents now pass a value.
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

## Spec defects found while planning

1. **Design 3.4's list of commands that must stop opening the store is
   incomplete.** `tcw work path` with no item opens it (`tcw/work/cli.py:318`)
   to print the work path, which is not inherited; and `tcw/refs.py:139` and
   `reference_resolver` (`tcw/work/open.py:210-241`) build a Jira-mode backend
   to answer a reference that they then answer from the item folders. With
   them unchanged, a Jira-mode project with an undecided `work.jira` would
   exit 7 on `tcw work path`, on `tcw validate`'s reference check, and on any
   `tcw taxonomy` or `tcw capabilities` command that checks a `tcw://` work
   link, which Design 3.4's last paragraph says are never stopped. The plan
   covers all three in Step 6 (choice 8); the spec's Risks bullet ("six
   places") and Decision 19's list could name them.
2. **`tcw capabilities drift` reads `work.jira` in Jira mode.** It lists the
   completed items through the backend (`tcw/capabilities/cli.py:183-218`),
   which in Jira mode asks Jira, so it needs every Jira setting and stops
   with exit 7 when `work.jira` is undecided. Design 3.4 says every
   `tcw capabilities` command is never stopped. The plan treats it as row (a)
   and tests it (Step 7c); the spec's sentence needs that exception.
3. **"No TCW-108 criterion or test changes" (Design 3.5) holds for the `tcw
   work list` halves only.** TCW-108's AC 20 and AC 31 also run `tcw validate`
   with a missing or unreadable parent that passes `config` and a child that
   sets no `work.tags`; by this spec's 3.6, their `unresolved` finding gains
   `; could not check the configuration inherited from it`. Their criteria
   ask for "exactly one finding naming `core`" and "containing" a phrase, so
   they hold; a test that compares the whole text would not. Step 0 checks,
   and Step 7c amends under Decision 24.
4. **Design 1.6's unreadable shared file "when it is not the active
   project"** reads as covering descendants too, while TCW-108 Design 6.6,
   which it extends, applies its rule to ancestors and projects read only for
   a lookup and keeps a descendant's committed problems as graph problems.
   The plan builds it for the `ancestor` and `outside` roles (choice 7); the
   spec could say which.
