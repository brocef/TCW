# Implement round 4 — TCW-113

Answers the qa rejection (qa findings, scenario 8 and the Outcome
paragraphs): a followed link to another project's capability showed an empty
page. Two smaller findings from the same qa were folded in by the dispatching
session: what the work listing reports under a project filter, and the
refusal of a `--project` that names no project at all. Made on the branch
`v4` in the worktree `.claude/worktrees/v4`, with that worktree's own virtual
environment. No lifecycle command was run, no ticket was moved or written to,
and nothing was pushed: the dispatching session makes every move. Hand runs
used the scratchpad wrapper on a copy of qa's family, never the repository as
the project.

## (a) A link to another project's object opens its page

**Found.** Under `scope=down`, the capability page's "Status by project"
links each project's own object, such as
`/capabilities/desktop.capabilities/abc?scope=down`. Following it, or typing
it, showed "Select an entry." and sent no request. The client
(`web/client/src/ui/app.tsx`) read a term or capability only when its key
was a row of the list shown, and under `down` the list shows an override's
original, not the override (Design 4.3), so the override was never a row.
Design 6.9 asks for each such project "linked to that object's page".

**Done.** The rule is now two rules:

- a full identifier of **another project** is read whether or not the list
  holds it, as the work page already did (Design 6.4: any object TCW can
  locate can be read). It is read once, not again as each list arrives,
  since nothing on the page writes another project's object;
- the **served project's** entry is still read only while the list holds it,
  so its page still clears when the selection is really gone from the list
  (filtered out, or no longer there after a reload).

A failed read of an object the list does not hold (a mistyped address, say)
now shows its message where the page would be, as the work page does,
instead of replacing the whole list with "Failed to load". A failed read of
a row still goes to the load error, as before.

Work items already behaved this way: the work page is read by its key
whatever the board holds, and qa's scenario 8 step 3 opened `desktop`'s item
by its full identifier.

Checked by hand with headless Chromium against `tcw serve` in `shared` of
qa's family: clicking `desktop` in "Status by project" on `abc`'s page under
`scope=down` opened `desktop.capabilities/abc`, "overrides
shared.capabilities/abc", "owned by desktop", with one request; the typed
address, plain and percent-encoded, did the same; a typed
`desktop.capabilities/nosuch` showed "no such capability:
'desktop.capabilities/nosuch'" beside the list; and
`/capabilities/abc?scope=down&project=desktop` (the served project's entry,
filtered out) still showed "Select an entry.".

## (b) What the work listing reports under a project filter

**Found by qa.** With `--project desktop`, the work listing still named
`mobile` (not on this machine) as unavailable in its JSON `projects`, in
`/api/work`, and in the board's notice, while the CLI's text form printed no
warning and the capabilities listing did not mark it.

**What the code was doing.** The finding's premise, that a filter on
`desktop` leaves nothing of `mobile`'s out, does not hold for the JSON form.
Design 3.3 computes every record's `children` and `blocks` "from the items of
every covered project that is not unavailable"; a project filter does not
narrow the scope (2.1 keeps the rows, not the projects covered). So
`--json`, and the board, still read `mobile` for those two keys, and an item
of `mobile`'s whose parent is `desktop`'s item really is missing from that
item's `children`. The CLI's `--json` form did warn, but in the words "its
work items are not listed"; the text form reads no other project at all, so
it rightly warned nothing. The capabilities listing differs because a
`--project` record carries no `statuses` (2.1), so it reads no other
project. Dropping `mobile` from `projects` would have made the result
incomplete without a word, which 1.8 ("only what is left out is reported")
forbids.

**Done.** `projects` is unchanged. What changed are the words: an
unavailable project that the filter does not keep, read only for `children`
and `blocks`, is warned about as `so its items are not counted in children
and blocks`, the words `tcw work show` already uses (1.8); the project the
filter keeps is still `so its work items are not listed`. `Covered.warn`
(`tcw/scope.py`) takes the second wording as `besides`; the words are one
constant, `COUNTED_ACROSS` (`tcw/work/scoped.py`), which `tcw work show`
now uses too. The board's notice (`leftOut`, `web/client/src/ui/app.tsx`)
says the same for a project the filter does not keep, and "its objects are
not listed" otherwise, as before.

## (c) A `--project` that names no project

**Found by qa.** `--project nosuch`, a well-formed ID no project has, was
refused only as "it is neither an ancestor nor a descendant of 'shared'",
which reads as if there were such a project somewhere.

