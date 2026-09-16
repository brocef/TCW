# Plan: Order and limit the output of the commands that list entities

Implements `spec.md`. Each task ends with the full suite green, run the way CI
runs it (bare `pytest` from the checkout root, not `python -m pytest`), and is
committed on its own.

**Shape.** Tasks 1–3 are the ordering half, unchanged from the plan written
before row limiting was folded in. Tasks 4–9 are the limiting half: the shared
module first, with no callers, so the suite stays green while it is written;
then one command group per task. Task 10 records the capabilities.

**No blocker on the timestamps item.** Every stored `created` today is a date
alone, which the shared contract already covers, so this item can be built and
shipped first. The one piece the two items share is the timestamp-reading
function, and Task 1 decides who writes it at the moment implementation starts.

**Re-read the sibling inbox item before Task 6.**
`2026-09-15-show-the-tracker-s-untriaged-tickets-on-tcw-work-inbox-list` gives
`tcw work inbox list` its own two sections. If it has landed by then, Task 6
limits *its* two sections rather than adding a single `# inbox` one. See
`spec.md` § Risks.

If implementing in a `--worktree` branch, follow CLAUDE.md § "Working in a
`--worktree` branch" before running `pytest` or `tcw`: the editable install
otherwise runs the primary checkout's code, not the worktree's.

## Task 1 — Settle the shared timestamp-reading function

The spec's shared contract: one function turns a stored timestamp (a string, a
`datetime.date` or a `datetime.datetime`; a date alone meaning 12:00 UTC; a full
ISO 8601 timestamp with an offset or `Z`) into a timezone-aware `datetime`. The
timestamps item owns it, and its plan (committed `a991ee36`) names it exactly:
**`read_timestamp(value) -> datetime` in the new module `tcw/timestamps.py`**,
which raises `ValueError` for anything it cannot read (a time with no offset,
non-date text, `""`, `None`, a `bool`, a number).

1. Check whether `tcw/timestamps.py` exists with `read_timestamp` in it. The
   timestamps item may already have landed; `tcw work show
   2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`
   says where it stands. If its plan has been revised since `a991ee36`, follow
   the revised name and behavior instead of the ones above.
2. Then exactly one of:
   - **It exists.** Use it; change nothing in this task. Commit nothing.
   - **It does not exist yet.** Create `tcw/timestamps.py` holding only
     `read_timestamp`, built exactly as the timestamps plan's Task 2 describes
     it, with that plan's `read_timestamp` tests (its AC 2-4) in
     `tests/test_timestamps.py`. Do not add `timestamp_now` or `stored_form`;
     they belong to the timestamps item. Say so in this item's `outcome.md`, so
     the timestamps item's Task 2 reduces to checking the function and adding
     the rest beside it.

**Files:** `tcw/timestamps.py`, `tests/test_timestamps.py` (only if created
here). **Proves it:** those tests.

## Task 2 — Ordering in the model: `WORK_SORT_KEYS`, `order_by`, `board(sort=…)`

In `tcw/store/base.py`:

1. Beside `WORK_LEVELS` (`:861`) add
   `WORK_SORT_KEYS = ("created", "priority", "effort", "title")`,
   `WORK_SORT_ORDERS = ("asc", "desc")`, and
   `WORK_SORT_DEFAULT_ORDER = {"created": "desc", "priority": "desc",
   "effort": "asc", "title": "asc"}`.
2. Beside `priority_order` (`:2696`) add
   `order_by(items: list[WorkItem], key: str, order: str | None = None) -> list[WorkItem]`.
   It reads only `WorkItem` fields. Behavior, exactly:
   - A value per item, or "unset":
     - `created`: `read_timestamp(created)`; a raised `ValueError` means
       unset.
     - `priority`: the value if it is an `int` and not a `bool`; else unset.
     - `effort`: `WORK_LEVELS.index(effort)` if it is in `WORK_LEVELS`; else
       unset.
     - `title`: `str(title).casefold()`; never unset.
   - The direction is `order`, or `WORK_SORT_DEFAULT_ORDER[key]` when `order`
     is `None`. Ascending means smallest value first: oldest, lowest priority,
     least effort, A to Z.
   - Ties by slug A to Z in either direction. Do it with two stable sorts:
     sort the items that have a value by slug A to Z, then sort that list by
     value with `reverse=(direction == "desc")`. Python's sort keeps equal
     values in their existing order even with `reverse=True`, so ties keep the
     slug order from the first pass.
   - Unset items follow, sorted by slug A to Z, whatever the direction.
   - An unknown `key` raises `ValueError` naming `WORK_SORT_KEYS`; an unknown
     `order` raises `ValueError` naming `WORK_SORT_ORDERS`.
