# Plan: Let tcw work edit change an item's type to or from epic

Sequential, on `main` in the primary checkout. Each task: failing test first, watch
it fail, then the code. Suite run once at the end (it takes ~16 minutes); targeted
test files run per task.

Per `CLAUDE.md`, once `tcw/` is being edited the lifecycle is not driven through the
`tcw` CLI: `start` runs before the first code edit, and `submit`/`complete` run only
after the code is committed and the suite is green.

## Task 1 — store: `type` on `update_work`, with the demotion rule

- Modify `tcw/store/base.py`:
    - `WorkStore.update_work` signature gains `type: Any = _UNSET`; docstring states
      the valid values and the two demotion refusals.
    - New concrete `WorkStore._check_type_change(self, item: WorkItem, new_type) -> None`:
      raises `ValueError` for a value outside `WORK_TYPES` (`base.py:972`); when
      `item.type == "epic"` and `new_type == ""`, raises if
      `initiative_children(item.slug)` is non-empty (message names them and says to
      complete the epic or clear their `--initiative` first), or if
      `incomplete_graph_note()` is non-empty (message ends with the note and says to
      run from a checkout that has those projects).
- Modify `tcw/store/fs.py` `FsWorkStore.update_work`: accept `type`; call
  `_check_type_change` with the other validation, before any write; apply
  `state["type"] = type` in the same form `create_work` writes it, and set
  `changed`.
- New tests in `tests/test_edit_type.py` (reusing `mk_node` from
  `tests/test_recursion.py`): criteria 2, 3 (open and completed child), 4
  (descendant project), 5 (unreachable parent config, as in
  `test_an_unresolvable_epic_names_the_missing_projects`), and that promotion and a
  same-type set succeed.
- Proof: `pytest tests/test_edit_type.py tests/test_recursion.py tests/test_epic_completable.py`.

## Task 2 — CLI: `tcw work edit --type`

- Modify `tcw/work/cli.py`:
    - parser: `pe.add_argument("--type", choices=["epic", ""], help=…)`; update the
      `edit` subcommand help to mention the type.
    - `_edit`: when `args.type is not None`, first refuse under strict mode via
      `_strict_says_no("edit", f"{bare} was not changed", …)`; then call
      `st._check_type_change(current, args.type)` before the blocker writes; pass
      `type=_provided(args.type)` to `update_work`.
- Tests in `tests/test_edit_type.py`: criteria 1, 6, 8 via `tcw.cli.main`.
- Strict test in `tests/test_tracker_strict.py` beside `test_an_epic_is_not_gated`:
  criterion 7, both directions.
- Proof: `pytest tests/test_edit_type.py tests/test_tracker_strict.py`.

`_check_type_change` is called from the CLI by name, although underscored, so the
refusal can precede blocker writes without reordering `_edit`'s existing blocker
logic. If that reads badly in review, the alternative is moving the blocker writes
after `update_work`, which changes when an invalid `--blocks` ref is caught.

## Task 3 — full suite

`pytest -q` (bare, as CI runs it).

## Documentation Sync

- `README.md` [Public-API] — fires: `:608` table row "changes an item's title,
  estimates, tags or blockers" → add "type".
- `docs/release-notes/upcoming.md` [Public-API] — fires: a short section.
- `docs/changelogs/upcoming.md` [Any-Code-Change] — fires: Added (`--type`,
  `update_work(type=)`, `_check_type_change`).
- `skills/<component>/SKILL.md` [Skill-Driven-Component] — fires for `work`:
  `skills/work/references/commands.md` gains a row for changing an item's type.
- `docs/guide/work.md` — not a configured entry, but its epic section (`:529`)
  shows `edit --initiative`; add one line for `--type epic`.
- `docs/guide/jira.md` [Tracker-Change] — fires: `:544` lists `tcw work edit` as
  never refused under strict mode; add the `--type` exception.
- `skills/configure/references/*` [Configuration-Key-Change] — does not fire.
- Capability ledger: update the two capabilities the spec names, with
  `Planning doc` set to this slug.

## Verification

- Hands-on: in a scratch project, promote an item, attach a child, see it grouped
  and `ready-to-close` after resolving the child; try demoting with the child;
  strict node refusal. The suite covers each, but the board output is read by eye.
