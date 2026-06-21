# Per-component init subcommands mirroring tcw init

## Product changes

- `tcw taxonomy init` and `tcw capabilities init` are added — each scaffolds
  its own `docs/<component>/` tree, mirroring `tcw init <component>`.
- `tcw work init` already existed; it now produces the same output as
  `tcw init work` so all three component inits are true mirrors.
- `tcw init` (all three by default, or named subset) is unchanged.

## Technical changes

- Extract `run_init(components)` in `tcw/cli.py` (git-root check → scaffold →
  report). The top-level `_cmd_init` and each component CLI's `init` subcommand
  call it; component CLIs import it function-locally to avoid an import cycle.
- No store-interface change — scaffolding stays a CLI/FS-adapter concern.

## Meta changes
