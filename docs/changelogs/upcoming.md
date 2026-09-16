# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

## Added

- **`tcw work stage validate [words…]`** (`tcw/work/cli.py`): reports whether a
  `tcw-work-stage` invocation's arguments are ones `tcw work stage prompt` would
  accept — a known stage id, no item for `inbox`, otherwise an optional
  reference resolving to exactly one item; status is not judged. Valid: no
  output, exit 0. Invalid: a Markdown usage error plus the reason on stdout,
  exit 1 (`_resolve`'s stderr message is captured into the reason). Under a
  harness other than Claude Code, a notice that injected commands must be run
  by hand is printed first, even when valid.
- **`tcw/harness.py`**: `ancestor_programs()` walks the process's ancestors via
  `ps`, falling back to `/proc`, and never raises; `detect()` returns the
  nearest `claude`/`codex` ancestor's harness, else `other` when
  `CODEX_THREAD_ID`, `CODEX_SANDBOX` or `CODEX_SESSION_ID` is set, else
  `claude`.

## Changed

- `skills/tcw-work-stage/SKILL.md` injects
  `` tcw work stage validate $ARGUMENTS 2>/dev/null || true `` ahead of its
  heading. `2>/dev/null` keeps an older `tcw` without the verb silent.
- `skills/tcw-work/SKILL.md` and `references/commands.md` no longer link or name
  the `references/lifecycle/stage-*.md` documents. The router sends agents to
  `tcw-work-stage` in an emphasized note; `commands.md` gains a `validate` row.
- `tcw-commands-plan-work`, `tcw-commands-verify-work`,
  `tcw-commands-process-inbox`, `tcw-commands-drive-work-to-completion`,
  `tcw-post-mortem` and `tcw-extras-triage-issues` invoke `tcw-work-stage`
  instead of reading stage documents. `agents/tcw-verifier.md` names the
  `verify` stage rather than its file.
- `stage` subparser metavar is `{prompt,gate,validate}`.

## Fixed

- `skills/documentation-sync/SKILL.md` cited steps 4, 6 and 9 of the stage
  documents; they are steps 1, 3 and 5.

## Removed

- `skills/tcw-work/references/lifecycle/default/README.md`, which pointed at
  `tcw/work/prompts/*.md` — files that ship with the Python package, not the
  plugin.

## Internal

- `tests/test_skill_lifecycle_parity.py`: the router test now asserts that
  nothing in `tcw-work` outside `references/lifecycle/` names a stage document,
  the orphan check exempts `references/lifecycle/`, and new tests require the
  bold `tcw-work-stage` note and the validation line as the stage skill's first
  injected command. New `tests/test_harness.py` and
  `tests/test_stage_validate.py`.
