# Plan — Pipe-delimit the list board output

TDD: update the failing test first, then minimal code.

1. **CLI delimiter** (`tcw/work/cli.py` `_list`)
   - Replace `\t` separators (row + blocked-by suffix) with ` | `.
   - Update `test_cli_list_shows_priority_column` to split on ` | `;
     it now asserts the pipe-delimited layout.

2. **Docs sync**
   - `README.md` board paragraph (row example → `|`-delimited).
   - `docs/changelogs/upcoming.md` (Changed) + `docs/release-notes/upcoming.md`.

3. **Capabilities reconcile** (completion)
   - Update `work#view-the-board` body to note the `|` delimiter;
     `tcw capabilities check`.
