# Plan — Show priority in the list board

TDD: failing test first, then minimal code.

1. **CLI column** (`tcw/work/cli.py` `_list`)
   - Insert `{item.priority if not None else '-'}` between phase and title.
   - Tests (capsys): a prioritized item's row shows its int; an unspecified
     item's row shows `-`.

2. **Docs sync**
   - `README.md` board paragraph (note the priority column).
   - `docs/changelogs/upcoming.md` (Changed) + `docs/release-notes/upcoming.md`.
   - `skills/tcw-work/SKILL.md` — no change (quick-ref already covers list).

3. **Capabilities reconcile** (completion)
   - Update `work#view-the-board` body to mention the priority column;
     `tcw capabilities check`.
