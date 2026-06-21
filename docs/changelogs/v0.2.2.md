# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category, with commit hash ranges so entries trace back to source.

## Added (ba3960d..aad36c8)

- Per-component `init` subcommands: `tcw taxonomy init` and `tcw capabilities
  init`, mirroring `tcw init <component>`. New shared `run_init(components)` in
  `tcw/cli.py`; the top-level `_cmd_init` delegates to it, and component CLIs
  import it function-locally to avoid the module-load import cycle.

## Changed (ba3960d..aad36c8)

- `tcw work init` now reports via the shared `Scaffolded N dir(s)…` output
  (was the bespoke `Initialized docs/work/ under …` line), so all three
  component inits are byte-identical to `tcw init <component>`. The unused
  `git_root`/`init` imports were dropped from `tcw/work/cli.py`.
