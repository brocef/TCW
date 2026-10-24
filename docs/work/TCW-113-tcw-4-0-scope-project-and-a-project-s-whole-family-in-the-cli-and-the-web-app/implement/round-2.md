# Implement round 2 — TCW-113

Answers review round 1 (`review/round-1.md`, rejected). Made on the branch
`v4` in the worktree `.claude/worktrees/v4`, with that worktree's own virtual
environment. No lifecycle command was run, no ticket was moved or written to,
and nothing was pushed: the dispatching session makes every move. No hand run
of `tcw` was needed; the CLI's answers were compared inside the tests, which
run `tcw` in the test's own scratch family (`tests/families.py`).

## Findings answered

1. **The web detail of another project's item counted the wrong items.**
   `detail()` (`tcw/serve/work.py`) passed the owner's backend to
   `every_item`, which takes its second argument as the served project's. The
   owner's items were read twice, the served project's not at all.

    Done: under a scope, `detail()` now passes the served project's backend
    (its own context when the item is the served project's, otherwise
    `context(request)`), so every covered project's items are read once. The
    read degrades, as before, when the backend owns the record, now checked
    against the served project when it does, else the owner.

    The round also showed that an item whose project the scope does not cover
    (a sibling, named by its full identifier) lost its own project's children
    and blocked items under any scope but `own`, **in the CLI as well**:
    `tcw work show other.work/<item> --scope down`, run in `shared`, counted
    `shared`'s, `desktop`'s and `server`'s items and not `other`'s, while
    `--scope own` counted `other`'s. Design 3.3 says the items come from every
    covered project, "not only the item's own project", so the owner's items
    belong in the answer. `every_item` (`tcw/work/scoped.py`) takes an
    optional third argument, `owner`: when the scope does not cover the owner's
    project, that project's items are added once, outside any catch (it was
    just read, Design 1.7). Both callers, `tcw work show` (`tcw/work/cli.py`)
    and the web detail, pass it, so the two keep giving the same answer
    (Design 6.2). These are the only two callers. The contract change is an
    added argument with a default, so the existing call shape is unchanged.

2. **Another project's item page advised a refused command.** The stage line
   said `Move it with tcw work advance <full id>`, which TCW-114's rule
   refuses in the served project.

    Done: `moveHint` (`web/client/src/model/work.ts`) takes the served
    project's id; for an item another project owns it names
    `tcw -C tcw://<owner>.path/ work advance <full id>`, the form TCW's own
    messages already use (`tcw/work/cli.py:269`). The page has what it needs:
    the item's `owner` is its full identifier's project. The served project's
    own items keep `tcw work advance <full id>`. The bundle is rebuilt.

## Decisions

- Name the `tcw -C` form, not no command, on another project's item page:
  the owner is always known from the full identifier, and the form is the one
  TCW's messages already give. Decided by the implementing agent.
- Fix the CLI as well as the web detail, rather than making the web detail
  alone add the uncovered owner's items: the spec requires the two answers to
  match, and the CLI's answer dropped items `own` would show. Decided by the
  implementing agent.

## Tests

- `tests/serve/test_scope.py`:
  `test_a_covered_owners_item_counts_each_covered_project_once[down|all]`
  (a `desktop` item with a child and a blocked item in each of `desktop` and
  `shared`, served from `shared`) and
  `test_an_owner_the_scope_does_not_cover_counts_its_own_items_once` (the
  same for a sibling's item, in `other`, `shared` and `desktop`). Each asserts
  every child and blocked item once, and that the web answer equals
  `tcw work show <full id> --scope <s> --json` run in `shared`.
- `web/client/src/model/work.test.ts`: another project's item gets the
  `tcw -C` form; the served project's keeps the plain one.
- `web/client/src/ui/work-views.test.tsx`: another project's item page shows
  the `tcw -C` command on its stage line.

## Mutation results

Each change was reverted alone, the tests run, and the change put back.

| Change reverted                                            | Result                                                 |
| ---------------------------------------------------------- | ------------------------------------------------------ |
| web: the old call, `every_item(covered, ctx.backend)`      | all three new server tests red (children wrong)        |
| web: the served backend passed, no `owner`                 | the uncovered-owner test red (`other`'s child missing) |
| CLI: `every_item(covered, active)`, no `owner`             | the uncovered-owner test red (web and CLI differ)      |
| client: the plain `tcw ` prefix for another project's item | both new client tests red                              |

## Checks run

- `.venv/bin/pytest -q -p no:cacheprovider tests/serve/test_scope.py
tests/serve/test_other_project.py`, and `tests/work/test_scope_work.py`.
- `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint`, and `pnpm check:build`
  after the rebuilt bundle was committed. `pnpm prettify:check` reports
  files across the repository that are not this round's; the files this round
  changed are formatted.

## The suite

The full Python suite was not run by the implementing agent; the
dispatching session runs it, as CI runs it, before the next review.
