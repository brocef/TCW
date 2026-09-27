# Plan: Say so when tracker import --parent meets a ticket already bound here

Work in a worktree (`tcw work start <slug> --worktree`) with its own venv.

## Tasks

1. **Tests first** — `tests/test_tracker_strict_gate.py`, beside the criterion 4
   tests of the earlier item (`test_import_nests_the_child_under_a_parent`,
   ~line 104), reusing its `strict` and `unclaimed` fixtures and `cli` helper.
   One test per criterion 1-6. For criterion 5, take `len(fake.writes())` and
   the bound item's `state.yaml` bytes before the second import and compare
   after. Proof: criteria 1, 2, 5 and 6 fail on main (exit 0); criteria 3 and 4
   pass, and are mutation-checked by temporarily making the new branch refuse
   every re-run and seeing them go red.

2. **The check** — `tcw/work/cli.py` `_tracker_import`, in the
   `ticket.assignee_id == ticket.me_id` branch (~2716): read
   `st.get(existing)`, compare `parent` and `initiative` as the spec's Design
   says, print one stderr line per mismatch and return 1; otherwise print
   `→ already bound` and return 0 as today. Proof: the task 1 tests pass.

3. **Help text** — `tcw/work/cli.py`, the `import` parser (~4360-4392): the
   epilog's "Running it again …" sentence gains "and refuses, changing nothing,
   when --parent or --initiative names a placement that item does not have";
   the refusal list gains the same case. Proof: `tcw work tracker import -h`
   shows it; any help-text test that pins the epilog is read and updated.

4. **Full suite** in the worktree.

5. **Documentation Sync** (one pass over the finished diff):
   - `docs/changelogs/upcoming.md` [Any-Code-Change]: under the existing entry
     for `tracker import --parent` / `--initiative`, add the refusal.
   - `docs/release-notes/upcoming.md` [Public-API]: the same, in plain words,
     beside the note that introduced the options.
   - `docs/guide/jira.md` [Tracker-Change]: "Running it again is safe" gains a
     sentence on the refusal and where to change the parent.
   - `skills/work/references/commands.md` [Skill-Driven-Component]: the import
     row says the options apply to the item it creates.
   - Capabilities `work/manage-external-tracker-intake` and
     `work/require-tracker-backed-work`: the changes in the spec; then the
     `capabilities` sub-skill's reconciliation.
   - Not firing: `README.md` (no new command or option), `docs/guide/<topic>.md`
     other than jira (nothing about files or settings changes),
     `skills/configure/references/*` (no configuration key).

## Verification

- Hands-on: the fake tracker is the only tracker the suite can drive, and a real
  Jira project is not available to this session without spending on the user's
  account. The hands-on check is therefore the CLI against the same fake used by
  the suite, run by hand in a scratch strict node: import a ticket, import it
  again with `--parent`, read the exit code, both output streams and the item's
  `state.yaml`.

## Notes

- The earlier item's changelog entry is in `docs/changelogs/upcoming.md`; this
  one extends it rather than adding a separate Fixed line, since the options
  have not shipped.
