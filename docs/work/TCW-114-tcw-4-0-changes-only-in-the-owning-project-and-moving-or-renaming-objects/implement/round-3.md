# Implement round 3 — TCW-114

Answers the qa rejection, on the branch `v4` in the worktree
`.claude/worktrees/v4`. The code was run from that worktree's own virtual
environment, by the tests alone; no hand run of `tcw` was made. No lifecycle
command was run and no ticket was moved or written to: the dispatching session
makes every move. This round gives no verdict.

## The qa rejection

QA entry 3: `tcw work edit <folder name> --blocks core.work/X` answered with
`tcw -C <core's folder> work edit core.work/X --blocked-by <folder name>`. Run
as printed, in `core`, that exits 4 (`no work item core.work/<folder name>`),
because a folder name there is read as one of `core`'s items.
`_blocks_removed` in `tcw/work/cli.py` built `--blocked-by` from `args.slug`,
the text as typed. The outcome asked for the advice to give this item's full
identifier, with a test that runs the suggested command.

## What was done

`_blocks_removed` now names this item, when the target is in another project
(or in a project not on this machine), by text that project reads the same
way, built by the new `_full_input`:

- a full identifier or an address (forms a and c of TCW-110 Design 3.1) is
  kept as typed: it already names this project;
- a folder's id-path (form d) or a tracker key alone (form b) gets this
  project's ID before it, `<this project>.work/<id-path or key>`. The other
  project resolves `app.work/<key>` by looking the key up in this project, as
  this project would, so no backend is opened and no Jira request is made to
  word the message. The project's ID is read from its configuration.

When the target is in this project, the message has no `-C` and keeps this
item as typed: the command runs in the same project, which resolves it as the
refused command would have. Each word the command holds (the folder, the
target, this item) is now shell-quoted, as `work new --project`'s title
already was, so a folder path with a space still gives a command that runs.

The other removed-option messages in the same area were checked for the same
mistake and have none: `work new --project` (CLI), `POST /api/work` with
another `project`, and the removed `delegation` procedure's message all name
the parent as the placeholder `<full id>`, never a value as typed.

The changelog and the release notes do not quote the advice, so neither
changed.

## Decisions

- **Text that cannot be resolved.** Decided by the implementing agent: when
  this item's text cannot be turned into a full identifier (it is malformed,
  or this project's ID cannot be read), the message ends `--blocked-by <this
  item's full id>`, a placeholder in the style of `--parent <full id>`.
  Repeating text the other project would misread, or failing, are worse:
  looking never changes the exit (Design 2.2). The item is not checked to
  exist; the suggested command checks it when run (exit 4 if it is missing).
- **A target in this project keeps the typed text.** Decided by the
  implementing agent, as above: it is correct where the command runs, and is
  what Design 2.2's same-project example shows.

## Tests

In `tests/work/test_removed_options.py`, written first:

- `test_edit_with_blocks_in_another_project` now expects
  `--blocked-by app.work/<a>`.
- `test_edit_with_blocks_in_another_project_names_this_item_in_full`, typed as
  a folder name and as a full identifier.
- `test_the_suggested_command_works_in_another_project`: takes the command
  from the message, runs it (with `-C`, into `core`), and sees exit 0 and
  `app.work/<a>` in `core`'s item; typed both ways.
- `test_the_suggested_command_works_in_this_project`: the same with the target
  in `app`, by folder name and by full identifier, no `-C`.
- `test_edit_with_blocks_by_tracker_key_puts_this_project_before_it`: a key
  alone gives `--blocked-by app.work/TCW-5`.
- `test_edit_with_blocks_naming_no_item_names_a_placeholder`.

Before the fix, four were red: the changed other-project test, the
folder-name cases of the two new other-project tests, and the placeholder
test; the run in `core` exited 4 with `no work item core.work/2026-10-01-a`,
the qa finding itself. The key test was written after the fix, and was red
under the mutation below. Mutation check: `args.slug` put back in place of
`_full_input(args.slug)` turned the same five red (the run test again on exit
4); restored, all green.

## The suite

Run here, from the v4 root:
`.venv/bin/pytest -q tests/work/test_removed_options.py tests/work/test_cli_items.py`:
48 passed. No other test file asserts the `--blocks` message. The full suite
is run by the dispatching session.

## Entry 8

Recorded from the qa Outcome: "Entry 8's edit half is not a defect of this
item, decided by the dispatching session: the web page has never offered a
properties edit for a Jira item, and the server refuses a property `PATCH` of
one with 403, a rule older than TCW-114 that the spec does not change."
