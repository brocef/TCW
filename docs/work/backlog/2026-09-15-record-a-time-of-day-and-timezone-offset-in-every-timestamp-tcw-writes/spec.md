# Spec: Record a time of day and timezone offset in every timestamp TCW writes

## Capability changes

No new capability. Four existing capabilities change wording, recorded under
`changed:` in this item's `capabilities.yaml` when the item is planned for
implementation:

- `work/start-a-work-item` — says the claim records "its UTC start time"
  (`docs/capabilities/work/start-a-work-item/description.md:7`). It becomes the
  local start time with its timezone offset.
- `work/view-the-board` — says active rows show the "UTC start time"
  (`docs/capabilities/work/view-the-board/description.md:14`). Same change.
- `work/record-a-tombstone-for-resolved-work` — says `--resolved <ISO date>` and
  that the date defaults to today
  (`docs/capabilities/work/record-a-tombstone-for-resolved-work/description.md:12-16`).
  It becomes: `--resolved` takes a date or a full timestamp with an offset, and
  the default is the current moment, which reads as "known resolved by then".
- `work/open-a-work-item` — gains one sentence: the item records the moment it
  was created, as local time with an offset; the slug still begins with the date.

Checked against the standing ledger with `tcw capabilities search` for
"timestamp", "date", "created" and a grep of `docs/capabilities` for "date",
"UTC", "timestamp" and "today". No other capability states a date shape. No
taxonomy entry names timestamps.

## Problem

Every moment TCW records is either a bare date, which loses the time of day, or
a UTC time, which reads as the wrong hour to anyone not in UTC. The requester
wants every recorded moment to carry the time of day in the writer's local time,
with the timezone offset (the number of hours the local clock is ahead of or
behind UTC) included, so the exact moment can always be recovered. Example:
`2026-09-15T14:03:22-07:00`.

What TCW writes today, found by searching all of `tcw/` for `date.today`,
`datetime.now`, `isoformat`, `strftime` and `fromtimestamp`:

| Value | Where it is stored | Written by | Today's form |
| --- | --- | --- | --- |
| `created` (item made by `tcw work new`, `tcw serve`, `tracker import`) | `state.yaml` | `tcw/store/fs.py:6212-6213`, `:6226` | date |
| `created` (item made by `inbox accept`) | `state.yaml` | `tcw/store/fs.py:5841`, `:5882` | date |
| `resolved` (default when none is given) | graveyard file | `tcw/store/fs.py:4595` | date |
| `resolved` (given to `tombstone add --resolved`) | graveyard file | `tcw/store/fs.py:4651` | date, normalized |
| `started` (filesystem store claim) | `state.yaml` | `tcw/store/fs.py:3707` | UTC, microseconds, `Z` |
| `started` (base store, used by non-filesystem stores) | the store | `tcw/store/base.py:3306`, `:3325` | UTC, microseconds, `Z` |
| `bound` (tracker link and import) | `tracker.yaml` | `tcw/work/cli.py:2003`, `:2060`, `:2153-2155`; `tcw/tracker/intake.py:175` | date |
| `unlinked-on` (tracker unlink) | `tracker.yaml` | `tcw/work/cli.py:2197`; `tcw/tracker/intake.py:219` | date |
| `at` on a sync record and on an owed comment record | `tracker.yaml` | `tcw/tracker/sync.py:127-128`, `:208`, `:317`; `tcw/tracker/progress.py:149` | UTC, seconds, `Z` |
| "Imported on …" sentence | `intake.md` of an imported item | `tcw/work/cli.py:1948` | date |

Not recorded moments, and so not in the table: the date prefix of a slug
(`_unique_slug`, `tcw/store/fs.py:4147-4154`) and of an inbox file written by
`delegate` or `escalate` (`tcw/work/recursion.py:286`), which are names; and
`modified` (`tcw/store/fs.py:105`, and `FsWorkStore._modified_timestamp`), which
is worked out from file modification times each time an item is read and is
never stored.

Who reads these values today:

- Nothing compares, sorts or does arithmetic on any of them. No `timedelta`
  exists in `tcw/`. They are passed through as text.
