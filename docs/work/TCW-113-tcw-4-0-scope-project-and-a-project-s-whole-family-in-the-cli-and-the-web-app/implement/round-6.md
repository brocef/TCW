# Implement round 6 — TCW-113

Answers review round 5's one finding. Made on the branch `v4` in the
worktree `.claude/worktrees/v4`, in the commit that adds this file. No
lifecycle command was run, no ticket was moved or written to, and nothing
was pushed: the dispatching session makes every move. The hand check used
the scratchpad wrapper on a copy of the round 5 reviewer's family, never the
repository as the project.

## The finding

A project whose own object at a capability path sets no Status is reported
in `statuses` as `inherited: true` (`tcw/store/base.py`, `scope_rows`). The
web page's "Status by project" (`StatusByProject`,
`web/client/src/ui/content-views.tsx`) linked a project only when its entry
was not inherited, or when the record named its object (`full-id`,
`overrides`, `overridden-by`, the last listing direct overrides only). So
with `server`'s own `abc` holding only a name, desktop's override page under
`down` showed `server` as plain text, and a grandchild's override that sets
no Status was plain text on the served page, though Design 6.9 links each
project that has its own object at the path.

## What was done

- **The server.** Each `statuses` entry gains `full-id`: the full
  identifier of the object the project's view at the path comes from (the
  `view_object` `scope_rows` already had for each `ProjectView`). When the
  project has an own object there, that is its own object, whether or not
  it sets Status; otherwise it is the object it inherits. `inherited` keeps
  its meaning. The CLI's `--json` and the server's answer share the record
  (`tcw/tree_scope.py`, `scope_keys`), so both carry it; the text form of
  `show` is unchanged.
- **The client.** `TScopeStatus` gains `"full-id"`. `StatusByProject` now
  maps each owner to an object of theirs from the record's full identifiers
  (its own, `overrides`, `overridden-by`) and every entry's `full-id`, and
  links an entry whenever that map holds the entry's project. The old
  inference, "a non-inherited entry has an object at the shown path", is
  removed: a non-inherited entry's `full-id` is its own object, so it says
  the same thing without guessing.
- **Documents.** The capability record
  `capabilities/see-each-projects-status-for-a-capability` lists the entry's
  fields and now names `full-id` and what it holds. The spec's Design 4.6
  gives the entry's shape, so it gains the field, marked as added in this
  round. The upcoming changelog and release-notes entries name `statuses`
  but not its fields, so neither changed.
- The bundle was rebuilt (`pnpm build`) and committed with the change.

## Decisions

Decided by the implementing agent:

- **The field's name is `full-id`**, the name the record itself uses for a
  full identifier, so an entry reads like a small record of its own.
- **The field is on every entry, not only on projects with an own object.**
  An entry that inherits names the object it inherits, which is what its
  status comes from; the client decides a link by the identifier's owner, so
  an inheriting entry is never linked to another project's object under its
  own name.
- **The field is required in the client's type**, since every answer the
  server gives under `down` and `all` carries it; the fixtures that build
  `statuses` were given it.
- **The spec's 4.6 was amended** rather than the departure recorded only
  here, since 4.6 is where the entry's shape is the contract a reviewer
  checks.

## Tests

- `tests/test_scope_rows.py`: every exact `statuses` entry now names its
  `full-id`, including an override that sets no Status (its own object) and
  projects that inherit (the object they inherit).
- `tests/test_scope_trees.py`: the same for `list --json`; under
  `test_ac15_a_status_inherited_without_a_ruling`, `list --json` and
  `show --json` name `server.capabilities/abc` for server's entry, which
  sets no Status; new `test_ac15_a_grandchilds_override_that_sets_no_status`
  adds `tablet`, a child of `desktop` whose own `abc` holds only a Priority,
  and checks that shared's record leaves it out of `overridden-by` and that
  its entry is inherited and names `tablet.capabilities/abc`.
- `tests/serve/test_scope.py`: new
  `test_each_status_entry_names_the_object_its_projects_view_comes_from`,
  the review's scenario plus the grandchild, on desktop's override page
  under `down`: server and tablet inherited, each naming its own object,
  and the answer's `statuses` equal to `show --json`'s.
- `web/client/src/ui/content-views.test.tsx`: new "a project whose own
  object sets no status is linked by its entry", on the served page: server
  and a grandchild `tablet` linked to their own objects, and `phone`, which
  inherits desktop's object, not linked.
- `web/client/src/ui/app.test.tsx`: new "an override's page links a project
  whose own object sets no status", on desktop's override page with an
  empty `overridden-by`: server and tablet linked to their own objects.

## Mutation results

Each mutation was made, the tests run, and the code put back:

- No `full-id` on an entry (the tests written before the code): the six
  `test_scope_rows` exact-entry tests, three `test_scope_trees` tests and the
  new serve test went red.
- `full-id` naming the row's shown object instead of the project's view
  object: six tests went red, among them both `ac15` tree tests, the
  grandchild test and the new serve test.
- The client ignoring the entries' `full-id`: the two new client tests and
  "an override's page links each project with its own object at the path"
  (whose non-inherited `server` was linked only by the removed inference)
  went red.
- The client linking every entry by its `full-id` whatever its owner: "under
  down the page lists each status with its projects", the new served-page
  test (`phone` linked) and the override test with an inheriting `tablet`
  went red.

## Checks run

- `.venv/bin/pytest -q tests/test_scope_rows.py tests/test_scope_trees.py
  tests/test_scope_members.py tests/test_scope_reader.py`: `109 passed`;
  `tests/serve/test_scope.py`: `33 passed`; `tests/work/test_scope_work.py`:
  `26 passed`.
- `pnpm test`: `247 passed` (17 files). `pnpm exec tsc --noEmit` and
  `pnpm lint`: clean. `prettier --check` on the changed client files: clean.
- `pnpm build`, then `pnpm check:build` with the bundle committed: clean.
- By hand, headless Chromium against `tcw serve --no-open --port 8909` run
  through the scratchpad wrapper in `shared` of a copy of the round 5
  reviewer's family (server's own `abc` holding only a name), with a
  grandchild `tablet` added under `desktop` whose own `abc` holds only
  `Priority: P2`:
    - desktop's override page, `/capabilities/desktop.capabilities/abc?scope=down`,
      showed `Missing: shared, server (inherited)`, `Supported: desktop,
      tablet (inherited)`, `unavailable: mobile`, with `server` linked to
      `/capabilities/server.capabilities/abc`; following it opened server's
      own object, "Abc on server".
    - The served page, `/capabilities/abc?scope=down`, showed the same lines
      with `tablet`, which its record's `overridden-by` does not name, linked
      to `/capabilities/tablet.capabilities/abc`; following it opened that
      page.
    - The server was stopped afterwards.

## The suite

The full Python suite was not run by the implementing agent. The
dispatching session runs it, as CI runs it, before the next review.
