## Added

- The output contract for every command (TCW-73): `tcw/output.py` (`say`,
  `wrote`, `removed`, `created`, `changed`, `print_json`), the top-level
  handler in `tcw/cli.py` that prints `tcw <command words>: <error>` and exits
  with the error's code, and `tcw.errors.NO_PROJECT`, the one message for a
  command run outside a project.
- `tcw/findings.py`: `Finding(severity, where, message)`, returned by
  `validate()` and every `check()`.
- `tcw/cli_help.py`: the `--help` standard (`Prints:` and `Writes:` lines,
  examples, the exit-code table on `tcw --help`).
- `tcw projects list [--json]`.
- `tcw validate` checks a single work item when asked by `tcw serve`
  (`ValidationTarget(axis="work")`), and reports an invalid latest verdict
  round as a warning.
- Tests: `tests/test_cli_contract.py` (every leaf command, run as a
  subprocess), `tests/test_cli_help_standard.py`, `tests/test_static_guards.py`
  (git words, stdin, quoting), `tests/test_no_node.py`, and contract tests for
  each axis.

## Changed

- `tcw validate` prints findings on stdout graded error, warning or
  unresolved, with the count on stderr, and checks only the current project.
- The taxonomy and capabilities commands print only their product on stdout,
  name every file they write on stderr, raise the exit classes of
  `tcw/errors.py`, and never stage anything in git.
- `tcw capabilities drift` prints `<kind>: <path>: <message>` lines and checks
  completed work through the backend in Jira mode.
- `tcw init` and `tcw provision` say everything on stderr.
- The configuration key `connected-projects` is `projects`; the old key is a
  graph error naming the migration guide.
- "node" is "project" throughout `tcw/` (outside `tcw/serve/`): for example
  `find_project_root`, `project_root`, `child_projects`; a term or capability
  folder is an "entry" (`_load_entry`, `_write_entry`).
- The capability fields `Planning doc` and `Tracker` are retired.
- `tests/cli/scenarios/` keeps two scenarios (stdin and release integrity),
  rewritten for 3.0.

## Removed

- `tcw work nodes`, `tcw <axis> init`, `tcw taxonomy check`,
  `tcw capabilities check`, `tcw work procedure prompt`, the `tcw <axis> <path>`
  shorthand, `tcw provision --refresh`, `tcw validate [path] --no-recurse`,
  `capabilities list --local-only`, `capabilities extends <id> --rm`, and the
  short options `-s` and `-p`.