3. Change `WorkStore.board` (`:3326`) to
   `board(self, status=None, sort=None, order=None)`: with `sort is None`,
   return `topo_order(priority_order(self.query(status)))` exactly as today
   (and ignore `order`); otherwise return `order_by(self.query(status), sort,
   order)`. Extend its docstring to say a store backed by a tracker may
   override it to have the tracker do the ordering.

Tests, new section `# ── order_by / board(sort=) ──` in `tests/test_work.py`,
building items with `st.create(..., created=…)` and adjusting fields with
`st.set_field(slug, key, value)`:

- **AC1** created: `2026-09-15` above `2026-09-09` with no order and with
  `"desc"`; below it with `"asc"`.
- **AC2** created mixed forms: date alone `'2026-09-15'` vs
  `'2026-09-15T10:00:00-07:00'` (the second first); vs
  `'2026-09-15T13:00:00+02:00'` (the first first).
- **AC3** `set_field(slug, "created", datetime.date(2026, 9, 15))` sorts with
  the quoted equivalent and does not raise.
- **AC4** `created` set to `'not-a-date'`, and another set to `''` (what the
  loader gives for a missing key, `tcw/store/fs.py:4255`), both last under
  `"asc"` and `"desc"`.
- **AC5** priority 50, 40, 10, then unset; `"asc"` gives 10, 40, 50, unset
  last.
- **AC6** effort low, medium, high, very-high, unset; `"desc"` gives very-high
  first, unset last; `effort: huge` (via `set_field`) is with the unset ones.
- **AC7** titles `apple`, `Banana`, `cherry`; `"desc"` gives `cherry`,
  `Banana`, `apple`.
- **AC8** two items with equal priority: slug A to Z under both `"asc"` and
  `"desc"`.
- **AC9 (model half)** B blocked by A, B higher priority: `board()` gives A
  first; `board(sort="priority")` gives B first.
- **AC14 (model half)** `board(status)` equals
  `topo_order(priority_order(query(status)))` for a store with blockers and
  mixed priorities; `order_by(items, "size")` and
  `order_by(items, "title", "up")` raise `ValueError`.

**Files:** `tcw/store/base.py`, `tests/test_work.py`. **Proves it:** the tests
above, and the existing `test_topo_order_*`, `test_priority_order_*` and
`test_cli_new_and_edit_priority_reorders_list` passing unedited.

## Task 3 — The CLI: `--sort` and `--order` on `tcw work list`

In `tcw/work/cli.py`:

1. Parser (`:3074-3082`): add
   `--sort` with `choices=WORK_SORT_KEYS` (import it from `tcw.store.base`),
   help `"order the board by this key instead of priority and blockers
   (unset values last)"`; and `--order` with `choices=WORK_SORT_ORDERS`, help
   `"asc or desc (default: desc for created and priority, asc for effort and
   title)"`.
2. `_list` (`:645`): if `args.order` and not `args.sort`, print
   `tcw work list: --order needs --sort` to stderr and return 2. Otherwise
   pass `args.sort` and `args.order` to both renderers.
3. `_visible_board_items` (`:509`): take `sort=None, order=None` and call
   `st.board(status=status, sort=sort, order=order)`. Filters are
   unchanged and keep the order they are given.
4. `_render_board` (`:555`): take and pass through `sort`/`order`. Nothing
   else changes; it already keeps the incoming order inside each sibling group.
5. `_render_descendant_boards` (`:574`): take and pass through
   `sort`/`order`. When `sort` is set, after `entries` is built (`:591-595`)
   and before the ownership pass, put `entries` into one cross-node order:
   `rank = {id(it): n for n, it in enumerate(order_by([e[2] for e in entries],
   sort, order))}` then `entries.sort(key=lambda e: rank[id(e[2])])`. Node
   headers still come from `roots`, so they stay in registered order, and each
   owner's child list is now built in the chosen order across nodes.

