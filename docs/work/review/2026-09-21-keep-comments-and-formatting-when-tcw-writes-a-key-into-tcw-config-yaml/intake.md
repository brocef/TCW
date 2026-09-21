# Keep comments and formatting when tcw writes a key into tcw-config.yaml

`tcw capabilities extends <id>` and `tcw taxonomy extends add <id>` add their key to
the node's `tcw-config.yaml` by re-serialising the whole file with `yaml.safe_dump`
(`FsTreeStore._write_node_config` in `tcw/store/fs.py`). Every comment in the file is
deleted, long strings are reflowed across lines, and the indentation style changes
(4 spaces became 2). The docstring there records this as "accepted, and true of
`tcw work tags add` before this", so `tcw work tags add` has the same effect.

The 2.5.0 migration guide recommends those two commands as the easy way to move
`extends`. So every project with a hand-annotated config silently loses its comments
on upgrade.

## What happened

In proposit-app on 2026-09-21 (tcw 2.5.0, macOS), migrating three nodes with
`tcw capabilities extends proposit-shared` and `tcw taxonomy extends add proposit-core`
produced a 31+/22- diff where 9+ was expected. It deleted three comment lines in one
node's `work.lifecycle` block and more in another node's documentation descriptions,
reflowed a long `work.tracker.candidate-query`, and switched the indentation from
4 spaces to 2. The workaround was to `git restore` the files and add the keys by hand.

## What is wanted

Writing one key into `tcw-config.yaml` changes only that key's lines. Comments,
ordering, quoting, line wrapping and indentation elsewhere survive. This applies to
every command that writes the node config.

## Origin

Reported 2026-09-21 by the Claude session working in proposit-app, after migrating to
2.5.0. The requester asked for all of that session's reports to be tracked at high
priority, and v2.5.1 is held until they are fixed.

## References

- `tcw/store/fs.py` `_write_node_config` and `_persist_extends`, and the
  `tcw work tags add` path that calls the same writer.
- `pyproject.toml`: runtime dependencies are deliberately `PyYAML` alone.
- `docs/migration-guide-2.4.X-to-2.5.0.md`: recommends the rewriting commands.
