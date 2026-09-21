# Keep comments and formatting when tcw writes a key into tcw-config.yaml

## Request

When a `tcw` command writes a key into a node's `tcw-config.yaml`, only that key's
lines should change. Comments, key order, quoting, line wrapping and indentation
everywhere else in the file must survive. Today `tcw capabilities extends`,
`tcw taxonomy extends add` (and `rm`), and `tcw work tags add` re-serialise the whole
file with `yaml.safe_dump`, deleting comments and reformatting the rest. The 2.5.0
migration guide recommends the `extends` commands as the easy route, so the damage
lands on every annotated config that is migrated that way.

## Constraints

- v2.5.1 is held until every item filed from the proposit-app reports on
  2026-09-21 is fixed and accepted. This is one of them.
- No new runtime dependency: `pyproject.toml` keeps runtime dependencies at
  `PyYAML` alone, deliberately.

## Notes

- Written during an autonomous run: the requester asked for proposit-app's reports
  to be tracked at high priority and fixed before v2.5.1, and was not asked the
  request-stage questions for this sixth item. Assumptions, marked for `spec`:
  - Scope is every command that writes the node config, not only the two `extends`
    commands, because they share one writer.
  - The migration guide's recommendation of the `extends` commands can stay once
    they no longer damage the file.
- Reference material: the proposit-app session's report, recorded in `intake.md`.
