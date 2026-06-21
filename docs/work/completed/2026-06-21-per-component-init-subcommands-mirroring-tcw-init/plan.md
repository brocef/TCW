# Plan — Per-component init subcommands

TDD: failing test first, then minimal code.

1. **Shared helper** (`tcw/cli.py`)
   - Extract `run_init(components)`; `_cmd_init` → `run_init(args.components or all)`.

2. **Component init subcommands** (`tcw/taxonomy/cli.py`, `tcw/capabilities/cli.py`)
   - Add `init` to `SUBCOMMANDS`; add an `init` subparser; `_init` does
     `from tcw.cli import run_init; return run_init([NAME])`.

3. **Unify work init** (`tcw/work/cli.py`)
   - Replace `_init` body with `return run_init([NAME])`; drop the now-unused
     `init` import.

4. **Tests** (`tests/test_taxonomy.py`, `tests/test_capabilities.py`, `tests/test_work.py`)
   - `tcw <component> init` returns 0, creates the tree (`.gitkeep`), and its
     output equals `tcw init <component>`.

5. **Docs sync**
   - `README.md` (init section), `docs/changelogs/upcoming.md`,
     `docs/release-notes/upcoming.md`, `skills/tcw-work/SKILL.md` if it mentions init.

6. **Capabilities reconcile** (completion)
   - Update `cli#scaffold-the-doc-trees` body; `tcw capabilities check`.
