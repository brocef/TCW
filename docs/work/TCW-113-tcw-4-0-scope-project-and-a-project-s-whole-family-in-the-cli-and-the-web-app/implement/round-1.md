# Implement round 1 — TCW-113

Built on the branch `impl-113`, made from `v4` at `78c88809`, in the worktree
`.claude/worktrees/impl-113`. The code under test was run only from that
worktree's own virtual environment (`.venv/bin/pytest`). Hand runs of `tcw` went
only through a wrapper, against scratch projects, never this repository. No
lifecycle command was run, and no ticket was moved or written to: the
dispatching session makes every move. The released 3.0.2 `tcw` was used only to
read (`tcw work stage prompt`, `tcw work show`, `tcw work docs`), to create this
repository's records in Step 18, and for `tcw validate`, which does not read
Jira. This is the first implement round, so it answers no rejection. It gives
no verdict.

## Commits

| Commit     | Steps                                                                                          |
| ---------- | ---------------------------------------------------------------------------------------------- |
| `a6ad62b9` | 1, 2: the starting outcome record; `tests/families.py`, the family fixture                     |
| `da641380` | 3: `scope_members` and `covering_scope` on the registry                                        |
| `dd938e5a` | 4: `tcw/scope.py`, each other project read inside one catch                                    |
| `5e746e8b` | 5, 6: `tcw work list` and `show` across a scope, `children` and `blocks` across it             |
| `5a41dac3` | 7: a Jira search kept for one command, keyed by site, account, token digest, text and fields   |
| `8d802aff` | 8: `scope_rows`, `statuses` and `overridden-by`, from plain data                               |
| `c0b20a86` | 9: `--scope` and `--project` on the six taxonomy and capability commands                       |
| `f8639169` | 9 (fix found by Step 10): a scoped show keeps its hints; ungrouped listings keep today's order |
| `98acbe06` | 10: tests that read inherited content say `--scope up` (by script)                             |
| `bb06cf7d` | 10: the calls the script could not reach (by hand)                                             |
| `d0997e59` | 11: `own` is the default                                                                       |
| `b32a74e4` | 12a: tests stop passing `--local` (by script)                                                  |
| `42c40e93` | 12b: `--local` refused with what to use instead; the passages that named it                    |
| `b203f55b` | 12b: the 3.0 migration guide's `list --local` named as removed                                 |
| `fbf8ef2c` | 13: the web server's read routes take `scope` and `project`; lists answer an object            |
| `200fb1e1` | 14: another project's object read from its owner; write handlers stay in the served project    |
| `be76073e` | 15: the web app's scope control and project filter, kept in the URL                            |
| `fc3cab61` | 16: read-only display with the owner, followed links, unavailable notices, status counts       |
| `169ca954` | 17: the backlog audit covers the family and names items by full identifier                     |
| `80222b6f` | 18: this repository's records                                                                  |
| `f870a5b6` | 19: the upcoming changelog and release-notes entries                                           |

Steps 20 and 21 are this file: the notes for later items, and the final
suite. Steps 5 and 6 were combined because `show`'s `children` and `blocks`
and `list --json` share one piece of code. The per-step comparison was kept as
one comparison, Step 1's record against Step 6's, over both halves of the
suite, with 0 problems and nothing deleted.

## Each step

**Step 1.** Starting suite, in two halves: 2064 passed and 2 skipped; 4750
passed and 111 skipped.

**Step 2.** `build_family` takes `docs_passes` with no default value, so each
test says what the family's documentation links pass down. The server's backend
is chosen by calling `jira_mode()`, not by a parameter. Items start at
`request`, so `tcw validate` on the fixture gives no warnings.

**Step 3.** `scope_members` refuses an unknown scope with a usage error (in the
CLI the argument parser refuses it first; the web server answers 400).
Mutation: taking the last child instead of the first from the queue turned the
breadth-first test red, after it was strengthened with a child under each of
two projects.

**Step 4.** `tcw/scope.py` was written together with its tests, since tests of
a module that does not yet exist can only fail on the import. Each mutation was
then checked to fail for the reason named: removing the re-raise of a usage
error; reading a failed project again; marking every entry `unavailable`;
dropping the fixed sentence used when there is no record; dropping the
`--project` coverage check.