Tests in `tests/test_work.py`, beside the existing `list` tests, driving
`main([...])` and reading `capsys`:

- **AC9 (CLI half)** blocked B with higher priority: plain `list` prints A
  first; `list --sort priority` prints B first.
- **AC10** a parent with three children under `--sort title`: children are
  indented directly beneath the parent in title order, and the parent is placed
  by its own title among the top-level items.
- **AC11** root epic with initiative children in two descendant nodes (the
  `subnode` helper, as in
  `test_list_include_descendants_indents_qualified_cross_node_initiative_child`),
  given titles that interleave across nodes: under `-i --sort title` they print
  beneath the epic in title order across both nodes, and `# .` precedes
  `# project-a` precedes `# project-b`.
- **AC12** `--sort priority --status backlog --tag cli` shows only backlog
  items tagged `cli`, in priority order; `--sort title --all` includes a
  completed and a discarded item, in title order.
- **AC13** `main(["work", "list", "--sort", "size"])` raises `SystemExit` with
  code 2 and stderr names `created`, `priority`, `effort`, `title`;
  `["work", "list", "--sort", "title", "--order", "up"]` raises `SystemExit`
  with code 2 and stderr names `asc` and `desc`;
  `main(["work", "list", "--order", "asc"])` returns 2 and stderr contains
  `--order needs --sort`.
- **AC1, AC5 (CLI half)** `list --sort created --order asc` and
  `list --sort priority --order asc` print oldest and lowest first.
- **AC29 (sort half)** `--help` output (via `SystemExit` from
  `main(["work", "list", "--help"])`) contains `--sort`,
  `{created,priority,effort,title}`, `--order`, `{asc,desc}` and the per-key
  defaults.

**Files:** `tcw/work/cli.py`, `tests/test_work.py`. **Proves it:** the tests
above; every existing `list` and `--include-descendants` test in
`tests/test_work.py`, `tests/test_work_tags.py` and
`tests/test_project_overrides.py` passing unedited (**AC14**); and
`tests/test_serve_descendants.py` plus the other `tests/test_serve*.py` passing
unedited, since `tcw serve` still calls `board()` with no sort (**AC28**).

## Task 4 — The shared limiting module: `tcw/listing.py`

New file `tcw/listing.py`. No store access, no I/O, no printing — it takes
already-formatted row strings and returns strings. No caller yet, so the suite
is green at this commit boundary.

```python
DEFAULT_ROW_LIMIT = 20
NO_ROW_LIMIT = -1        # the sentinel; 0 is a real limit meaning "counts only"

def limit_rows(rows: list[str], limit: int) -> tuple[list[str], int]:
    """(kept, withheld). `limit == NO_ROW_LIMIT` (-1) means no limit, and
       withheld is then 0. `limit == 0` keeps nothing and withholds all."""

def section_heading(label: str, emitted: int, total: int) -> str:
    """'# <label> (<total>)' when emitted == total,
       '# <label> (<emitted> of <total>)' otherwise."""

def withheld_note(withheld: int) -> str:
    """'… and <withheld> additional rows' — the caller prints it to stderr.
       Singular 'row' when withheld == 1."""
```

Two argparse helpers live here too, extending the spec's list of contents for
one reason: six parsers across three subcommand groups must spell the option
identically, and a second copy is how they drift. Neither touches a store.

```python
def row_limit(value: str) -> int:
    """argparse `type=`: `NO_ROW_LIMIT` or any int >= 0. Anything below -1, and
       any non-integer, raises `argparse.ArgumentTypeError`."""

def add_limit_argument(parser) -> None:
    """Adds `--limit` with `type=row_limit`, `default=DEFAULT_ROW_LIMIT`, and
       help 'print at most N rows per section (default: 20; -1 for no limit,
       0 for counts only)'."""
```

Tests in a new `tests/test_listing.py`:

- `limit_rows(["a","b","c"], 2) == (["a","b"], 1)`;
  `limit_rows(["a","b"], 5) == (["a","b"], 0)`;
  `limit_rows(["a","b"], NO_ROW_LIMIT) == (["a","b"], 0)`;
  `limit_rows(["a","b"], 0) == ([], 2)` — the one that pins `0` as a real
  limit rather than a second sentinel;
  `limit_rows([], 5) == ([], 0)`.
