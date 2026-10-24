# Implement round 2 — TCW-114

Answers review round 1's two findings, on the branch `v4` in the worktree
`.claude/worktrees/v4`. The code was run from that worktree's own virtual
environment; the one hand run of `tcw` went through the guarded wrapper,
against a scratch project, never this repository. No lifecycle command was
run and no ticket was moved or written to: the dispatching session makes every
move. No client file changed. This round gives no verdict.

## (a) A web write answers only the lines about a parent or blocker

`reported()` in `tcw/serve/work.py` collected every line the backend reported
while a request ran, so a files-mode `PATCH /api/work/<item>` setting a
priority answered the warning `wrote docs/work/<item>/tcw-work-item.yaml`,
`POST /api/work` answered `created …` and `wrote …`, and the page showed
"Saved with 1 validation issue" on every ordinary edit. It now keeps, as
warnings, only the lines that name a parent or a blocker, and passes every
other line to the report function the backend already had, which in the
server prints to its standard error, as the CLI prints the same lines.

Decisions (each decided by the implementing agent):

- **Which lines are warnings.** Design 3.3 asks for the sentence
  `<item>'s parent <full id> is not a ticket on <site>, so it is recorded in
  <state file> and Jira shows no link for it` (and its `blocker` form), the
  thing Jira will not show. Those are matched as before, by `'s parent ` and
  `'s blocker `. One more line is kept: the backend's `not nested: <parent>
  belongs to project '<id>', so the item's folder is made at the top …`, as a
  warning on the parent. It names the parent, and it is the only place the
  person learns that the `nest` they asked for was not done; it is not a
  record of a file written. Every other line the backends report is about
  files created, written, removed or moved.
- **Where the other lines go.** To the backend's own report function, not
  dropped: that is the server's standard error (`tcw/serve/services.py`), the
  same place they went before TCW-114 added the collection, so a person
  running `tcw serve` in a terminal still sees what was written.
- **The Jira test is a create, not an edit.** The page refuses every
  property edit of a Jira item (`writable`, "this project's backend keeps the
  item's … properties"), so a create is the Jira-mode web write that can carry
  another project's blocker. The test makes the in-memory backend report the
  recorded-blocker sentence and a `wrote …` line during `create`.

Tests, in `tests/serve/test_work_write.py`, written first and red on the old
code for the reason each names:

- `test_a_plain_edit_answers_no_warnings`: a files-mode priority change has
  no `warnings`, and the `wrote` line reaches standard error.
- `test_a_plain_create_answers_no_warnings`: likewise for a create, with the
  `created` line.
- `test_a_jira_create_answers_a_recorded_blocker_and_not_what_it_wrote`: the
  recorded-blocker sentence is a warning on `blocked-by`; the `wrote` line is
  not a warning and goes to the backend's report function.
- `test_nest_under_another_projects_parent_answers_why_it_is_not_nested`: the
  `not nested` line is a warning on `parent`; no `created` or `wrote` line is.

Mutation checks, each restored afterwards:

- The old collection put back (every line a warning): all four tests red.
- The `not nested` clause removed: the nest test red.
- The other lines dropped instead of passed on: the two plain tests and the
  Jira test red, on their standard-error and report assertions.

By hand, with `tcw serve --port 8896` in a scratch files-mode project
(stopped afterwards): a priority edit and a plain create answered no
warnings; a nested create under `other.work/2026-01-01-x` answered the
page's own "does not check" warning and the `not nested` one; the server's
standard error held the five `created`/`wrote` lines.

The changelog entry that described every note as a warning is corrected
(`docs/changelogs/upcoming/TCW-114-…md`). The release notes do not make the
claim, so they are unchanged.

## (b) The removed `delegation` procedure's message

`tcw/work/config.py` told a project still configuring `delegation` that its
rule "is now fixed text in the work skill" (no longer true, Design 9.5) and
that delegating is `tcw work new --project` (which now exits 2). It now
reads: "a part in another project is now made in that project, with
`tcw -C <folder> work new "<title>" --parent <full id>`", the wording
`skills/work/SKILL.md` uses. `tests/test_procedure_config.py`'s parametrized
case for `delegation` now checks for that command.

## The suite

Run here: `tests/serve` and `tests/test_procedure_config.py`, from the v4
root (result below). The full suite is run by the dispatching session.

`.venv/bin/pytest -q -p no:cacheprovider tests/serve tests/test_procedure_config.py`: 411 passed. No other file in the repository repeats the old `delegation` message.
