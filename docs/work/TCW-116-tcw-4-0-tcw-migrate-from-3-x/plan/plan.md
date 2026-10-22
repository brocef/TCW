# Plan — TCW 4.0: `tcw migrate` from 3.x

All work is on the `v4` branch, in the worktree `.claude/worktrees/v4`, with
its own virtual environment (`.venv/bin/pytest`, `.venv/bin/tcw`). This item
is built last of TCW-106 to TCW-115, in the landing order 106, 107, 110, 108,
111, 109, 112, 114, 113, 115, so it plans from the state their final plans
leave. Code those items create is cited by plan step and name
(`P10n:L` is line L of that item's `plan/plan.md`, `S10n:L` of its
`spec/spec.md`); code that exists today is cited at `b2fa5810` (TCW-107 is
landing while this plan is written), and the 3.x code migration copies is
cited at tag `v3.0.2` (spec, "Citations at `v3.0.2`"). Step 0 re-finds every
citation once they have all landed. Revised on 2026-10-22 after the plan's
review; "Revision 2" at the end lists what changed and why. "Design n", "Cn", "An", "Bn", "Dn", "Pn" and "criterion n"
are this item's spec.

**Which `tcw` runs what.** The lifecycle of this repository is driven by the
`tcw` first on `PATH`, the primary checkout's editable install of `main`
(3.0.2), which reads this repository's 3.x records. Those records stay 3.x on
`v4` (Design 9.1). The `v4` code runs only in the suite, whose projects are
under `tmp_path`, and in scratch clones and throwaway folders under the
session's scratchpad (Steps 14 and 25). Never `.venv/bin/tcw migrate` in the
worktree or in the primary checkout, never `.venv/bin` first on `PATH` in a
shell that runs a lifecycle command, and never a real run with Jira
credentials set except `--dry-run` (criterion 55). The `v4` `tcw` is always
run by its full path; a bare `tcw` is the lifecycle's 3.0.2. Beyond these
rules, the code itself keeps `--no-jira` off Jira (Decided 19), and every
fixture's Jira `site` is `https://example.invalid`, a name that can never
resolve, so a test that escaped the fake could send no credentials
anywhere. While `tcw/` is being
changed in the worktree, the lifecycle is worked by hand, as CLAUDE.md says.

**The two parts.** The spec builds the engine first (part 1: one project, its
files and its Jira tickets, `--no-jira`), then related projects (part 2).
Steps 1 to 14 are part 1, and end with the engine proven on clones of this
repository (Step 14). Steps 15 to 25 are part 2. Steps 26 to 29 close the
item. Until part 2 lands, any 3.x form only part 2 converts is B5 (spec, "The
two parts"), so a project needing part 2 is refused, never half converted.
The suite passes at the end of every step.

## What this plan relies on

From the earlier items, by name (Step 0 confirms each):

- **TCW-106:** `tcw/project_files.py`: `SENTINEL`, `LOCAL_SENTINEL`,
  `LEGACY_SENTINEL`, `CONFIG_NAME`, `LOCAL_CONFIG_NAME` (`:31-38`),
  `_RENAMED_KEYS` (`:55`), `find_marker` (`:96`), `legacy_message` (`:122`),
  `version_line` (`:132`), `version_problem` (`:142`), `without_version`
  (`:164`), `key_problems` (`:182`); `refuse_legacy_project`
  (`tcw/store/fs.py:318`), `ignore_personal_files` (`:229`), `git_root`
  (`:248`); `tests/projectfiles.py` (`write_config`, `_versioned`).
- **TCW-107:** `MANIFEST`, `LOCAL_MANIFEST` (`tcw/project_files.py:41-44`);
  `tcw/store/manifest.py`: `parse_manifest(mapping, file, *, personal)` and
  `ManifestEntry` (P107 Step 1); `FsProjectRegistry.project_folder`
  (`tcw/store/project.py:1241`), `_locate` (`:1508`), `_search` (`:270`),
  `_manifests_of` (P107 Step 3); the line `/tcw-manifest.local.yaml` in
  `.tcw/.gitignore` (S107 Design 1.9); `write_manifest` (P107 Step 2).
- **TCW-110:** `tcw/ids.py`: `FullId`, `parse_full_id`, `parse_stored`,
  `looks_full`, `parse_address`, `FolderAddress`, `is_3x_address`,
  `ThreeXReference` (P110 Step 1); `store_location` (P110 Step 13);
  `_store_overlaps` (P110 Step 14); `_store_location_problems` (P110 Step
  12); the Jira `list` warning for 3.x `TCW Item` values (P110 Step 5); the
  guard `tests/test_identifier_sweep.py` (P110 Step 15, P110:1189-1196),
  which this plan gives an exemption (Decided 18).
- **TCW-108:** `tcw/store/links.py`: `parse_parents`, `parse_children` (P108
  Step 1); `tcw/store/base.py`: `ParentLink`, `LoadOrder`, `find_loop`,
  `load_order_of`, `passing`, `loop_message` (P108 Step 2);
  `InheritedUnavailable`, exit 7 (P108 Step 3); `translate_projects`, which
  P108 Step 8b deletes (its parent commit holds it, P108:1024).
- **TCW-109:** `tcw/config_keys.py`: `known_keys`, `override_name`,
  `read_overrides` (P109 Steps 1-2); `INHERITED_KEYS`; `SetList(inherit=)`
  (P109 Step 3); `parse_jira_config(undecided=)` (P109:1334).
- **TCW-111:** `tcw/object_folders.py`: `STATE_FILES`, `LEGACY_STATE_FILES`,
  `RESOURCES`, `DESCRIPTION`, `fixed_files`, `fixed_folders`,
  `reserved_names`, `walk`, `read_state`, `state_text`, `exact_path`,
  `folder_parent` (P111 Step 1); `ID_LIMIT` and `length_problem` in
  `tcw/ids.py` (P111 Step 2); `tests/statefiles.py` (P111 Step 3); the guard
  `tests/test_object_folder_sweep.py` (P111 Step 17, P111:1387-1398),
  exempted by Decided 18.
- **TCW-112:** the combined view (P112 Step 7); `overrides:` reported as an
  error (P112 Step 9); the opaque `id` removed, row k applied to
  capabilities (P112 Step 10); an object that overrides nothing must be
  complete (P112 Step 11); `_CAP_STRUCTURAL`; the guard
  `tests/test_no_3x_inheritance.py` (P112 Step 20, P112:1802-1810),
  exempted by Decided 18.
- **TCW-113:** `--scope up` on the tree listings (P113 Step 9).
- **TCW-114:** `_enter` and `_check_here()` in `tcw/cli.py` (P114 Steps 5-6);
  `tcw/reference_fields.py` (`FIELDS`, `fields_of`, `values`, P114 Step 9);
  `tcw/rewrite.py` (`rewrite_yaml`, `rewrite_references`, `mentions`, P114
  Step 16) and `links_outside_code` (P114 Step 11); `tcw/move.py`
  `move_object` and `move_object_folder` (P114 Step 17);
  `tests/move_stops.py` (P114 choice 10, P114:185-226; defined there as
  driving a command, so Step 0 checks whether it also takes a callable, and
  Step 3 adds that form if not);
  `tests/processes.py` (`allowed_read_only_git`, `recorded_processes`,
  P114 Step 1); the fake Jira's `fail_edit`, `before_request` and `hide`
  (P114 Step 12); the Jira `move` that refuses a ticket holding a 3.x
  `TCW Item` (P114:1489-1493).
- **TCW-115:** `tcw project provision` (`tcw/provision.py`, P115 Step 12),
  standard error only for its output; the stale `tcw init --id` message
  (`tcw/store/project.py:791`) replaced (P115:897).
- **Today's code** (at `b2fa5810`): `_atomic_write_all`
  (`tcw/store/fs.py:1157`); `LOCAL_CONFIG_RULE` and `LOCAL_MANIFEST_RULE`
  (`tcw/store/fs.py:204-205`); `tcw/store/config_edit.py`
  (`ConfigEditRefused` `:47`, `read_text` `:95`, `edit_text` `:126`,
  `_verify` `:542`); the Jira backend's `rename`
  edit (`tcw/work/jira/backend.py:891`), `metadata` (`:248`), `list`
  (`:433-483`); the client's `search` (`tcw/work/jira/client.py:242-267`,
  page size `PAGE = 100`, `:39`), `edit_metadata` (`:370`), `edit_issue`
  (`:404`); `jql.item_query` (`tcw/work/jira/jql.py:38`); the fake Jira
  (`tests/work/jira/fake.py`: `off_edit_screen` `:172`, `unreachable`
  `:242`, `unauthorized` `:245`, `page_size` `:166`, `_editmeta` `:560`);
  exit codes (`tcw/exit.py`).

## Decided while planning

Each decided by this plan, preferring the simpler and safer option.