- `section_heading("board", 5, 5) == "# board (5)"`;
  `section_heading("board", 20, 53) == "# board (20 of 53)"`;
  `section_heading("board", 0, 0) == "# board (0)"`.
- `withheld_note(33)` ends with `and 33 additional rows`;
  `withheld_note(1)` ends with `and 1 additional row`.
- `row_limit("-1") == NO_ROW_LIMIT`, `row_limit("0") == 0`,
  `row_limit("7") == 7`; `row_limit("-2")` and `row_limit("abc")` each raise
  `argparse.ArgumentTypeError`.

**Files:** `tcw/listing.py`, `tests/test_listing.py`. **Proves it:** those
tests.

## Task 5 — `--limit` on `tcw work list`, both views

In `tcw/work/cli.py`. This is the riskiest wiring — two renderers, nested rows,
and per-node sections — and it lands after both the ordering work and the
shared module exist, with its tests written against them.

1. **Turn the row printer into a row builder.** Rename `_render_board_item`
   (`:520`) to `_board_row(st, it, prefix, depth) -> str` and have it `return`
   the line it currently passes to `print`. Its body is otherwise unchanged.
   Both callers below collect instead of printing, which is what makes the
   count exact.
2. `_render_board` (`:555`): the `emit` walk appends
   `_board_row(...)` to a list instead of printing. Then
   `kept, withheld = limit_rows(rows, limit)`; print
   `section_heading("board", len(kept), len(rows))`, then each kept row, then
   `withheld_note(withheld)` to **stderr** when `withheld`.
   The label is `"board"`, deliberately not `"."` — see `spec.md` § The
   section, and AC27.
3. `_render_descendant_boards` (`:574`): `emit` appends to a per-section list.
   Keep the existing shared `emitted` set, so a malformed ownership cycle still
   cannot print an item twice. For each root, build that node's rows through
   the existing two passes (`:637-643`), then limit **that list**, print
   `section_heading(label, len(kept), len(rows))` in place of
   `print(f"# {label}")` at `:635`, print the kept rows, and print the note to
   stderr. The blank line between sections stays where it is.
4. Parser (`:3074-3082`): `add_limit_argument(pl)`.
5. `_list` (`:645`): pass `args.limit` to both renderers.

Tests in `tests/test_work.py`:

- **AC15** 25 backlog items, `--limit 10`: stdout has 10 rows, heading
  `# board (10 of 25)`, stderr contains `and 15 additional rows`.
- **AC16** 5 items, `--limit 10`: 5 rows, heading `# board (5)`, stderr has no
  `additional row`.
- **AC17** `--limit -1`: all 25 rows, heading `# board (25)`, no note.
  `--limit 0`: heading `# board (0 of 25)`, no rows, `and 25 additional rows`
  on stderr.
- **AC18** 25 items, no `--limit`: 20 rows, heading `# board (20 of 25)`.
- **AC19** `-i` with two nodes of 25 items each and `--limit 10`: **each**
  section prints 10 rows under its own `(10 of 25)` heading, and stderr carries
  two notes. This is the per-section proof; a per-command cap fails it.
- **AC20** `--sort title --limit 3` prints the 3 alphabetically first titles.
- **AC25** `main(["work","list","--limit","-2"])` and `--limit abc` each raise
  `SystemExit` with code 2; `--limit -1` and `--limit 0` each return 0.
- **AC26 (work half)** `--limit -1` stdout equals the pre-change output with the
  heading line prepended: assert the rows after the heading, in order, are the
  rows the item slugs produce.
- **AC29 (limit half)** `--help` contains `--limit` and `default: 20`.

**Edits to existing tests, and only these:** `tests/test_work.py:1676`'s
`out.index("# .\n")` becomes `out.index("# . (")`, because the node heading now
carries counts. `tests/test_work.py:1757`
(`test_list_without_flag_has_no_node_headers`) must pass **unedited** (AC27) —
if it fails, the flat label is wrong, not the test. Re-run
`tests/test_work_tags.py:314`, which compares two `work list` outputs to each
other and so survives a heading both gain.

**Files:** `tcw/work/cli.py`, `tests/test_work.py`. **Proves it:** the tests
above, plus the whole of `tests/test_work.py`, `tests/test_work_tags.py`,
`tests/test_project_overrides.py` and `tests/test_serve*.py` green.

## Task 6 — `--limit` on `tcw work inbox list`

