# Implement round 1 — TCW-114

Built on the branch `v4`, from `bab05f37`, in the worktree
`.claude/worktrees/v4`. The code under test was run from that worktree's own
virtual environment (`.venv/bin/pytest`; hand runs of `tcw` only through a
wrapper, against scratch projects, never this repository). No lifecycle command
was run and no ticket was moved or written to: the dispatching session makes
every move. The released 3.0.2 `tcw` was used only to read (`tcw work stage
prompt implement TCW-114`, `tcw work show TCW-114`, and `tcw validate`, which is
offline, on this repository's 3.x ledger). This is the first implement round,
so it answers no rejection. It gives no verdict.

## Commits

| Commit     | Steps                                                                                                                                         |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `d500ff15` | 0, 1, 2: the starting point, the outcome record of the suite, the ownership check, and the rule that only read-only `git rev-parse` runs      |
| `9bd66698` | 3: every CLI writer calls the check before the other project is read                                                                          |
| `1941a3e9` | 4: the web router checks a route marked `writes` before it runs                                                                               |
| `832be00c` | 5, 6: `tcw -C` by path and by folder address; the test command checkers learn `-C`                                                            |
| `3c13037d` | 7: `--project` and `--blocks` refused, naming `tcw -C`; delegation removed, CLI and server; the passages that wrote a removed option          |
| `8d48870b` | 9: the one table of reference fields                                                                                                          |
| `2fda9e65` | 10: the checkers read the table                                                                                                               |
| `1e45fd0e` | 11: code spans located, not deleted                                                                                                           |
| `e3986868` | 12: the fake Jira's three switches                                                                                                            |
| `520b6a5a` | 8: the web client loses the project selector, "Blocks (add)" and `readOnly` (done after Step 12, once the server half was in)                 |
| `f9cce299` | 13, 14, 15: recorded Jira parents and blockers, read and validated                                                                            |
| `753a6224` | 16: the repository's references rewritten, and mentions listed                                                                                |
| `02f74121` | 17, 18, 19: the backend `move`, `tcw work rename` through it, `tcw work move`, the tree stores' `move` and their `rename` and `move` commands |
| `3d82fe67` | 20: shipped text                                                                                                                              |
| `c1836372` | 21: the sweep guards                                                                                                                          |
| `2c20da47` | 22: this repository's ledger                                                                                                                  |
| `ab95282e` | 24: the release note and changelog entries                                                                                                    |
| `ad4ee222` | 24: the guides and the work skill say what `rename` prints (see decisions)                                                                    |

**Steps combined, and how each per-step comparison was kept.** 1 and 2; 5 and
6; 13 to 15; 17 to 19 (the commands, the contract rows and the ownership rows
are in the same files, so splitting them would have left commits that do not
pass). Each step still ran the tests it names. The per-step outcome
comparisons (the suite's record against the Step 1 record) were run at Step 7
and at the end; the end one covers the whole item with every removed test
named, which is the equivalent the plan's Step 25 describes. Step 8 came after
Step 12 because its client change depends on the server's answer from Step 7
only; nothing in Steps 9 to 12 depended on it.

## What was done, step by step

- **Step 0.** TCW-106 to TCW-112 are on `v4`. The process record of Step 0
  (`git` commands TCW runs) is kept in the scratchpad.
- **Step 1.** The suite's outcome record before any change: 2006 tests in
  `tests/work tests/serve`, 4660 in the rest; the recording plugin.
- **Step 2.** `tcw/ownership.py`: `check_owned`, its one refusal shape, and
  `active_project_id`. Locating the owner only words the refusal.
- **Step 3.** `resolve_item(writing=True)` and `find_tree_writable` run the
  check for every CLI writer, before the other project is read.
- **Step 4.** The route table's `writes`; `check_writes` answers 403 before the
  handler runs.
- **Steps 5, 6.** `tcw -C <folder>` and `tcw -C tcw://<id>.path/…`, repeatable;
  the folder is given back afterwards, on a broken pipe too.
- **Step 7.** `--project` and `--blocks` are hidden and refused, naming
  `tcw -C` and `--blocked-by`; delegation and the code that only served it are
  removed; every passage that wrote a removed option as a command names one
  that works.
- **Step 8.** The web client has no project selector, no "Blocks (add)" and no
  `readOnly`; `GET /api/project` lists no connected projects. Rebuilt
  `tcw/serve/dist`.
- **Steps 9, 10.** `tcw/reference_fields.py`; every reference checker reads it.
- **Step 11.** `code_spans` and `links_outside_code`.
- **Step 12.** The fake Jira's `fail_edit`, the hook before each request, and a
  hidden ticket.
- **Steps 13 to 15.** A parent or blocker that is not a ticket on this Jira site
  is recorded in the item's state file and reported; `show`, `list` and
  `list --parent` read it; `tcw validate` checks it offline, and `--remote`
  reports a ticket with both a Jira parent and a recorded one. Jira sites are
  compared by host, ignoring letter case.
- **Step 16.** `tcw/rewrite.py`: `rewrite_yaml` keeps quoting, comma lists and
  `!`; `rewrite_links`; `rewrite_references`; `mentions`.
- **Step 17.** The backend operation `move(id_path, new_id_path,
before_folder)` in both backends and the memory backend; `tcw/move.py`'s
  order (checks writing nothing, the backend's own writes, the repository's
  references, the folder last, then tidying); the stop message; `tcw work
rename` through it, nested items included. The tests that tested the old
  `rename` were rewritten in place: they are listed with a reason each in
  [`rewritten-tests-step17.txt`](rewritten-tests-step17.txt).
- **Step 18.** `tcw work move <item> --into <id-path> | --top`, AC 13, AC 14 and
  AC 25's move half; the xfail on AC 1's move row is gone.
- **Step 19.** `move` on both tree stores, with `report=`; `tcw taxonomy
rename|move` and `tcw capabilities rename|move` (`tcw/move.py`
  `add_tree_commands`); `tests/test_tree_move.py` (AC 15 to AC 17, AC 19 to
  AC 21, AC 25's tree half, AC 26's rename half for every table row and an
  added row, every stop of a taxonomy rename and of a capabilities move); the
  two tree xfails in `tests/test_owning_project.py` are gone. An id-path with
  no own object and no readable view is exit 4, as `rm`'s is (TCW-112).
- **Step 20.** Step 6 of the plan prompt and `docs/lifecycle/abstraction.md`
  (see the combined review below); the prompt fallback fixture recaptured, and
  only step 6 differs.
- **Step 21.** `tests/test_ownership_sweep.py` and `tests/write_callers.py`;
  the `@writes` marker on the eleven write methods. The site list is below.
- **Step 22.** Five new capabilities, the thirteen changed ones, the new
  `owning-project` term, `reference` and `project`, in their 3.x form.
  `tcw validate` (3.0.2) on this repository: 0 errors, 0 warnings, 0
  unresolved.
- **Step 23.** The handoff notes are below, for the dispatching session to
  check on each ticket.
- **Step 24.** Documentation Sync, below.
- **Step 25.** The suite and the web checks, below.

### The combined review of the plan prompt (Step 20)

`git diff 07161cea~1 -- tcw/work/prompts/plan.md` (TCW-111's change and this
item's together): step 6 now reads, in order, the `--nest` split with
TCW-111's wording kept, a part for another project made there with `tcw -C …
--parent <slug> --nest`, `--blocked-by` set the same way, and the recorded
parent Jira cannot link. Nothing of the 3.x sentences remains (the printed
ticket key, setting `--parent` afterwards, uncommitted changes). The one
difference from the plan's text, "this item is the parent", is TCW-111's
sentence saying the same thing ("`--parent`, not the folder, is what makes it
a part"), kept as the plan allows.

## Decisions (each decided by the implementing agent)

| Decision                                                                                                                                                                       | Reason                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The web routes' `written_item` takes the route's key as written: a full identifier is checked; any other key names an item of the served project                               | Another project's item is refused before any backend is opened, and a bare key cannot name another project's item, so looking it up would only cost a read                                                                 |
| The registry's `read_only_reason` and its helpers are removed, not renamed                                                                                                     | Nothing but the removed `read-only` key and delegation called it; provisioning on `v4` has no caller (the plan's `_connected_declarations` does not exist), so there was nothing to keep                                   |
| A bare value in `capabilities.yaml` is reported as a TCW 3.x reference naming `tcw migrate`                                                                                    | The table's capabilities-yaml rows check the same way as every other field; a probe of every row is in the scratchpad                                                                                                      |
| `fail_edit` takes `then_unreachable` and `status`                                                                                                                              | A dropped connection after an edit, and a 400 against a 500, are different stops (exit 1 against exit 5)                                                                                                                   |
| The taxonomy checkers keep their own loops, reading only the field names from the table                                                                                        | `vocabulary` counts only on a Feature, a rule of the kind, not of the field                                                                                                                                                |
| `_place` opens the project with `open_project`, `personal=False`, through the command's registry                                                                               | The site of another project is its committed configuration's, the same for every clone                                                                                                                                     |
| AC 12's "exit 1" for a failed `TCW Item` edit is met with a 400 answer; a 500 is exit 5                                                                                        | 5xx answers already mean Jira cannot be reached (exit 5) everywhere else; the fake gained `status=` to test both                                                                                                           |
| The web half of the recorded-references tests covers create only; PATCH stays 403                                                                                              | The page edits no Jira item's properties                                                                                                                                                                                   |
| The `Reviewed by` added-row test monkeypatches the files backend's `KEYS`                                                                                                      | The item model reads only the keys it knows, so a new row needs a key to read                                                                                                                                              |
| The backend's "wrote" and "already names" report lines feed the stop message                                                                                                   | They are what was written by this run or an earlier one; collected through the report rather than returned                                                                                                                 |
| The clash advice is a function, `clash_advice`, exempt from the guard against git words                                                                                        | The spec requires "pull its commit": a move made in another clone reaches this one only that way, and the guard exempts by function                                                                                        |
| `advance()`'s own comparison of project IDs (`tcw/work/advance.py:253`) is kept                                                                                                | It is the "not an item of this backend" step of 3.0's Design 6.2, reached only after `resolve_item(writing=True)` has run `check_owned`; replacing it with `check_owned` broke every direct caller that passes a bare root |
| The `projects list --json` help no longer names `read-only`                                                                                                                    | The key is gone (Step 7)                                                                                                                                                                                                   |
| Three places that said `rename` prints the new slug now say it prints `<old> -> <new>` lines (`docs/guide/cli.md`, `docs/guide/work.md`, `skills/work/references/commands.md`) | Left alone they state a wrong output; nothing else in them is changed, and teaching the move commands stays TCW-117's                                                                                                      |
| The helper's Step 17 list was not used as a list of removed tests                                                                                                              | Every test on it still exists under its own ID; it lists tests rewritten in place                                                                                                                                          |

No decision contradicts the spec.

## Mutation checks

Each mutation was made, the named tests went red for the reason given, and the
code was restored.

- Step 2: the error order in `_where` swapped: the unknown-project test red
  ("cannot be located" for an unknown project).
- Step 4: the router's `check_writes` call removed: 9 of 14 request-level tests
  in `tests/serve/test_route_writes.py` red; the route-list tests stayed green.
- Steps 5, 6: the run-as and the folder restore removed: 5 tests in
  `tests/test_run_in_folder.py` red.
- Step 10: the capability `Roles` row removed by a plugin: the table's Roles
  case, `test_check_unresolved_role_slug` and three `rm` refusals red ("no
  finding reported", "DID NOT RAISE").
- Steps 13 to 15: `_items` without the recorded parent (2 red); `same_site` as
  exact text (2); `update` not clearing the Jira parent (2); the placement
  error loop off (1); the web report not collected (1); the remote
  both-parents check off (1); the jira-item `blocked-by` row removed (3).
- Step 16: the `Roles` row removed (4 red: values left unrewritten); the
  `taxonomy.changed` row removed (2).
- Step 17: the files backend moving the folder before `before_folder` (4 red:
  references left unrewritten); the Jira move not reading a ticket again
  before its edit (2 red: AC 12's two clash tests overwrite instead of
  refusing); the stop advice always "run again" (the same 2 red).
- Step 21: a scratch module with an unlisted writer caller, a `Path.cwd()`
  read, a `blocks_target(` call and a store `rename` (4 red, one per guard);
  `@writes` removed from `WorkBackend.comment` (2 red).

## The site list (Step 21, from a fresh search after Step 20)

1. **Write sites and their check.** CLI: `work edit`, `comment`, `advance`,
   `discard` run `resolve_item(writing=True)` (`tcw/work/cli.py:53`, calling
   `check_owned` at `:69` and `:72`); `work rename` and `move` through
   `tcw/move.py` `_work_target`, and a `--into` given as a full identifier at
   `tcw/move.py:167`; `taxonomy rm`, `capabilities rm` and the four tree
   `rename`/`move` commands through `find_tree_writable` → `removal_target`
   (`tcw/store/fs.py:1968`, `:1981`); `capabilities set` and `reset` through
   `override_target`, which calls `_not_inherited` (`tcw/store/fs.py:2900`,
   `:2906`), whose `check_owned` is at `:2122`. Web: the seven routes marked
   `writes=written_item` or `_written(...)` (`tcw/serve/files.py:387-390`,
   `tcw/serve/records.py:324`, `:329`, `tcw/serve/work.py:626-627`), checked
   by `tcw/serve/server.py:237`. `generate:` bindings and hooks write only
   inside the item's folder, run with `cwd` the project root. **Creators**,
   with no call: `tcw work new` (`new_item`), `tcw work tickets adopt`,
   `tcw taxonomy add`, `tcw capabilities add`, and the web's
   `POST /api/work`, `/api/taxonomy`, `/api/capabilities` and
   `/api/tickets/<key>/adopt` (`writes=creates`): each writes only the
   active project's store. The guard's list holds all of these, each with
   its check or reason, and 29 calls on sets, dicts and an event, each named.
2. **Comparisons of `.project`.** Every one left is a read: which project an
   identifier is in, for a link, a parent's nesting, a list filter, a
   warning, or Jira placement. The one that refuses is `advance.py:253`, kept
   as above. `_own`, and `tcw/serve/work.py`'s two comparisons, are gone.
3. **Removed names.** None of `delegate`, `open_for_update`,
   `blocks_target`, `delegate_to_jira`, `uncommitted_changes` or
   `_cannot_make_item` is defined or called in `tcw/`, `web/client/src/`,
   `scripts/` or `evals/`; no route ends `/blocks`; no "Jira links only
   tickets on one site"; no `def rename` in a backend or store class (the one
   `def rename` in `tcw/` is the command handler in `add_tree_commands`); no
   reader of `read-only` or `readOnly` (the 403 answer's error kind
   `read-only` in `tcw/serve/server.py:63` is a name the server sends, read by
   no code).
4. **Readers of reference fields.** `tcw/store/fs.py`, `tcw/work/references.py`,
   `tcw/work/fs_backend.py`, `tcw/work/jira/backend.py`, `tcw/work/jira/remote.py`,
   `tcw/serve/records.py` and `tcw/rewrite.py` all read `tcw/reference_fields.py`.
5. **A Jira item's `parent` and `blocked-by`.** Written through `_place`,
   `_item_file` and `_record`; read through `recorded_references` in `_items`,
   `list --parent`, `recorded_problems` and `remote.py`.
6. **Reads of the current folder.** `cli.py` `run_init` and `main`,
   `projects_cli.py` `_list`, `config_cli.py` `_show`, `project_files.py`
   `find_marker`, `output.py` `shown`, `work/cli.py` `project_root` and
   `_procedure`, `store/project.py` `_resolve_override`, `store/fs.py`
   `git_root`: Design 11's ten, plus `main`'s `os.getcwd()`, which saves the
   folder `-C` gives back. The guard holds this list.
7. **Configuration keys.** None holds an object reference: `work.path` and the
   store paths hold folders or folder addresses, which a move does not change;
   `work.stages`, `work.documentation`, `work.procedures`, the hooks and the
   Jira block hold no identifiers.

## Handoffs (for the dispatching session to check on each ticket)

- **TCW-113:** every write route is marked in the route table with `writes`,
  and the router checks it; a route TCW-113 adds is marked the same way.
  `GET /api/project` carries no connected projects at all now (no `projects`
  key, no `readOnly`); TCW-113's views of other projects bring back what they
  need.
- **TCW-115:** the refusal's tail for a project not on this machine can add
  `tcw project provision <id>` in `check_owned`, its one place.
  `read_only_reason` is removed; provisioning on `v4` never called it, so no
  rule needs keeping there.
- **TCW-116:** a move refuses while a ticket holds a 3.x `TCW Item`, naming
  `tcw migrate`; this repository's own tickets are refused until migrated. The
  ledger records this item wrote are in the 3.x form, to convert with the
  rest: five new capabilities and the `owning-project` term. A Jira item's
  state file may now hold `parent` and `blocked-by`; a 3.x file never does, so
  migration has nothing to convert there.
- **TCW-117:** beyond the spec's list: `tcw -C` in `docs/guide/cli.md` and the
  global options; `tcw work move`, `tcw taxonomy rename|move` and `tcw
capabilities rename|move`, and that `rename` carries nested items; that a
  Jira-mode create form now accepts blockers in other projects, recorded; the
  removal of `report_mentions` changes nothing a user sees. The passages
  changed here only as far as naming a working command, to rewrite for 4.0:
  `README.md`, `docs/guide/cli.md`, `docs/guide/jira.md`,
  `docs/guide/multi-repo.md`, `docs/guide/work.md`, `docs/use-cases.md`,
  `skills/capabilities/SKILL.md`, `skills/configure/references/projects.md`,
  `skills/work/SKILL.md`, `skills/work/references/commands.md` (Step 7), and
  the `rename` output in `docs/guide/cli.md`, `docs/guide/work.md` and
  `skills/work/references/commands.md` (`ad4ee222`). Still describing
  "read-only from here", which 4.0 no longer has as a separate idea:
  `docs/guide/cli.md:145`, `:156`, `docs/guide/multi-repo.md:89`, `:154`.
- **TCW-118:** CI does not run on `v4`, so Step 25 was run locally; the live
  Jira scenario (`tests/work/jira/scenario.py`) now expects `rename` to print
  `<old> -> <new>`, and it has been run only against the fake here, so it
  should be run against a real site before the release.

## Documentation Sync

| Entry                                                                  | Fires? | Answer                                                                                                                                                   |
| ---------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md` [Public-API]                                               | yes    | The removed option's cell changed in Step 7; the rest is TCW-117's 4.0 rewrite (handoff above).                                                          |
| `docs/guide/jira.md` [Jira-Change]                                     | yes    | Changed in Step 7 as far as naming a working command; the rest TCW-117's.                                                                                |
| `docs/guide/<topic>.md` [Guide-Topic-Change]                           | yes    | `cli.md`, `work.md`, `multi-repo.md` changed in Step 7 as far as naming a working command, and the `rename` output corrected; the rest TCW-117's.        |
| `docs/release-notes/upcoming/<folder>.md` [Public-API]                 | yes    | Written.                                                                                                                                                 |
| `docs/changelogs/upcoming/<folder>.md` [Any-Code-Change]               | yes    | Written.                                                                                                                                                 |
| `skills/<component>/SKILL.md` [Skill-Driven-Component]                 | yes    | Changed in Step 7 as far as naming a working command, and the `rename` output corrected; teaching `tcw -C`, `move` and the nested `rename` is TCW-117's. |
| `skills/configure/references/<document>.md` [Configuration-Key-Change] | no     | No configuration key is added or changed; `projects.md`'s two lines changed in Step 7.                                                                   |
| `docs/use-cases.md` [Project-Setup-Change]                             | yes    | UC-3 and UC-4's two sentences changed in Step 7; the requirements' rewrite is TCW-117's.                                                                 |

## Suite and web checks (Step 25)

- `.venv/bin/pytest tests/work tests/serve -q -p no:cacheprovider`:
  **2064 passed, 2 skipped**.
- `.venv/bin/pytest tests --ignore=tests/work --ignore=tests/serve -q -p
no:cacheprovider`: **4750 passed, 111 skipped**.
- The outcome comparison, the Step 1 record against these two runs: 0 problems
  in either half. 74 tests are gone on purpose, each with its reason in
  [`removed-tests.txt`](removed-tests.txt); 335 tests are new, all passing.
- `pnpm install --frozen-lockfile`, `pnpm test` (198 passed), `pnpm exec tsc
--noEmit`, `pnpm lint`, `pnpm build`, `pnpm check:build`: all pass.
- `prettier --check` over every file this item's commits added or changed:
  `skills/work/references/commands.md` was the one this item left
  unformatted, and is fixed; the other files it reports were unformatted
  before this item and are left as they were.

## Not done

- No live Jira run (the rules forbid it); the scenario is for TCW-118 above.
- The user-facing documents' 4.0 rewrite, deferred to TCW-117 as the spec
  says.
- No commit was pushed, no ticket moved, nothing posted.