**Steps 5 and 6.** `scope_options()` lives in `tcw/scope.py`, so all eight
commands share one help text. The active project's backend is opened once.
`find_in_scope` uses `is_item_folder` for a folder name and `lookup` for a
ticket key, so a project without the item answers "no match" rather than an
error. Twelve mutations, each red for its own reason (listed in the notes kept
for this round): among them, `--mine` for a Jira project using `user.name`,
personal settings read for another project, and `--project` ignored. One
survived at first: a full identifier sent through the scope search; the test
was strengthened to run under `down` and `all`, and the mutation then failed.

**Step 7.** The fake Jira does not record which account each request was sent
as (the plan's Step 0 note said it did). The account test wraps
`JiraClient._request` in the test itself, so the shared fake is unchanged
(TCW-115 runs in parallel). `test_every_operation_is_accounted_for_here` now
also accepts `account_key`, which sends no request; a new case proves it sends
nothing. Mutations, each red: listing not through the kept search; no deep
copy; a key without the account; the raw token in the key; the token not
stripped; the write that forgets kept searches removed (one parametrized case
per write); the span restoring nothing; a holder shared between threads. A
mutation written within the same second as the last run can be run from stale
compiled files; the mutation script now clears them and the write mutations
were rerun.

**Step 8.** `ScopeRow.overridden_by` holds an entry for every member of the
group, so the record for any full identifier in a group finds its own list.
`row_order` takes how to read a row's full identifier, so it orders both rows
and plain identifiers. Eight mutations, each red; the chain-join mutation
survived until a test with a chain through a middle project was added.

**Step 9.** `tcw/tree_scope.py` holds the scoped `list`, `show` and `search`.
`find_component_project` gains an `opener`, so the scoped path opens the
active project's store once (the count test found a second open). Mutations,
each red: a multi-line reason left multi-line; an unreadable state file not
reported; ancestors never read under `all`; the chain dropped; the view read
under `down`; `--status` tested on the shown object only; show by full
identifier without its group; the hint dropped; the probe in
`find_component_project`; view warnings always printed; `--project Q` marking
the view as read. One survived: removing path halving from the grouping, which
only saves time and changes nothing visible.

**Step 10.** Done in a separate throwaway worktree with its own virtual
environment, with the default changed there only; that worktree was removed
afterwards. 43 tests failed with the default changed, and every one was read:
they lacked the inherited rows or TCW-112's warnings, `show` of an inherited
path now exited 4 with the hint, or `list` and `search` exited 0 with partial
records instead of 7. Two other failures had causes outside those groups and
were fixed in Step 9's code first (commit `f8639169`), and the step restarted.
The conversion: a script changed 23 test functions (33 calls), and five places
were changed by hand. Proof: each test function's syntax tree compared before
and after, with `--scope up` removed: 0 differences over 5002 functions; the
comparison was itself checked by planting two differences, both caught. With
`up` made to behave as `own`, all 43 converted tests went red.

**Step 11.** Seven new tests, five red before the change. All eight parsers
default to `own`; the old code paths of the six handlers are deleted. AC 7
found a defect: in a project with no parents and no children, `show --scope
down` printed a status block naming only itself, against Design 1.9. Fixed with
`rows_scope`. Mutations: `rows_scope` always using the scope (AC 7 red); the
default `up` (AC 2 red).

**Step 12a.** A script removed 6 `"--local"` strings from 5 test functions.
Syntax trees compared with the strings put back: 0 differences over 5009
functions; the 150 tests in the three files kept their outcomes.

**Step 12b.** Four AC 30 tests, red before. `--local` stays, hidden, and is
refused by `refuse_local`. Passages changed: `README.md:415`,
`skills/capabilities/SKILL.md` (160, 189, 190), `skills/taxonomy/SKILL.md`
(135-138, 157; not named by the plan, but `test_documented_cli_surface`
required it), `docs/guide/taxonomy-and-capabilities.md` (32, 94), both
capability records' `--local` sentences, and the `own_declarations` docstring.
The full suite then found `tests/test_migration_guide.py` failing: the 3.0
guide names `tcw capabilities list --local`, so `REMOVED_AFTER_3_0` lists it.

**Step 13.** The server code was written before `tests/serve/test_scope.py`
(20 tests), so mutation checks were used in place of a red first run: removing
`command_span` (the one-request test went red), the scope's other projects in
the detail, and the pickers' own data all went red. One survived: the CLI
record winning over a server field with the same key in `list_document`, which
these fixtures cannot show, since no key differs between the two. Records
moved to `tcw/tree_scope.py` so the CLI and the server share them. 11 existing
tests were changed on purpose: the list answer's new shape, `?scope=up` where
they read inherited entries, and the project summary test skipping `scopes`.

**Step 14.** `tests/serve/test_other_project.py`, 19 tests. `work_key`,
`WorkKey` and `context_for` in `tcw/serve/work.py`; `files.py`'s `_target` is
split into `_read_target` and `_write_target`. `/api/resolve` answers `ok` for
another project's object on this machine. Mutations, each red: `put_file` on
the read target; `item_folder`'s project check removed (red only after giving
`shared` an item with `desktop`'s folder name); the detail read from the served
project; files read from the served project; the unresolved branch removed;
the unknown-project catch removed. Two tests were renamed, listed in
`removed-tests.txt`.

**Step 15.** `model/scope.ts` and `ui/scope-control.tsx`, with 8 tests; 6 app
tests. The choice is read from `location.search` through `useLocation`, which
the app already used. Every navigation keeps the query string; changing the
scope asks about unsaved changes first. Mutations: navigation without the
query string (red); the capability list without the scope (2 red).

**Step 16.** The `owned by <owner>` badge on rows, pages and another project's
item page; the capability page's "Status by project" block; `SlugLink` follows
a link once `/api/resolve` answers `ok`; one notice per unavailable project;
`itemKey` uses the full identifier for another project's item. 15 new tests.
Two existing tests changed on purpose, neither removed: "inherited from base"
became "owned by base" (Design 6.7), and the tree test now renders as project
`p`. Mutations, each red: the ownership check forced true; notices filtered
out; the row summary removed; `SlugLink` never linking; "(inherited)" dropped;
`itemKey`'s work branch back to the folder; the badge branch removed.

**Step 17.** Two AC 37 tests, red before. The procedure starts from `tcw work
list --scope down --json`, names every project, reports unavailable ones as not
audited, uses `<full-id>` in every per-item command, and gives the `tcw -C`
form for changing another project's item. `agents/backlog-auditor.md` is given
an item by its full identifier. `tests/fixtures/prompt_fallback/` holds no
procedure text, so nothing was regenerated. Hand check on a scratch family:
the procedure, `work path` and `work show` with `desktop`'s full identifier,
run from `shared`, read `desktop`'s item.

**Step 18.** New, with the released `tcw capabilities add`:
`cli/choose-which-projects-a-list-or-show-command-covers` and
`capabilities/see-each-projects-status-for-a-capability`, both `Supported`.
New term `scope`, which relates to `project`; `local-web-app` gains the scope
control and the read-only display, and `scope` in its vocabulary. All 15
changed records rewritten from the spec's sentences. Every claim was checked
by hand on the scratch family. `tcw validate`: 0 errors, 0 warnings, 0
unresolved.

**Step 19.** The entries `tcw work docs` lists match the plan's table. Both
`upcoming/` files written, formatted, and passing
`tests/test_upcoming_entries.py`. The rest is deferred to TCW-117, below.

## Decided by the implementing agent

1. A `ConfigError`'s problems are joined with "; ", and any multi-line reason
   is joined into one line, so each unavailable project gets one warning line
   (Design 1.8).
2. A project with no identity for `--mine` is unavailable, with `_me`'s own
   message: the plan names no message, and that one is already known to users.
3. An unreadable item in another project that keeps its items in files makes
   that project unavailable for `list`. The files backend refuses its whole
   board for one unreadable item, and changing that is outside this item. The
   reason names the file. `show --scope down` keeps the readable items and
   warns.
4. `--project Q` on `show` reads `Q.<axis>/X` as that full identifier is read,
   outside any catch, so a project not on this machine exits 5 rather than
   warning (Design 1.7: the object asked for is never made unavailable).
5. Another project with an unreadable state file is unavailable, its reason
   naming the file, rather than having its rows left out without a word.
6. Design 4.4's order applies to the grouped rows of `down` and `all`; `own`,
   `up` and `--project` keep each command's order today. This replaces a first
   choice in Step 9 that Step 10 showed to be wrong: `--scope up` must answer
   what the old default did, and `own` what `--local` did.
7. `rows_scope`: a project with no parents and no children gets `own`'s rows
   under every scope (Design 1.9); a project with parents keeps `down`'s rows
   even with no children, since `down` still needs its view (AC 21).
8. `command_span()` wraps the write check as well as the handler: the write
   check's lookups belong to the same request.
9. The work routes under `own` with no project keep today's code path exactly.
   A detail answer's `warnings` name each unavailable project.
10. `ScopeRow.overridden_by` has an entry for every group member; `row_order`
    takes how to read a row's identifier.
11. The work detail's route key is the folder for the served project's item and
    `<owner>.work/<folder>` for another's.
12. The audit procedure names every item by `<full-id>`, its own project's
    items too, with one paragraph giving the `tcw -C` form for another
    project's item, rather than a `-C` form beside each recommendation.

None contradicts the spec.

## Found, not changed

- `tcw/refs.py` has no `route_key` (the spec's TCW-110 handoff and the plan
  name it). `resolve_address` already gives another project's key as its whole
  full identifier, and the client's `itemKey` now does the same for work, so
  nothing was needed there.
- The fake Jira does not record the account per request (Step 7).
- `README.md`, `docs/guide/taxonomy-and-capabilities.md`,
  `skills/capabilities/SKILL.md` and `skills/taxonomy/SKILL.md` already failed
  `prettier --check` at `78c88809`. They were not reformatted, to keep this
  item's changes to them small next to TCW-115's; every other file this item
  changed passes.
- `tcw work advance TCW-113 --dry-run` (the records gate) was not run: the
  dispatching session runs every lifecycle command.

## Notes for later items

Post the spec's Handoffs, "Handoff to TCW-114" and "Handoff to TCW-117"
sections as written, plus the following.

- **TCW-115:** `--project`'s refusal (Design 2.2) is built in one place,
  `tcw/scope.py`'s `cover`, where `tcw project path <id>` can be added. The
  fake Jira (`tests/work/jira/fake.py`) was not changed by this item.
- **TCW-116:** nothing to migrate.
- **TCW-117:** the spec's lists, plus:
    - the warning wording of each `show`: `tcw capabilities show` says "so its
      status is not shown"; `tcw taxonomy show` says "so its taxonomy entries
      are not included"; `tcw work show` says "so its items are not counted in
      children and blocks";
    - the web app's list records are the server's full objects with the CLI
      record's keys over them;
    - `--project` never groups: one owner's objects, no `statuses`, no
      `overridden-by`;
    - `README.md`'s table row for `tcw capabilities list` was changed only as far
      as `--local` (Step 12b);
    - the four files above that were already unformatted;
    - `skills/taxonomy/SKILL.md` 135-138 and 157 were changed for `--local`
      only; the rest of `--scope` is for TCW-117;
    - `docs/guide/web-viewer.md`: the scope control is shown only for a project
      with parents or children; changing the scope asks about unsaved changes;
      another project's work item page has no edit, comment, file or declaration
      controls.
- **TCW-118:** the scope tests build their projects with `tests/families.py`;
  any check of the whole 4.0 release can use the same family.
- **TCW-50:** ordering is `row_order` for taxonomy and capabilities and scope
  order, then each backend's own order, for work; limits apply per project.

## Final suite

Run as CI runs it: bare `.venv/bin/pytest` from the worktree root, every
`TCW_*` variable unset, in two halves.

- `tests/work tests/serve`: 2157 passed, 2 skipped.
- The rest: 4879 passed, 111 skipped.
- Compared with the record before Step 16: no test lost, 10 new, 0 problems.
  Compared step by step from Step 1, no test was deleted, and the only changed
  outcomes are the tests listed above as changed on purpose.

Web: `pnpm install --frozen-lockfile`, `pnpm check:build` (the committed bundle
matches), `pnpm test` (227 passed in 17 files), `pnpm exec tsc --noEmit`,
`pnpm lint`, and `pnpm test:e2e` (18 passed) all clean. A hand check of `tcw
serve` on a scratch family answered `scopes`, `statuses` and the `mobile`
project as unavailable with the command that fetches it, and refused a write to
`desktop`'s item as read-only.

## Not done

- Everything the spec defers to TCW-117 (the guides, the skills beyond the
  `--local` passages, `docs/use-cases.md`, the migration guide).
- The records gate dry run, which belongs to the dispatching session.
