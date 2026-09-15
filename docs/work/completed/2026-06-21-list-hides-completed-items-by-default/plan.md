# Plan — List hides completed items by default

TDD: failing test first, then minimal code.

1. **CLI default + `--all`** (`tcw/work/cli.py`)
   - `_list`: no `--status` → drop `completed`; `--status` honored as-is;
     `--all` → full board.
   - Add `--all` flag to the `list` subparser.
   - Tests (CLI, capsys): default omits a completed item; `--status completed`
     shows it; `--all` shows it alongside the live columns.

2. **Docs sync**
   - `README.md` board paragraph + the `tcw work list` example lines.
   - `skills/tcw-work/SKILL.md` quick-ref ("see the board" row).
   - `docs/changelogs/upcoming.md` (Changed) + `docs/release-notes/upcoming.md`.

3. **Capabilities reconcile** (completion)
   - Update `work#view-the-board` body for the default + `--all`; `tcw capabilities check`.
