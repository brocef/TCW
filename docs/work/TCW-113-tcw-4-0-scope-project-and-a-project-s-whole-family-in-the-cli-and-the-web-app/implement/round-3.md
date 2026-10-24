# Implement round 3 — TCW-113

Answers review round 2 (`review/round-2.md`, rejected), items (a) and (b), and
item (c), found by TCW-115's review round 3 on the combined `v4` tree. Made on the branch
`v4` in the worktree `.claude/worktrees/v4`, with that worktree's own virtual
environment. No lifecycle command was run, no ticket was moved or written to,
and nothing was pushed: the dispatching session makes every move. No hand run
of `tcw` was needed; the CLI's answers were compared inside the tests, which
run `tcw` in the test's own scratch family (`tests/families.py`).

## Finding answered

1. **A work detail route showed a full identifier of another project than
   `project`.** `GET /api/work/desktop.work%2F<item>?scope=down&project=server`
   answered 200 with `desktop`'s item, where `tcw work show desktop.work/<item>
--scope down --project server` exits 2 naming both (Design 2.3).

    Done: `detail()` (`tcw/serve/work.py`) reads its key through a new
    `_shown_key`, which reads it as `show --project` reads its input. A full
    identifier whose project is not `project` is refused before anything is
    read, as a `UsageError`, which the server answers as 400 `usage` with the
    message as its `error`. The message is built once, by
    `not_its_project` (`tcw/scope.py`), which `tcw work show`
    (`tcw/work/cli.py`), `show_row` (`tcw/tree_scope.py`, used by
    `tcw taxonomy show`, `tcw capabilities show` and their detail routes) and
    the work detail route all call, so the words cannot drift apart. The
    route still answers 200 when `project` is the identifier's own project
    or is absent.

    The same check found a second difference on that route, under the same
    Design 2.3 sentence: a work folder name or ticket key with `project`
    named the served project's item, where `show <folder> --project desktop`
    names `desktop`'s. `_shown_key` now gives such a key `project`'s project,
    so its folder or ticket key is looked up in that project's backend only,
    and an item of the served project asked for with `project=desktop` is not
    found, as the CLI does not find it. The order of the refusals follows the
    CLI: the conflict is refused first, then the scope and project are
    checked (`cover`).

    **The taxonomy and capabilities detail routes already refused it**: they
    go through `show_row`, which raises the same refusal, and the server maps
    it to 400 `usage`. Tests now cover both.

    **The web client did send a conflicting `project` on followed links.**
    In-app navigation keeps the page's query string, and the work detail
    request sent the page's `project` with whatever key it opened. With the
    filter on `desktop`, a link from a `desktop` item to `server`'s item asked
    for `server.work/<item>?…&project=desktop`, which is now refused; a link
    to the served project's item asked for its folder name with
    `project=desktop`, which now names `desktop`'s. `detailScope`
    (`web/client/src/model/scope.ts`) gives a detail request the page's scope,
    and its project only when that is the object's own project (the full
    identifier's, or the served project's for a plain key); both detail
    fetches in `app.tsx` use it. A 400 from a work detail shows its message
    where the item would be (`detailError`), and one from a taxonomy or
    capability detail in the load error, as every other failed read does;
    neither is reachable now from the page's own links. The taxonomy and
    capability detail is only fetched for a key the loaded list holds, and a
    list under `project` holds only that project's objects, so it never
    conflicted; it uses `detailScope` all the same, so the rule is one rule.
    The bundle is rebuilt.

## (c) Found by TCW-115 review round 3

**`show` under `own` said nothing when the inherited store could not be
read.** In `desktop`, whose parent `shared` declares its taxonomy store in a
repository that is not fetched, `tcw taxonomy show invoice` printed only
`no such term: 'invoice'` (exit 4). With the store present it adds the hint
that `desktop` inherits `shared.taxonomy/invoice` there. Design 4.9 makes an
inherited store that cannot be read under `own` a warning, which `list`
already gives, naming TCW-115's `tcw -C <parent folder> project provision
--component <axis>`.

Done: `_inherits_hint` (`tcw/tree_scope.py`), which builds `P`'s view only
for the hint, now passes the reason the view could not be built to a `say`
that `show_row` takes, and `tcw taxonomy show` and `tcw capabilities show`
pass theirs. The warning line is printed before the not-found line, and its
words are `list`'s: the line is now built once, by `own_only_line`
(`tcw/output.py`), which `own_only` and `list_rows`' own-only warning both
use. The hint is still left out and the exit is still 4 (Design 4.8, AC 17).
`capabilities show` had the same gap and is fixed the same way. `tcw serve`
gives `show_row` no `say`, as its other reads print nothing, so its 404
answer is unchanged.

`test_explicit_own_show_by_id_path_names_the_projects_own_object` asserted
that the word `inherits` was absent from that command's standard error, to
check the hint was left out; the warning names the inheritance, so the
assertion now checks the hint's own words are absent and the warning is
present.

## Decisions

- Honor `project` for a plain work key on the detail route, rather than
  ignore it, since the route must answer what `show --json` gives for the
  same input (Design 6.2) and the taxonomy and capability detail routes
  already did. Decided by the implementing agent.
- The client drops `project` from a detail request for another project's
  object rather than navigating to a view without the filter: the filter is
  the list's, the key already names the object, and the scope still decides
  its `children`, `blocks` and `statuses`. Decided by the implementing agent.

- Print the warning beside the not-found error rather than fold it into the
  error's text: it is the line `list` prints, and folding it in would give
  `show` a second wording of it. Decided by the implementing agent.

## Tests

- `tests/serve/test_scope.py`:
  `test_a_full_identifier_of_another_project_than_project_is_refused[work|capabilities]`
  (400 `usage`, the error inside the CLI's exit-2 message, both projects
  named); `test_a_full_identifier_with_its_own_project_or_none_is_shown`
  (200 with `project` matching or absent, both axes);
  `test_a_term_of_another_project_than_project_is_refused` (the same for a
  term, and 200 matching or absent);
  `test_a_folder_name_with_project_names_that_projects_item` (the web record
  equals `tcw work show <folder> --scope down --project desktop --json`; the
  served project's folder with `project=desktop` is 404, and the CLI fails).
- `web/client/src/model/scope.test.ts`: `detailScope` keeps the project only
  for its owner.
- `web/client/src/ui/app.test.tsx`: a page at another project's item with
  the filter on a third project, and at the served project's item with the
  filter on another, asks for the item with the scope alone; one with the
  filter on the item's own project keeps it.

Before the fix the work refusal test and the folder-name test were red; the
capabilities and taxonomy ones were green, which is how the two existing
routes were found to be correct already.

- `tests/test_scope_trees.py`:
  `test_show_under_own_of_a_path_not_its_own_warns_when_the_view_cannot_be_built[taxonomy|capabilities]`
  (`shared`'s store declared in a repository and removed; `show` in
  `desktop` exits 4 with one warning line, naming `tcw -C <shared's folder>
