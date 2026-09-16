# Outcome — Compose a procedure's instructions from project bindings the way a stage's are composed

## What shipped, task by task

| Plan task | Commit | What |
| --- | --- | --- |
| spec | `b2b8c857` | `spec.md` |
| plan | `c118b921` | `plan.md` |
| 1. Ids and defaults | `d90e492d` | `PROCEDURE_IDS`; ten `tcw/work/procedures/<id>.md` copied verbatim from their sources; `Builtins.procedures` loaded by a `_load_texts` helper shared with stage prompts; package data; `tests/test_shipped_procedures.py`; the wheel test in `tests/test_shipped_prompts.py` also checks the procedures |
| 2. Config | `c4b9a5a1` | `parse_procedures`, `LifecyclePolicy.procedures` / `.procedure()`, adapter wiring, `file:` checks, `tests/test_procedure_config.py` |
| 3. Resolution | `c47da9f6` | `resolve_procedure` and the shared `_compose` loop; `tests/test_resolve_procedure.py` |
| 4. Command | `d23f3b68` | `tcw work procedure prompt <id> [slug] [--no-exec]`; `tests/test_procedure_verb.py` |
| 5. Ledger | `f5e4d343`, `920e1471` | `work/run-a-procedure` and `work/configure-procedures` added as `Missing`, with Feature, Subject and Planning doc set; one sentence added to `work/configure-the-work-lifecycle`; `capabilities.yaml` |
| id correction | `d43b112f`, `0515903e` | `autonomous-work` renamed to `unattended-work` (see below) |
| 6. Documentation | `fcf57fcc` | README, release notes, changelog, `tcw-work` `commands.md` and `hooks.md`, `tcw-configure` `work.md`, `docs/guide/configuration.md` |

Every new test was watched failing first: at import, then on its assertion.
Mutation checks were run where a test could pass by accident. Dropping the
procedure `file:` check turned three config tests red. Setting the hook role back
to `prompt` turned the generator test red. Removing the stderr note turned the
note test red. Editing one byte of a default made the parity test name that id.
`tcw work procedure prompt delegation` diffed clean against
`skills/tcw-work/references/procedures/delegation.md`.

## Test result

A bare `pytest`, run from the worktree root with the worktree's own virtual
environment first on `PATH`, just before this was written: `3460 passed in
1935.88s`. `tcw capabilities check` printed "capabilities OK", and
`tcw validate` printed "validate OK".

## Documentation Sync

- `README.md` [Public-API] — fired. Added a paragraph under the lifecycle
  section and a `tcw work procedure` row in the command table.
- `docs/release-notes/upcoming.md` [Public-API] — fired.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — fired: Added and Changed
  entries.
- `skills/tcw-work` [Skill-Driven-Component] — fired. `SKILL.md` is untouched
  (its body is 59 of 60 lines); the new verb went into `references/commands.md`,
  and a `procedure` row went into the roles table in `references/hooks.md`.
- `skills/tcw-configure/references/work.md` [Configuration-Key-Change] — fired:
  a new `work.procedures` section.
- `docs/guide/jira.md` [Tracker-Change] — did not fire.
- `docs/guide/configuration.md` is not a documentation entry, but it documents
  `stage prompt` for users, so it gained a paragraph on procedures.

## What the plan or spec got wrong

1. **The id `autonomous-work` could not ship.** It is the name of a skill TCW
   removed, and `DELETED_NAMES` in `tests/test_skill_lifecycle_parity.py` fails
   any live document that names it. The docs pass caught this. The spec had not
   checked that list. The id is now `unattended-work`, and the spec's Notes
   record the change. An id that reads like a skill name is the confusion the
   id rule exists to prevent, so the id was renamed and the guard left alone.
2. **Plan task 1 proposed a second wheel build** in a new test file.
   `tests/test_shipped_prompts.py` already builds a wheel from a clean copy of
   the tracked files, so its test was extended instead. Building one wheel
   instead of two keeps the suite from getting slower.
3. **The wheel test only sees files git tracks.** New default files show as
   missing from the wheel until they are staged. That is correct behaviour and
   not a bug, but neither the spec nor the plan mentioned it.
4. The plan's example test for criterion 4 guessed a store API
   (`create(..., tags=)`) that does not exist. The test uses
   `register_tags` / `update_work` instead, following the existing
   `test_stage_verb.py`.

Nothing else departed from the plan.

## Notes

- **The lifecycle was driven by hand, not by the `tcw` CLI.** This item changed
  `tcw/`, so `docs/work/` was edited directly. No transition was run: the item
  stays `active`. The two new capabilities stay `Missing` until the coordinating
  session's `complete` sets them to `Supported`.
- **Gates.** The `spec` and `plan` gates refused because the item was already
  active; the requester chose to go ahead anyway. The `implement` gate passed.
  The only `pre` check bound to any of these stages, `require_artifact.py spec`
  on `plan`, was run by hand and passed. The spec and plan Notes say this.
- **Tests used the worktree's code.** They ran against a virtual environment in
  `.worktrees/<slug>/.venv`; the shared editable install was not changed.
  Running `python -c 'import tcw'` from the primary checkout loads the primary
  checkout's `tcw/`, so every command ran from the worktree root.
- **Decisions for the requester to confirm** are listed in `spec.md`: the id
  names (now including `unattended-work`), verbatim defaults guarded by a parity
  test, a plain list per id, no header or harness notice in the output,
  conditional-only bindings resolving to nothing plus a stderr note, and shared
  limits with `TCW_HOOK_ROLE=procedure`.
- **For conversion children 3–6.** When a child turns a skill into a reader of
  `tcw work procedure prompt`, it changes that skill's row in `SOURCES` in
  `tests/test_shipped_procedures.py`, in the same commit that changes the
  default.
- **No defect found in the existing CLI.** `tcw work list` has no `--json`
  (only `show` does), but no document claims otherwise.
