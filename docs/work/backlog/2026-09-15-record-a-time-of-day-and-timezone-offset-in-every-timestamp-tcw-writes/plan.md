# Plan: Record a time of day and timezone offset in every timestamp TCW writes

Implements `spec.md`. "AC n" below means acceptance criterion n in the spec.

Tests run the way CI runs them: bare `pytest` from the repository root
(`.github/workflows/test.yml:51`). Every task ends with the whole suite green, so
each task is one commit.

## Dependencies

No blocker is recorded. The sibling item
`2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title` reads
`created` through `read_timestamp` but does not need this item to land first.
Whichever item is implemented first creates `tcw/timestamps.py`; if the sort item
got there first, Task 2 here reduces to checking that its `read_timestamp` meets
AC 2-4 and adding `timestamp_now` beside it.

## How callers use the new module

Every caller writes `from tcw import timestamps` and calls
`timestamps.timestamp_now()`, never `from tcw.timestamps import timestamp_now`.
That way a test can freeze the clock in one place —
`monkeypatch.setattr(timestamps, "timestamp_now", lambda: "2026-01-01T23:59:59-05:00")`
— and every writer sees it. Tasks 3-6 rely on this to test the midnight case and
exact stored values without racing the clock.

## Tasks

### Task 1 — Record the capability changes

- **Creates** `docs/work/backlog/2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes/capabilities.yaml`
  (write it with the path `tcw work path <slug>` prints once the item is active):

  ```yaml
  changed:
      - work/start-a-work-item
      - work/view-the-board
      - work/record-a-tombstone-for-resolved-work
      - work/open-a-work-item
  ```

- **Proves it:** `tcw capabilities show <path>` resolves each of the four paths;
  `tcw capabilities check` exits 0.

### Task 2 — Add `tcw/timestamps.py` (AC 1-5)

- **Creates** `tcw/timestamps.py`, importing only the standard library:
  - `timestamp_now() -> str` returns
    `datetime.now().astimezone().isoformat(timespec="seconds")`.
  - `read_timestamp(value) -> datetime`:
    - `bool` → `ValueError` (checked first, because `bool` is a subclass of `int`).
    - `datetime` → itself if `tzinfo` is set and `utcoffset()` is not `None`,
      otherwise `ValueError("… has a time but no timezone offset")`.
    - `date` → `datetime(y, m, d, 12, tzinfo=timezone.utc)`.
    - `str` matching `^\d{4}-\d{2}-\d{2}$` → `date.fromisoformat`, then as a
      `date`. (The pattern check matters: on Python 3.11+ `date.fromisoformat`
      also accepts `20260915`, which the spec refuses.)
    - any other `str` → `datetime.fromisoformat(value)`, then the `datetime`
      rule above; a parse failure re-raises as `ValueError` naming the value.
    - anything else (including `None`, `int`) → `ValueError`.
  - `stored_form(value: str) -> str` — the Goal 5 rule for caller-supplied
    values, so Tasks 3 and 4 share it rather than writing it twice: calls
    `read_timestamp` to check; returns the input unchanged if it matched
    `^\d{4}-\d{2}-\d{2}$`, otherwise
    `datetime.fromisoformat(value).isoformat(timespec="seconds")`, which keeps
    the offset it was given.
- **Creates** `tests/test_timestamps.py`, one test per acceptance criterion:
  - AC 2: both date forms equal `datetime(2026, 9, 15, 12, tzinfo=timezone.utc)`.
  - AC 3: the `-07:00` value equals `21:03:22` UTC; the `Z` value with
    microseconds equals `datetime(2026, 9, 15, 21, 3, 22, 123456, tzinfo=timezone.utc)`.
  - AC 4: parametrized over `"2026-09-15T14:03:22"`, `"yesterday"`, `""`,
    `None`, `True`, `20260915`, and `"20260915"`, each raising `ValueError`.
  - AC 5: `monkeypatch.setenv("TZ", "UTC")` then `time.tzset()` — value matches
    the spec's pattern and ends `+00:00`; the same with `America/Los_Angeles`
    ends `-07:00` or `-08:00`. Restore with `time.tzset()` after
    `monkeypatch.undo()` in a `finally`, so the zone does not leak into later
    tests. Skip on platforms without `time.tzset`.
  - `stored_form`: `"2025-06-01"` → `"2025-06-01"`;
    `"2025-06-01T09:30:00.5+02:00"` → `"2025-06-01T09:30:00+02:00"`;
    `"2025-06-01T09:30:00"` → `ValueError`.
