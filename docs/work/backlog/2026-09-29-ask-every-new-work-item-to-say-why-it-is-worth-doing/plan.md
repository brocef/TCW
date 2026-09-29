# Plan — Ask every new work item to say why it is worth doing

## Tasks

1. Write `docs/procedures/create-work.md`.
2. Add the `work.procedures.create-work` bindings to `tcw-config.yaml`.
3. Run `tcw validate`, then `tcw work procedure prompt create-work`, and read
   the output against the acceptance criteria.

## Documentation Sync

- **`skills/work-create/SKILL.md`:** not changed. It already injects whatever
  the procedure prints.
- **`skills/configure/references/work.md`:** not changed. No key changes
  meaning; this is a use of an existing key.
- **Changelog and release notes:** not triggered, because `tcw/` does not
  change. This is this repository's own configuration, not a change users of
  TCW receive.