**First, re-read the sibling item** (see this plan's opening). What follows is
for the output as it stands today: one section, no headings.

1. `_inbox_list` (`tcw/work/cli.py:451-457`): collect
   `f"{entry.ref} | {entry.kind} | {entry.title}"` into a list, limit it, print
   `section_heading("inbox", len(kept), len(rows))`, the kept rows, and the
   note to stderr.
2. Parser (`tcw/work/cli.py:2844`): the entry is currently built and discarded
   in one expression; bind it (`pil = ing.add_parser("list", …)`) so
   `add_limit_argument(pil)` can be called, then `pil.set_defaults(func=_inbox_list)`.

Tests in `tests/test_work.py`:

- **AC21** 3 entries, `--limit 1`: 1 row, heading `# inbox (1 of 3)`, stderr
  contains `and 2 additional rows`.
- An empty inbox prints `# inbox (0)` and exits 0.
- **AC26 (inbox half)** `--limit -1` prints every entry in today's order, with
  only the heading line added.
- **AC29 (inbox half)** `inbox list --help` contains `--limit` and
  `default: 20`.

**Edit to an existing test:**
`tests/test_work.py:2533` (`test_inbox_list_still_shows_the_filename_label`)
asserts `capsys.readouterr().out` as an exact string; prepend
`"# inbox (1)\n"` to the expected value. Its docstring's claim — that the
entry's title is its addressable identifier — is untouched, so only the
expected string changes.

**Files:** `tcw/work/cli.py`, `tests/test_work.py`. **Proves it:** the tests
above.

## Task 7 — `--limit` on `tcw taxonomy list` and `tcw taxonomy search`

In `tcw/taxonomy/cli.py`:

1. `_list` (`:44-62`): keep the existing sort exactly as it is — its comment
   at `:50-56` explains why the key is the segment tuple, and none of that
   changes. Group the sorted terms into sections by `t.origin` with a `dict`
   keyed on origin, which preserves first-seen order and does not depend on the
   sort keeping origins contiguous. For each origin, build its row strings with
   the existing formatting (`:60`), limit, print the heading with that origin
   as the label, the kept rows, and the note to stderr. Separate sections with
   a blank line, as `_render_descendant_boards` does.
2. `_search` (`:129-135`): one section, label `matches`.
3. Parsers (`:187-189`, `:214-216`): `add_limit_argument` on both.

Tests in `tests/test_taxonomy.py`:

- **AC22** a store with local entries and one inherited alias: one heading per
  origin, each with its own counts; `--limit 1` shortens **each** origin to one
  row, with a note per shortened section.
- **AC24** `search <q> --limit 2`: 2 rows under `# matches (2 of N)`, note on
  stderr.
- **AC26 (taxonomy half)** `list --limit -1` prints every row in today's order.
- **AC29 (taxonomy half)** `taxonomy list --help` and `taxonomy search --help`
  each contain `--limit` and `default: 20`.

**Edits to existing tests:** `tests/test_taxonomy.py:537` and `:554` each
assert `capsys.readouterr().out` as an exact string for `taxonomy list`. Both
gain the `# local (N)` heading line at the top. Their subject — depth-first
pre-order at three levels, and hyphen-vs-slash segment ordering — is unchanged,
so only the expected strings move.

**Files:** `tcw/taxonomy/cli.py`, `tests/test_taxonomy.py`. **Proves it:** the
tests above, plus the rest of `tests/test_taxonomy.py` green.

## Task 8 — `--limit` on `tcw capabilities list` and `tcw capabilities search`

In `tcw/capabilities/cli.py`, mirroring Task 7 so the two groups read alike:

1. `_list` (`:48-55`): group `st.list_all(...)` by `c.origin` with a `dict`,
   same reason as Task 7 — `list_all` returns local entries then each alias's
   (`tcw/store/fs.py:2398-2405`), but the grouping must not depend on that.
   Row formatting (`:54`) is unchanged.
2. `_search` (`:146-152`): one section, label `matches`.
3. Parsers (`:281-286`, `:319-321`): `add_limit_argument` on both.

Tests in `tests/test_capabilities.py`:

- **AC23** `list --limit 2` and `search <q> --limit 2`: 2 rows each under a
  counted heading, note on stderr.
- A store with local and federated capabilities prints one heading per origin.
- **AC26 (capabilities half)** `list --limit -1` prints every row in today's
  order.
- **AC29 (capabilities half)** `capabilities list --help` and
  `capabilities search --help` each contain `--limit` and `default: 20`.

**Files:** `tcw/capabilities/cli.py`, `tests/test_capabilities.py`.
**Proves it:** the tests above, plus the rest of `tests/test_capabilities.py`
green. Sweep `tests/` for any other exact-stdout assertion over
`capabilities list|search` before committing; the enumeration in `spec.md`
§ Risks found none beyond the ones Tasks 5–7 name, but it was made before these
edits landed.

## Task 9 — Update the procedures that read these lists

A default limit changes what an agent following TCW's own instructions sees,
and those instructions conclude from absence. This task is the one the spec
calls the highest-value part of the limiting half.

1. `skills/work-create/references/find-overlap.md` — its Candidates section
   (`:14-17`) names `tcw work list`, `tcw work inbox list` and
   `tcw work list --all`. Add `--limit -1` to each of the three, and one
   sentence saying why: the search concludes `no overlap` from an empty
   result, so it must see the whole board. Its closing `searched:` line
   (`:64`) shows the same three commands and gains the flag too.
2. `skills/work/SKILL.md:47` — `tcw work list --status active`, used to resume
   a session. An active board is short and the default limit is unlikely to
   bite, so leave the command as it is; no edit.
3. Confirm no other skill reads a list command's output for completeness:
   `skills/capabilities/SKILL.md:38` copies one path out of
   `tcw capabilities list`, and `:136` shows `--local-only` as a browsing
   example — both are fine under a limit, since the user sees the count and
   can raise it. Record that judgement in `outcome.md`.

**Files:** `skills/work-create/references/find-overlap.md`. **Proves it
(AC30):** `grep -c -- "--limit -1" skills/work-create/references/find-overlap.md`
returns 4 (three candidate lines plus the `searched:` line), and
`tests/test_skill_lifecycle_parity.py` passes.

## Task 10 — Capability records

1. Create the item's `capabilities.yaml` sidecar (in the folder
   `tcw work path 2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title`
   prints) containing:
   ```yaml
   changed:
       - work/view-the-board
       - work/manage-the-work-inbox
       - taxonomy/browse-the-term-forest
       - taxonomy/search-terms
       - capabilities/browse-capabilities-by-status
       - capabilities/search-capabilities
   ```
