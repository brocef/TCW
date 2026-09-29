## Fixes

- `--blocked-by` now understands a reference to an item in the same project
  written with the project's own name (`myproject/<item>`) or with its status
  (`backlog/<item>`), and records it as that item. Before, it was stored as plain
  text that never stopped blocking — and an item could be made to block itself.
  `--unblocked-by` accepts the same forms. A blocker stored as text by an
  earlier version is replaced when you add the same item again.