- `FsWorkStore._item_from_dir` copies `created` and `started` out of
  `state.yaml` as loaded (`tcw/store/fs.py:4255`, `:4271`). A value a person
  typed without quotes (`created: 2026-09-15`) is loaded by YAML as a Python
  `date` or `datetime` object rather than text, and is carried as that object.
- The graveyard reader turns `resolved` into text with `str()`
  (`tcw/store/fs.py:5039`).
- The binding reader turns a `bound` loaded as a `date`/`datetime` into text
  (`tcw/store/base.py:402-404`).
- `tcw work show --json` declares `created` and `started` as strings
  (`tcw/work/projection.py:174`, `:192`) and turns a `date`/`datetime` object
  into text with `str()` (`tcw/work/projection.py:85-87`). The tracker block's
  `bound` and `at` are strings too (`:115`, `:127`, `:145`).
- `tcw work show` prints `started` (`tcw/work/cli.py:196-197`); the board prints
  it on active rows (`:543`); `show` of a removed item prints `resolved`
  (`:688-689`); `tombstone add` prints it (`:2320`). All print the stored text.
- `tcw serve` accepts an optional `created` in the body of a create request
  (`tcw/serve/__init__.py:849`) and passes it to `create_work`, which parses it
  with `date.fromisoformat` — so a full timestamp is refused today. The web
  client never sends one (no `created` in `web/client/src/model/api.ts`).
- `tcw validate` does not look at any of these values.

Writing these values as local time with an offset: `yaml.safe_dump` quotes a
timestamp string, as it already quotes a date string, so a written value loads
back as text. Checked: `yaml.safe_dump({"a": "2026-09-15T14:03:22-07:00"})`
gives `a: '2026-09-15T14:03:22-07:00'`.

## Goals

1. Every value in the table above is written as local time with its offset, to
   the second: `datetime.now().astimezone().isoformat(timespec="seconds")`,
   e.g. `2026-09-15T14:03:22-07:00`. A machine whose local zone is UTC writes
   `+00:00`, not `Z`, so every newly written value has one shape.
2. One function reads any stored moment into a timezone-aware `datetime`. This
   is the **shared contract** with
   `2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title`:

   **`read_timestamp(value) -> datetime`, in the new module `tcw/timestamps.py`.**

   - Text of exactly the form `YYYY-MM-DD` → 12:00 (noon) UTC on that date.
   - A Python `date` that is not a `datetime` → 12:00 UTC on that date.
   - Text in full ISO 8601 form with a time and an offset or `Z`
     (anything `datetime.fromisoformat` reads that carries an offset) → that
     moment.
   - A Python `datetime` that carries an offset → itself.
   - Anything else raises `ValueError`: a time with no offset (the moment is
     unknown), non-date text, an empty string, `None`, a `bool`, a number. A
     caller that must not fail — a sort — catches it and decides.

   The same module holds the one writer, **`timestamp_now() -> str`**, which every
   row in the table calls instead of its own `date.today()` or `datetime.now()`.
3. Values already on disk are never rewritten. A date-only `created` or
   `resolved`, and a UTC `Z` `started` or `at`, keep reading as the moments
   described in Goal 2.
4. A slug and an inbox file name still begin with a date only, and for a newly
   created item that date is the local date of the same moment written to
   `created` — computed once, so an item created a second before midnight cannot
   get a slug dated one day and a `created` dated the next.
5. A moment a caller supplies — `created` to `create_work` (including through
   `tcw serve`) and `--resolved` to `tombstone add` — may be a date or a full
   timestamp with an offset. It is checked with `read_timestamp` and stored as
   follows: a date stays a date (inventing a time of day would record a
   precision nobody had; it reads as noon UTC); a full timestamp is stored in the
   Goal 1 form, keeping the offset it was given. A timestamp with no offset is
   refused with a message that says an offset is required. The slug of an item
   given a full `created` begins with the date as written in that value.

## Non-goals

- **Slug and inbox file-name dates stay date-only.** They are identifiers.
  Changing their shape would change every future item's identifier and every
  reference pattern that expects `YYYY-MM-DD-` (`_DATE_PREFIX`,
  `tcw/store/fs.py:1168`).