project provision --component <axis>` and `showing only 'desktop''s own
declarations`, identical to `list`'s line, and before the error). Red
  before the fix (no warning line).

## Mutation results

Each change was reverted alone, the tests run, and the change put back.

| Change reverted                                       | Result                                               |
| ----------------------------------------------------- | ---------------------------------------------------- |
| server: the conflict check in `_shown_key`            | the work refusal test red (200)                      |
| server: a plain key given `project`'s project         | the folder-name test red                             |
| `show_row`: its conflict check                        | the capabilities refusal test and the term test red  |
| client: `detailScope` returning the page's choice     | the unit test and the two conflicting-link tests red |
| client: the work fetch passed `scopeChoice` unchanged | the two conflicting-link tests red                   |
| (c): the warning in `_inherits_hint`                  | both (c) tests red                                   |
| (c): `taxonomy show` passing no `say`                 | the taxonomy (c) test red                            |
| (c): `capabilities show` passing no `say`             | the capabilities (c) test red                        |

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/serve/test_scope.py
tests/serve/test_other_project.py`: `50 passed`.
- `tests/test_scope_members.py tests/test_scope_reader.py
tests/test_scope_rows.py tests/test_scope_trees.py`: `105 passed`;
  `tests/work/test_scope_work.py`: `25 passed`.
- For (c): `tests/test_scope_trees.py tests/test_tree_parent_missing.py
tests/test_tree_inheritance.py tests/test_project_provision.py
tests/test_capabilities_federation.py`: `230 passed`; the taxonomy and
  capabilities CLI files (`tests/test_capabilities*.py`,
  `tests/test_capability_ref_wording.py`, `tests/test_taxonomy*.py`):
  `258 passed, 10 skipped`; the serve files again: `50 passed`.
- `pnpm test` `233 passed`; `pnpm exec tsc --noEmit` and `pnpm lint` clean;
  the changed client files are formatted; `pnpm check:build` after the
  rebuilt bundle was committed.

## The suite

The full Python suite was not run by the implementing agent; the
dispatching session runs it, as CI runs it, before the next review.

The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, run by
the dispatching session at `79ece028` (2026-10-24), with TCW-115 landed, in two
halves by folder: `2183 passed, 2 skipped` and `5110 passed, 111 skipped`.
`pnpm test` `233 passed`; `tsc --noEmit`, `pnpm lint` and `pnpm check:build`
clean.
