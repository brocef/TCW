# Outcome

Work completed successfully. Implemented exactly as planned; no direction change.

## What changed

- **`tcw/store/base.py`** — added `WORK_LEVELS = ("low", "medium", "high", "very-high")`
  and two optional `WorkItem` fields, `effort: str = ""` / `complexity: str = ""`.
- **`tcw/store/fs.py`** — `_item_from_dir` reads `state.get(k) or ""` for both
  fields (null-coercing). No store-signature change; `set_field` persists them.
- **`tcw/work/cli.py`** — `--effort`/`--complexity` (`choices=WORK_LEVELS`) on
  `new` and `edit`, applied via `set_field`; `show` prints them after `priority`
  when set. `list` untouched.
- **`tests/test_work.py`** — 5 new tests (persist/read-back, single-field edit,
  show display/omit, invalid-value rejection, missing/null keys → `""`).
- **Docs-sync:** README (new/edit examples + `show` note), `skills/tcw-work/SKILL.md`
  (quick-ref row), `docs/capabilities/work/capabilities.md` (new capability),
  `docs/changelogs/upcoming.md`, `docs/release-notes/upcoming.md`.

## Verification

- `python -m pytest tests/ -q` → **220 passed**.
- Live CLI smoke (throwaway repo): `new --effort high --complexity very-high` →
  `show` displays both; `list` shows no new column; `edit --effort medium` leaves
  complexity intact; `--effort nope` → argparse usage error, exit 2.
- Local LLM review (qwen25-coder + gemma4-26b) on the diff: no correctness bugs,
  no blocking issues. (gemma looped — known local-model failure — but its
  substantive point was captured.)

## Deviations from plan.md

None.

## Commits (on `main`)

- `64d0746` request + spec · `9a2b747` plan · `209eb4c` start transition
- `10fe40f` code + tests · `08fad3b` docs-sync

## Follow-up notes (not yet TCW items)

- **No CLI unset.** Once `effort`/`complexity` is set it can be re-tagged to
  another level but not blanked back to unset (argparse `choices` excludes `""`).
  Deliberate (spec non-goal; mirrors `--priority`), but flagged by review. If
  wanted, the smallest add is a `--clear-effort`/`--clear-complexity` flag, or
  accepting a sentinel like `none`. Awaiting user decision.
- **No filtering/sorting** by these fields (YAGNI). Data is stored plainly, so
  either can be added later with no migration.
- **Version bump** not taken — closeout decision for the user.
