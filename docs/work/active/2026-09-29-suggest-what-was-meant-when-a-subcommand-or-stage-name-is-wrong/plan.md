# Plan — Suggest what was meant when a subcommand or stage name is wrong

Worked in a worktree (`start --worktree`), with a scratch venv pinned to it.

## Task 1 — Failing tests

**Creates** `tests/test_command_suggestions.py`: one test per acceptance
criterion 1-8. They drive `tcw.cli.main` in-process and capture stderr and
the `SystemExit` code, except criterion 4, which runs the CLI as a
subprocess. Criteria 1-6 are `xfail(strict=True)`. Criteria 7 and 8 must pass
before and after: 7 guards that option values get no hint, and 8 runs on the
current tree, where most parsers are plain `ArgumentParser`s, so it is also
`xfail`.

## Task 2 — The parser class and the index

**Creates** `tcw/cli_suggest.py`:
- `SuggestingParser(argparse.ArgumentParser)` sets
  `suggest_on_error = False`.
- `_visible_choices(action)` returns the names the action lists in its help
  (`action._choices_actions`). That leaves out the removed stage spellings
  generally, since they are registered without `help=`, and needs no
  special-casing.
- `_check_value(action, value)`: for a `_SubParsersAction` with an invalid
  value, raise `ArgumentError` with argparse's own message, built from
  `_visible_choices`, followed by `hint(...)` on a new line. Any other action
  goes to `super()`.
- `hint(parser, word, following)` applies, in order, the elsewhere-in-the-tree
  rule (using the next word), the synonym table, then `difflib` among the
  visible choices, and returns "" when nothing matches.
- `attach_index(root)` walks the tree once and gives every parser the same
  `name → [full paths]` map and a reference to the root. The root keeps the
  argument list it is parsing (`parse_known_args` override) so a nested
  parser can find the word after the invalid one.

**Modifies** `tcw/cli.py`: `build_parser` uses `SuggestingParser` and calls
`attach_index`. **Modifies** `tcw/work/cli.py`: `_HidesRemovedSpellings`
becomes a subclass whose only remaining job is the existing
`{"prompt","gate"}` message shape. Its "choose from" list now comes from
`_visible_choices`, the same set as before, and it gains the hint.
**Proves** criteria 1-3, 6-8.

## Task 3 — Stage names

**Modifies** `tcw/work/cli.py` `_stage_step`: after today's message, one hint
line built from `LIFECYCLE_STEPS`:
- an artifact name (with or without `.md`) → its stage;
- `post-mortem` → the `postmortem` stage;
- a transition → its command;
- `rework` → both;
- otherwise `difflib` among the stage ids.

The exit code stays 1. **Proves** criteria 4-5.

## Task 4 — Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change];
  `docs/release-notes/upcoming/<slug>.md` [Public-API: what an error prints].
- The new capability `cli/get-a-suggestion-for-a-mistyped-command` (with
  `tcw capabilities add`) and the item's `capabilities.yaml` (`added:`).
- `skills/work/SKILL.md` [Skill-Driven-Component]: not triggered. No verb,
  field or lifecycle rule changes. Re-checked at implementation.
- README and the guides: one sentence in `docs/guide/work.md`'s command
  reference only if it has a section on errors. Re-checked.

## Task 5 — Full suite

Bare `pytest`, with the venv first on PATH. **Proves** criterion 9.

## Verification

By hand: the three commands from the issue, plus `tcw work strat x`, `tcw work
stage gat x`, `tcw spec`, and `tcw work list --status bogus`, with their
stderr read as a user would read it.