- Nothing calls the module yet, so nothing else changes.
- **Proves it:** `pytest tests/test_timestamps.py`, then the full suite.

### Task 3 — Write `created` as a timestamp; keep slugs date-only (AC 6, 10)

- **Modifies** `tcw/store/fs.py`:
  - `create_work` (`:6209-6226`): replace the `date.fromisoformat(created)` /
    `date.today()` pair with `created_value = timestamps.stored_form(created) if
    created else timestamps.timestamp_now()`; build the slug from
    `created_value[:10]`; store `created_value` under `created`. A
    `ValueError` from `stored_form` propagates before anything is written,
    which is what `create_work`'s docstring already promises ("validated before
    any persistence").
  - `inbox_accept` (`:5825`; the value at `:5841`, stored at `:5882`): `created = timestamps.timestamp_now()`,
    slug from `created[:10]`.
  - The comment above the old parse (`:6209-6211`) is rewritten to say the value
    is checked by `stored_form` and that the slug takes its date.
- **Modifies** `tcw/work/recursion.py:286`: the inbox file-name prefix becomes
  `timestamps.timestamp_now()[:10]`, and the `from datetime import date` at
  `:9` is removed (that line was its only use).
- **Modifies** `tests/test_work.py`: the assertions at `:2556-2560`, `:2567` and
  `:2619` that compare a stored `created` to `date.today().isoformat()` instead
  assert the spec's pattern and that `slug[:10] == created[:10]`.
- **Adds to** `tests/test_work.py` (next to the existing `new` and `inbox accept`
  tests):
  - AC 6: `tcw work new "X"` and `inbox accept` store a `created` matching the
    pattern, with `slug[:10] == created[:10]`.
  - Midnight: with `timestamp_now` frozen at `"2026-01-01T23:59:59-05:00"`, the
    slug starts `2026-01-01-` and `created` is exactly that value.
  - AC 10: `create_work` with `created="2026-01-01"`, with
    `"2026-01-01T23:30:00-05:00"`, and with `"2026-01-01T23:30:00"` (raises
    `ValueError`; the backlog folder holds no new item afterwards).
- **Proves it:** the new tests, then the full suite. The many existing tests
  that build a slug from `date.today()` still pass unchanged.

### Task 4 — Write `resolved` as a timestamp; accept one from `--resolved` (AC 8, 9)

- **Modifies** `tcw/store/fs.py`:
  - `_write_tombstone` (`:4595`): default becomes `timestamps.timestamp_now()`.
  - `record_tombstone` (`:4648-4651`): `resolved = timestamps.stored_form(resolved)`
    replaces the `date.fromisoformat` normalization; the comment above it is
    updated to say the same form rule applies as for `created`. The docstring's
    "defaults to today rather than guessing a real date" becomes "defaults to
    the current moment".
- **Modifies** `tcw/work/cli.py:2773`: `--resolved` help becomes
  `"when it was resolved: a date, or a timestamp with a timezone offset (default: now)"`.
- **Modifies** `tests/test_tombstone.py:131` and `:267-268`: compare to the
  frozen `timestamp_now` value instead of `date.today().isoformat()`.
- **Adds to** `tests/test_tombstone.py`:
  - AC 8: after `tcw work complete` and after `tombstone add` with no
    `--resolved`, the graveyard's `resolved` matches the pattern.
  - AC 9: the three `--resolved` cases; the no-offset one exits non-zero, its
    message contains "offset", and `tombstone(<slug>)` is still `None`.
- **Proves it:** the new tests, then the full suite (`tests/test_tombstone.py:271`,
  `:336` and `:358` keep passing: a date given stays a date).

### Task 5 — Write `started` as local time with an offset (AC 7)

- **Modifies** `tcw/store/fs.py:3707`: `started = timestamps.timestamp_now()`.
- **Modifies** `tcw/store/base.py:3306` and `:3325`: both
  `set_field(slug, "started", timestamps.timestamp_now())`. Remove `timezone`
  from the `datetime` import at `tcw/store/base.py:22` (these were its only
  uses); `date` and `datetime` stay, for `tcw/store/base.py:403`.
