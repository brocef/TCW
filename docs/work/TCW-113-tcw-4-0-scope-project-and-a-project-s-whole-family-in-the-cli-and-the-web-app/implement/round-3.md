# Implement round 3 — TCW-113

Answers review round 2 (`review/round-2.md`, rejected). Made on the branch
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

## Decisions

- Honor `project` for a plain work key on the detail route, rather than
  ignore it, since the route must answer what `show --json` gives for the
  same input (Design 6.2) and the taxonomy and capability detail routes
  already did. Decided by the implementing agent.
- The client drops `project` from a detail request for another project's
  object rather than navigating to a view without the filter: the filter is
  the list's, the key already names the object, and the scope still decides
  its `children`, `blocks` and `statuses`. Decided by the implementing agent.

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

## Mutation results

Each change was reverted alone, the tests run, and the change put back.

| Change reverted                                           | Result                                                     |
| --------------------------------------------------------- | ---------------------------------------------------------- |
| server: the conflict check in `_shown_key`                | the work refusal test red (200)                            |
| server: a plain key given `project`'s project             | the folder-name test red                                   |
| `show_row`: its conflict check                            | the capabilities refusal test and the term test red        |
| client: `detailScope` returning the page's choice         | the unit test and the two conflicting-link tests red       |
| client: the work fetch passed `scopeChoice` unchanged     | the two conflicting-link tests red                         |

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/serve/test_scope.py
tests/serve/test_other_project.py`: `50 passed`.
- `tests/test_scope_members.py tests/test_scope_reader.py
tests/test_scope_rows.py tests/test_scope_trees.py`: `105 passed`;
  `tests/work/test_scope_work.py`: `25 passed`.
- `pnpm test` `233 passed`; `pnpm exec tsc --noEmit` and `pnpm lint` clean;
  the changed client files are formatted; `pnpm check:build` after the
  rebuilt bundle was committed.

## The suite

The full Python suite was not run by the implementing agent; the
dispatching session runs it, as CI runs it, before the next review.
