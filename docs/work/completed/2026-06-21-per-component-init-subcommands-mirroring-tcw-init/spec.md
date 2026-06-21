# Spec — Per-component init subcommands

## Behavior

- `tcw taxonomy init` → scaffolds `docs/taxonomy/`.
- `tcw capabilities init` → scaffolds `docs/capabilities/`.
- `tcw work init` → scaffolds `docs/work/{inbox,backlog,active,completed}/`.
- Each is byte-identical to `tcw init <component>` (same git-root refusal, same
  "Scaffolded N dir(s)…" report).
- `tcw init [components…]` unchanged (defaults to all three).

## Design

One shared `run_init(components: list[str]) -> int` in `tcw/cli.py`:
git-root check → validate components ⊆ `COMPONENTS` → `init(components, root)` →
print created dirs. `_cmd_init` delegates; each component CLI's `_init` does a
function-level `from tcw.cli import run_init` (avoids the module-load cycle —
`cli.py` imports the component modules) and returns `run_init([NAME])`.

`tcw work init` loses its bespoke "Initialized docs/work/…" message in favor of
the unified report — no test asserts the old message, so the mirror is safe.

## Litmus

Scaffolding is a CLI/FS-adapter concern; `init()` already lives in `fs.py`. No
abstract store-interface method added.

## Capability delta

- **Changed:** `cli#scaffold-the-doc-trees` — also reachable as
  `tcw <component> init`.