- **Modifies** `tests/test_external_work_store.py:128` and `:548`: replace
  `started.endswith("Z")` with a match against the spec's pattern.
- **Modifies** `tests/test_non_git_writes.py:478`: widen the pattern that blanks
  a claim's time to `\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d{2}:\d{2})`. The
  output it compares against was captured before the guard it tests, so check
  that the stored expected text is also blanked by the widened pattern — if the
  expected text holds a literal `Z` time, it is still matched.
- **Adds to** `tests/test_external_work_store.py`: `start` and
  `start --take-over` on the base store both record a `started` matching the
  pattern (AC 7, base-store half). **Adds to** `tests/test_work.py` or the
  existing claim test file: the filesystem store's `start` does the same.
- **Proves it:** the new tests, then the full suite.

### Task 6 — Tracker binding dates, sync and comment records, import sentence (AC 11)

- **Modifies** `tcw/tracker/sync.py:127-128`: `_now()` returns
  `timestamps.timestamp_now()`. Keep the name, since `tcw/tracker/progress.py:32`
  imports it; `progress.py:149` then needs no change.
- **Modifies** `tcw/work/cli.py`:
  - `_tracker_import` (`:1984`, `:2003`), `_tracker_link` (`:2110`, `:2153`),
    `_tracker_unlink` (`:2174`, `:2197`): `today = timestamps.timestamp_now()`
    and remove each function's now-unused `from datetime import date`. Rename
    the local `today` to `now` in all three, and the `today` parameters of
    `_intake_text` (`:1945`) and `_binding_for` (`:1952`) to `now`, so no
    variable named "today" holds a time.
- **Modifies** `tcw/tracker/intake.py:211-219`: rename `unlink_document`'s
  `today` keyword to `now`, and update its caller (`cli.py:2197`).
- **Modifies** the tests that pass `today=` by keyword, renaming it to `now=`:
  `tests/test_tracker_binding.py:219`, `:246`, `:255`, `:258`;
  `tests/test_tracker_comment.py:138`; `tests/test_tracker_sync.py:79`;
  `tests/test_tracker_surface.py:168`, `:188`, `:337`, `:350`. Re-run
  `grep -rn "today=" tests/` afterwards and expect no tracker hits.
- **Adds to** `tests/test_tracker_link.py` and `tests/test_tracker_import.py`:
  with `timestamp_now` frozen, `bound` after link and import, `unlinked-on`
  after unlink, and the imported item's `intake.md` "Imported on <value>"
  sentence all equal the frozen value. **Adds to** `tests/test_tracker_sync.py`
  and `tests/test_tracker_comment.py`: a written `at` equals the frozen value.
- Existing fixtures that hold `"bound": "2026-09-14"` or `"at": "…Z"` stay as
  they are — they are exactly the old on-disk values AC 12 says must keep
  working.
- **Proves it:** the new tests, then the full suite.

### Task 7 — Field comments, old-value reading, and the clock-read sweep (AC 12, 14)

- **Modifies** `tcw/store/base.py`: the `WorkItem.created` and `WorkItem.started`
  lines (`:2452` area) and the `Tombstone` class docstring (`:2476` area) gain a
  comment naming the stored form — local time with offset, or a bare date or a
  UTC `Z` time written before this change — and saying to compare them only
  through `tcw.timestamps.read_timestamp`.
- **Adds** `tests/test_timestamps.py::test_old_values_still_load` (AC 12): write
  an item folder by hand with `created: '2026-01-01'` and
  `started: '2026-01-02T03:04:05.678901Z'`; assert `get`, `tcw work show`, and
  `tcw work show --json` report those exact strings, and that `state.yaml`'s
  bytes are unchanged after the reads. Also assert `read_timestamp` reads both.
- **Adds** `tests/test_timestamps.py::test_only_one_clock_read` (AC 14): read
  every `tcw/**/*.py` file and assert `date.today(` and `datetime.now(` appear
  only in `tcw/timestamps.py`. This keeps a later change from adding a writer
  that bypasses the module.
- **Proves it:** the two tests, then the full suite.

### Task 8 — Capability descriptions (AC 13)