2. Edit `docs/capabilities/work/view-the-board/description.md`. After the
   sentence ending "…is how I look at what was closed.", add:
   "With `--sort created|priority|effort|title` I choose the board's order
   instead, and `--order asc|desc` chooses its direction (titles ignore case).
   Left off, the order is newest first, highest priority first, least effort
   first, or titles A to Z. Items with no value for the key stay last either
   way, and items that compare equal are ordered by slug.
   A chosen sort replaces the usual rule that lists a blocker above what it
   blocks; child items still print beneath their parent or epic, in the chosen
   order among themselves."
   Then, at the end of the body, add:
   "The board prints at most 20 rows per section, and `--limit` changes that
   — `--limit -1` prints every row, and `--limit 0` prints the counts alone.
   Each section is headed by its own count,
   showing how many rows it printed of how many there are, and a section that
   was cut short says how many rows it held back."
3. Edit the other five `description.md` files (under `tcw capabilities path`,
   at `work/manage-the-work-inbox/`, `taxonomy/browse-the-term-forest/`,
   `taxonomy/search-terms/`, `capabilities/browse-capabilities-by-status/`,
   `capabilities/search-capabilities/`), adding the same limit sentences,
   reworded to that command's own subject — "entries", "terms", "matches",
   "capabilities" — rather than pasted verbatim.
4. `tcw capabilities check` exits 0.

**Files:** the item's `capabilities.yaml`, and the six `description.md` files
named above. **Proves it (AC31):** `tcw capabilities show <path>` shows the new
sentences for each of the six; `tcw capabilities check` exits 0.

## Documentation Sync

One pass over the finished diff, after Tasks 1–10, committed together before
`outcome.md` is written. Every entry from `tcw work docs`, evaluated:

