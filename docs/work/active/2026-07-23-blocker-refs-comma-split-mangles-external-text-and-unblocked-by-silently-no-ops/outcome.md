# Outcome — Blocker refs fix

Work completed successfully. All three defects fixed at the shared helpers, so
the CLI, the web app, and `create_work`/`update_work` all inherit the fix.

## What changed

### `tcw/store/base.py`

- New `WorkStore._normalize_ref` staticmethod: strips surrounding whitespace and
  one leading `external:` label (case-insensitive). Applied in `_entry_for`
  **before** the slug probe, and in `remove_blocker` before matching.
- `remove_blocker` now raises `ValueError(f"no such blocker on {slug}: {ref}")`
  when nothing matched, using the ref as the user typed it. Docstring records the
  deliberate asymmetry with the still-idempotent `add_blocker`.

Because `tcw/store/fs.py:2217,2324` already route through `_entry_for`,
`create_work`, `update_work`, and the web app's `blockers` field
(`tcw/serve/__init__.py:736`) were fixed with no edit of their own.

### `tcw/work/cli.py`

- `--blocked-by` (on `work new` and `work edit`) and `--unblocked-by` (on
  `work edit`) are `action="append"`; their `_split` calls are gone. `--blocks`
  and `_split` itself are untouched — `--blocks` takes slugs, which cannot
  contain a comma.
- `_edit` applies `--unblocked-by` removals **before** the `--blocked-by` /
  `--blocks` additions. Not in the original plan: with `remove_blocker` now
  failing closed, the old ordering would have left the additions already
  persisted when a removal aborted. Reordering gets the same "validate before you
  mutate" guarantee the `--blocks` pre-check already provides, for one moved
  loop. Covered by `test_bad_unblock_aborts_before_any_blocker_write`.
- No new error handling needed: the blocker loops are already inside `_edit`'s
  `try`, and `_ERRORS` includes `ValueError` (verified before relying on it, as
  the plan required).

### `tests/test_work.py`

Added `test_external_prefix_roundtrips_with_display_form`,
`test_external_blocker_survives_a_comma`, `test_blocker_flags_are_repeatable`,
`test_unblocked_by_unmatched_ref_fails_closed`,
`test_bad_unblock_aborts_before_any_blocker_write`,
`test_new_blocked_by_is_repeatable`.

Two existing tests asserted the old contract and were updated:
`test_add_and_remove_blocker_roundtrip` (absent ref: no-op → raises) and
`test_cli_new_blocked_by` (comma form → repeated flags).

### Documentation

`README.md` (both blocker examples), `docs/changelogs/upcoming.md` (Fixed +
Changed, `fe43e40..HEAD`), `docs/release-notes/upcoming.md` (plain-language
section including the comma-form breaking change), and a new
`skills/tcw-work/SKILL.md` quick-reference row for recording/clearing blockers.
The plan predicted no skill change; the row was added because `CLAUDE.md` requires
the driving skill to track the component's CLI surface, and the new contract
(repeatable, prefix-tolerant, fail-closed) is exactly the kind of thing an agent
would otherwise get wrong.

## Verification

- `python -m pytest -q` → **689 passed** (full suite, after the change).
- Manual end-to-end reproduction of the original bug report in a throwaway node:
  - `--blocked-by "waiting on vendor A, then legal signoff"` → **one** entry in
    `state.yaml` with the comma intact (previously two mangled entries);
  - `tcw work show` prints
    `blocked_by: external: waiting on vendor A, then legal signoff`, and that
    exact string passed to `--unblocked-by` removes it, exit 0, leaving
    `blocked_by: []`;
  - `--unblocked-by nope` → `tcw work edit: no such blocker on <slug>: nope`,
    exit **1** (previously `edited <slug>`, exit 0, no change).

All six spec acceptance criteria met. Criterion 6 (web-app path) is met by
construction — the shared `_entry_for` helper — not by a separate test.

## Deviations from plan

1. The removals-before-additions reorder described above (addition, not a cut).
2. A `skills/tcw-work/SKILL.md` row was added where the plan expected none.

## Follow-up notes

- Existing items may still hold blockers mangled by the old comma-split. Not
  migrated; each is now removable by its stored text, which is what the fix
  enables. No known instance in this repo.
- Local-LLM review (`bllm-review-many`) was attempted on the spec per the user's
  standing rule. The default model set crashed on startup (`ggml_abort` in the
  Metal backend, see `~/llama/logs/reviewer-*.log`); `--models fast` ran. Its one
  actionable point — assert the `ValueError` at the store level, not only through
  the CLI — was applied. Its other findings were dismissed: the claimed
  litmus-test violation (CLI flag parsing has no storage-abstraction bearing), a
  request for tests pinning the old comma behavior (that behavior is the bug), and
  two points already covered by the spec's Risks and Documentation sync sections.