- **Modifies**:
  - `docs/capabilities/work/start-a-work-item/description.md:7` — "its UTC start
    time" → "its start time, in my local time with its timezone offset".
  - `docs/capabilities/work/view-the-board/description.md:14` — "UTC start time"
    → "start time (local time with its timezone offset)".
  - `docs/capabilities/work/record-a-tombstone-for-resolved-work/description.md:12-16`
    — `--resolved <ISO date>` → `--resolved` with a date or a timestamp that
    includes a timezone offset; "The date defaults to today" → "It defaults to
    the current moment"; add that a timestamp without an offset is refused.
  - `docs/capabilities/work/open-a-work-item/description.md` — one sentence: the
    item records the moment it was created, in local time with its timezone
    offset, and the slug still begins with that moment's date.
- **Proves it:** `tcw capabilities check` exits 0.

### Task 9 — Documentation Sync (one pass over the finished diff)

Every entry in `tcw work docs`, evaluated:

- `docs/changelogs/upcoming.md` **[Any-Code-Change]** — fires. Under
  **Changed**: every timestamp TCW writes (`created`, `started`, `resolved`,
  tracker `bound`, `unlinked-on`, sync and comment `at`, the import sentence) is
  now local time with offset to the second; slugs and inbox file names stay
  date-only; old values are not rewritten and read as noon UTC (date-only) or as
  written. Under **Added**: `tcw.timestamps` with `timestamp_now`,
  `read_timestamp`, `stored_form`. Under **Changed**: `tombstone add --resolved`
  and `create_work(created=…)` accept a timestamp with an offset and refuse one
  without.
- `docs/release-notes/upcoming.md` **[Public-API]** — fires. Plain language: TCW
  now records the time of day, not only the date, in your local time with the
  timezone offset; start times are shown in local time rather than UTC; older
  records keep working unchanged; `tombstone add --resolved` accepts a date or a
  time with an offset.
- `README.md` **[Public-API]** — fires, expected no change: a search of
  `README.md` for "UTC", "created:", "started:", "--resolved" and "timestamp"
  finds nothing that describes a date's shape. Re-run that search on the
  finished diff and update only if it now finds something.
- `docs/guide/jira.md` **[Tracker-Change]** — fires (link, import and unlink
  write a different `bound`/`unlinked-on`), expected no change: the guide does
  not mention either field's form. Re-check on the finished diff.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component]** — fires for
  the `work` skill. Update `skills/work/references/commands.md:19`:
  `[--resolved <ISO>]` → `[--resolved <date or timestamp with offset>]`.
  `skills/work/references/procedures/search.md:66` (`started: <timestamp>`)
  stays correct. No other skill names a date form (searched `skills/`).
- `skills/configure/references/<document>.md` **[Configuration-Key-Change]**
  — does not fire: no configuration key changes.
- Not an entry, but found by the same search: `docs/guide/work.md:90` shows
  `--resolved 2026-09-01`, which stays valid. No change.

## Verification

What the suite cannot check, to do by hand before `outcome.md`:

1. In a scratch repository (`tcw init` in a temporary directory), run
   `TZ=America/Los_Angeles tcw work new "LA item"` and
   `TZ=Asia/Tokyo tcw work new "Tokyo item"`; open both `state.yaml` files and
   confirm `created` carries `-07:00`/`-08:00` and `+09:00` respectively, and
   that each slug's date is the local date in that zone.
2. `tcw work start` one of them; confirm `tcw work list` and `tcw work show`
   print `started` with an offset and no `Z`.
3. Copy a real completed item's `state.yaml` from this repository's history
   (any item with `created: '2026-0…'`) into the scratch store and confirm
   `tcw work show` and `tcw work show --json` still read it.
4. `tcw serve` against the scratch store: create an item from the web app and
   confirm it is created and its `created` has the new form; the web client sends
   no `created`, so this proves the default path through the server.
5. Tracker writes (Task 6) are covered by the fake tracker in the suite; no
   live Jira check is planned.

## Notes

- `stored_form` is a third public function beyond the spec's two. It exists
  because the Goal 5 rule is applied in two places (`create_work` and
  `record_tombstone`), and the spec's design already routes both through
  `read_timestamp`; putting the rule next to it keeps the two from drifting.
- Task 1's `capabilities.yaml` is written at implementation time rather than
  committed with this plan, so the plan commit touches only `plan.md`.
- The `today` → `now` renames in Task 6 are not cosmetic: a variable named
  "today" holding a full timestamp would mislead the next reader.
