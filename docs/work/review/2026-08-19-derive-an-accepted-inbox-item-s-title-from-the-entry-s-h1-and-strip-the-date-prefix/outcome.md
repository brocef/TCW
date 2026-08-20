# Outcome — Derive an accepted inbox item's title from the entry's H1 and strip the date prefix

Shipped as planned: four code tasks, then the documentation block. No task was
abandoned, no design was improvised, and no scope was added. Six commits.

## What shipped

| Task | Commit | What landed |
| --- | --- | --- |
| 1 — bound `_unique_slug` | `297039d` | Slug body capped at 120 chars, `rstrip("-")` after the cut, `or "untitled"`; collision loop untouched. `create_work` and `inbox_accept` both inherit it. 6 tests in `tests/test_work.py`. |
| 2 — the heading scan | `c2b3081` | `body_title` and `frontmatter_end` as module-level functions in `tcw/store/base.py`; `FsWorkStore._frontmatter` refactored onto `frontmatter_end`. New `tests/test_inbox_title.py`, 20 assertions. No caller yet. |
| 3 — wire it in | `6c733e5` | `_DATE_PREFIX` beside `slugify`; `inbox_accept`'s single `accepted_title` line becomes the precedence plus the label-slug rule; `WorkStore.inbox_accept`'s docstring states the contract. 17 tests in `tests/test_work.py`. |
| 4 — capability ledger | `3c4ae83`, `077c9ea` | `manage-the-work-inbox` states the precedence, `open-a-work-item` states the slug floor; both stay `Supported`. Item `capabilities.yaml` written. `tcw validate` exits 0. |
| Documentation Sync | `933122d` | `README.md`, `docs/work-inbox-template.md`, `skills/tcw-work/references/stage-inbox.md`, `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`. |

Every test was written first and watched fail. Task 1's six: five red, one
(`…_ordinary_title_is_unchanged`) green from the start, which is what it is for.
Task 2's file failed at import. Task 3's seventeen: fourteen red, and the three
that passed immediately are the ones asserting behavior that must *not* move —
the `--title` override, the `inbox list` label, and the degenerate dated
filenames.

## Test result

`python -m pytest` → **1850 passed**, 0 failed (7m28s, run after the final
commit). No test was edited to accommodate the change. In particular
`test_inbox_show_and_accept_resolve_listed_file_title` (`tests/test_work.py`),
which the plan named as the tripwire, passes unmodified.

`python -m pytest tests/test_work.py -k inbox` → 38 passed (was 21 + 17 new).

The four hand checks the plan reserved for `submit`, run against the installed
console script in a scratch node outside this repo:

1. **The reporter's reproduction.** `→ now at docs/work/backlog/2026-08-20-another-raw-request`
   and `2026-08-20-another-raw-request | backlog | i | - | Another Raw Request`.
   One date, and the title is the entry's H1. This is the bug, fixed.
2. **Delegate and escalate, across two registered nodes.** `tcw work delegate child "Ship the exporter"`
   → accepted in the child as `2026-08-20-ship-the-exporter`, titled
   `Ship the exporter`. `tcw work escalate "Clarify the export format"` from the
   child → same shape in the parent. Both titles round-trip exactly; both slugs
   carry one date.
3. **`tcw work new` on the two crashing inputs.** `"東京"` → `2026-08-20-untitled`,
   `"a"*300` → a 131-character slug, `"京都"` → `2026-08-20-untitled-2`. All exit 0.
4. **The capability descriptions read as a user.** `tcw capabilities show` on
   both — the added sentences read as product statements. One defect found in
   the reading: the inbox sentence ran into the preceding paragraph with no
   blank line, fixed in `077c9ea`.

## What the plan and spec got wrong

- **The baseline test count.** The plan and spec both record **1763 passed** as
  the tree's baseline. The tree was at **1807** when this item started — three
  sibling items landed in between, exactly as the plan's `## Notes` predicted for
  the line numbers. 1807 + 43 new = 1850. Nothing failed; the recorded number was
  simply stale, which is why the plan told the implementer to treat a failure as
  a signal to investigate rather than as proof of causation.
- **The parity test's assertion, as specified, is half wrong.** The plan wrote
  that `_frontmatter` "either returns/raises consistently with" the delimiter
  predicate. The *raise* half holds. The *return* half does not: the body
  `---\n\n# Swallowed\n\n---\n\n# Real\n` is delimited (so `frontmatter_end` is
  non-zero) and `_frontmatter` still returns `None`, because the YAML it
  delimits is a comment. What the two functions share is the **boundary**, not
  the parse result, so the shipped test asserts the boundary predicate plus
  "raises exactly when the block is unterminated". That is the invariant that
  actually prevents drift; the stronger claim would have been a false one.
- **Every `tcw/store/fs.py` line number in the plan and spec is stale**, as the
  plan itself predicted: `slugify` is at `:769` (planned `:640`), `_frontmatter`
  at `:2456` (`:2296`), `_unique_slug` at `:2602` (`:2441`), `inbox_accept` at
  `:3164` (`:2995`). Every symbol resolved; nothing had changed inside them.
- **The plan did not name the `capabilities.yaml` sidecar.** Its Task 4 covers
  the two `description.md` edits, but the work→capability back-pointer the
  `complete` gate reads did not exist on this item. Written as part of Task 4.
  A planning miss, not an implementation surprise — the sidecar belongs to the
  `## Capability changes` planning check.
- **One test detail:** `docs/work/backlog/` holds a `.gitkeep`, so the
  long-title test has to count directories, not entries. Cosmetic, but it is the
  kind of thing the plan's "the created directory name is `len == 131`" phrasing
  hid.
- **`skills/tcw-work/references/commands.md:6` needed no edit**, as the plan
  predicted. Verified and left alone.

## Notes

The plan's ordering claim held exactly: Task 1 fixes a defect reachable without
any of the title work, and going first meant Task 3's slug-safety tests had a
floor to stand on rather than needing their own. Task 2 landing with no caller
meant Task 3 was pure wiring — one line replaced by five, and every test that
could have been hard to debug had already been debugged in isolation.

The `_frontmatter` refactor is the part worth remembering: `body_title` needed
to skip frontmatter, and the tempting version computes the boundary a second
time. Both callers now go through `frontmatter_end`, so a title read out of the
wrong half of a file is not a bug that can appear later.