- `README.md` **[Public-API] — fires** (new public CLI options on six
  commands). Three table rows:
  - `tcw work list` (`:605`) → "shows the board; completed and discarded items
    only when asked; `--sort` orders it by created date, priority, effort or
    title; `--limit` caps the rows per section".
  - `tcw taxonomy list` (`:296`) → append "; `--limit` caps the rows per
    origin".
  - `tcw capabilities list` (`:354`) → append "; `--limit` caps the rows per
    origin".
  Add a sentence where the board is introduced saying that every list command
  prints at most 20 rows per section, heads each section with its count, and
  reports what it withheld.
- `docs/release-notes/upcoming.md` **[Public-API] — fires.** Two short
  plain-language entries: `tcw work list --sort` with the four keys,
  `--order asc|desc` and each key's default, unset values last, children still
  nested; and `--limit` on the six list commands, with the default of 20, the
  counted headings, the withheld-rows line, `--limit -1` for all of it and
  `--limit 0` for the counts alone. Say
  plainly that the lists are now shortened by default, because that is the
  change a reader most needs to notice.
- `docs/changelogs/upcoming.md` **[Any-Code-Change] — fires.** Under
  **Added**: `tcw work list --sort {created,priority,effort,title}` and
  `--order {asc,desc}`; `WORK_SORT_KEYS`, `WORK_SORT_ORDERS`,
  `WORK_SORT_DEFAULT_ORDER`, `order_by`, and `WorkStore.board(sort=, order=)`
  in `tcw/store/base.py`; the new module `tcw/listing.py`
  (`DEFAULT_ROW_LIMIT`, `limit_rows`, `section_heading`, `withheld_note`,
  `row_limit`, `add_limit_argument`); `--limit` on `tcw work list`,
  `tcw work inbox list`, `tcw taxonomy list`, `tcw capabilities list`,
  `tcw taxonomy search`, `tcw capabilities search`; the timestamp-reading
  function if Task 1 added it. Under **Changed**: `-i` orders entries across
  nodes before building child lists when a sort is chosen; every list command
  in scope now prints a counted section heading on stdout and a withheld-rows
  note on stderr; `_render_board_item` became `_board_row` and returns its
  line instead of printing it.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component] — fires for all
  three components**, because all three CLI surfaces changed.
  - `skills/work/SKILL.md` mentions only `tcw work list --status active`
    (`:44`) and needs no change; its option list lives in
    `skills/work/references/commands.md`, whose "the board" row (`:8`) becomes
    `tcw work list [--status <s>] [--tag|--tags <t[,t]>] [--all] [-i] [--sort
    created|priority|effort|title [--order asc|desc]] [--limit <n>]` — hides
    resolved; `-i` adds descendant boards; `--sort` replaces priority-and-blocker
    order; `--limit` caps rows per section, 20 by default, `-1` for all and
    `0` for counts only. Its
    "triage the inbox" row (`:6`) gains `[--limit <n>]` on `inbox list`.
  - `skills/taxonomy/SKILL.md:113` lists `tcw taxonomy list` and
    `tcw taxonomy search` in its browse row — add `[--limit <n>]` to both.
  - `skills/capabilities/SKILL.md:136` shows `tcw capabilities list
    --local-only` — add a row for `--limit`, and check `:38`'s instruction to
    copy a path out of `tcw capabilities list` still reads correctly under a
    default limit (it does; the count tells the user to raise it).
- `docs/guide/jira.md` **[Tracker-Change] — does not fire.** No
  `tcw work tracker` command changes behavior — `tracker list` is explicitly
  carved out in `spec.md` § Non-goals — and no `work.tracker` key changes.
- `skills/configure/references/<document>.md` **[Configuration-Key-Change] —
  does not fire.** No key is added to `tcw-config.yaml`, no component config
  file, no `docs/work/dod.yaml` entry and no `TCW_PROJECT_<ID>` variable: the
  requester chose per-run flags only. This is the one trigger the "flag only"
  decision keeps closed, and it is worth re-checking at implementation that no
  configuration key crept in.
- Not a declared entry, but the full reference README points to it:
  `docs/guide/work.md:241-247` lists every `tcw work list` form. Change the
  comment on `:241` to say the plain board is priority first, then blocker
  order, unless `--sort` is given, and add:
  ```
  tcw work list --sort created --order asc   # oldest first; also priority, effort, title; --order defaults per key
  tcw work list --limit 50                   # more rows per section (default 20; -1 for all, 0 for counts only)
  ```