**Done.** When no scope covers the ID, `_not_covered` (`tcw/scope.py`) asks
the locator for that project's folder (`Locator.owner_root`, which reads
project configuration files, never a store, so 2.2's "reading nothing" still
holds for objects). When the locator answers that no project has the ID, the
refusal ends with its message instead: `--project nosuch: 'nosuch' is not
covered by --scope down in 'shared', which covers shared, desktop, server,
mobile; no project with ID 'nosuch' is known or found near this one; check
the spelling`. A sibling, or a project declared but not on this machine, or
a lookup that meets a graph problem, keeps "neither an ancestor nor a
descendant". The exit code is still 2, as 2.2 says for every refusal, and
`tcw serve` answers it as 400 `usage` with the same message, since it calls
the same `cover`.

## Decisions

- Read another project's term or capability by its full identifier whatever
  the list holds, and keep the row rule for the served project's, rather
  than read every key: an id-path that is no row is the case the clearing
  rule exists for, and reading it would turn a selection that is really
  gone into a failed request. Decided by the implementing agent.
- Read another project's object once, not on every list reload: the page
  writes nothing of another project's, and the reload after a save is for
  the served project's entries. Decided by the implementing agent.
- (b): keep `unavailable` in `projects` under a filter and correct the
  warning's words, rather than drop the project as the brief proposed,
  because the JSON records really do leave its items out of `children` and
  `blocks` (Design 3.3), and 1.8 requires what is left out to be reported.
  Proposed by the implementing agent and decided by the dispatching
  session, 2026-10-24: qa's observation was right that the wording
  disagreed, and wrong that the project should be dropped.
- (c): add a third ending to 2.2's message rather than a separate error or
  another exit code, since 2.2 makes every refusal of `--project` a usage
  error before anything is read. Decided by the implementing agent.

## Tests

- `web/client/src/ui/app.test.tsx`:
  `a status line's link to another project's override opens its page`
  (clicks `desktop` in "Status by project", the page opens at the full
  identifier with "owned by desktop", and the request is made);
  `a typed address of another project's capabilities|taxonomy entry the list
lacks opens it` (and is read once after all five lists arrive);
  `another project's entry that is not found says so beside the list`;
  `the served project's entry the list does not hold is not read` (the
  clearing case: "Select an entry.", no detail request);
  `with one project chosen the board says what another leaves out`.
- `tests/test_scope_reader.py`: `test_a_project_id_no_project_has_says_so`
  (the whole message, and nothing opened).
- `tests/work/test_scope_work.py`:
  `test_a_project_the_filter_leaves_out_is_named_for_children_and_blocks`
  (`--json` under `--project desktop`: `mobile` unavailable in `projects`,
  one warning with the children-and-blocks words; the text form warns
  nothing; `--project mobile` keeps "its work items are not listed").
- `tests/serve/test_scope.py`:
  `test_the_board_with_a_project_names_what_its_records_leave_out`
  (`/api/work?scope=down&project=desktop` has the CLI's items and
  `projects`, `mobile` unavailable). It records the server's answer, which
  this round does not change, so it was green before the change.

## Mutation results

Each change was reverted alone, the tests run, and the change put back.

| Change reverted                                             | Result                                                             |
| ----------------------------------------------------------- | ------------------------------------------------------------------ |
| (a): the whole client change (the file as at round 3)       | the link test, both typed-address tests and the not-found test red |
| (a): read every key, dropping the row rule                  | the clearing test red                                              |
| (a): a failed read always to the load error                 | the not-found test red                                             |
| (a): re-read on every list reload                           | both typed-address tests red (read more than once)                 |
| (b): `tcw work list` passing no `besides`                   | the CLI test red                                                   |
| (b): `besides` used for the kept project too                | the CLI test red (the `--project mobile` case)                     |
| (b): the board's notice always "its objects are not listed" | the board notice test red                                          |
| (c): `_not_covered` as at round 3                           | `test_a_project_id_no_project_has_says_so` red                     |

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/test_scope_reader.py
tests/test_scope_members.py tests/test_scope_rows.py tests/test_scope_trees.py`:
  `108 passed`.
- `tests/work/test_scope_work.py`: `26 passed`;
  `tests/work/test_cli_items.py tests/work/test_cli_surface.py
tests/work/jira/test_kept_search.py`: `77 passed`.
- `tests/serve/test_scope.py tests/serve/test_other_project.py`: `51 passed`.
- `pnpm test` `239 passed`; `pnpm exec tsc --noEmit` and `pnpm lint` clean;
  the changed client files are formatted; `pnpm check:build` clean after the
  rebuilt bundle was committed.

## The suite

The full Python suite was not run by the implementing agent; the
dispatching session runs it, as CI runs it, before the next review.
