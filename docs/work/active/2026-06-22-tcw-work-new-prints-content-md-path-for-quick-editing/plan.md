# Plan

1. **`tcw/store/fs.py`** — add `FsWorkStore.body_path(slug) -> Path | None`:
   resolves the item dir and appends `content.md` (keeps the filename literal in
   the adapter; litmus: FS-only, not on the abstract `WorkStore`).
2. **`tcw/work/cli.py`** — in `_new`, after `print(item.slug)`, print
   `→ edit: {st.body_path(item.slug)}` to stderr (guard `None`).
3. **`tests/test_work.py`** — assert `body_path` returns `<dir>/content.md` and
   exists after `create`.
4. **Docs sync:**
   - `docs/capabilities/work/capabilities.md` — extend "Open a work item" wording.
   - `docs/changelogs/upcoming.md` — Changed entry + hash range.
   - `docs/release-notes/upcoming.md` — user-facing line.
   - `skills/tcw-work/SKILL.md` — note the edit line in `work new` description.
   - `README.md` — update if it shows `work new` output (check).