- **`modified` is unchanged.** It is not stored; it is worked out on each read,
  and the web app already formats it for the viewer (`ModifiedAt`,
  `web/client/src/ui/modified-at.tsx`).
- **No new displays.** `tcw work show` and the board do not start printing
  `created`. Sorting the board by it is the sibling item's job. Existing displays
  print the stored text as they do now.
- **No migration**, and `tcw validate` gains no timestamp check.
- **No change to how `tcw work show --json` renders a hand-typed unquoted YAML
  timestamp** (`str()` gives a space instead of `T`). That is existing behavior
  for a hand edit, not something TCW writes.
- **No new recorded moments.** Nothing that records no time today starts
  recording one (for example, inbox entries get no `created`).
- Repository tooling outside `tcw/` (`scripts/`, `hooks/`) — searched, and none
  of it writes these values.

## Design

`tcw/timestamps.py`, a new module with no imports from the rest of `tcw`, so the
store, the command line, `tcw serve` and the tracker package can all use it
without import cycles. It holds `timestamp_now()` and `read_timestamp(value)` as
described in Goals 1 and 2, and nothing else.

The litmus test — "could a non-filesystem store implement this operation?" —
passes: a timestamp's text form and how it is read are properties of the model,
not of the filesystem. A tracker-backed store records the same text in a field.
That is why the writer lives outside `fs.py`, and why the base store's `start`
(`tcw/store/base.py:3306`, `:3325`) changes alongside the filesystem store's.

Each writer in the Problem table calls `timestamp_now()`. The two places that
build a slug from the creation moment call `timestamp_now()` once and take the
slug's date prefix from its first ten characters (Goal 4); the inbox file name
written by `delegate` and `escalate` (`tcw/work/recursion.py:286`) does the same. The `today` variables in the
tracker commands (`tcw/work/cli.py:2003`, `:2153`, `:2197`) become the full
timestamp; the "Imported on …" sentence uses it as well.

Caller-supplied values (Goal 5) pass through `read_timestamp` for checking. The
stored text is the input's own date (`YYYY-MM-DD`) when the input was a date,
or `isoformat(timespec="seconds")` of the parsed moment when it had a time. This
replaces the `date.fromisoformat` calls at `tcw/store/fs.py:4651` and `:6212`.
The `--resolved` help text (`tcw/work/cli.py:2773`) changes to say a date or a
timestamp with an offset.

`WorkItem.created`, `WorkItem.started` and `Tombstone.resolved` keep type `str`.
Their comments in `tcw/store/base.py` name the form and point at
`read_timestamp` as the way to compare them.

**Harness compatibility:** the whole change is in the `tcw` command, so Claude
and Codex users get identical behavior. No skill or hook carries any part of it.

## Acceptance criteria

1. `tcw/timestamps.py` exists and defines `timestamp_now` and `read_timestamp`.
2. `read_timestamp("2026-09-15")` and `read_timestamp(date(2026, 9, 15))` both
   equal `datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)`.
3. `read_timestamp("2026-09-15T14:03:22-07:00")` equals
   `datetime(2026, 9, 15, 21, 3, 22, tzinfo=timezone.utc)`, and
   `read_timestamp("2026-09-15T21:03:22.123456Z")` reads as the same second plus
   its microseconds.
4. `read_timestamp` raises `ValueError` for each of `"2026-09-15T14:03:22"`,
   `"yesterday"`, `""`, `None`, `True` and `20260915`.
5. `timestamp_now()` matches
   `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$` — with `TZ=UTC` set in
   the environment it ends `+00:00`, and with `TZ=America/Los_Angeles` it ends
   `-07:00` or `-08:00`.
6. After `tcw work new "X"`, the item's `state.yaml` has a `created` matching the
   pattern in criterion 5, and the slug's first ten characters equal the first
   ten characters of `created`. The same holds for `tcw work inbox accept`.
7. After `tcw work start <slug>`, `state.yaml` has a `started` matching the
   pattern in criterion 5 — no `Z`, no fractional seconds. The same holds for the
   base store's `start` and `start --take-over`.