## Verification

What the suite cannot check, done by hand at the end of implementation:

1. **Unchanged rows on a real board.** Before Task 2, from the checkout
   implementation runs in, save `tcw work list`, `tcw work list --all`,
   `tcw work list -i`, `tcw taxonomy list`, `tcw capabilities list` and
   `tcw work inbox list` to files in the session's scratchpad directory. After
   Task 8, with no store files changed in between (check
   `git status docs/work docs/taxonomy docs/capabilities`), run each again with
   `--limit -1` and `diff` against its saved copy: every diff must be exactly
   one added heading line at the top (and, for `-i` and the two origin-grouped
   lists, one per section) and nothing else.
2. **The default bites, and says so.** Run each of the six commands with no
   flag on this repository, whose board is 53 rows, taxonomy 47 and
   capabilities 97. Each must print 20 rows per section, a heading whose two
   numbers match what is on screen, and a withheld count that adds up.
   Count the rows by hand at least once rather than trusting the heading —
   the heading is the thing under test.
3. **stdout and stderr separate cleanly.** `tcw work list > /tmp/rows.txt`
   leaves the withheld-rows note on the terminal and the heading plus rows in
   the file; `tcw work list 2>/dev/null` prints heading and rows and no note.
4. **Reads well on this repository's board:** `tcw work list --sort created`
   (today's items at the top), `--sort effort` (low effort first, unset at the
   bottom), `--sort title --order desc`, `--sort created --order asc`, and
   `-i --sort priority`. Look for rows out of order or children detached from
   parents, and for a family cut across the limit boundary — that is expected
   (`spec.md` § What a row is, when rows nest), but confirm it reads
   acceptably rather than looking like a bug.
5. **The procedure still works.** Follow
   `skills/work-create/references/find-overlap.md` by hand against this
   repository with the edited commands and confirm the candidate set is the
   whole board, not the first 20.
6. **`--help` reads clearly** for all six commands: the limit wording, the
   default, `-1` for no limit and `0` for counts only; plus `--sort`/`--order`
   on `work list`.
7. **Bare `pytest`** from the checkout root passes, the way CI runs it.

## Notes

- **No open questions.** Every question `initial-request.md` left for `spec` is
  answered, and `spec.md` § Notes maps each one to where. Nothing in this plan
  waits on the requester; it can be executed start to finish without asking
  anything. Two steps are conditional rather than open — Task 1 branches on
  whether `read_timestamp` already exists, and Task 6 on whether the sibling
  inbox item has landed — and each carries the rule that resolves it.
- The requester settled the sort's direction questions by asking for explicit
  ascending and descending sorts; the plan follows the revised spec
  (`--order asc|desc`, per-key defaults when it is left off, ties by slug A to
  Z in either direction).
- The requester chose a per-run flag over a configured default. That is what
  keeps the `Configuration-Key-Change` trigger closed and `tcw validate`
  untouched, and it is also why the default of 20 can only be changed by a
  release. If the default proves wrong in use, that is a new item, not a
  revision of this one.
- **`0` is a real limit, not a second sentinel**, and Task 4's
  `limit_rows(rows, 0) == ([], len(rows))` test is what stops it drifting back
  into one. The natural mistake when writing `limit_rows` is `if limit <= 0:
  return rows, 0`, which silently makes `--limit 0` print everything — the
  opposite of what it says. Write the guard against `NO_ROW_LIMIT` explicitly.
- The requester confirmed the heading prints whatever the limit, knowing that
  it costs the four exact-stdout assertions Tasks 5-7 name. Suppressing it
  under `--limit -1` would have kept those tests untouched; it was rejected
  because the output's shape would then depend on the flag. Do not reintroduce
  it as a convenience while fixing those tests.
- `WorkItem.created` stays annotated `str` although YAML can hand it a
  `datetime.date` or `datetime.datetime`; this item reads it through the shared
  function instead of changing the loader. That is the timestamps item's
  territory.
- The web app keeps its own client-side sort
  (`web/client/src/model/tree.ts:105`) and is not limited; offering these keys
  or a row cap there would be a separate item, not filed here.
- Tasks 7 and 8 are deliberately parallel in structure. If the item is cut down
  at implementation, they are the natural pair to defer together — the work
  axis (Tasks 5, 6, 9) is what the request actually named.