1. **One package, `tcw/migrate/`**, used by nothing but `tcw migrate`
   (Design 8.2): `cli.py` (the command), `model.py` (the plan's records),
   `legacy.py` (the 3.x readers, restored from tag `v3.0.2`), `plan.py`
   (reads everything and makes the plan), `config.py` (C1-C8), `stores.py`
   (C9-C15), `references.py` (C16), `jira.py` (Design 5's glue),
   `family.py` (part 2: related projects), `execute.py` (phases A-F),
   `progress.py` (the progress record), `record.py` (the migration
   record), `report.py` (the lines printed). Reason: Design 8.2 puts the 3.x
   readers in one place, and the litmus test puts the conversion in the
   deployment layer.
2. **The 3.x readers are copied from tag `v3.0.2`, not rewritten**
   (`git show v3.0.2:<file>`), each function with a comment naming the
   tag, file and line it came from, trimmed only of what reads 4.0 files or
   opens a backend. Not from `32c510f0`, which already holds TCW-106's
   changes to `load_config`, `parse_connected_entry` and the personal layer
   (the review's M2; checked: `git diff v3.0.2 32c510f0 -- tcw/` changes 17
   files, `git diff v3.0.2 main -- tcw/` is empty). Each copy is renamed
   with a `_3x` ending, so no 4.0 name is defined twice. Reason: the conversions must read the files exactly as
   3.x read them (Problem 4), and a copy is checked against 3.x's own output
   (Step 2's recorded listings). That includes 3.x's own configuration
   layering (`_merge` and `PERSONAL_KEYS`), since 4.0's merge now removes a
   value at `null` (TCW-109) and would change what the 3.x layers mean.
3. **The 3.x behaviour the copies must match is recorded once, from a
   pinned 3.0.2, by a script run by hand, whose output is committed.**
   `tests/migrate/record_3x_listings.py` is a script, not a test: pytest
   collects only `test_*.py` and `*_test.py` files (`pyproject.toml` sets
   `testpaths` and no `python_files`), and nothing in the suite imports or
   runs it. Its output, `tests/migrate/golden/<fixture>.json`, is committed,
   and the suite reads only those files. The script:
   - **needs network access, or stops.** Before anything else it fetches
     `https://pypi.org/pypi/tcw-cli/3.0.2/json` with the environment pip
     will use, with a 10-second timeout. If that fails, it stops with exit 1
     and `record_3x_listings: cannot reach PyPI (<error>); run it with
     network access and with no proxy that points nowhere`, having made
     nothing. So pip is never run behind a dead proxy: a shell that set
     `https_proxy=http://127.0.0.1:9` (as Step 14's proof does) stops here
     rather than at a failed install;
   - makes its own throwaway virtual environment in a new
     `tempfile.mkdtemp()` folder (`python -m venv <tmp>/venv`, then
     `<tmp>/venv/bin/pip install tcw-cli==3.0.2`). pip runs with the
     caller's environment and never with the dead proxy, which is set only
     for the `tcw` runs below. It then checks that
     `<tmp>/venv/bin/tcw --version` prints exactly `tcw 3.0.2`, saves
     `<tmp>/venv/bin/pip freeze` (PyYAML is not pinned by `tcw-cli`), and
     runs only that `tcw`, by its full path, never the one on `PATH`;
   - **records from fixtures only.** It builds each fixture with
     `tests/migrate/fixtures.py` in another new `mkdtemp()` folder outside
     every project. Before each command it checks that the nearest
     `tcw-config.yaml` above the command's folder is the fixture's own, and
     stops if not. It never runs in this repository;
   - runs each `tcw` with an environment it builds: `XDG_CONFIG_HOME` and
     `XDG_CACHE_HOME` set to the fixture's own folders (F-single has a
     user-wide file, F-full's `lib` a 3.x cache clone), every `TCW_*`
     variable and the two credential variables removed, and `https_proxy`
     and `HTTPS_PROXY` set to `http://127.0.0.1:9`;
   - runs `tcw taxonomy list --json`, `tcw capabilities list --json`,
     `tcw capabilities show <path> --json` for each override and each
     object a reference names, and `tcw validate`;
   - writes each output with the fixture's absolute folder replaced by the
     placeholder `<fixture>` (and its `XDG_*` folders by `<config>` and
     `<cache>`), so that no temporary path is saved;
   - saves, in each golden, the `tcw --version` line, the `pip freeze`
     lines, the date, and `fixture-digest`: the SHA-256 of the fixture's
     files, each relative path and its bytes in sorted order, `.git/`
     left out.
   A suite test, `tests/migrate/test_goldens_current.py`, builds each
   fixture in `tmp_path` and checks that its digest, computed the same way,
   equals its golden's `fixture-digest`. A changed fixture therefore fails
   with `golden/<fixture>.json was recorded from another fixture; run
   tests/migrate/record_3x_listings.py`, rather than being compared silently
   against an old recording. That matters most after TCW-118, when no 3.x
   `tcw` is on this machine. The digest function lives in
   `tests/migrate/fixtures.py`, so the script and the test share it.
   Decided by the dispatching session, 2026-10-22 (the re-check's D2
   section and S6): a script whose output is committed keeps the suite
   offline; the network check is the one way to keep pip away from a dead
   proxy without the script editing a caller's settings. Reason: the lifecycle `tcw`
   becomes 4.0 at TCW-118, after which nothing on this machine could
   re-record a golden when a fixture changes (the review's D2, decided by
   the dispatching session, 2026-10-22), and the shell's own variables
   would otherwise change 3.x's answers (S6). Work items are compared by
   their folders (Design 4.1), not by a 3.x listing, since the fixtures'
   tickets live in the in-process fake. 3.x prints no cache folder and no
   routing of a `capabilities.yaml` entry to a child, so those copied
   readers are checked against expected values written by hand into the
   fixture from the tag's code (the review's question 1).
4. **The progress record is YAML** with `tcw-version` first, written with
   `yaml.safe_dump(sort_keys=False, allow_unicode=True, width=float("inf"))`,
   which round-trips any text exactly; a file's bytes are stored as its text
   (every file migration writes is a UTF-8 store, configuration or Markdown
   file; one that is not valid UTF-8 is B14). Every planned input is read
   with `config_edit.read_text` (no line-ending translation,
   `tcw/store/config_edit.py:95-101`), never `Path.read_text`, so a file with
   Windows line endings keeps them on every untouched line (the review's
   S10). Digests are SHA-256 of the bytes on disk. It is written atomically
   and read back before phase B.
5. **Inside phase A the order is: the record, the ignore line, then the
   progress record** (spec Design 2.4, now written this way), so the
   progress record, which holds personal values, is never on disk without
   its ignore line. A stop before the progress
   record is P2: the next run plans again and finds the first two writes
   already equal to its plan, so it does not write them again.
6. **A later step that writes a file an earlier step wrote records the
   earlier step's output digest as what it expects to find.** So phase D's
   whole `.tcw/.gitignore` expects phase A's version, and phase C's state
   file in a folder phase B moved expects the moved bytes at the new path.
7. **Every file write goes through four functions in
   `tcw/migrate/execute.py`:** `_write` (one file, by
   `fs._atomic_write_all([(path, text)])`, called through the module
   (`from tcw.store import fs`), never imported by name, so that
   `tests/move_stops.py`'s patch of `tcw.store.fs._atomic_write_all` reaches
   it and each write counts once; then read back and compared), `_move`
   (`os.rename`, nothing else: on `EXDEV`, the cross-device error, it raises
   `MigrateStopped` with spec Design 2.5's message and copies nothing),
   `_delete` (`Path.unlink`) and `_mkdir` (`Path.mkdir(parents=True,
   exist_ok=True)`). Reason: `tests/move_stops.py` counts exactly these
   primitives (P114:187-209), so each Design 2.5 write is one counted write
   and every change is explained. move_stops also counts `mkdir`, so the
   stop sweep stops at more points than Design 2.5 lists, never fewer.
   Ticket edits go through `set_item_values` (Decided 10), and the fake's
   `PUT` is counted by the same helper.
8. **The planned files are checked as text by 4.0's own parsers.** Where a
   4.0 parser reads only from a path (`tcw.config._read`,
   `object_folders.read_state`), Step 10 splits out a pure function of text
   (`parse_project_file_text`, `parse_state_text`) that the path reader then
   calls, with no change of behaviour. Reason: Design 2.1 forbids reading
   planned files from disk, and a second parser would drift.
9. **The editor is extended, not replaced** (Design 2.8), and the extension
   is larger than three small edits. Today's editor addresses exactly two
   levels, `section.key`, with string or list-of-string values
   (`tcw/store/config_edit.py:53-81`, `intended` at `:104-122`). The
   conversions need: `RenameKey(key_path, new)` (C2) at any depth, through
   list indexes, with YAML aliases resolved to the one place the key is
   written (this repository's `not_tags` sits at
   `work.stages.spec.prompt[4].when.not_tags`, in a list whose first entry
   is an alias, `*pull-text`, `tcw-config.yaml:101-112`);
   `RemoveTop(key)` (`projects`, `id`, `overrides`); and `SetTop(key,
   value)` whose value may be a list of mappings (`parents: [{id: core,
   inherit: [taxonomy]}]`), plus `parent` and `name` in state files. So
   `intended` and `_verify` are generalised to key paths of any depth and to
   values that are mappings and lists of mappings, and `edit_text` gains a
   `versioned=True` mode that puts `version_line()` first. Reference values
   (C16) are replaced by TCW-114's `rewrite_yaml`, generalised from a list
   of identifier pairs to a function `replace(field, value) -> str | None`,
   the pair form kept as a wrapper that still returns everything it
   returned before: per file, the fields changed, those already naming a
   new identifier ("already done", P114:1286-1288), and `mentions`
   (P114:160-163). **Order on one file:** `edit_text`'s structural edits
   first, checked by `_verify`; then `rewrite_yaml` on that output; then the
   final text is parsed by `parse_state_text` or `parse_project_file_text`
   (B3) and compared with the mapping the plan intends, so the text written
   is the text checked (the review's S7).
10. **The Jira half is two methods of `JiraBackend`, used only by
    `tcw migrate`**: `item_values()`, the paged search of Design 5.1
    returning `(key, TCW Project value, TCW Item value)` for each ticket,
    and `set_item_values(pairs)`, which for each `(key, old, new)` reads the
    ticket's `TCW Item`, edits it to `new` with
    `client.edit_issue(key, {item_field: new})` (the request
    `backend.py:891` sends) only when it still holds `old`, counts it done
    when it holds `new`, and lists it otherwise. Spec Design 5.4 now names
    these two methods. Neither is one of the twelve operations.
11. **The Jira backend is built from the `work.jira` of the project's own
    layers, in whichever form they are on disk** (spec Design 5.1, revised
    for the review's M4). `legacy.own_jira_layers(root)` reads the shared
    layer from the root `tcw-config.yaml` when present, else from
    `.tcw/tcw-config.yaml`; the user-wide file; and the personal layer from
    the root `tcw-config.local.yaml` when present, else from
    `.tcw/tcw-config.local.yaml`; each read raw, only its `work.jira` kept,
    merged by the copied 3.x `_merge` and `PERSONAL_KEYS`, with no parent
    and no environment override. `jira.py` builds `JiraBackend(project,
    work_path, work_config, jira)` with `jira` from
    `parse_jira_config(<that work.jira>)` and `work_config` the defaults,
    `parse_work_config({})[0]`. The two methods of Decided 10 read only
    `self.jira`, `self.project`, `self.client` and the field ids
    `metadata()` finds from `jira.fields`, never `self.config` or
    `self.layout`, and their docstrings say so. So no work section is read
    for them, and a 4.0 project whose `work` keys come from a parent
    (TCW-109) plans the same tickets as one that sets them itself (decided
    by the dispatching session, 2026-10-22, the re-check's S7: reading the
    own `work` section would have been incomplete there, and nothing needs
    it). Step 9 tests it: the same tickets and edits with `work_config`
    built from F-single's whole `work` section and from the defaults. A
    missing required key or a
    refusal of `parse_jira_config` is a Jira failure while planning (spec
    Design 2.3): exit 1, nothing written, the file and key named with
    `--no-jira`. So the re-run after a phase F stop (P11) and the plain run
    after `--no-jira` (P12), when the root files are gone, read `.tcw/`, and
    a user-wide `not_tags` (A5) never stops the ticket half.
12. **`tcw -C` with an address still checks the starting folder.** `migrate`
    skips the final `_check_here()` after the last `-C` target, but an
    address target keeps the check TCW-114 makes before resolving it (P114
    Step 6), since an address can only be resolved from a 4.0 project.
    `tcw -C <path> migrate` reads nothing at the starting folder.
13. **A12 is defined against 3.x's own `tcw validate`** (spec Design 2.9,
    the review's D3). At run time: each report records the 4.0 finding it
    predicts, by file and kind (A2 predicts "state file under
    `resources/`", A5 the user-wide `not_tags`, and so on); a finding equal
    to a prediction belongs to that report; every other finding is listed
    as A12. A finding in the same file but of another kind is not absorbed.
    In the tests: each fixture's golden holds 3.x's `tcw validate` output,
    and each fixture carries a fixed list, written by hand once, of the 4.0
    counterpart of each of those findings; criterion 51 requires the run's
    A12 list to equal it, so a finding a conversion caused fails the test.
    The findings come from `collect_findings(root, remote=False, work=…)`,
    split out of `_cmd_validate` (`tcw/cli.py:208`) in Step 10 with no
    change of behaviour; `remote=False` keeps the check off Jira, `--no-jira`
    or not. `work` is `False` exactly when the run was given `--no-jira`
    and the project's work is kept in Jira. Then `validate`'s work-store
    checks are skipped: its section (e), `_work_findings`
    (`tcw/validate.py:455`), calls `open_backend` (`:574`), which builds
    `JiraBackend` (`tcw/work/open.py:83-84`) and so `JiraClient`
    (`tcw/work/jira/backend.py:228`). The summary says `work store not
    checked after the run (--no-jira): run 'tcw validate' to check it`
    (spec Design 1.1; decided by the dispatching session, 2026-10-22, the
    re-check's N1: the simplest change that keeps "never builds" true).
    `validate(project_root, *, work=True)` gains the keyword, and every
    other caller keeps the default.
14. **Line forms** (Design 1.5), relative to the active project's root
    (absolute for a path outside it): `write <path>: C9, C10, C16`,
    `move <old> -> <new>: C13`, `delete <path>: C9`,
    `edit <KEY>: C17 TCW Item: <old> -> <new>`; a dry run puts `would `
    first. Reports: `<An|Dn> <where>: <text>` under `needs attention:` and
    `reads differently in TCW 4:`; blockers `<Bn> <where>: <why>; <what to
    do>` under `refused:`. Criterion 6's test parses these.
15. **The proof clones use one editable install** of the first clone, in a
    virtual environment outside every clone. The three clones hold the same
    code, so the second and third running the first's code changes nothing,
    and the suite in the first clone runs its own `tcw` as
    `tests/test_suite_runs_its_own_tcw.py` requires.
16. **A merge in a proof clone is expected to be a fast-forward**: today
    `git merge-base main v4` is `main`'s head (checked 2026-10-22). The
    implement round records whether it was. If `main` has moved and the
    merge conflicts, it is resolved in that clone only and every file
    resolved is listed; nothing is pushed (the review's D4: a rule for each
    folder can wait for a real conflict).
17. **The part-1 refusal of part-2 forms is one function**,
    `part_two_forms(read) -> list[Blocker]` in `tcw/migrate/plan.py`, giving
    B5 with the reason `tcw migrate does not convert <form> yet`. Its forms,
    and the step that removes each: `projects:` (Step 18, once manifest
    entries exist, never before, so a converted parent is never left
    without the entry that locates it: the review's M5), `taxonomy.extends`
    and `capabilities.extends` (Step 19), a store path leading out of the
    project and a store with only a `repository` (Step 20), `overrides:`
    (Step 21), and a reference prefixed with another project's ID or a
    cross-project `blocked-by` (Step 22, which deletes the function). Each
    of those steps deletes or changes that form's part-1 refusal test,
    listed in the step's allowed list.
18. **The siblings' guard tests get named exemptions** (spec Design 8.2,
    the review's M1). Each guard's scan is a function of a root folder (as
    the handoffs to TCW-110, TCW-111 and TCW-112 ask; reshaped here with no
    change of findings if it landed otherwise), and each holds its
    exemption in one constant matched by whole path parts:
    `tests/test_identifier_sweep.py` and `tests/test_object_folder_sweep.py`
    exempt `tcw/migrate` (both already skip test files);
    `tests/test_no_3x_inheritance.py` exempts `tcw/migrate` from its rules
    over `tcw/` and `tests/migrate` from its rule over test files. Each
    exemption comes with a test in that guard: the forbidden text in a
    temporary tree at `tcw/migrate/x.py` (or `tests/migrate/test_x.py`)
    gives no finding, and at `tcw/migrate_x.py`, `tcw/store/x.py` and
    `tests/migrate_x/test_x.py` gives one naming the file (criterion 67).
    Each is added in the step that first puts such text there: Step 2 for
    TCW-110's and TCW-111's (`legacy.py` copies `parse_tcw_uri` and walks
    for `meta.yaml`) and for TCW-112's test-file rule (the fixtures write
    `id: cap-`); Step 15 for TCW-112's `tcw/` rules (the override match's
    copy names `_apply_override`).
19. **`--no-jira` never builds a Jira client** (spec Design 1.1, the
    review's S1, the re-check's N1, N2 and S8). Three places could build
    one, and each is closed:
    - **Planning.** `tcw/migrate/jira.py` is the one module of the package
      that imports from `tcw.work.jira`. One function imports it:
      `plan_jira_half(root, project_id, *, jira_backed, no_jira) -> JiraHalf
      | None` in `tcw/migrate/plan.py`. It returns `None` before the import
      when `no_jira` is set or `jira_backed` is false. Otherwise it builds
      the planning backend over `_ReadOnlyClient`, calls `plan_tickets`
      (the search and B16), and returns `JiraHalf(tickets, blockers,
      apply)`. Both runs call it, before any write. `make_plan` calls it for
      a fresh run, with the ID and backend it read. `cli.run` calls it for
      a run that follows a progress record, with the ID and backend the
      record holds (Step 3's `project` and `work-backend` fields). That call
      does not go through `make_plan`, so criterion 60's patch of
      `make_plan` still shows the record is followed.
    - **Phase F.** `JiraHalf.apply` is a function `jira.py` returns. When it
      is called, it builds the phase F backend over the plain client and
      calls `apply_tickets`. `execute.py` calls `half.apply()` in phase F
      and imports nothing from Jira. With no half there is no phase F.
    - **The check after the run.** It is called with `work=False` under
      `--no-jira` for a Jira-backed project (Decided 13).

    `_ReadOnlyClient(client)` is an allowed list. Its `__getattr__` passes
    on only `search`, `issue`, `edit_metadata`, `project`,
    `create_metadata` and `myself`, the reading calls `metadata()`,
    `item_values()` and B16 make (Step 0 confirms the list against those
    three as landed). Any other name raises `AssertionError("tcw migrate:
    <name> is not allowed while planning")`: the six writing calls,
    `_request`, `_payload`, `_json`, `config`, and any writing call a later
    item adds. The backend already takes its client as an argument
    (`JiraBackend(..., client=)`, `tcw/work/jira/backend.py:219-228`), so
    planning builds `JiraBackend(..., client=_ReadOnlyClient(JiraClient(jira)))`
    and `JiraHalf.apply` a second backend over the plain client. The static
    check of criterion 66 reads the package's syntax trees. Of
    `tcw/migrate/*.py`, only `jira.py` names `tcw.work.jira`. The only
    import of `tcw.migrate.jira` in the package is inside `plan_jira_half`.
    Decided by the dispatching session, 2026-10-22: one function at one
    point serves both kinds of run, so one guard covers both.
20. **No new test reads this repository's root `tcw-config.yaml`** (spec
    Design 8.4, the review's M6). Step 4 saves
    `tests/migrate/data/repo-tcw-config-3x.yaml`, a byte-for-byte copy of
    the root file at the commit Step 0 starts from, and
    `tests/migrate/data/README.md` naming that commit; criteria 15 and 63
    and Step 4's anchor test read it.
21. **An operating-system failure inside the executor becomes
    `MigrateStopped`**, so `_dispatch`'s one-line `OSError` handler
    (`tcw/cli.py:494-498` at `5a9ca9b7`) never swallows the run-again
    message. Step 3 tests it with a `PermissionError`, which is what Step
    14's `chmod` stop produces.
22. **The git rule for criterion 4 is this item's own.** TCW-114's
    `allowed_read_only_git` (`tests/processes.py`) is left as it is; the
    migrate test composes `rev-parse`, `ls-files`, `status` (only with
    `--no-optional-locks`) and `check-ignore` from the recorded calls
    itself (the review's S5).
23. **Migration's messages pass `tests/test_static_guards.py`** (spec
    Design 8.6, the re-check's N3). The stopped run says `do not save these
    files in version control until 'tcw migrate' finishes`. A6, A7 and B13
    are worded as Design 8.6 gives them. B5's message is built by one
    function, `family.absent_project_message(project, folder, repository)`,
    which `EXEMPT` names: `("migrate/family.py", "absent_project_message")`,
    with the comment `# TCW-116 Design 6.5, 8.6: B5 names the one command
    that fetches a project here, since every tcw command is refused in a
    3.x project`. The entry is added in Step 16, which creates the function.
    `tests/work/test_git_write_scan.py`'s `SCANNED` gains
    `*(PACKAGE / "migrate").rglob("*.py")` in Step 1, which creates the
    package. Decided by the dispatching session, 2026-10-22: the rewording
    keeps each message's meaning and the guard's strictness, and the one
    exemption covers a command line that has no other wording.
24. **Test text that TCW-112's test-file rule forbids is written only under
    `tests/migrate/`** (the re-check's S3). That text is `overrides:`,
    `extends:` under `taxonomy:` or `capabilities:`, and `id: cap-`. So
    Step 4's editor tests of `RemoveTop("id")` and `RemoveTop("overrides")`,
    and all of Step 23's cases (one is a 3.x reader holding
    `overrides: M/cap-1`), go in
    `tests/migrate/`, not in `tests/test_config_edit.py` or
    `tests/test_rewrite.py`. The editor tests outside `tests/migrate/` use
    neutral keys and values (`id: x1`, `projects:`). Decided by the
    dispatching session, 2026-10-22: the rule is TCW-112's, and the
    exemption Decided 18 gives covers that folder only.
25. **TCW-114's `tests/test_ownership_sweep.py` may gain entries** (the
    re-check's S2). Its list holds every function under `tcw/` that calls
    `add`, `set`, `update`, `remove` or `move` on a receiver it cannot
    prove to be a builtin container. Each function of `tcw/migrate/` it
    reports is added in the step that writes it, with the reason `tcw
    migrate writes files through its executor, never through a backend or
    store`. `set_item_values` is not one of the interface's operations and
    carries no `@writes` marker; its ownership rule is Design 5.1's `TCW
    Project` filter.

## The conversion safeguards

For every step that removes or rewrites existing tests (12, and each part 2
step that retires a part-1 refusal), the safeguards of TCW-107 Step 9 and
TCW-108 Steps 7-8 (P107:628-700, P108:813-832), as TCW-112 restates them
(P112:361-423). All scripts are one-off and kept in the scratchpad, never in
the repository.

- **The inventory:** `.venv/bin/pytest --collect-only -q`, and per test
  function the count of `assert` statements and `pytest.raises` blocks from
  a script walking its syntax tree. Taken in Step 0 and at the end of each
  such step: no test ID disappears and no count drops except those on the
  step's allowed list, each with its design rule.
- **The outcome record and comparison:** `.venv/bin/pytest -q
  --junitxml=<scratchpad>/outcomes-step<N>.xml` from the worktree's root,
  bare pytest as CI runs it, saved at the end of every step from Step 0;
  `compare_outcomes.py <before.xml> <after.xml> <allowed.txt>` (TCW-108's
  script, copied, or written again from P108:821-832 if gone) must exit 0.
- **A mutation check per conversion:** the code the converted tests rely on
  is broken in the named way and those tests must go red; the reasons of at
  least ten red tests across files are read and confirmed to be the broken
  behaviour.
- **Commits:** a mechanical commit by script, then hand edits, so a
  reviewer can read each alone.

## Fixtures

Built by `tests/migrate/fixtures.py` (Step 2), as literal 3.x files written
into `tmp_path`, never through 4.0 writers. A git repository is made where a
criterion names one (`git init` in the fixture folder, as
`tests/test_project_registry.py` does).

**F-single** (part 1), one project `app` keeping its work in Jira, with no
related project. What each part exercises:

| Part | Exercises |
| --- | --- |
| root `tcw-config.yaml` with comments, two anchors (`&pull`, `*pull`) and `not_tags` under a stage's `when` | C1, C2, criterion 15 |
| `work.jira.credentials.email-env: TCW_JIRA__EMAIL`; `work.tags: null`; a stage `post` running `tcw provision`; a procedure `command:` with `--blocks` | A9, D5, A13 |
| root `tcw-config.local.yaml` with `user.name`; user-wide `$XDG_CONFIG_HOME/tcw/config.yaml` with `not_tags` | C1, C7, A5 |
| root `.gitignore` holding `/tcw-config.local.yaml` | A4 |
| taxonomy: `invoice` (with `meta.yaml`), `invoice/line` (nested), `customer` (no `meta.yaml`, no `description.md`), `order` with `id: other`, `roles/admin` | C9, C11, C12, D7, A1 |
| capabilities: `cli/x` with `id: cap-1a2b3c`, `Subject: [invoice]`, `Roles: ['!roles/admin']`, `When: [conditions/online]`, `prependedDocs: [camera.md]` and a loose `camera.md`; `cli/x/y` nested; `cli/z` with no `name` and no `description.md`; `cli/w` with no `Status`; `cli/v/resources/meta.yaml` (a sample) | C9, C10, C11, C12, C13, C16, A2, A12 |
| work, Jira backend: `APP-1-a` with `item.yaml` (`ticket: APP-1`), a `capabilities.yaml` with `new: [cli/new-thing]`, `changed: [cli/x]`, `taxonomy: {new: [invoice]}`, a loose `design.md` and a loose folder `notes/`; `APP-2-b` whose `spec/spec.md` holds `docs/work/APP-1-a/design.md`, `APP-1-…/design.md` and `APP-1-.../design.md`, and `](tcw://C/cli/x)` once outside code and once inside a code span | C9, C13, C16, A3 |
| fake Jira tickets in project `APP`: `APP-1` and `APP-2` holding `app/<folder>`; `APP-3` holding `app/APP-3-gone` (no folder here); `APP-4` already `app.work/APP-4-d`; `APP-5` holding `other/APP-5-e`; `APP-6` whose 4.0 value would be 256 characters; `LIB-1` with `TCW Project: lib`; `APP-7` with no `TCW Item` | C17, A10, criteria 43-44 |
| a `README.md` outside the stores holding `docs/work/APP-1-a/design.md` | C13's "outside the stores" |

**F-single-files:** the same stores with the files backend, its items
holding `parent: app/APP-1-a` and `blocked-by: [app/APP-2-b]`, for criterion
33's files-backend half and criterion 41's work rows.

**F-full** (part 2): F-single's `app` placed in a family, built in Step 24
from the pieces Steps 16-22 add:

| Project | Where | Exercises |
| --- | --- | --- |
| `ws` | a git repository holding `app` in `ws/app`; sets `work.tags`, holds capability `cli/shared` and a `jira` block on its child entry for `app` | C3 (parent, enclosing: M6 no entry), C6, D1, D2 (`app` also has `cli/shared`), D6 |
| `core` | its own git repository at `../core`, 3.x, with `cap-…` ids and its own override | C3 upstream, C4 M1, C8 E2, C14 bare and `core/<id>`, D3 |
| `sib` | `ws/sib`, sibling of `app` | C8 E4, C14 through a middle project (`sib` overrides `core`'s capability: D4) |
| `kid` | `ws/kid`, listed as `app`'s child and extended by `app` | C8 E3, D6 |
| `lib` | named only by `repository: {url: …/lib.git}`, with its 3.x cache clone present | C4 M5, A6 (with the clone moved away) |
| `app` | `ws/app`, Jira, `work.path: ../docs/app/work` inside `ws` | C5 `..` to `tcw://ws.path/docs/app/work`, Design 6.3 |
| `app`'s overrides | `ov/login` overriding `core`'s `auth/login` by bare id; `core/billing` by `<alias>/<id>`; one already at its original's path | C14 rows of criterion 38 |

The order of a load that falls back (D8) and A7, A8, A11 are made by the
criteria's own variants (Steps 18, 19, 24), not by F-full, which has no
blocker and no fallback.

## Step 0 — start from what the earlier items left

No code changes.

1. `git log --oneline` shows TCW-106 to TCW-115 completed on `v4`;
   `git status` is clean; `git rev-parse v3.0.2` resolves and
   `git diff v3.0.2 main -- tcw/` is still empty (Decided 2).
2. **Re-find every citation** of the spec and this plan on the merged tree,
   by name, and write the new line numbers into the implement round: every
   name in "What this plan relies on"; in `tcw/cli.py` `build_parser`,
   `_dispatch`, `_check_here`, `_enter`, `_cmd_validate`, `main`;
   `validate`'s section (e) and `_work_findings` (`tcw/validate.py:455`,
   `:554`), which Step 10's `work` keyword skips; and the 3.x readers that
   Steps 2 and 15 copy, confirmed at tag `v3.0.2` from the spec's
   "Citations at `v3.0.2`" table, which is where they are copied from:
   `tcw/store/project.py:614-668`, `tcw/store/base.py:865`,
   `tcw/store/fs.py:884` (`_extends_ids`), `:1743` (`_local_slugs`),
   `:1796`, `:2191`, `:2235`, `:2238`, `:2281`, `:2324` (the match at
   `:2332`), `:2405-2420`, `:3162-3300`, `tcw/store/checkouts.py:60-127`,
   `tcw/refs.py:59-125`, `tcw/work/gates.py:331-380`, `:430-437`,
   `tcw/validate.py:48-71`, and `tcw/config.py:44` (`PERSONAL_KEYS`) and
   `:454` (`_merge`). These line numbers are the tag's (the re-check's
   S5), and the tag does not move, so they need confirming only by
   `git show v3.0.2:<file>`.
   A name that no longer exists, or behaves otherwise than this plan
   assumes, is reported to the dispatching session before Step 1, and the
   affected step rewritten in the round.
3. **The checks `_dispatch` makes before a command, as they stand.**
   Expected: `_enter` for each `-C` target, then `_check_here()`
   (`refuse_legacy_project`, `refuse_retired_config` unless the group is
   `validate`, and the configuration-problems check unless `own_config`),
   and anything TCW-109, TCW-113 or TCW-115 added there. Each is listed in
   the round, since `migrate` must skip all of them (Design 1.2, 8.1).
4. **The four parsers Decided 8 needs**: whether `tcw.config` already has a
   function of text for one project file, and `object_folders` one for a
   state file. Recorded; Step 10 splits out whichever is missing.
5. **The tests that read this repository's own records** (Design 8.4):
   `grep -rlnE "meta\.yaml|item\.yaml|STATE_FILES|LEGACY_STATE_FILES" tests`
   intersected with the files that read `REPO`/`ROOT` under `docs/`
   (`tests/test_ledger_3_0.py`, `tests/test_documented_cli_surface.py`,
   `tests/test_git_example.py`, `tests/test_require_artifact.py`,
   `tests/test_migration_guide.py`, `tests/work/test_cli_installed.py` at
   `b2fa5810`, plus whatever TCW-107 to TCW-115 added). Saved for Step 12.
6. The inventory and `outcomes-step0.xml` (the safeguards).
7. The stale message `missing project id; migrate with tcw init --id` is
   gone (P115:897); if not, Step 1 changes it to name `tcw project new`.
8. **The three guards and the stop helper, as landed** (Decided 18, S9):
   whether `tests/test_identifier_sweep.py`,
   `tests/test_object_folder_sweep.py` and `tests/test_no_3x_inheritance.py`
   scan through a function of a root folder with an exemption constant, as
   the handoffs asked; whether `tests/move_stops.py` takes a callable, and
   patches `tcw.store.fs._atomic_write_all` on the module. Each answer is
   recorded; Steps 2, 3 and 15 reshape what is missing.
9. **The tests that read this repository's root `tcw-config.yaml`**: only
   `tests/test_repo_config_pair.py` at `5a9ca9b7` (Decided 20); any other
   found is listed for Step 12.
10. **The other guards this item's code meets** (Decided 23-25): the
    `EXEMPT` set and `GIT_WORDS` of `tests/test_static_guards.py`, the
    `SCANNED` list of `tests/work/test_git_write_scan.py`, and TCW-114's
    `tests/test_ownership_sweep.py` and how its list is written. Also the
    client methods that `metadata()`, `item_values()` and B16 call, for
    `_ReadOnlyClient`'s allowed list (Decided 19). Each is recorded; a
    guard shaped differently from what Decided 23-25 assume is reported to
    the dispatching session before Step 1.

## Step 1 — the command, and what runs before it

Design 1.1, 1.2, 1.5, 1.6 (codes 0, 1, 2), 8.1, 8.6 (the git-write scan);
criteria 1, 2 (its refusal half), 3, 69 (its scan half).

**Tests first**, new `tests/migrate/test_migrate_command.py`:

- `tcw migrate --help` shows `[--dry-run]` and `[--no-jira]` and no
  positional argument; `tcw migrate x` exits 2; outside any project exits 1
  with `NO_PROJECT`'s text (`tcw/errors.py`); standard output is empty in
  every case (criterion 1).
- In a 3.x project (root `tcw-config.yaml`, no `.tcw/`), `tcw migrate
  --dry-run` is not refused (exit 0) while `tcw work list` there exits 1
  with `legacy_message` (criterion 2).
- From a 4.0 project, `tcw -C <3.x folder> migrate --dry-run` gives the same
  lines and code as the same run started in that folder (criterion 3).
- With a `.tcw/tcw-config.yaml` holding a configuration problem, `tcw
  migrate --dry-run` is not refused by it (the problems check is skipped).

**Creates** `tcw/migrate/__init__.py` and `tcw/migrate/cli.py`:
`add_subparser(sub)` registering `migrate` with `command(...)`
(`tcw/cli_help.py`), `prints="nothing; every change, report and blocker on
stderr"`, `writes="the active project's files and its tickets' TCW Item"`,
and `set_defaults(skips_checks=True, func=_cmd_migrate)`. `_cmd_migrate`
finds the nearest marker with `find_marker` (3.x or 4.0), refuses none with
`BackendError(NO_PROJECT)`, and calls `run(root, dry_run=, no_jira=)`,
which in this step plans nothing and prints `nothing to migrate`.

**Changes** `tcw/cli.py`: `build_parser` (`:356`) calls
`migrate_cli.add_subparser(sub)` beside `validate`; `_dispatch`'s final
`_check_here()` (Step 0, item 3) is skipped when `skips_checks` is set; an
address `-C` target still checks (Decided 12). `tests/test_cli_help_standard.py`:
`migrate` joins `SURFACE` (`:22`) and the count (`:70`) grows by one.
`tests/work/test_git_write_scan.py`: `SCANNED` gains
`*(PACKAGE / "migrate").rglob("*.py")` (Decided 23, criterion 69), so every
git call the package makes from here on is held to TCW-70's rule.

**Proves it:** the new tests; `tests/work/test_git_write_scan.py` and
`tests/test_static_guards.py` green with the package present; the full
suite.

## Step 2 — the 3.x readers part 1 needs, and the fixture builders

Design 4.1, 8.2; Decided 2, 3, 18, 24; criterion 67 (TCW-110's and TCW-111's
exemptions, and TCW-112's test-file one).

**Creates** `tcw/migrate/legacy.py`, copied from tag `v3.0.2` (Decided 2;
lines below are the tag's):

- `read_3x_layers(root) -> Layers3`: the root file, the user-wide file and
  the root personal file, each parsed with the 3.x loader's duplicate-key
  refusal (a read failure is B14 with its message), merged by the copied
  `_merge` and `PERSONAL_KEYS`, keeping each layer's raw mapping and text.
- `own_jira_layers(root)`: Decided 11's raw reading of `work.jira` from
  the project's own layers, in 3.x or 4.0 places.
- `objects_3x(store_root, namespace) -> list[str]`: taxonomy, every folder
  (`_local_slugs`, `fs.py:1743-1749`); capabilities, every
  folder holding `meta.yaml` (`_is_capability`, `:2235-2236`), skipping
  hidden parts as `_all_meta_dirs` (`:2238`) does; work, every folder of
  the store holding `item.yaml`, both backends, found on disk (Design 4.1).
- `links_3x(text)`: `_LINK_RE` and `_strip_code` (`tcw/validate.py:48-71`)
  and `parse_tcw_uri` (`tcw/refs.py:59`, copied as `parse_tcw_uri_3x`),
  returning each link outside code with its position.
- `store_folder_3x(root, component, raw)`: the path rungs of `resolve_store`
  (`fs.py:3162-3300`: `anchor_configured_path`, `~`
  expanded, the default `docs/<component>`) for a store with a path; a
  store with only a `repository` is a part 2 form in part 1 (Decided 17).

**Changes** the two guards whose rules `legacy.py` now meets, and the one
whose test-file rule the fixtures meet (Decided 18):
`tests/test_identifier_sweep.py` and `tests/test_object_folder_sweep.py`
gain `MIGRATION_FOLDERS = ("tcw/migrate",)`;
`tests/test_no_3x_inheritance.py` gains `MIGRATION_TESTS =
("tests/migrate",)` for its test-file rule only. Each gains its reach test
(criterion 67). A guard not yet written as a function of a root folder is
first reshaped so, in its own commit, with the inventory and
`compare_outcomes.py` showing the same tests and outcomes before the
exemption is added.

**Creates** `tests/migrate/fixtures.py`: `build_f_single(root, *,
backend="jira")`, `seed_tickets(fake)`, `snapshot(*roots, user_file)`
(path, kind, bytes and modification time of every path), and the pieces
F-full adds later, and `fixture_digest(root)` (Decided 3);
`tests/migrate/record_3x_listings.py`, run by hand once with network
access, and its committed output `tests/migrate/golden/f-single.json` and
`f-single-files.json` (Decided 3; the run, its `pip freeze` and the
network check's result are recorded in the implement round);
`tests/migrate/test_goldens_current.py`, the fixture-digest check.

**Tests first**, `tests/migrate/test_migrate_legacy.py`: `objects_3x` of
F-single equals the golden listings' id-paths for taxonomy and
capabilities; `read_3x_layers` merges `user.name` from the personal file
and refuses a duplicate key; `links_3x` finds the link outside code and not
the one in a code span; `own_jira_layers` gives the same `work.jira` for a
fixture in 3.x form and for the same fixture with its files moved to
`.tcw/`, and takes the credential names from a 3.x root personal file;
**mutation check:** with `objects_3x` taxonomy
counting only folders holding `meta.yaml`, the golden comparison goes red
naming `customer`. `test_goldens_current.py`: each golden's
`fixture-digest` equals the digest of the fixture built today, and no
golden holds the fixture's temporary path; **mutation check:** with one
byte of F-single's `cli/x` state file changed in `fixtures.py`, it goes red
naming `golden/f-single.json` and the script. The script itself, with
`https_proxy=http://127.0.0.1:9` set in its environment, stops at the
network check with exit 1 and its message, and has made no virtual
environment (run by hand once, recorded in the round, since the suite
never runs the script). In each of the three guards, the reach test of
criterion 67; **mutation check:** with the exemption matched as a text
prefix instead of by path parts, the `tcw/migrate_x.py` case goes red.

**Proves it:** the new tests; the three guards green with `legacy.py` and
the fixtures in place; the full suite.

## Step 3 — the plan, the writes and the progress record, on hand-made plans

Design 2.2, 2.4 (phases A-E), 2.5, 2.7 (the progress record, following it,
B17, the stop points, the stopped run's message), 2.8 (only listed
deletions), 8.6; Decided 4-7, 23; criterion 69 (the message). The
riskiest code of the item, built and tested alone, before any conversion
exists, on plans written by hand in the tests.

**Creates** `tcw/migrate/model.py`: `Write(path, phase, expect, text,
conversions)` (`expect` a digest or `"absent"`), `Move(old, new, phase,
files, conversions)` (`files` the relative path and digest of each file a
folder holds), `Delete(path, phase, digest, waits_for, waits_digest,
conversions)` (`digest` the deleted file's own, as planned; `None` only for
the progress record's own deletion),
`TicketEdit(key, old, new)`, `Report(code, where, text)`, `Blocker(code,
where, why, fix)`, `Plan(project, work_backend, steps, tickets, reports,
blockers, owners, resolved, summary)` (`owners` and `resolved` hold Design
2.7's "why each byte is what it is"; `project` and `work_backend` are what
a run following the record needs to decide about the Jira half, Decided
19).

**Creates** `tcw/migrate/progress.py`: `PROGRESS = ".tcw/tcw-migration-progress.yaml"`,
`dump(plan) -> str`, `load(root) -> Progress | None`, where `Progress`
holds `project`, `work_backend` and the steps (a file that is not this
format, or lacks either field, is B17 naming it).

**Creates** `tcw/migrate/execute.py`: `_write`, `_move`, `_delete`, `_mkdir`
(Decided 7); `state(step, root) -> "done" | "todo" | "changed"` (Design
2.7: done when the result is on disk, a move's new path holding its
recorded files and digests; todo when what it reads is as recorded, a
deletion's file still holding `digest` and its 4.0 file `waits_digest`;
changed otherwise); `run_local(plan, root, *, follow)`,
which walks the steps in order, skips done ones, stops before the first
changed one with B17, and otherwise performs each; `apply(plan, root)`:
phase A's writes in Decided 5's order, then `progress.dump`, then
`run_local`, then the progress record deleted last in phase E. A failure
raises `MigrateStopped(done, not_done)`, which `cli.py` prints with `run
'tcw migrate' again to finish` and `do not save these files in version
control until 'tcw migrate' finishes` (Decided 23), exit 1; `run_local`
turns every `OSError` from a write into it (Decided 21). If Step 0 found that `tests/move_stops.py` drives only commands,
**changes** it to take a callable that performs one run as well, beside
the command form and with no change to it.

**Tests first**, `tests/migrate/test_migrate_execute.py`, each on a plan of
a few hand-written steps in a temporary folder:

- Every step of a plan of one of each kind is done in order; the progress
  record exists after phase A and is gone at the end; the record and ignore
  line come before it (Decided 5).
- **Every stop**, with `tests/move_stops.py` driving `apply` on a plan of
  eight steps (a record write, an ignore-line write, a folder move, a file
  move into a new `resources/`, a state-file write, its 3.x file's
  deletion, a configuration write, a root deletion): for every counted
  write k, the first run stops, the second (`apply` again, following the
  record) finishes, and the tree equals the uninterrupted run's byte for
  byte, with no progress record left.
- B17: with the progress record present and a todo file changed by hand,
  the second run stops with B17 naming the file and the fix, exit 3, and
  writes nothing more.
- A cross-device move (P5's mechanics): `os.rename` patched to raise
  `EXDEV` for one move; the run exits 1 with Design 2.5's message naming
  both paths, and nothing is copied (the snapshot differs from the stopped
  state only by what was done before); the test then moves the folder by
  hand with the real `os.rename`, and the next run finds the move done and
  finishes, giving the uninterrupted tree.
- A delete waits for its 4.0 file: with that file's bytes different from
  its recorded digest, B17.
- A delete checks its own file (the review's M3): stopped after the 4.0
  state file is written (P7), the 3.x file is then edited by hand; the next
  run stops with B17 naming it, exit 3, and the edited file is still there
  with its edit.
- A `PermissionError` from `_write` gives `run 'tcw migrate' again to
  finish`, exit 1, not `_dispatch`'s one-line error (Decided 21).
- The stopped run's two lines are printed exactly, and
  `tests/test_static_guards.py` passes with them in `tcw/migrate/cli.py`
  (criterion 69's message half).
- `progress.load` returns the `project` and `work_backend` that `dump`
  wrote; a record without either is B17.
- The progress record round-trips a text with Windows line endings, a
  leading byte-order mark and trailing spaces exactly, and a file read for
  the plan with `\r\n` endings is written back with them on every untouched
  line (Decided 4).
- `_write` reads back: with the read-back patched to return other bytes,
  the old file is not deleted and the run stops.

**Proves it:** the new tests; mutation check: with `state` ignoring a
deletion's own `digest`, the M3 case goes red; the full suite (nothing
outside the package uses it yet).

## Step 4 — the editors

Design 2.8; Decided 9.

**Tests first**, in `tests/test_config_edit.py`, new
`tests/test_rewrite_values.py`, and new `tests/migrate/test_migrate_editors.py`
for every case whose text TCW-112's test-file rule forbids elsewhere
(Decided 24): `RemoveTop("id")` on a state file holding `id: cap-1a2b3c`, and
`RemoveTop("overrides")`. The cases in `tests/test_config_edit.py` use
neutral text (`id: x1`, `projects:`):

- `RenameKey(("work", "stages", "spec", "prompt", 4, "when", "not_tags"),
  "not-tags")` on the frozen copy of this repository's configuration
  (`tests/migrate/data/repo-tcw-config-3x.yaml`, Decided 20, saved in this
  step) changes only those characters, and the aliases in that file
  (`*pull-text`, `*commit-after-move`) still resolve to the same values; a
  key under an anchor that is aliased elsewhere (a fixture of its own)
  renames once and the alias still resolves to the renamed mapping.
- `SetTop("parents", [{"id": "core", "inherit": ["taxonomy"]}])`: a list of
  mappings is written in TCW's usual style and parses back equal; `_verify`
  checks values of any depth (a mapping inside a list inside a mapping).
- The order on one file (Decided 9): `edit_text`, then `rewrite_yaml`, then
  the final parse; a test in which the second changes a value the first
  also touched shows the final check catches a disagreement.
- `RemoveTop("projects")` removes a whole block and reports a comment inside
  it in the returned dropped-comments list; a removed block that defines an
  anchor used outside it is `ConfigEditRefused` (B12).
- `SetTop("parents", [...])` appends a block in TCW's usual style after the
  last top-level key; `SetTop("parent", "app.taxonomy/invoice")` in a state
  file goes after `name` when present, else last.
- `edit_text(..., versioned=True)` on a file with no `tcw-version` puts
  `version_line()` first and leaves every other byte; on a file that has one,
  leaves it.
- `rewrite_yaml(text, fields, replace)` with a function: replaces a flow and
  a block sequence entry, keeps quoting and a leading `!`; the pair form
  still passes TCW-114's own `tests/test_rewrite.py`, and for the same input
  returns the same "already done" fields and the same `mentions` as before
  the change (compared on TCW-114's own fixtures).

**Changes** `tcw/store/config_edit.py` (the three edits; `intended` and
`_verify` generalised to key paths of any depth and to mapping and list
values; `versioned`); `tcw/rewrite.py` (`rewrite_yaml`'s `replace`
argument; the pair list wrapped, keeping every result it returned).
**Creates** `tests/migrate/data/repo-tcw-config-3x.yaml` and
`tests/migrate/data/README.md` (Decided 20).

**Proves it:** the tests above; `tests/test_rewrite.py`; the full suite.

## Step 5 — the configuration

C1, C2, C7, Design 2.7 (both files, configuration), 2.9 (B1, B2, B11,
B14, B15; A4, A5, A9 for `work.jira.credentials`, A13; D5); criteria 13
(configuration half), 15, 18, 19, 20, 29 (`TCW_JIRA__EMAIL` in
`work.jira.credentials`), 30, 31, 63.

**Tests first**, `tests/migrate/test_migrate_config.py`, each a small 3.x
project run with `tcw migrate`:

- C1 and criterion 18: `.tcw/tcw-config.yaml` and
  `.tcw/tcw-config.local.yaml` start with the version line; inside a git
  repository `.tcw/.gitignore` holds the three lines; outside one it does
  not exist; store paths are unchanged text; the root files are gone.
- Criterion 15: the frozen copy `tests/migrate/data/repo-tcw-config-3x.yaml`
  (never the repository's own root file, Decided 20), copied into a
  fixture, converts to `tcw-version: <running>` followed by its text with
  `not_tags` written `not-tags`, compared byte for byte.
- Criterion 13 (configuration): a root file beside a `.tcw/` file whose
  parsed values without `tcw-version` equal its conversion keeps the `.tcw/`
  file's bytes and deletes the root file; one differing in a value is B11
  naming both and the first differing key; one differing only in a comment
  is equal.
- Criterion 19: an empty `.tcw/tcw-config.local.yaml` gains only its version
  line; an empty `.tcw/tcw-config.yaml` beside a root file gets the root
  file's conversion; an empty one with no root file is B15; `tcw work list`
  in a project whose `.tcw/tcw-config.yaml` is empty is still refused with
  TCW-106's missing-version message.
- Criterion 20: `not_tags` renamed in both project files; `work_tags` is B1.
- B2: `connected-projects` names the 3.0 migration guide. B14: a root file
  with a duplicate key. (B12 needs a replaced block, and part 1 replaces
  none, so it is Step 17's.)
- Criterion 29's part 1 half, 30, 31, 63 as written, each checking the
  file's bytes unchanged for A4, A5 and A13.
- Part 2 forms (Decided 17): `projects:`, `taxonomy.extends`,
  `capabilities.extends`, a store path leading out of the project and a
  store with only a `repository` each give B5 with `does not convert …
  yet`, and nothing is written.

**Creates** `tcw/migrate/config.py`: `plan_config(layers, root) -> (steps,
reports, blockers)`: C1's two `.tcw/` files through `edit_text(versioned=True)`
with `RenameKey` for every `not_tags` key (`_RENAMED_KEYS`); `key_problems`
(`tcw/project_files.py:182`) on the planned mappings, every refusal not
fixed by a rename being B1; B2 by `retired_key_problem`
(`tcw/store/base.py:480`); the both-files rule by comparing parsed values;
the `.tcw/.gitignore` text planned as a `Write` from the rule constants
`LOCAL_CONFIG_RULE` and `LOCAL_MANIFEST_RULE` (`fs.py:204-205`) and the
progress record's line, by the same "already there" test
`ignore_personal_files` uses, only when `git_root(root)` is not None; never
by calling `ignore_personal_files`, which writes the file itself and so
would bypass the dry run, the read-back and the progress record (the
review's S4); the root deletions in phase E, each with its own digest and
waiting for its `.tcw/` copy. Reports: A4 from the root `.gitignore`; A5 from the
user-wide file; A9 for credential names matching `TCW_` and `__`; A13 for a
bound command whose text names `tcw provision`, `tcw projects`, `tcw init`,
`--project` or `--blocks` (word-bounded); D5 for `null` at `work.tags`,
`work.jira` or below in the shared file.

**Creates** `tcw/migrate/plan.py`: `make_plan(root, *, no_jira) -> Plan`,
which reads (`legacy.read_3x_layers`, the `.tcw/` files), calls
`plan_config` and `part_two_forms`, and in later steps the stores and Jira;
`tcw/migrate/report.py`, the lines of Decided 14 and the summary.
`cli.run` now: when `progress.load(root)` finds a record, it follows it
(`execute.follow(progress, root, dry_run=)`, built on Step 3's `run_local`;
a dry run lists the steps still to do) and never calls `make_plan`;
otherwise `make_plan`; blockers → print all, exit 3; `--dry-run` → print,
exit 0; else `execute.apply`. Step 9 puts the Jira half in front of both
paths.

**Proves it:** the new tests; the full suite.

## Step 6 — the stores' state files

Design 4.1, 4.2 (B8; B7 for the project's own stores), C9, C10 (the
project's own ids recorded), C11, C12, Design 2.7 (both files, state files),
Design 7 (the record's `capability-ids`); A1, A2, D7; criteria 13 (state
half), 17 (part 1), 33, 34, 35, 36, 42.

**Tests first**, `tests/migrate/test_migrate_stores.py`:

- Criterion 33: each 3.x state file of taxonomy, capabilities,
  files-backend and Jira-backend work becomes its 4.0 name, the version
  first, the rest unchanged except the listed edits (a line-by-line
  comparison).
- Criterion 34: every `id: cap-…` is gone and recorded in
  `.tcw/tcw-migration.yaml` with its id-path; `id: <folder name>` stays;
  `id: other` in a taxonomy state file is A1.
- Criterion 35: `invoice/line` and `cli/x/y` get `parent:` with their
  parent's full identifier, and 4.0's `tcw validate` gives no
  folder-and-parent warning for them.
- Criterion 36: `customer` gets `tcw-taxonomy.yaml` with `name: customer`
  and an empty `description.md`, each reported D7; `cli/z` gets both.
- A2: `cli/v/resources/meta.yaml` is reported, not moved or renamed.
- Criterion 13 (state): `meta.yaml` beside an equal `tcw-capability.yaml` →
  only the latter, its bytes unchanged; differing → B11 naming both.
- Criterion 42: a folder `has.dot`, a term `resources`, a work item whose
  full identifier would be 256 characters, and a capabilities store inside
  the taxonomy store are each refused before anything is written (B8, B7).
- Design 4.1, objects already 4.0: a store holding one `tcw-capability.yaml`
  object and one `meta.yaml` one converts only the second; the first counts
  as taken for C11's enclosing object.
- A part 2 form: an `overrides:` key gives B5 (Decided 17).

**Creates** `tcw/migrate/stores.py`: `plan_stores(read) -> (steps, reports,
blockers, ids)`. For each object of `legacy.objects_3x` and each 4.0 object
of `walk` (TCW-111): the final state file through
`edit_text(versioned=True)` with `RemoveTop("id")` for a `cap-…` id,
`SetTop("parent", …)` where `folder_parent` names an object (C11),
`SetTop("name", <folder>)` (C12, for an object that overrides nothing and
has no `name`; in part 1 no object overrides anything), and C16's edits added by Step 8 in the same text;
an empty `description.md` written where missing (C12); the 3.x file deleted
after, waiting for the 4.0 one. B8 from `tcw/ids.py`'s grammar,
`reserved_names` and `length_problem` over every object and organising
folder; B7 with `_same_folder` and `_in_folder` (`fs.py:599-613`) over the
planned store folders. **Creates** `tcw/migrate/record.py`: `plan_record(
root, ids, moved, removed) -> Write | None`, which merges with an existing
record and returns no write when nothing changes.

**Proves it:** the new tests; the full suite.

## Step 7 — loose entries into `resources/`

C13, A3; criterion 37; stop point P6's write order.

**Tests first**, in `tests/migrate/test_migrate_stores.py`: criterion 37 as
written, on F-single: `design.md` and `notes/` of `APP-1-a` under
`resources/`; `prependedDocs: [resources/camera.md]` and `tcw capabilities
show cli/x` in 4.0 including the file; the exact text in `APP-2-b`'s spec
rewritten; the two shortened forms left and reported A3 with file and line;
`README.md` left and not reported. Moved files keep their bytes
(criterion 16's first half).

**Changes** `tcw/migrate/stores.py`: for each object folder, every entry
`walk` reports as out of place (S111 Design 2.6 rows a and b) becomes a
`Move` into `resources/` in phase B (with `_mkdir` of `resources/`), its
`files` digests recorded; a `prependedDocs` or `appendedDocs` entry naming
it is rewritten in the state file's one write; exact mentions
(`<store path>/<id-path>/<file>`, and a relative Markdown link from within
the same folder) are rewritten in a phase C write of each Markdown or YAML
file of the project's stores that holds one; every other mention matching
Design 2.9 A3's pattern is A3.

**Proves it:** the new tests; the full suite.

## Step 8 — references within the project

C16 for the project's own objects and work slugs; B10 where a single
project can give it; criterion 41's rows that name no other project, and 62.

**Tests first**, `tests/migrate/test_migrate_references.py`, one fixture
per row of S110 Design 5.1's table (TCW-114's `FIELDS`, P114 Step 9): each
3.x value becomes the full identifier 3.x resolves it to: a files-backend
`parent` and `blocked-by` (`app/APP-1-a` to `app.work/APP-1-a`);
`capabilities.yaml` entries under `new:` (one naming a capability that does
not exist), `changed:`, `removed:` and `taxonomy:`; `relatesTo` and
`vocabulary`; `Subject`, `Feature`, `Superseded by`, `Blocked by`, `Roles`
and `When` with `!` and the `roles/` and `conditions/` id-paths kept; the
link outside code to `](tcw://app.capabilities/cli/x)` and the one in a
code span unchanged. Criterion 62: in a migrated project a branch brings a
`meta.yaml` capability whose `Subject` names a bare path only a 4.0 object
has, and an `item.yaml` whose `blocked-by` names a 4.0 item; only those two
convert, each given the project as owner, and a `meta.yaml` beside its
folder's `tcw-capability.yaml` with other values is B11. A prefixed
reference to another project, and a cross-project `blocked-by`, are B5
(Decided 17). B10's part 1 form (spec Design 2.9): in a project that keeps
no capabilities ledger and declares no child, an item's `capabilities.yaml`
entry is B10 with 3.x's own problem line (`gates.py:377-380` at
`v3.0.2`).

**Creates** `tcw/migrate/references.py`: `owner_of(value, field, read)`,
the 3.x rule in part 1 (a bare path is the project's own; a `capabilities.yaml`
entry routed as `route_capability_path` routes it with no sources and no
children; a work slug `<project>/<folder>` with the project's ID); every
owner recorded in the plan (Design 2.7). `plan_references` builds the
`replace` function for `rewrite_yaml` per record (Decided 9) and applies it
inside the one write of each state file (Step 6) and in a phase C write of
each `capabilities.yaml` and Markdown file; links found by `links_3x`,
rewritten by position.

**Proves it:** the new tests; mutation check: with `owner_of` returning no
owner for `Roles`, the `Roles` row goes red and the failure read; the full
suite.

## Step 9 — Jira

Design 1.1 (`--no-jira`), 1.6 (codes 1 and 5 for Jira), 2.1 (the search
and the edit screen while planning), 2.3, 2.4 (phase F), 2.6 (the offline
re-run), 5.1-5.4, C17, A10, B16; criteria 12, 14 (offline parts), 43, 44,
57, 58, 59, 65.

Also criteria 66 and 68; Decided 11, 19; spec Design 2.7 (the Jira half
of a run that follows a progress record).

**Tests first**, `tests/work/jira/test_jira_migrate.py` (the backend
methods) and `tests/migrate/test_migrate_jira.py` (the command), with the
fake (`tests/work/jira/fake.py`); every fixture's `site` is
`https://example.invalid`:

- Criterion 43: in a fake Jira project shared by `app` and `lib`, `app`'s
  run edits each of `app`'s 3.x tickets once, the body holding only the
  `TCW Item` field, to `app.work/<folder>`; `lib`'s tickets, `app`'s 4.0
  ones and those with no `TCW Item` get no edit.
- Criterion 44: `APP-3` (no folder here) converted; `APP-5` and `APP-6` A10
  and not edited.
- Criterion 65: the `PUT` the fake records for a migrated ticket equals, in
  method, path form and body, the one TCW-114's `move` sends for the same
  field and value; the search and edits use the field names of the 3.x
  `work.jira.fields`; `set_item_values` given the pairs swapped puts every
  3.x value back and edits no other field. (The 4.0 parent half, D1 for
  `fields.effort`, is Step 19's.)
- The search is paged at the client's page size, 100 (`PAGE`): with the
  fake's `page_size` set to 2, five tickets are read in three pages.
- Criterion 59 (B16): with `off_edit_screen` holding the `TCW Item` field
  for the first ticket's type, the real run exits 3, the snapshot is
  unchanged and no edit is recorded.
- Criterion 58: Jira unreachable (`fake.unreachable()`) while planning:
  exit 5; the credential variables unset: exit 1 (`TrackerAuthError`, no
  request made); `fake.unauthorized()`: exit 1; each with the snapshot
  unchanged, no edit, and `nothing was written; 'tcw migrate --no-jira'
  converts the files without Jira`; the dry run in the same three cases
  lists every local change and exits 5, 1, 1.
- Criterion 57: `--no-jira` with a fake failing every request records no
  request, makes every local change the plain run makes, exits 0, and its
  summary names the Jira project and says the tickets are not converted; a
  later plain run changes no file and edits exactly the tickets the plain
  run would have; `--dry-run --no-jira` records no request; in a
  files-backend project the flag changes nothing.
- Criterion 12: reachable while planning, `fail_edit` with
  `then_unreachable` in phase F: every local write made, exit 5, the
  tickets left named; a second run edits exactly those and changes no file;
  the same with credentials refused in phase F: exit 1.
- Criterion 14's Jira parts: a second run after a finished one records the
  search and no edit; unreachable: `nothing to migrate in the files; the
  tickets could not be checked`, exit 5; `--no-jira`: exit 0, no request.
- Criterion 66: with `JiraClient.__init__` and `JiraBackend.__init__`
  patched to raise, `--no-jira` and `--dry-run --no-jira` on F-single
  finish as criterion 57 says. The same two runs, made with a progress
  record present (a first run stopped by `tests/move_stops.py` at its
  first write after phase A, with `--no-jira`), finish too: the real one
  completes the local steps, and the fake records no request in either.
  A static check reads the syntax trees of `tcw/migrate/*.py`: only
  `jira.py` names `tcw.work.jira`, and the only import of
  `tcw.migrate.jira` is inside `plan.plan_jira_half`. With `plan_tickets`
  patched to call `edit_issue` on the client it is given, a dry run fails
  with `_ReadOnlyClient`'s error and the fake records no `PUT`, both
  fresh and with a progress record present. `_ReadOnlyClient` refuses
  `create_issue`, `edit_issue`, `apply_transition`, `add_comment`,
  `add_link`, `delete_link`, `_request`, `_payload` and a made-up
  `new_writer`, and passes on its six allowed calls. In this step the
  constructor patch covers planning and phase F. Step 10 adds the check
  after the run, and this test stays green there because of Decided 13's
  `work=False`; Step 10 runs it again as its own check.
  **Mutation checks:** with `plan.py` importing `tcw.migrate.jira` at the
  top and building the backend before the `no_jira` test, the constructor
  patch makes the `--no-jira` case go red. With `cli.run`'s
  progress-record path calling `jira.backend_for` directly instead of
  `plan_jira_half`, the static check and the progress-record case go red.
- The Jira half of a run that follows a progress record (spec Design 2.7):
  stopped after phase A on F-single without `--no-jira`, the re-run
  searches the fake before its first write (the fake's request log and the
  write counter share one counter). With the fake unreachable at that
  point, it exits 5, writes nothing more (the snapshot equals the stopped
  state), and prints `nothing more was written; 'tcw migrate --no-jira'
  finishes the files without Jira`. With the edit screen lacking the
  field, it exits 3 with B16 and writes nothing more. `--dry-run` with the
  record present lists the steps still to do and the planned ticket edits,
  and records no `PUT`. With `make_plan` patched to raise, all of these
  still behave so.
- Decided 11: `item_values()` and `set_item_values()` give the same
  tickets and edits with `work_config` built from F-single's whole `work`
  section and from `parse_work_config({})[0]`.
- Criterion 68: after `--no-jira` on F-single, `fields.item` in
  `.tcw/tcw-config.yaml` changed by hand to `Other Item`: the plain run
  searches and edits `Other Item`; credential names set only in a 3.x root
  `tcw-config.local.yaml` are used; F-single's user-wide `not_tags` does
  not stop the run; with `work.jira.project` removed from every layer, the
  run exits 1 naming the file, the key and `--no-jira`, the snapshot
  unchanged and no edit recorded.

**Changes** `tcw/work/jira/backend.py`: `item_values()` and
`set_item_values(pairs)` (Decided 10), each with a docstring saying it is
used only by `tcw migrate` and is not one of the twelve operations;
`set_item_values` raises, after trying every ticket, `Unreachable` when any
attempt could not reach Jira, else `BackendError`, each naming the tickets
left.

**Creates** `tcw/migrate/jira.py`: `backend_for(root, project_id, client)`
(Decided 11, from `legacy.own_jira_layers`, with the default
`work_config`); `_ReadOnlyClient`, an allowed list (Decided 19);
`plan_tickets(project_id, backend)` (Design 5.1's filter by `TCW Project`;
Design 5.2's classification; B16 by `client.edit_metadata(<first key>)`
holding the `TCW Item` field id), given a backend over the read-only
client; `half(root, project_id) -> JiraHalf`, which plans and returns the
tickets, the blockers, and `apply`, a function that builds the backend over
the real client and calls `apply_tickets(tickets, backend)` for phase F;
and `restore_tickets(pairs, client)`, the way back (Step 26), which takes
the client as an argument. **Changes** `tcw/migrate/plan.py`:
`plan_jira_half(root, project_id, *, jira_backed, no_jira)` (Decided 19),
the only place that imports `tcw.migrate.jira`. `make_plan` calls it.
**Changes** `tcw/migrate/cli.py`: `cli.run` calls it before following a
progress record, with the record's `project` and `work_backend`.
**Changes** `tcw/migrate/execute.py`: phase F is `half.apply()` when there
is a half. `cli.run`: a Jira failure while planning prints the local plan
and Design 2.3's message and exits with the backend's code; with a
progress record present, the message is spec Design 2.7's `nothing more
was written; …`; with an empty local plan it prints Design 2.6's offline
line instead.

**Proves it:** the new tests; the full suite.

## Step 10 — the planned files checked, `tcw validate` after, the summary

Design 2.1 (B3; A12; the work-store checks left out under `--no-jira`),
2.10 (part 1: counts, files left in another repository, the `--no-jira`
sentences); Decided 8, 13; criteria 57 (its summary line) and 66 (the check
after the run).

**Tests first**, in `tests/migrate/test_migrate_command.py`:

- B3: a planned configuration that 4.0's reader refuses (a fixture whose
  root file holds `work.stages.spec.status: 5`, which 3.x also refuses but
  which reaches the planned file unchanged) is B3 naming the file and
  4.0's message, nothing written; a planned state file refused by
  `parse_state_text` likewise.
- A12: after F-single's real run, `cli/w`'s missing `Status` is listed as
  A12 in 4.0's words, and `tcw validate` then reports exactly the A-reports
  the run gave; a dry run says these findings are known only after a real
  run. The run's A12 list equals F-single's fixed expected list
  (`tests/migrate/fixtures.py`, `F_SINGLE_A12`), written from the 3.x
  `tcw validate` output in `golden/f-single.json` (Decided 13). A finding
  in the same file as a report but of another kind (an extra fixture: a
  state file under `resources/` (A2) beside a malformed `Roles` value in the
  same capability) is listed as A12, not absorbed by A2. **Mutation
  check:** with a conversion made to write a bad `parent:`, the fixed-list
  comparison goes red naming the new finding.
- The summary: counts of files written, moved and deleted and of tickets
  edited (or would be), and the `--no-jira` sentences of Design 1.1.
- The check after the run under `--no-jira` (Decided 13): on F-single (Jira)
  with `--no-jira`, `collect_findings` is called with `work=False`, the
  summary prints `work store not checked after the run (--no-jira): run
  'tcw validate' to check it`, and the A12 list holds every expected
  finding outside the work store. On F-single-files with `--no-jira`, the
  work-store checks run and the line is absent, so the flag changes
  nothing there (criterion 57). Step 9's criterion 66 test, with the
  constructors patched to raise, is run again and passes with the check in
  place. **Mutation check:** with `work` always `True`, that test's
  `--no-jira` case goes red, failing in `JiraBackend.__init__` reached from
  `_work_findings`.
- `validate(..., work=False)` skips section (e) and nothing else: on a
  files-backend fixture, every finding outside the work store is the same
  with `work=True` and `work=False`.

**Changes** `tcw/config.py`: `parse_project_file_text(text, file, *,
layer)`, split from `_read` (`:233`) if Step 0 found none; `_read` calls it.
`tcw/object_folders.py`: `parse_state_text(text, file)`, split from
`read_state`. `tcw/validate.py`: `validate(project_root, *, …, work=True)`,
whose section (e) runs only when `work` is true. `tcw/cli.py`:
`collect_findings(project_root, *, remote, work=True)` split from
`_cmd_validate` (`:208`), which calls it with the defaults and prints as
today.
`tcw/migrate/plan.py`: each planned configuration and state file parsed
from its text (B3). `tcw/migrate/execute.py`: after phase E, ends and
begins the configuration cache (`layered.end_command()`,
`begin_command()`, as `_cmd_serve` does, `tcw/cli.py:351-352`) and calls
`collect_findings(root, remote=False, work=not (no_jira and jira_backed))`,
mapping findings to reports by each report's predicted finding (Decided
13). `tcw/migrate/report.py`: the summary's work-store line.

**Proves it:** the new tests; `tests/test_validate_command.py` unchanged;
the full suite.

## Step 11 — F-single end to end: every stop, the dry run, running again

Design 2.2-2.8 on one project; criteria 4, 5, 6, 7, 9 (its interim form), 10, 11, 14,
16, 17, 49, 51 (on F-single), 60, and 8 for the blockers part 1 gives.

**Tests first**, `tests/migrate/test_migrate_f_single.py`:

- Criterion 5: the dry run leaves the snapshot unchanged; the fake records
  the search (with the fake's `page_size` at 2, one request per page), one
  edit-screen request, the field-id reads `metadata()` makes, and no `PUT`
  and no `POST` other than the search's; exit 0.
- Criterion 6: the dry run's `(path, action)` set equals the real run's
  changed paths (by snapshots), and its ticket keys the keys edited; the
  progress record and folders are left out of both sets.
- Criterion 7: every change line names its conversion, every report its
  number, every ticket line both values.
- Criterion 10: spies on `_write`, `_move`, `_delete` and the fake's `PUT`
  log, with one shared counter, show phase A first, every move before the
  first state file write, each state file written once, every store write
  before `.tcw/tcw-config.yaml`, the root files then the progress record
  deleted after, and every edit last.
- Criterion 11: `tests/move_stops.py` over `tcw migrate` on F-single (and
  on F-single-files): for every counted write k, the stopped run exits 1
  (5 or 1 for an edit, by the fault injected), prints `run 'tcw migrate'
  again to finish` and what it did; the healthy re-run exits 0; the tree
  and tickets equal the uninterrupted run's; no progress record left.
- Criterion 60: stopped at P2, P3, P6, P7, P8 and P9 (each the first write
  of that point's kind, found from the uninterrupted run's write list), the
  progress record is present and listed in `.tcw/.gitignore`; the second
  run follows it with `tcw.migrate.plan.make_plan` patched to raise, and
  gives the uninterrupted snapshot. After P8 with one not-yet-converted
  `meta.yaml` changed by hand: B17 naming it, exit 3, nothing more written.
  After P7 with the `meta.yaml` waiting to be deleted changed by hand: B17,
  exit 3, and that file still holds the edit. P5: `os.rename` raising
  `EXDEV` for `APP-1-a`'s `design.md` move: exit 1, both paths named, no
  copy made; moved by hand, the next run finishes with the uninterrupted
  snapshot.
- Criterion 14: a second run prints `nothing to migrate`, exits 0, leaves the
  snapshot unchanged (modification times included).
- Criterion 16 and 17 on F-single: the only paths gone are 3.x files whose
  4.0 copies exist and the old places of moved files; the record holds
  every `cap-…` id with its id-path and starts with the version line.
- Criterion 51 on F-single: 4.0's `tcw validate` reports exactly the A
  findings the run reported, and the A12 list equals `F_SINGLE_A12`;
  `tcw work list` lists the items whose tickets
  were converted, and `tcw taxonomy list --scope up` and `tcw capabilities
  list --scope up` list the golden id-paths with owner `app`.
- Criterion 4: in a git repository with uncommitted changes and in a copy
  outside git, the same changes apart from `.tcw/.gitignore`; with a `git`
  shim first on `PATH` recording every call, only `rev-parse`, `ls-files`,
  `status` and `check-ignore` appear, and every `status` carries
  `--no-optional-locks`, checked by a rule composed in this test from
  `recorded_processes` (Decided 22), leaving `allowed_read_only_git`
  unchanged.
- Criterion 49: in a linked worktree of F-single's repository, only the
  worktree's files change, and a root `tcw-config.local.yaml` present only
  in the main checkout is A7 and unchanged.
- Criterion 8 (part 1): one fixture per blocker part 1 gives (B1, B2, B3,
  B5, B6, B7, B8, B10 in its "no capabilities ledger" form, B11, B14, B15,
  B16, B17, the last in both its forms: a file to write and a file to
  delete changed by hand): dry and real runs each exit
  3, name the place and reason; the snapshot is unchanged and no edit
  recorded. B5's fixture uses the part 2 form `overrides: cap-000000` in a
  capability of a project with no `extends`, which Step 21 changes into a
  true B5 (an `extends` source not on this machine that the pointer must be
  resolved in). B4, B9, B10's other forms, B12 and B13 are part 2's (spec,
  "The two parts").
- Criterion 9's interim form: one fixture holding B1, B8 and the same
  `overrides: cap-000000` pointer lists all three in one run, the pointer
  as B5 for now; Step 21, which converts `overrides:`, changes that
  expected code to B9 (a pointer that names nothing) in the same fixture,
  which is then criterion 9 as written.

**Changes** whatever these tests find, in the step that owns it, each listed
in the implement round.

**Proves it:** the new tests; the full suite.

## Step 12 — tests that read this repository's records by a state file's name

Design 8.4; criterion 54's code half.

**Tests first:** a new case in `tests/test_ledger_3_0.py` runs its checks on
a copy of `docs/` in which every `meta.yaml` has been renamed to its 4.0
name with the version line added (by `tests/migrate/fixtures.py`'s
`as_4_0_records(src, dst)`), so the either-name reading is proven on `v4`
before the merge.

**Changes**, mechanical then by hand, each file from Step 0's list: a record
is found by `record_file(folder, namespace)` in `tests/statefiles.py`, which
returns the 4.0 state file when present, else the 3.x one;
`rglob("meta.yaml")` becomes a walk for either name. Nothing else changes in
those tests. Step 0's list of tests reading the root `tcw-config.yaml`
(item 9) is checked again here: only `tests/test_repo_config_pair.py`, which
the merge deletes, may read it (Decided 20); one added since is changed to
read the frozen copy.

**Proves it:** the inventory and `compare_outcomes.py outcomes-step11.xml
outcomes-step12.xml allowed-step12.txt` (an empty list) exit 0, with
commit 1's assertion dumps unchanged; **mutation check:** with
`record_file` returning only the 3.x name, the new copy-based case goes red.

## Step 13 — records

Capability changes; criterion 52.

On `v4`, in this repository's 3.x ledgers, written by hand (Design 9.1):

- New `docs/capabilities/cli/migrate-a-tcw-3-x-project-to-tcw-4/`
  (`meta.yaml` with `id: cap-<six hexadecimal digits from
  secrets.token_hex(3)>`, `Status: Supported`, `Subject: [project]`,
  `Feature: project-registry`; `description.md` from the spec's Capability
  changes, naming `tcw migrate`, `--dry-run` and `--no-jira` only).
- `docs/capabilities/cli/read-a-file-by-the-format-version-it-records/description.md`:
  "the command that converts a TCW 3.x file to TCW 4" names `tcw migrate`.
- New `docs/taxonomy/migration/` (`meta.yaml`, `description.md`).

**Proves it:** `tests/test_documented_cli_surface.py` with the suite; the
lifecycle `tcw validate` from the worktree; the records gate at the end of
implement (`tcw work advance TCW-116 --dry-run`).

## Step 14 — the engine proven on this repository

Design 9.2, made now that part 1 has landed; criteria 53, 54, 55. **The
engine part ends with this step**: steps 1 to 13 committed, the suite green
as CI runs it, and this proof recorded in the implement round, before Step
15 starts.

In the scratchpad, never pushed (Decided 15, 16):

```sh
P=<scratchpad>/tcw116-proof
git clone /Users/brian/Projects/TCW "$P/c1"
git -C "$P/c1" checkout -b proof origin/main
git -C "$P/c1" merge --no-edit origin/v4
git clone "$P/c1" "$P/c2"; git clone "$P/c1" "$P/c3"   # each then checked out at proof
python -m venv "$P/venv"; "$P/venv/bin/pip" install -e "$P/c1[dev]"
```

Every command runs `"$P/venv/bin/tcw"` by its full path, written `T`
below; a bare `tcw` is the lifecycle's 3.0.2 (the review's S2). Steps 2 to
5 also run with `https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9`
(an address nothing listens on, which Python's `urllib` honours), so a
request, if one were made, could not leave the machine (the review's S1).
Every file the steps save goes under `$P/`, never inside a clone.

1. In `c1`, with the Jira credentials set (`source ~/.bashrc` in the same
   command): `"$P/venv/bin/python" "$P/log_requests.py" migrate --dry-run
   2> "$P/dry-run.txt"`, where `log_requests.py` (kept in the scratchpad)
   wraps `urllib.request.urlopen` to append each request's method and path
   to `$P/requests.txt` and then calls `tcw.cli.main`. It searches the live
   board, asks for one edit screen, edits nothing; `requests.txt` holds no
   `PUT` and no `POST` but the search's; every listed ticket is this
   project's, with old and new value.
2. In `c1`: `T migrate --no-jira`, with the credential variables also unset
   (`env -u TCW_JIRA_EMAIL -u TCW_JIRA_API_KEY`, the names in the root
   `tcw-config.yaml`): exit 0, the summary says the tickets are not
   converted and that the work store was not checked after the run
   (Decided 13); step 6's `T validate` checks it. The flag is what is tested; the unset variables and the proxy
   are further guards, and Decided 19 is the structural one.
3. In `c1`: `git -C "$P/c1" status --porcelain > "$P/before"`;
   `T migrate --no-jira` again: `nothing to migrate in the files`, exit 0;
   `git -C "$P/c1" status --porcelain` equals `$P/before`.
4. In `c2`: `chmod a-w` one item folder that phase C writes into and that
   phase B moves nothing into (no loose file, so not TCW-99's or TCW-76's;
   for example TCW-106's); `T migrate --no-jira`: exit 1, `run 'tcw
   migrate' again to finish`, the progress record present; `chmod u+w`; run
   again: exit 0, no progress record. Then compare the two clones by the
   files git would track and their contents, which leaves out build
   leftovers (`tcw_cli.egg-info` from the editable install, `__pycache__`,
   `.pytest_cache` and everything else `.gitignore` names; the review's M7):

   ```sh
   for c in c1 c2; do
     git -C "$P/$c" ls-files -z --cached --others --exclude-standard \
       | (cd "$P/$c" && xargs -0 shasum -a 256) | sort -k 2 > "$P/$c.files"
   done
   diff "$P/c1.files" "$P/c2.files"     # prints nothing
   ```

   (A file the migration deleted is still listed by `--cached`, since
   nothing is staged; `shasum` reports it on standard error and writes no
   line for it, in both clones alike, while a file present in one clone
   only still shows as a difference.) If the session runs as a user whom
   `chmod` does not stop, the run finishes in one go; the round says so,
   and the stop on real data is then not shown, the suite's criterion 11
   and 60 tests standing alone.
5. In `c3`, credentials unset as in step 2: `T migrate` exits 1, names
   `--no-jira`, and `git -C "$P/c3" status --porcelain` is empty.
6. In `c1`: `rm tests/test_repo_config_pair.py`; `"$P/venv/bin/pytest"` bare
   from `c1`'s root, with the credential variables unset and no proxy set
   (the suite's own servers listen on this machine; its two live Jira tests
   run only when `TCW_JIRA_LIVE=1`, which nothing here sets, and write to
   `TCWTEST`, never `TCW`); then `T validate`.

Recorded in the implement round: the counts (work items, ledger objects,
ids recorded, files moved into `resources/`, references and links
rewritten, tickets listed, A3 mentions; the spec's 12 at `ebce3fd6` will
have grown with later specs that write `TCW-99-…/design.md`), every
report, and the commits of `main` and `v4` used. A failure here is fixed in
the step that owns it, and the proof made again.

## Step 15 — the 3.x readers part 2 needs

Design 8.2; Decided 2, 3, 18; criterion 67 (TCW-112's `tcw/` rules).

**Changes** `tcw/migrate/legacy.py`, copied from tag `v3.0.2` (lines are
the tag's): the `projects:` reader and `_relation`
(`tcw/store/project.py:614-668`) and `parse_connected_entry`
(`tcw/store/base.py:865`) as `relations_3x(raw, file)`; `_extends_ids`
(`tcw/store/fs.py:884-913`) as `extends_3x(raw, axis)`; `checkout_root`,
`provisioned_root`, `_cache_root` and `_cache_key`
(`tcw/store/checkouts.py:60-127`) as `cache_folder_3x`; `_override_index`
and the match of `_apply_override` (`tcw/store/fs.py:2281-2289`,
`:2324-2369`, the match at `:2332`) as `override_target_3x(pointer,
sources)`; the owner rule of `get` (`:2405-2420`) and the taxonomy reader's
(`:1796`) as `bare_owner_3x(path, own, sources)`; `route_capability_path`
(`tcw/work/gates.py:331-380`) and `_LedgerReader.term` (`:430-437`) as
`route_entry_3x`; and `resolve_tcw_ref` (`tcw/refs.py:84-125`) as
`link_owner_3x`. **Changes** `tests/test_no_3x_inheritance.py`: its rules
over `tcw/` gain `MIGRATION_CODE = ("tcw/migrate",)`, since the override
match's copy names `_apply_override` (Decided 18), with the reach test. TCW-108's `translate_projects` (P108 Step 4, its Step 8b
parent commit) is read for its mapping, not copied, since this item writes
files rather than translating in the reader.

**Tests first**, `tests/migrate/test_migrate_legacy.py`: each copied reader
on F-full's pieces gives what the golden listing of `f-full.json` records
3.x gave: the owner of each bare reference (`tcw capabilities show <path>
--json` gives its qualified key) and each override's original. 3.x prints
no cache folder and no routing of a `capabilities.yaml` entry to a child,
so `cache_folder_3x` and `route_entry_3x`'s child routing are checked
against expected values written by hand into the fixture from the tag's
code (Decided 3). **Mutation check:** with `override_target_3x` ignoring
the `<alias>/` form, the `core/billing` case goes red.

**Proves it:** the new tests; the full suite.

## Step 16 — related projects, read in either format

Design 1.3, 6.1, 6.5, 6.6, 8.6 (B5's fetch line), 2.10 (the family's 3.x
projects, parents first), B5 narrowed; A7 in a related worktree, A8;
criteria 48, 69 (the exemption).

**Tests first**, `tests/migrate/test_migrate_family.py`, calling
`family.read_family` directly, since a fixture with a related project
holds `projects:` or `extends`, which `part_two_forms` still refuses at the
command until Steps 18 and 19 (the review's S8): a related project
is read in either format and never written (its snapshot unchanged); a
parent named only for its location is not
read (a counting spy on `legacy.read_3x_layers` for its folder); a project
whose content E1 must read and that is not here gives the B5 naming it, its
folder, a `git clone <repository> <folder>` line when a `repository` is
declared, and `tcw project provision` for after; that message is built
by `absent_project_message`, and `tests/test_static_guards.py` passes with
its new `EXEMPT` entry. **Mutation check:** with the entry removed, the
guard goes red naming `migrate/family.py` and the `git clone` string.
The summary's list of
related 3.x projects, parents first, with `tcw -C <folder> migrate`, and A8
for each, are checked through the command in Step 19, once both forms
convert.

**Creates** `tcw/migrate/family.py`: `read_family(root, layers) -> Family`:
each related project located the way 3.x located it (a locator, a
`checkout`, the cache clone) and the way 4.0 would (the planned manifests,
`_search`); read in either format, never written. In this step
`read_family` computes no predicted links: `Family.predicted` is left
empty, since `config.predict_links` does not exist until Step 19, which
adds it and fills the field (the re-check's S4). Each needed and absent
project is B5 with Design 6.5's message, built by
`absent_project_message(project, folder, repository)` (Decided 23).
**Changes** `tests/test_static_guards.py`: `EXEMPT` gains
`("migrate/family.py", "absent_project_message")` with Decided 23's
comment, in the same commit as the function.

**Proves it:** the new tests; the full suite.

## Step 17 — `projects:` becomes `parents:` and `children:`

C3, C6, Design 7's `removed:`, A9 (a `projects:` entry's `jira` block), D6,
B2 (with `projects:` present), B12 (a replaced block's anchor); criteria 21,
27, 17 (the `jira` blocks).

**Tests first**, in `tests/migrate/test_migrate_config.py`, calling
`config.plan_relations` directly, since `part_two_forms` keeps refusing
`projects:` at the command until Step 18 writes the manifest entries that
locate each converted parent and child (Decided 17, the review's M5):
criterion 21's conversions (each result loaded by `parse_parents` and
`parse_children` without a problem); criterion 27's (a `jira` block
dropped, D6, recorded with its file and key; `connected-projects` B2);
several 3.x parents converted in the order written; B12 for a `projects:`
block holding an anchor used outside it.

**Changes** `tcw/migrate/config.py`: `plan_relations`, with
`RemoveTop("projects")`, `SetTop("parents", …)`, `SetTop("children", …)`
(Decided 9); each dropped comment reported; `jira` blocks to the record's
`removed:` (phase A). `part_two_forms` keeps `projects:`.

**Proves it:** the new tests; the full suite (no existing test changes).

## Step 18 — manifest entries, and `projects:` converted by the command

C4 (M1-M6), B3 (manifests), B13, A6, A11; criteria 22, 23, 24, and 21 and
27 through the command.

**Tests first**, `tests/migrate/test_migrate_manifests.py`: criterion 22, one
fixture per row M1 to M6 (an absolute locator to the personal manifest with
the shared entry at M5's path; a URL holding `#` B3; a `repository.path`
not at the end of the locator B3); criterion 23 (the cache clone under
`$XDG_CACHE_HOME/tcw/stores/…` named in the personal manifest and found by
4.0's `project_folder`; absent, A6 naming the folder `tcw project
provision` will fetch into); criterion 24 as written, including A11 with
`TCW_PROJECT_<ID>` set; B13 for a committed `../<name>` folder holding
another project; criteria 21 and 27 as written, through `tcw migrate`, each
converted parent and child found by 4.0's `project_folder` through the
written manifests or the search. The part-1 B5 test for `projects:` is
deleted (allowed list, Decided 17).

**Changes** `tcw/migrate/config.py`: `plan_manifests(family)` writing
`.tcw/tcw-manifest.yaml` and `.tcw/tcw-manifest.local.yaml` in phase D with
the version line; each planned manifest parsed by `parse_manifest` (B3); M6
by `_search` over the planned manifests only (S107 Design 2.4-2.5), never a
parent's manifests and never `TCW_PROJECT_<ID>`. `part_two_forms` loses
`projects:`, in the same commit as `plan_manifests`, so no run converts
`projects:` without writing the entries.

**Proves it:** the new tests; `compare_outcomes.py` with the step's allowed
list; the full suite.

## Step 19 — `extends` becomes parent links

C8 (E1-E5), B4, D1, D8, the load-order check of Design 2.1; criteria 25,
26, 32 (D1), 65 (D1 for `fields.effort`).

**Tests first**, in `tests/migrate/test_migrate_config.py`: criterion 25
(E1-E4 one fixture each; an ancestor added by E4 before the parent it is an
ancestor of; `load_order_of` gives no warning for each); criterion 26 (`p`
then `k` and `k` then `p` give identical files, D6 each time); Design 6.1
(a related 3.x project and the same project already migrated give the
active project the same planned files, through `predict_links`); E5 and a
two-project loop B4; D8 for a family whose load order falls back;
criterion 32's D1 half (a parent setting `work.tags`: D1 names it and the
axes now inherited); criterion 65's last half (a 4.0 parent setting
`fields.effort` differently: D1, and the search and edits still use the
project's own `work.jira.fields`, Decided 11); Step 16's summary and A8
through the command (the family's 3.x projects, parents first, each with
`tcw -C <folder> migrate`). The part-1 B5 tests for `extends` are
deleted.

**Changes** `tcw/migrate/config.py`: `plan_extends(family)` classifying each
target by E1-E5 with `passing` and `find_loop` over the planned links of the
whole family (Design 2.1), `load_order_of` for D8; `RemoveTop`-style removal
of `taxonomy.extends` and `capabilities.extends` (the existing `Remove`
edit, which drops an emptied section); `predict_links`, and
`family.read_family` now filling `Family.predicted` with it for each
related 3.x project (Step 16 left it empty), tested through `read_family`
by Design 6.1's case above. D1 from
`passing` and `INHERITED_KEYS`. `part_two_forms` loses `extends`.

**Proves it:** the new tests; `compare_outcomes.py`; the full suite.

## Step 20 — store locations outside the project

C5 (outside), B6, B7 (with a related project's store), Design 1.4 (files
left in another repository or a cache clone), 6.3; criteria 28, 47.

**Tests first**, `tests/migrate/test_migrate_locations.py`: criterion 28 as
written (each converted location resolving in 4.0, through
`store_location`, to the folder `legacy.store_folder_3x` gave);
criterion 47 with two real git repositories (`app`'s store at
`../docs/app/work` in the workspace converted, its files named under `left
in another repository: <folder>`, `work.path:
tcw://<workspace>.path/docs/app/work`, and the workspace's own run changing
nothing under `docs/app/work`); B7 with a related project's store.

**Changes** `tcw/migrate/config.py` and `stores.py`: the rules of C5; a
store's `repository` kept unchanged; the stores of `store_folder_3x`
converted wherever they sit, each file outside the active project's
repository listed by `git_root` of its folder. `part_two_forms` loses store
paths leading out and a store with only a `repository` (which C5 keeps
unchanged, its folder found as `store_folder_3x` finds the cache clone);
their part-1 B5 tests are deleted.

**Proves it:** the new tests; `compare_outcomes.py` with the step's allowed
list; the full suite.

## Step 21 — overrides

C14, C15, B9, D2, D3, D4, Design 7's `capability-ids` at moved paths and
`moved:`, stop point P4; criteria 38, 39, 40, 61, 32 (D2), and 8 and 9
for the fixtures Step 11 gave an interim B5.

**Tests first**, `tests/migrate/test_migrate_overrides.py`: criterion 38
(bare id, `<alias>/<id>`, `ov/login` overriding `auth/login`, a middle
project; one already at its original's path loses only its key; 4.0's
`tcw capabilities show` gives the fields 3.x showed, from the golden
listing; D3 and D4); criterion 39 (the source migrated: resolved through
its record; record deleted: B9; record naming a path the source no longer
has: B9 with the fix by hand); criterion 40 (each B9 case); criterion 32's
D2 half and C15 for a term; criterion 61 (P4: `move_stops` stopping after
the override folder's move, re-run with no B9). Step 11's two fixtures
holding `overrides: cap-000000` are changed here, in the commit that
removes the form from `part_two_forms` (the review's S8): criterion 9's
fixture now expects B1, B8 and B9 (a pointer that names nothing), and
criterion 8's B5 fixture becomes a true B5 (the pointer's `extends` source
not on this machine). The part-1 B5 test for `overrides:` is deleted; all
three are on the step's allowed list.

**Changes** `tcw/migrate/stores.py`: `plan_overrides(family)`: each pointer
resolved by `override_target_3x` against a 3.x source or through a migrated
source's record (`record.read_record`); the folder `Move` in phase B before
C13's; the state file at the new place without `overrides:`; references to
the old id-path recorded for C16; B9's cases; D2, D3, D4. The record's
`capability-ids` give each id its path after this run and `moved:` each
move. `part_two_forms` loses `overrides:`.

**Proves it:** the new tests; `compare_outcomes.py`; the full suite.

## Step 22 — references owned by another project

C16 for other owners, B10; criterion 41's rows naming another project.

**Tests first**, in `tests/migrate/test_migrate_references.py`: a bare
capability path resolved through `extends`; a prefixed `core/term` to
`core.taxonomy/term`; a `capabilities.yaml` entry routed to a listed child;
a `taxonomy:` entry resolved through the taxonomy store's 3.x rule; a
cross-project `blocked-by: other/<folder>` written by 3.x `--blocks`; a
prefixed reference to an override the source's migration moved, through
its `moved:`; an ambiguous bare reference B10. The remaining part-1 B5 tests
are deleted.

**Changes** `tcw/migrate/references.py`: `owner_of` takes the family and
uses `bare_owner_3x`, `route_entry_3x` and `link_owner_3x`; a moved target's
new id-path from Step 21 or a source's `moved:`. **`part_two_forms` and its
call are deleted.**

**Proves it:** the new tests; `compare_outcomes.py`; `grep -rn
part_two_forms tcw/ tests/` finds nothing; the full suite.

## Step 23 — TCW-114's move keeps the record correct

Design 7 ("It stays correct"), 8.5; criterion 64.

**Tests first**, new cases in `tests/migrate/test_migrate_overrides.py`
only, since a reader's fixture holds `overrides: M/cap-1` and the record's
cases sit beside it (Decided 24; TCW-114's `tests/test_rewrite.py` gains no
case and is run as it stands): criterion 64 as written (`M`
migrated, `cli/x` moved to `cli/y` by `tcw capabilities move`; the record's
`cap-1` value is `cli/y`; a 3.x reader of `M` with `overrides: M/cap-1`,
migrated afterwards, moves its override to `cli/y`; `M`'s own
`ov/login -> auth/login` under `moved:` and a reader's `M/ov/login` becoming
`M.capabilities/auth/login`); a `capability-ids` value below the moved
path rewritten too; a project with no record unchanged; and TCW-114's
every-stop test of a capabilities move run once more on a fixture holding a
record, the record's write counted and explained.

**Changes** `tcw/rewrite.py`, `rewrite_references` (P114 Step 16): when the
active project holds `.tcw/tcw-migration.yaml` and a change is in the
capabilities namespace, every `capability-ids` and `moved` value equal to
the old id-path or below it is rewritten by `rewrite_yaml`, written with
`_atomic_write_all` like the other files; its docstring names the record
as the one file outside the stores it reads.

**Proves it:** the new tests; TCW-114's `tests/test_rewrite.py` and move
tests; the full suite.

## Step 24 — F-full end to end, and the families

Criteria 5-17 and 51 on F-full, 8 for B4, B9, B10's other forms, B12 and
B13 through the command, 9 on F-full's pieces, 45, 46, 48 (as a whole), 50,
61 on F-full, and 66 and 68 on F-full.

**Tests first**, `tests/migrate/test_migrate_f_full.py`: every F-single test
of Step 11 run again on F-full (parametrised over both fixtures, so the two
cannot drift); `move_stops` over F-full; criterion 45 (two orders of the
family, identical files in every project); criterion 46 (the monorepo with
a root and three packages, one Jira-backed with only the required keys:
package first, its `tcw work list` exit 7 naming the root and `work.jira`,
`tcw taxonomy list --scope up` exit 7, the summary naming the root with
`tcw -C <root> migrate`; root next, the listing works; after all four,
4.0's `tcw validate` passes in each, D8 allowed, and each package's
`--scope up` listing equals the golden 3.x listing plus exactly what its D1
and D2 name); criterion 50 (second person: a migrated project with a root
`tcw-config.local.yaml` and a 3.x cache clone: the personal file moved, the
personal manifest entry written, no tracked file changed, no edit; after a
first run with `--no-jira`, every 3.x ticket edited); criterion 51 on F-full
with D1, D2 and D4 taken out as it says.

**Creates** `tests/migrate/golden/f-full.json` and the monorepo's goldens
(Decided 3).

**Proves it:** the new tests; the full suite.

## Step 25 — the whole command proven on this repository

Step 14's procedure again, now that part 2 has landed (Design 9.2: "and
again when part 2 has"), recorded the same way. This repository has no
`projects:`, no `extends` and no `overrides:`, so the result is expected to
equal Step 14's; any difference is read and explained in the round.

It also rehearses Design 9.3 step 3 (the re-check's S9), when TCW-117 has
landed on `v4` by then. In `c1`, after step 2's `T migrate --no-jira`,
delete `UNMIGRATED_RECORDS` from `tests/test_docs_describe_4_0.py` and run
`"$P/venv/bin/pytest" tests/test_docs_describe_4_0.py` bare, with the
credential variables unset and no proxy. Save its output as
`$P/unmigrated-hits.txt` and record the count of hits and the files they
are in, in the implement round. Nothing is fixed here, since the hits are
TCW-118's to fix in the merge clone. Then restore the file with
`git -C "$P/c1" checkout -- tests/test_docs_describe_4_0.py` before step
6's suite. If TCW-117 has not landed, the round says the rehearsal could
not be made, and the TCW-118 comment says so.

## Step 26 — this repository's migration at the merge (Design 9.3)

What is **code and tests in this item**, already built by the steps above:

- the command, `--dry-run` and `--no-jira` (Steps 1-11);
- the both-files rule that ends this repository's configuration pair
  (Design 9.4; criteria 13 and 15, Step 5);
- the request phase F sends, proven against the fake to be the one
  `rename` sends (criterion 65), and the edit-screen check of the dry run
  (criterion 59), which are what Design 9.3 step 6 rests on;
- the way back for the tickets: `set_item_values` with the pairs swapped
  (criterion 65);
- the tests that read this repository's records under either name (Step 12).

What is a **written procedure**, carried out by TCW-118 and proven here only
in part (Design 9.2 steps 1-6 prove 9.3 steps 2 and 3): Design 9.3 steps 0
to 8 and the way back. This step writes it, unchanged in substance, as a
comment on TCW-118 (Step 27), with the concrete commands of Step 14 and
these additions (spec Design 9.3, revised for the re-check's S9): step 2
saves the dry run's output outside the repository as
`tcw116-dry-run.txt`, a cross-check only; step 3 deletes
`UNMIGRATED_RECORDS` and fixes its hits, with Step 25's count, and runs the
suite with the credential variables unset; step 6 saves its own output as
`tcw116-step6.txt`, whose `C17` lines are the edits really made and the
way back's list. The way back for the tickets is a short Python snippet
that parses `tcw116-step6.txt`'s `C17` lines into `(key, new, old)`,
reports any key that is in only one of the two files and stops until a
person has read it, and calls `jira.restore_tickets(pairs, client)`, which
takes the client as an argument (spec Design 5.4; the review's S1): the
implement round runs it once with the fake passed in, never a client
built from a folder, to show it puts every 3.x value back. The comment for
TCW-118 says how to build the real client from `.tcw/tcw-config.yaml` only
for the day it is needed.

**Proves it:** the snippet's fake run, recorded in the implement round.

## Step 27 — notes for the later children

Posted by the dispatching session (the text goes in the implement round
first):

- **TCW-117:** the spec's handoff (Notes, "Handoffs to later items" and
  "Handoff to TCW-117") as written, plus: the line forms of Decided 14,
  which the migration guide quotes; that `--no-jira` is the way to keep a
  run off the live board, and that it leaves the work store out of the
  check after the run; that a run stopped partway names its progress record
  and says `do not save these files in version control until 'tcw migrate'
  finishes`; and that a stopped run re-run while Jira cannot be reached
  writes nothing more and is finished with `--no-jira`.
- **TCW-118:** Step 26's procedure, with the way-back snippet, and the
  spec's "Handoff to TCW-118".
- **TCW-110, TCW-111, TCW-112 and TCW-114:** the spec's handoffs to each,
  posted when this revision is accepted rather than at Step 27, since they
  ask for a shape in code those items build first.
- **TCW-99:** the departure of C5 and decision 4 (a store's `repository`
  stays on the store), as the request's Constraints require.

## Step 28 — Documentation Sync

Each documentation entry, evaluated with the `documentation-sync` skill:

| Entry | Fires? | Answer |
| --- | --- | --- |
| `README.md` [Public-API] | yes: a new command | Deferred to TCW-117, which rewrites the user-facing documents for 4.0 in one pass (TCW-99 design, "How 4.0 is built"); recorded in the implement round. |
| `docs/guide/jira.md` [Jira-Change] | yes: `tcw migrate` edits `TCW Item` | Deferred to TCW-117, with the spec's handoff (exit codes, `--no-jira`, the window in which tickets are hidden). |
| `docs/guide/<topic>.md` [Guide-Topic-Change] | yes: new files TCW writes (`.tcw/tcw-migration.yaml`, the progress record) | Deferred to TCW-117 (the migration guide). |
| `docs/release-notes/upcoming/TCW-116-tcw-4-0-tcw-migrate-from-3-x.md` [Public-API] | yes | Written: `tcw migrate`, `--dry-run`, `--no-jira`, what it converts, that it can be run again to finish, and the migration record. |
| `docs/changelogs/upcoming/TCW-116-tcw-4-0-tcw-migrate-from-3-x.md` [Any-Code-Change] | yes | Written, under Added (`tcw/migrate/`, `JiraBackend.item_values` and `set_item_values`, the three editor edits, `parse_project_file_text`, `parse_state_text`, `collect_findings`, `validate`'s `work` keyword), Changed (`rewrite_yaml`'s `replace`, `rewrite_references` and the record, `_dispatch` skipping its checks for `migrate`, `config_edit`'s edits at any depth), Internal (`tests/migrate/`, `record_file`, the goldens, their script and the fixture-digest check, the frozen configuration copy, the three guards' `tcw/migrate` exemptions, the git-word guard's one entry and the git-write scan's new folder, `move_stops`'s callable form if added). |
| `skills/<component>/SKILL.md` [Skill-Driven-Component] | yes: the `setup` and `work` skills name how a 3.x project is upgraded | Deferred to TCW-117. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no | No configuration key is added, removed or changes meaning. |
| `docs/use-cases.md` [Project-Setup-Change] | yes: S-8 and S-9 | Deferred to TCW-117, as the spec's handoff says. |

## Step 29 — the suite as CI runs it

Bare `.venv/bin/pytest` from the worktree's root. A failure is fixed in the
step it belongs to, not with a skip.

## Verification the tests cannot do

- **Design 9.2's proofs** (Steps 14 and 25): on scratch clones, with the
  live board read by the dry run only. Recorded in the implement round.
- **The live board is never written** (criterion 55): every real run of the
  proofs uses `--no-jira` or has the credentials unset, behind the
  unreachable proxy, with the `v4` `tcw` named by its full path; the dry
  run's own request log shows no `PUT` and no `POST` but the search's.
  Checked by the round's commands and that log, since no test can observe
  the live board; criterion 66's structural guard backs it.
- **The user's two setups** (Design 9.5, criterion 56): at qa, `tcw migrate
  --dry-run` with the `v4` code in each, run by or with the user; the
  counts, reports and blockers recorded in the qa findings without naming
  either.
- **The QA plan's scenarios** are run at qa by hand with the scratch clones
  and the suite's fixtures, as the QA plan comment lists them.
- **A ticket edit refused for some tickets only** cannot be produced by the
  fake per ticket permission; the re-run path is the same as criterion 12's
  and is not tested separately (QA plan, "Not tested").
- **Step 14's `chmod` stop** depends on the user not being an administrator
  account that ignores permissions; the round says how the stop was made.

## Self-review against the spec

Every criterion and the step that checks it:

| Criteria | Step |
| --- | --- |
| 1, 2, 3 | 1 (2's dry-run lines and exit with the full plan: 11) |
| 4, 49 | 11 |
| 5, 6, 7, 10, 11, 14, 16, 17 | 11 (F-single), 24 (F-full); parts in 3, 6, 7, 9 |
| 8 | 11 (part 1's blockers, B10's "no ledger" form from Step 8, B17 in both forms), 21 (the B5 fixture made true), 24 (B4, B9, B10's other forms, B12, B13 through the command); each blocker's fixture in the step that adds it |
| 9 | 11 (interim, with a B5), 21 (as written, with B9), 24 |
| 12, 43, 44, 57, 58, 59, 65, 66, 68 | 9 (57's and 66's check after the run: 10; 65's D1 half: 19; 66 and 68 on F-full: 24) |
| 13 | 5 (configuration), 6 (state files) |
| 15, 18, 19, 20, 29, 30, 31, 63 | 5 (15's and 63's frozen copy: 4; 29's `jira` block half: 17) |
| 21, 27 | 17 (the conversions), 18 (through the command) |
| 22, 23, 24 | 18 |
| 25, 26 | 19 |
| 28, 47 | 20 |
| 32 | 19 (D1), 21 (D2) |
| 33, 34, 35, 36, 42 | 6 |
| 37 | 7 |
| 38, 39, 40, 61 | 21 (61 on F-full: 24) |
| 67 | 2 (TCW-110's and TCW-111's guards, TCW-112's test-file rule), 15 (TCW-112's `tcw/` rules) |
| 41 | 8 (own), 22 (other owners) |
| 45, 46, 50 | 24 |
| 48 | 16 |
| 51 | 11, 24 |
| 52 | 13 |
| 53, 54, 55 | 14, 25 (54's code: 12; 55: Verification) |
| 56 | Verification (qa) |
| 60 | 11 (mechanics, the deletion's own digest and P5's refusal: 3) |
| 62 | 8 |
| 64 | 23 |
| 69 | 1 (the git-write scan), 3 (the stopped run's message), 16 (B5's exemption) |

Design rules with no criterion of their own: where 8.2's readers live is
Steps 2 and 15 (its exemptions are criterion 67); 8.3 is
Step 13; 9.3 is Step 26; 9.5 is Verification. Steps 0, 4 and 27-29 trace to
no single criterion: Step 0 is the starting check, Step 4 the editors the
conversions use (Design 2.8), and 27-29 the closing steps the stage
requires.

The suite stays runnable at each boundary: Steps 1 to 10 add code that
nothing outside `tcw/migrate/` calls except the registered command, whose
behaviour each step widens with its own tests; the only existing tests
changed are `tests/test_cli_help_standard.py` (Step 1),
`tests/work/test_git_write_scan.py` (Step 1, `SCANNED` gains the package),
`tests/test_static_guards.py` (Step 16, one `EXEMPT` entry), TCW-114's
`tests/test_ownership_sweep.py` (entries for `tcw/migrate/` functions, in
the step that writes each, Decided 25), the three
siblings' guards `tests/test_identifier_sweep.py`,
`tests/test_object_folder_sweep.py` and `tests/test_no_3x_inheritance.py`
(Steps 2 and 15: an exemption constant and its reach test each, after any
reshaping into a function of a root folder, which the safeguards show
changes no outcome), `tests/move_stops.py` (Step 3, a callable form added
beside the command form, only if Step 0 finds none), the editor's and
rewrite's tests (Step 4, additions), the records tests (Step 12, through
the safeguards), and none of TCW-114's rewrite tests (Step 23's cases are
all under `tests/migrate/`, Decided 24). The one
change to existing code a step's tests could feel is Step 10's
`validate(work=True)` keyword, whose default keeps every caller as it is.
Step 9's criterion 66 test stays green at Step 10 because the check after
the run is called with `work=False` under `--no-jira` (Decided 13); each
part-2 step deletes only the part-1 refusal test of the form it now
converts, and Step 21 changes Step 11's two `overrides:` fixtures, through
an allowed list.

## Spec issues found while planning

The five issues the first draft listed here were accepted by the plan's
review and are now in the spec (revised 2026-10-22): two methods in Design
5.4 (issue 1); criterion 5's count widened to the search's pages, the
field-id reads and no `PUT` or other `POST`, in Design 2.1 and criteria 5
and 14 (issue 2); criteria 8 and 9 split between the parts in "The two
parts" (issue 3); phase A's order in Design 2.4 and P2 (issue 4); and
Design 9.2 step 4's folder chosen so that phase B moves nothing into it,
with the comparison made on the files git would track (issue 5). None is
open.

## Revision 2 (2026-10-22): what changed after the plan's review

Each decided by the dispatching session, 2026-10-22, for the reason given
in the decision or step named. The review's must-fix items:

- **(a) M1**, the siblings' guards: Decided 18, Steps 0, 2 and 15,
  criterion 67, and the handoffs to TCW-110, TCW-111 and TCW-112 (spec).
- **(b) M2**, copy from `v3.0.2`: Decided 2, Steps 0, 2 and 15.
- **(c) M3**, a deletion's own digest: Step 3 (`Delete.digest`, `state`,
  its tests), criterion 60.
- **(d) M4**, Jira settings once the project is 4.0: Decided 11,
  `legacy.own_jira_layers` (Step 2), Step 9, criterion 68.
- **(e) M5**, `projects:` not allowed before the manifests: Decided 17,
  Steps 17 and 18.
- **(f) M6**, no test reads the root configuration: Decided 20, Steps 0, 4,
  5 and 12.
- **(g) M7**, the proof's comparison: Step 14.

The should-fix items: S1 (Decided 19, Step 9, Step 14, Step 26), S2 (Step
14), S4 (Step 5), S5 (Decided 22, Step 11), S6 (Decided 3), S7 (Decided 9,
Step 4), S8 (Decided 17, Steps 11, 16, 17, 18, 20, 21), S9 (Decided 7,
Steps 0 and 3), S10 (Decided 4, Step 3). S3 is moot: the copy across
filesystems it repaired is removed (D1). The decisions: D1 (spec Design
2.5, Decided 7, Step 3, criteria 60 and 61), D2 (Decided 3), D3 (Decided
13, Steps 10 and 11, criterion 51), D4 (Decided 16). The review's questions:
1 (Decided 3, Step 15), 2 (Step 0 item 8, Step 3), 3 (Decided 11), 4
(B10's "no ledger" form, Step 8), 5 (Step 11's `overrides: cap-000000`).
Its notes: the `OSError` message (Decided 21), `remote=False` (Decided
13), the fixtures' `site` (the opening rules).

## Revision 3 (2026-10-22): what changed after the plan's re-check

Each decided by the dispatching session, 2026-10-22, for the reason given
in the decision or step named. The re-check's must-fix items:

- **N1**, the check after the run built the Jira backend: Decided 13
  (`work=False` under `--no-jira`), Step 10, spec Design 1.1 and 2.1,
  criteria 57 and 66.
- **N2**, the Jira half of a run that follows a progress record:
  Decided 19 (`plan_jira_half`, `JiraHalf.apply`), Steps 3 (the record's
  `project` and `work_backend`), 5 and 9, spec Design 2.7, criterion 66.
- **N3**, the git-word guard: Decided 23, Steps 1, 3 and 16, spec Design
  8.6, criterion 69.

D2, the recording of the goldens: Decided 3 (a script run by hand, with a
network check before pip, the dead proxy only for the `tcw` runs,
`pip freeze`, placeholders for temporary paths, and a fixture digest the
suite checks), Step 2.

The smaller items: S1 (spec Design 8.2, criterion 67), S2 (Decided 25),
S3 (Decided 24, Steps 4 and 23), S4 (Steps 16 and 19), S5 (the opening
list's `config_edit` lines, Step 0 item 2), S6 (Decided 3), S7 (Decided
11, Step 9), S8 (Decided 19, spec Design 1.1, criterion 66), S9 (spec
Design 9.3, Steps 25 and 26). And the re-check's note on
`tests/work/test_git_write_scan.py` (Decided 23, Step 1). None is
deferred.

### QA plan amendment

Changes to the ticket's QA plan, for the dispatching session to post with
the rest of this revision:

- **What you need:** run the `v4` TCW by the full path of its virtual
  environment's `tcw` in every step; a bare `tcw` is the 3.0.2 that drives
  this project, which has no `migrate`.
- **Scenario 2 (stop and finish):** pick a folder the run writes into and
  moves nothing into (an item folder with no loose file); compare the two
  copies by the files git would track and their contents (`git ls-files
  --cached --others --exclude-standard` with a digest of each), not by the
  raw folders, which differ in build leftovers such as `*.egg-info` and
  `__pycache__`. Add: with the folder made writable again and one of the
  old `meta.yaml` files then edited by hand before the second run, the
  second run refuses (exit 3), names that file, and the edit is kept.
- **Scenario 2 (no Jira):** add: runs made with `--no-jira` also have the
  proxy set to an address nothing listens on, and the dry run's requests
  are logged; the log holds no change to a ticket. A `--no-jira` run's
  summary says the work store was not checked after the run; `tcw
  validate` then checks it.
- **Scenario 2 (stop and finish), with Jira down:** add: a run stopped
  partway and run again without `--no-jira` while the proxy points
  nowhere exits 5, writes nothing more, and names `tcw migrate --no-jira`;
  that run then finishes the files. The stopped run's message reads `do not
  save these files in version control until 'tcw migrate' finishes`.
- **Scenario 3 (refusals):** the examples given (two overrides of one
  capability) need the part of the command that converts related projects;
  until it lands, use a folder named with a dot and an unknown
  configuration key.
- **Not tested:** add: a move across filesystems (a store with a mount
  point inside it) is refused with a message and finished by moving the
  folder by hand; it is shown by the suite with a simulated error, not on a
  real second filesystem.