8. After `tcw work complete` (which writes a graveyard record,
   `tcw/store/fs.py:6023`) and after `tcw work tombstone add <slug>` with no `--resolved`, the recorded
   `resolved` matches the pattern in criterion 5.
9. `tcw work tombstone add <slug> --resolved 2025-06-01` records `2025-06-01`;
   `--resolved 2025-06-01T09:30:00+02:00` records `2025-06-01T09:30:00+02:00`;
   `--resolved 2025-06-01T09:30:00` is refused with a message naming the missing
   offset, and records nothing.
10. `create_work(title, created="2026-01-01")` stores `created: '2026-01-01'` with
    a slug starting `2026-01-01-`; `created="2026-01-01T23:30:00-05:00"` stores
    that value with a slug starting `2026-01-01-`; `created="2026-01-01T23:30:00"`
    raises `ValueError` and creates nothing.
11. After `tcw work tracker link` and `tcw work tracker import`, `tracker.yaml`'s
    `bound` matches the pattern in criterion 5; after `tracker unlink`, the new
    `unlinked` entry's `unlinked-on` does too; the imported item's `intake.md`
    says "Imported on" followed by a value matching that pattern; and a sync or
    comment record's `at` matches it.
12. An item whose `state.yaml` holds `created: '2026-01-01'` and
    `started: '2026-01-02T03:04:05.678901Z'` loads, shows, and projects to JSON
    exactly as before this change, and neither file is rewritten by reading it.
13. The four capability descriptions named under **Capability changes** state the
    new behavior, and `tcw capabilities check` passes.
14. A search of `tcw/` for `date.today(` and `datetime.now(` finds only
    `tcw/timestamps.py` — slug and inbox file-name dates are taken from the first
    ten characters of a `timestamp_now()` value, not from a separate clock read.
15. The full test suite passes when run the way CI runs it (bare `pytest`).

## Risks

- **Tests that pin today's shapes will fail and must be updated, not deleted.**
  Found by searching `tests/`: `tests/test_external_work_store.py:128`, `:548`
  (`started.endswith("Z")`); `tests/test_non_git_writes.py:478` (a pattern that
  blanks only `…Z` timestamps in compared output); `tests/test_tombstone.py:131`,
  `:267-268` and `tests/test_work.py:2556-2560`, `:2567`, `:2619` (a stored value
  equal to `date.today().isoformat()`). The many tests that build a slug from
  `date.today()` (`tests/test_work.py`, `tests/test_recursion.py:535`,
  `tests/test_store_publication.py:171`) keep passing, since slugs stay
  date-only — except in the second around local midnight, which is already true
  today.
- **A test that compares a stored moment to "now" is sensitive to the clock
  ticking over a second.** Tests should match the shape, or freeze the writer,
  rather than compare to a second call of `timestamp_now()`.
- **Mixed shapes on disk are permanent.** Old date-only and `Z` values stay.
  Anything that ever compares two of them as text will get the wrong order;
  `read_timestamp` is the only correct way to compare, which is why the field
  comments point at it.
- **Two machines in different zones write different offsets for the same kind of
  field.** That is what the requester asked for — the offset preserves the exact
  moment — but a reader skimming a file sees mixed offsets.
- **The sibling sort item may land first.** If it does, it will not find
  `tcw/timestamps.py`. It must then create `read_timestamp` in that module with
  exactly the Goal 2 behavior, and this item reuses it instead of writing it
  again.

## Notes

- The requester chose "every date TCW writes" over "created only" or "created,
  resolved, started". That choice is why the tracker binding dates and the UTC
  `Z` writers are in scope. It is also why the "Imported on …" sentence changes:
  it is a record of when the import happened, written by TCW.
- Seconds, not microseconds: the requester asked for "the time", the existing
  tracker `at` values are already to the second, and a claim's microseconds carry
  nothing a reader uses.
- A timestamp with no offset is refused rather than assumed to be local or UTC,
  because the request's stated purpose is knowing the exact moment, and guessing
  an offset would record a moment nobody knew.

- Planning asked whether `tcw work show` (and perhaps the board) should start
  printing `created` now that it carries a time. The requester answered no: the
  existing columns stay as they are, which is the "No new displays" non-goal.
