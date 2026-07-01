# Plan — optional effort & complexity fields for work items

Input: `spec.md`. Small additive change; one implementer, mostly one sitting.
Phases 1–3 are the code; Phase 4 is tests; Phase 5 is docs-sync. Phases 4 and 5
can run in parallel with each other once Phases 1–3 land.

## Phase 1 — spine (`tcw/store/base.py`)

1. Add the value-set constant near `WORK_RESOLUTIONS` (~`:184`):
   ```python
   WORK_LEVELS = ("low", "medium", "high", "very-high")
   ```
2. Add two fields to `WorkItem` (after `priority`, ~`:206`):
   ```python
   effort: str = ""        # WORK_LEVELS or "" (unset)
   complexity: str = ""    # WORK_LEVELS or "" (unset)
   ```
No signature changes to `create`/`set_field` — they stay generic.

## Phase 2 — FS adapter (`tcw/store/fs.py`)

In `_item_from_dir` (~`:917`), add to the `WorkItem(...)` construction:
```python
effort=state.get("effort") or "",
complexity=state.get("complexity") or "",
```
Use `or ""` (not a `""` default) so a hand-edited `state.yaml` with a bare
`effort:` (YAML null) coerces to `""` instead of `None`, honoring the `str` type
hint (degrade-don't-crash, like `_safe_yaml`). Nothing else — `set_field` (`:997`)
already persists arbitrary keys to `state.yaml`.
`create` (`:976`) is left as-is; new items simply have no `effort`/`complexity`
keys until set (read back as `""`).

## Phase 3 — CLI (`tcw/work/cli.py`)

1. **Parsers** (`add_subparser`): add to both `new` (~`:398`) and `edit` (~`:427`):
   ```python
   p.add_argument("--effort", choices=WORK_LEVELS, help="estimated effort")
   p.add_argument("--complexity", choices=WORK_LEVELS, help="estimated complexity")
   ```
   Import `WORK_LEVELS` from `tcw.store.base` (extend the existing import at `:7`).
2. **`_new`** (~`:162`, beside the `--epic`/`--initiative` `set_field` calls):
   ```python
   if args.effort is not None:
       st.set_field(item.slug, "effort", args.effort)
   if args.complexity is not None:
       st.set_field(item.slug, "complexity", args.complexity)
   ```
   (`is not None` in both `_new` and `_edit` — consistent, and correct if a clear
   flag is ever added.)
3. **`_edit`** (~`:301`, beside `--priority`/`--initiative`):
   ```python
   if args.effort is not None:
       st.set_field(args.slug, "effort", args.effort)
   if args.complexity is not None:
       st.set_field(args.slug, "complexity", args.complexity)
   ```
   (`choices` makes argparse default `None`; a passed value is always valid.)
4. **`_print_item`** (~`:58`, right after the `priority` line):
   ```python
   if item.effort:
       print(f"effort: {item.effort}")
   if item.complexity:
       print(f"complexity: {item.complexity}")
   ```
`_list` is untouched.

## Phase 4 — tests (parallel with Phase 5)

Add to the existing work test module (find via
`grep -rl "work new\|FsWorkStore" tests/`; likely `tests/test_work_cli.py` or
`tests/test_work.py`). Cover the 6 acceptance criteria:
- `new --effort high --complexity low` → `state.yaml` has both keys; `get()` reads them.
- `edit --effort medium` updates only effort, leaves complexity.
- `show` prints the lines when set, omits them (no blank line) when unset.
- invalid `--effort bogus` → argparse `SystemExit` / non-zero, no write.
- pre-existing item with no keys → `effort == "" and complexity == ""`, `list` unchanged.
- **hand-edited `state.yaml` with `effort:` null → reads back `""`** (guards the
  `or ""` coercion in Phase 2).

## Phase 5 — docs-sync (parallel with Phase 4)

Per CLAUDE.md Documentation Sync triggers that fire:
- `README.md` — add `--effort`/`--complexity` to the `work new`/`edit` examples
  (near `:291`/`:309`).
- `skills/tcw-work/SKILL.md` — add a quick-reference row (beside the `set priority`
  row): `set estimates | tcw work new/edit … --effort <l> --complexity <l>`.
- `docs/capabilities/work/capabilities.md` — add the "Estimate a work item's effort
  and complexity" capability from `spec.md` (Status: Supported).
- `docs/changelogs/upcoming.md` — Added entry (technical), with commit hash range.
- `docs/release-notes/upcoming.md` — Added entry (plain language).

**Not touched:** the 5 version files / `tests/test_plugin_manifests.py` — no release
cut here (version bump is a closeout decision, per `scripts/cut_version.py`).

## Implementation boundary & verification

- Run `tcw work start <slug>` before the first code edit; commit that transition
  first (AGENTS.md). No `--worktree` needed — small single-checkout change.
- Verify: `python -m pytest tests/ -q` (whole suite; manifests test guards versions).
- Manual smoke:
  ```
  tcw work new "smoke" --effort high --complexity low
  tcw work show <slug>            # shows effort/complexity
  tcw work edit <slug> --effort medium
  tcw work new "bad" --effort nope   # argparse rejects
  ```

## Touch-point summary

| File | Change |
|---|---|
| `tcw/store/base.py` | +`WORK_LEVELS`, +2 `WorkItem` fields |
| `tcw/store/fs.py` | +2 read lines in `_item_from_dir` |
| `tcw/work/cli.py` | +2 flags ×2 parsers, +2 `set_field` blocks ×2 handlers, +2 display lines |
| `tests/…` | new field round-trip + rejection tests |
| README, SKILL.md, capabilities.md, changelog, release-notes | docs-sync |
