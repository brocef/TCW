# Implement round 2 — TCW-109

Answers review round 1 (rejected). Built on the branch `impl-109`, from
`f798612e`, in the worktree `.claude/worktrees/impl-109`, with the code under
test run from that worktree's own virtual environment (`.venv/bin/pytest`).
`.venv/bin/tcw` was never run with this repository as the project. The
lifecycle was not driven by any CLI: the dispatching session makes every
move, so no ticket was moved and nothing was posted. This round gives no
verdict.

## What was done, per review item

- **(a) Finding 1: the decided keys under an undecided `work.jira`**
  (`82a8715c`). The loader dropped every parse problem under an undecided
  key, and `work.jira` is always undecided in Jira mode behind a gap, so a
  key the project sets itself was never checked. Now a problem is dropped
  only when the value at its own key path is not known (`_Fold.unknown`):
  it lies under an undecided key, and no layer after the last gap replaces
  it, or a key above it, whole. So `work.jira.timeout` and
  `work.jira.credentials.email-env` set by `app` are reported, and
  `work.jira.site: required` is not. An ancestor's problem takes the same
  test: one at a key a parent after the gap sets is a warning at that
  parent's file in `tcw validate`, while `work.jira` stays undecided (exit 7
  for a command that reads it); one at a key whose value is not known gives
  no warning, as round 1's decision 4 and `cdd6be20` require. To report the
  review's scenario, `parse_jira_config` also had to change (decision 1).
- **(b) Finding 2: a variable's name first** (code in `82a8715c`, test in
  `54cc3813`; the `tcw/config.py` hunk went into the first commit with the
  rest of that file). A problem the parser finds after the fold, at a value
  whose origin is a variable, is now a problem with no file whose message
  starts with the variable's name, followed by the key and the message
  (`error: environment: TCW_WORK_STAGES_SPEC_PROMPT__APP:
work.stages.spec.prompt[0]: a binding must be a mapping …`). Every Design
  4 problem path was checked by hand first: the name (4.2), the key (4.3),
  a shared key (4.5), YAML, kind and `null` (4.6), `user.name` and the
  credential names (4.6), the `inherit` entry and a `file:` binding leaving
  the root (4.8) already started with the name, from `read_override` and
  `_confinement`. The ones that did not were all from `parse_work_config`:
  a binding's shape, its keys, its kinds, a `post` entry, a stage's `prompt`
  that is not a list, an unknown stage and an unknown procedure.
- **(c) Finding 3: the wording** (`e604c39a`). The sentence is in the
  release-notes entry, not the changelog: "stops commands in that project"
  is now "in any project", and it now also names a value the setting cannot
  take and says `tcw validate` starts the problem with the variable's name.
  The release notes add that `tcw validate` still checks the Jira settings a
  child, or a parent after the missing one, sets itself. The changelog gains
  three lines: the decided keys under an undecided `work.jira`, the
  variable's name, and `parse_jira_config`'s credential check.
- **(d)** This file.

## Decisions

Each was decided by the implementing agent, with its reason. None
contradicts the spec.

1. **`parse_jira_config` checks a credential name that is given when the
   other is missing.** It returned at the "required" problem before looking
   at the names given, so the review's `credentials: {email-env: "bad
name"}` was never checked, even with no parent (the review's "with no
   parent it reports both" holds for `timeout` and "required", not for the
   name). Design 3.2 drops "required" and keeps every other check of a
   decided key, so the name has to be checked on its own. The project with
   no parent now gets one more error, beside the "required" one; the
   parser's comment already said "every bad key is reported".
2. **A key TCW does not know, under an undecided `work.jira`, is decided
   when a layer after the last gap writes anything at or under it.** A
   mapping-valued unknown key (`bogus: {a: 1}`) is never itself "replaced
   whole", so the first form of the rule hid its "unknown key" problem. Its
   problem is that it is there, which no gap can undo, since a missing
   parent sits before that layer.
3. **The warning for an ancestor's decided key leaves the key undecided.**
   Design 1.6 treats a key both broken and undecided as undecided, and
   commands stop with exit 7; Design 3.2 still checks the decided part. The
   warning is the check; the withheld error stays 3.3's.
4. **A problem from a variable naming an ancestor** gets the same name-first
   message before it is marked broken, so its warning names the variable
   too. The file shown for another project's problem is unchanged (no
   display root), as before.

## Tests and mutation checks

New in `tests/test_inherited_config.py`: the review's scenario (both errors,
exit 1, no "required"); the same project with no parent; an ancestor after
the gap with a bad `timeout` (a warning naming its file, exit 0, exit 7 for
`require("work.jira")`); the same ancestor before the gap (no warning); and
unknown keys set by the project behind a gap. New in
`tests/test_config_environment.py`: thirteen variables, one per kind of
problem, each giving exactly one `tcw validate` error starting
`error: environment: <NAME>: `, and a `tcw work list` error starting with
the name.

Each mutation was applied, run against both files, and reverted:

- The old prefix filter back: the review's scenario, the ancestor warning
  and the unknown-key tests red (3).
- No warning for an ancestor's decided key: the ancestor warning test red.
- A warning for every mark under an undecided key: `cdd6be20`'s
  `test_a_broken_key_that_is_also_undecided_is_undecided` red. The new
  "before the gap" test stays green under it, because that problem is
  dropped earlier, by the filter; it guards the filter instead.
- `parse_jira_config` returning at "required" again: the review's scenario
  and the no-parent test red.
- No rule for unknown keys: the unknown-key test red.
- No variable name on a parser problem: nine of the thirteen variable cases
  red; the four that stay green are the problems `read_override` and
  `_confinement` already named.

## The suite

At `e604c39a`, from the worktree's root, with `-q -p no:cacheprovider`:

- The item's files (`tests/test_inherited_config.py`,
  `tests/test_config_environment.py`, `tests/test_config_keys.py`,
  `tests/test_config_overrides.py`, `tests/test_config_edit.py`,
  `tests/test_parent_links.py`, `tests/test_parent_links_cli.py`,
  `tests/test_manifest_cli.py`) with the four `tests/test_validate*.py`
  files: 540 passed, 14 skipped.
- `tests/config`: 244 passed.
- `tests/work tests/serve`: 1915 passed, 2 skipped (204 s).
- `tests --ignore=tests/work --ignore=tests/serve`: 4209 passed, 111 skipped
  (338 s).

No test failed, so `test_check_versions.py` needed no rerun.
