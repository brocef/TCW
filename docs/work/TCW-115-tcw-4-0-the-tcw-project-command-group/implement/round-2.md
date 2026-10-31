# Implement round 2 — TCW-115

Answers review round 1 (rejected), on the branch `impl-115` in the worktree
`.claude/worktrees/impl-115`, from `7d7c0c9b`. The code under test was run
from that worktree's own virtual environment (`.venv/bin/pytest`). No `tcw`
command was run by hand in this round, no lifecycle command was run, and no
ticket was moved or written to: the dispatching session makes every move.
Nothing reached the network: every clone in the tests is of a repository made
in a temporary folder. It gives no verdict.

## Commits

| Commit     | What |
| ---------- | ---- |
| `499d2ae0` | findings 1 and 3: the refusal names the project that holds the file; an unreadable target folder is refused |
| (this one) | finding 2: the commit table of round 1; this round; the changelog entry |

## The findings, and what was done

1. **Design 7.11's refusal named the last project fetched**
   (`tcw/provision.py`, the `except ValueError` after `require_valid`). The
   registry's error was plain text, so nothing said which file a problem was
   about without reading the message. `require_valid` now raises
   `GraphProblems` (`tcw/store/project.py`), a `ValueError` subclass, so
   every caller that catches `ValueError` is unchanged. It carries `files`,
   the file each problem in the message is about, in the same order: the
   registry's `_problem` already received that path for every graph problem,
   and now also keeps it beside the rendered text. Provisioning's new
   `_holding` picks the project fetched this round whose own folder (its
   entry's folder) holds the first of those files that any of them holds,
   and names it, its clone folder and its ID in the undo advice. When no
   fetched project holds any of the files, the message is the general one
   ("correct it"), as before when nothing had been fetched.
2. **The commit table of round 1 cited the hashes from before the rebase.**
   Each row now gives the commit on the branch with the same subject, the
   opening paragraph says the branch was rebased onto `93b17acb`, and the
   line-number reference for TCW-117 names the rebased Step 3 commit
   `081559ac`.
3. **An unreadable target folder printed Python's error text** (it was
   caught at the top of the command as `[Errno 13] Permission denied: <path>`,
   not a traceback, but named neither the problem nor the entry).
   `_folder_state` now returns `unreadable` when listing the folder raises
   `OSError`, and `_folder_problem` refuses it: `<id>: <folder> cannot be
   listed, so whether it is empty is not known; correct its permissions, or
   the manifest entry in <file>`. The run goes on with the other projects and
   exits 1, as for an occupied folder; nothing is cloned, written or removed.

## Decisions (decided by the implementing agent)

- **A structured answer over parsing the message.** The file is carried on
  the error rather than recovered from the text, because a path can contain
  `: ` and `; `, the separators the message uses.
- **The project's own folder, not the clone folder, decides who holds a
  file.** Projects that share one clone (Design 7.7) share its folder, so
  matching on the clone folder would name whichever came first. Matching on
  each project's entry folder, and taking the deepest when one holds
  another, names the project whose files have the problem; the advice still
  says to remove the clone folder, since that is what undoes the fetch.
- **The first file any fetched project holds decides**, when several
  problems are reported at once: the message lists them all, and naming one
  project keeps the advice to a single folder to remove.
- **The message for an unreadable folder** follows the registry's own words
  for the same case ("cannot be listed, so whether it is empty is not
  known"), so the two read alike.

## Tests, written first, and the mutation checks

In `tests/test_project_provision.py`. The two that reproduce the findings
were written first and failed on `7d7c0c9b`; the other two cover choices made
while fixing them (the deeper-holder test would pass on `7d7c0c9b` by chance,
since `server` is fetched last there).

- `test_ac32_the_refusal_names_the_project_with_the_problem`: parents `aa`
  and `bb` fetched in one round, `aa`'s manifest with an unknown key. The
  message names `aa`, its folder and its ID in the undo advice, and never
  says to remove `bb`. Mutation: `fetched_here[-1]` put back, red at the
  `aa: fetched into` assertion, with the message naming `bb` as the review
  described.
- `test_ac32_the_refusal_names_the_deeper_of_two_holders`: `top` at a
  repository's top and `server` in its `apps/server`, one clone, the problem
  in `server`'s manifest. Two mutations, each red at the `server: fetched
  into` assertion: taking the first holder instead of the deepest, and
  matching on the clone folder instead of the project's own.
- `test_ac32_no_fetched_project_holds_the_file`: `_holding` names no project
  for a file outside every fetched project's folder, and names the one that
  holds it.
- `test_ac24_an_unreadable_folder` (skipped when run as root): the target
  folder made unreadable with `chmod 0`. Exit 1, no traceback, the message
  names the folder, nothing cloned, the folder's file and the parent
  folder's listing unchanged, no staging folder left. Mutation: the new
  `except OSError` narrowed to `except FileExistsError`, red at the
  `cannot be listed` assertion, the message back to `[Errno 13]`.

## Checks run

From the worktree root, `.venv/bin/pytest -q -p no:cacheprovider`:

- `tests/test_project_provision.py`, `tests/test_fetch_project.py`,
  `tests/test_static_guards.py` and `tests/test_object_folder_sweep.py` (the
  last two list `_folder_problem` and `_folder_state`): `152 passed`. No
  other test file asserts Design 7.11's text.
- The files that call `require_valid`, for the new exception type:
  `tests/test_parent_links.py`, `tests/test_multiproject.py`,
  `tests/test_environment_hardness.py`, `tests/test_store_nodes.py`,
  `tests/test_project_registry.py`, `tests/test_project_overrides.py`,
  `tests/work/test_gates.py`: `241 passed, 7 skipped`.

## The suite

The full suite was not run in this round; the dispatching session runs it as
CI runs it.

The full suite as CI runs it, `.venv/bin/pytest -q -p no:cacheprovider`, run by
the dispatching session on the branch at `318c68cd` (2026-10-24) in two halves
by folder: `2078 passed, 2 skipped` and `4979 passed, 111 skipped`. `pnpm test`
`198 passed`; `tsc --noEmit`, `pnpm lint` and `pnpm check:build` clean.
