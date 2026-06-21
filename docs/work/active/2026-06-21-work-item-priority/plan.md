# Plan — Work item priority

TDD: write the failing test first per step, then the minimum code.

1. **Model + ordering core** (`tcw/store/base.py`)
   - Add `priority: int | None = None` to `WorkItem`.
   - Add `priority_order(items)`: stable sort, specified priorities (desc)
     above unspecified (input order kept). Lazy two-key sort.
   - `WorkStore.board()` → `topo_order(priority_order(self.query(status)))`.
   - Add `priority` param to abstract `create(...)`.
   - Test: `priority_order` puts higher first, unspecified keep input order;
     `board()` with a blocker still precedes blocked (priority can't jump a
     hard constraint).

2. **FS persistence** (`tcw/store/fs.py`)
   - `create(..., priority=None)` writes `priority` into `state.yaml`.
   - `get()` reads `state.get("priority")`.
   - Test: round-trip create-with-priority → get; set via `set_field` → get.

3. **CLI** (`tcw/work/cli.py`)
   - `new`: `--priority` (`type=int`) → pass to `create`.
   - `edit`: `--priority` (`type=int`) → `set_field` when provided.
   - `_print_item` (show): print `priority:` when set.
   - Test: `new --priority` then `list` ordering; `edit --priority` reorders.

4. **Docs sync** (documentation-sync skill at the end)
   - `README.md`, `docs/release-notes/upcoming.md`,
     `docs/changelogs/upcoming.md`, `skills/tcw-work/SKILL.md` quick-reference.

5. **Capabilities reconcile** (completion gate)
   - Add `## Prioritize a work item` heading to `docs/capabilities/work/capabilities.md`,
     set Status Supported; update `view-the-board` body for the ordering;
     `tcw capabilities check`.
