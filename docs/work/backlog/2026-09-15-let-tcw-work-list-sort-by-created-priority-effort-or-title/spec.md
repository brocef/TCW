# Spec: Order and limit the output of the commands that list entities

This item has two halves, folded together on 2026-09-16 at the requester's
decision (`initial-request.md` § Added 2026-09-16):

- **Ordering** — `tcw work list --sort`, as originally requested.
- **Limiting** — every command that emits a list of entities prints at most a
  set number of rows per section, says in each section heading how many it
  emitted, and closes a shortened section by naming how many rows it withheld.

They meet in one place: a limit keeps the *first* N rows, so the order decides
which rows survive. That is the reason they are one item.

## Capability changes

- **changed:** `work/view-the-board` — gains the sort option (keys,
  `--order asc|desc`, each key's default, where unset values go, that a chosen
  sort replaces the blocker ordering while children stay nested) **and** the row
  limit (`--limit`, its default, the count in each section heading, the
  withheld-rows note).
- **changed:** `work/manage-the-work-inbox` — `tcw work inbox list` gains the
  same `--limit`, heading count and withheld-rows note.
- **changed:** `taxonomy/browse-the-term-forest`, `taxonomy/search-terms`,
  `capabilities/browse-capabilities-by-status`,
  `capabilities/search-capabilities` — the same four, each on its own command.

No new capability: choosing how much of a list you see is part of viewing it,
not a separate thing a user does. No taxonomy change; the Subjects and Features
these capabilities carry are unaffected. Records are written at implementation
(the item's `capabilities.yaml` sidecar) and the descriptions are updated at
completion.

## Problem

### Ordering

`tcw work list` prints the board in one fixed order, and the user cannot change
it. There is no way to see the newest items first, find the cheapest items, or
scan titles alphabetically.

Current behavior, from the code:

- `WorkStore.board` returns `topo_order(priority_order(self.query(status)))`
  (`tcw/store/base.py:3207-3210`). `priority_order` puts items with a priority
  first, highest number first, and keeps unset ones after them in input order
  (`tcw/store/base.py:2577-2583`). `topo_order` then moves an item that blocks
  another above the item it blocks (`tcw/store/base.py:2542-2574`).
- The "input order" both of those keep is the order of item folder paths
  (`FsWorkStore._item_dirs`, `tcw/store/fs.py:3670-3692`), which for top-level
  items is alphabetical by status folder and then by slug. Because a slug begins
  with its creation date, that is roughly creation order.
- The CLI reads that order through `_visible_board_items`
  (`tcw/work/cli.py:506-514`), which filters by `--status`, `--all` and `--tag`
  without reordering.
- `_render_board` (`tcw/work/cli.py:552-568`) groups children under their
  parent while preserving the incoming order within each group, so whatever
  order the item list has is also the order siblings print in.
- `_render_descendant_boards` (`tcw/work/cli.py:571-639`), used by
  `-i`/`--include-descendants`, prints one section per node in registered
  order, and indents items under a visible parent or owning epic, which may be
  in another node. Its per-owner child lists are built by walking all nodes'
  items in node order (`tcw/work/cli.py:588-614`).
- The `list` options are `--status`, `--tag`/`--tags`, `--all` and
  `-i`/`--incl-desc`/`--include-descendants` (`tcw/work/cli.py:3074-3082`).
- The values being sorted: `WorkItem.priority` is `int | None`,
  `WorkItem.effort` is one of `WORK_LEVELS = ("low", "medium", "high",
  "very-high")` or `""` for unset (`tcw/store/base.py:852`, `2455-2456`), and
  `WorkItem.title` is a string. `WorkItem.created` is annotated `str`
  (`tcw/store/base.py:2452`) but is taken straight from the parsed `state.yaml`
  (`tcw/store/fs.py:4255`). YAML reads a quoted `'2026-09-15'` as a string, an
  unquoted `2026-09-15` as a `datetime.date`, and an unquoted
  `2026-09-15T14:03:22-07:00` as a `datetime.datetime`. Every item in this
  repository has a quoted string today, but a hand-edited file can produce the
  other two.

### Limiting

Every list command prints its whole result set, however long, and says nothing
about how long it is. Measured on this repository today: `tcw work list` prints
53 rows, `tcw taxonomy list` 47, and `tcw capabilities list` 97. None of them
fits a terminal screen, and none tells the reader how many rows went past.

Current behavior, from the code — each of these is a bare `for … print(…)` with
no count, no limit and no heading:

- `_inbox_list` (`tcw/work/cli.py:451-457`) — one line per entry, no heading.
- `_render_board` (`tcw/work/cli.py:552-568`) — rows only; the flat board has
  **no** heading at all, and `tests/test_work.py:1757` pins that absence.
- `_render_descendant_boards` (`tcw/work/cli.py:571-639`) — the only command
  that already has sections: `print(f"# {label}")` at `tcw/work/cli.py:635`,
  one per node, blank-line separated, no count.
- `tcw taxonomy list` (`tcw/taxonomy/cli.py:44-62`) — rows only. It is already
  ordered origin-first: the sort key is
  `(t.origin != "local", t.origin, tuple(t.slug.split("/")))`
  (`tcw/taxonomy/cli.py:57`), so a section per origin is a boundary the output
  already has and does not name.
- `tcw capabilities list` (`tcw/capabilities/cli.py:48-55`) — rows only, and
  `list_all` likewise returns local entries then each inherited alias's
  (`tcw/store/fs.py:2398-2405`).
- `tcw taxonomy search` (`tcw/taxonomy/cli.py:129-135`) and
  `tcw capabilities search` (`tcw/capabilities/cli.py:146-152`) — rows only.

**The repository already holds the precedent this half should follow.**
`_tracker_list` (`tcw/work/cli.py:2029-2055`) prints a short list and warns
about it on stderr, with the reasoning in a comment at
`tcw/work/cli.py:2048-2049`: _"Never silently short: a user would conclude they
have nothing else."_ That is exactly the failure a default limit would
otherwise introduce here, and it is not hypothetical: TCW's own procedures tell
an agent to read these lists and draw a conclusion from what is absent.
`skills/work-create/references/find-overlap.md:14-17` builds its candidate set
from `tcw work list`, `tcw work inbox list` and `tcw work list --all`, and
closes with `no overlap` when it sees nothing; `skills/work/SKILL.md:47` resumes
a session from `tcw work list --status active`. A limit that truncated silently
would make those procedures wrong.

## Goals

### Ordering

1. `tcw work list --sort <key>` orders the board by one of four keys:
   `created`, `priority`, `effort`, `title`.
2. `--order asc` or `--order desc` chooses the direction explicitly. Ascending
   means, for each key:
   - `created` — oldest first
   - `priority` — lowest number first
   - `effort` — least effort first (`low`, `medium`, `high`, `very-high`)
   - `title` — A to Z, ignoring upper and lower case
3. Without `--order`, each key uses the direction whose first row a user most
   likely wants: `created` and `priority` descending (newest first, highest
   priority first — the latter matching today's board), `effort` and `title`
   ascending.
4. Items with no value for the key (unset priority, unset effort, a missing or
   unreadable `created`) always go last, whichever direction is chosen.
5. Items that compare equal are ordered by slug, A to Z, in either direction. A
   slug is unique within a node, so the order is always fully determined.
6. With `--sort`, the blocker ordering is not applied. Child items still print
   nested under their parent (or owning epic, in the `-i` view), and siblings
   are in the chosen order among themselves — including siblings that live in
   different nodes under one owner in the `-i` view.
7. With no `--sort`, the *order* of every existing `tcw work list` form is
   exactly what it is today.
8. `--sort` and `--order` combine with `--status`, `--tag` and `--all`, which
   decide *which* items appear, while the sort decides *their order*.
9. Sorting by `created` reads each value through the shared timestamp-reading
   function described in Design, so date-only values and full timestamps
   compare correctly against each other.

### Limiting

10. Each command in scope takes `--limit <n>`, capping how many rows it prints
    **per section**, not across the output as a whole. `--limit 0` means no
    limit. The commands in scope are exactly: `tcw work list`,
    `tcw work inbox list`, `tcw taxonomy list`, `tcw capabilities list`,
    `tcw taxonomy search`, `tcw capabilities search`.
11. The default is **20 rows per section** when `--limit` is not given.
12. Every section in scope is introduced by a heading carrying its counts:
    `(<emitted> of <total>)` when the section was shortened, `(<total>)` when
    every row was printed.
13. A shortened section is followed by a note naming the rows it withheld, in
    the shape `… and 33 additional rows`, on **stderr**.
14. Where a command already has sections, they are the sections limited:
    `tcw work list -i` limits per node (`tcw/work/cli.py:635`), and
    `tcw taxonomy list` and `tcw capabilities list` limit per origin. Where a
    command has one implicit section, it gets one heading.
15. The limit keeps the **first** rows in the order the command was going to
    print them, so `--sort` decides which rows survive a limit, and a
    `--limit` alone keeps today's order's first rows.
16. A negative `--limit`, or a non-integer, is refused with argparse's usual
    usage error (exit status 2).
17. Nothing is ever silently short: a section that printed every row says so
    through its heading count, and one that did not is followed by the note.

## Non-goals

- **Sorting anything but `tcw work list`.** The limiting half reaches every
  list command; the ordering half is `tcw work list` only, as requested. The
  other lists keep the order they have.
- **`tcw work tracker list` (`tcw/work/cli.py:2029-2055`).** It is already
  truncated by the tracker, server-side, and `SearchResult` reports no total
  (`tcw/tracker/jira.py`), so `(<emitted> of <total>)` and "and X additional
  rows" cannot be computed for it. It keeps the stderr note it has. Giving it a
  client-side `--limit` on top of a server-side one would report two different
  truncations as one.
- **`tcw work nodes` (`tcw/work/cli.py:231-270`) and `tcw work tags list`.**
  Neither is a list of entities: `nodes` is a fixed-shape topology report with
  labelled `parent:`/`children:` lines, and `tags list` prints a small
  registered set a project chose. Bounded by construction; a limit adds noise.
- **`tcw capabilities drift` (`tcw/capabilities/cli.py:172-197`).** A report,
  not a list: it already prints its own total on stderr and its exit status
  depends on the count. Limiting it would hide drift, which is the one thing it
  exists to show.
- **A configured default.** The requester chose a per-run flag only — no
  `tcw-config.yaml` key, no environment variable, no `tcw validate` shape check.
  A project cannot record a standing preference.
- **Paging, or an offset.** There is no `--offset`, no "next page", and no way
  to ask for rows 21–40. `--limit 0` is how a user sees the rest.
- **Sorting in `tcw serve` or the web app.** The web client already sorts its
  work tree itself, by name or last-modified time, and does not use the
  server's order (`sortWorkTree`, `web/client/src/model/tree.ts:105-145`).
  `tcw serve` keeps calling `board()` with no sort
  (`tcw/serve/__init__.py:495`) and is not limited: it serves a payload to a
  client that does its own presentation.
- **More sort keys** (complexity, status, modified, started), **sorting by more
  than one key**, and **short flags** for `--sort`, `--order` or `--limit`.
- **Changing what `created` records.** Adding a time of day is
  `2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`.
- **Validating stored values.** A `state.yaml` with a nonsense effort or
  `created` is `tcw validate`'s concern; the board only has to not crash on it.

## Design

### Command-line syntax

```
tcw work list        [--sort {created,priority,effort,title}] [--order {asc,desc}] [--limit N]
tcw work inbox list  [--limit N]
tcw taxonomy list    [--limit N]
tcw taxonomy search  [--limit N] <query>
tcw capabilities list   [--limit N]
tcw capabilities search [--limit N] <query>
```

**`--sort` / `--order`**, from how common tools do it:

- A `--sort <key>` option naming the field is the most widely shared form:
  GNU `ls --sort=time|size|…`, `ps --sort`, `gh search issues --sort`,
  and `kubectl`'s close cousin `--sort-by`.
- The requester asked for both ascending and descending to be available, so
  that no key's default direction has to be guessed. A separate
  `--order asc|desc` option is how `gh search` spells that, and `asc`/`desc`
  are the words SQL and Jira's query language (`ORDER BY created DESC`) use.
  It was chosen over a `--reverse` switch, which only flips a default the user
  must already know, and over a combined `--sort created:desc`, which argparse
  cannot check with `choices`.
- Per-key defaults when `--order` is left off put the "most notable" entry
  first, as `ls` does (`--sort=time` is newest first, `--sort=size` is largest
  first).

`--sort` and `--order` use argparse `choices`, so an unknown key or direction
is refused with the usual usage error (exit status 2) that lists the valid
values. `--order` without `--sort` is refused the same way (exit status 2,
message: `--order needs --sort`): the default board's order is priority and
blockers, which has no single direction to choose, and flipping it would print
blocked items above their blockers.

**`--limit`** is spelled the way `gh` spells it (`gh issue list --limit`), and
takes a plain count rather than `head`'s `-n`, which is a short flag this item
does not add. `--limit 0` for "no limit" is chosen over a separate `--all`
switch because `tcw work list --all` already means something else — include
completed and discarded items — and a second `--all`-shaped spelling on the same
command would be read as that one. It is `type=int` with `choices` unavailable
for an open range, so a negative value is refused by a small argparse type that
raises `ArgumentTypeError`, giving the same exit status 2 as a bad `--sort`.

### The section, and what a heading says

A **section** is a group of rows the command already emits together. Making the
limit per-section rather than per-command is what the request asked for ("for
each section or TCW project"), and it is also the only reading that keeps a
multi-node board useful: a single output-wide cap would spend all its rows on
the first node and print nothing for the rest.

| Command | Sections | Heading label |
| --- | --- | --- |
| `tcw work list` | one | `# board` |
| `tcw work list -i` | one per node, as today (`tcw/work/cli.py:635`) | `# .`, `# project-a`, … |
| `tcw work inbox list` | one | `# inbox` |
| `tcw taxonomy list` | one per origin (`tcw/taxonomy/cli.py:57`) | `# local`, `# <alias>` |
| `tcw capabilities list` | one per origin (`tcw/store/fs.py:2398-2405`) | `# local`, `# <alias>` |
| `tcw taxonomy search` | one | `# matches` |
| `tcw capabilities search` | one | `# matches` |

The heading is `# <label> (<counts>)`, where `<counts>` is `<total>` when the
section printed every row and `<emitted> of <total>` when it did not. So a
complete section reads `# board (12)` and a shortened one `# board (20 of 53)`.
Printing only the total when nothing was withheld keeps the common case short,
and makes "two numbers" itself the signal that rows are missing.

**The flat board's heading is `# board`, deliberately not `# .`.** `# .` is the
`-i` view's label for the anchor node, and `tests/test_work.py:1757`
(`test_list_without_flag_has_no_node_headers`) pins that the flat board carries
no node header — that absence is how the two views are told apart. A distinct
label keeps that contract, and that test, intact.

**Headings go to stdout; the withheld-rows note goes to stderr.** The rule is
_structure on stdout, warning on stderr_. A heading labels the rows beneath it
and is meaningless if separated from them — a user redirecting stdout to a file
must get the grouping in that file, and the `-i` view already prints its
headings there (`tcw/work/cli.py:635`). The note is not structure; it is the
warning that the output is short, and putting it on stderr is what
`_tracker_list` already does for the same reason
(`tcw/work/cli.py:2047-2052`). It also means a pipeline reading rows on stdout
never has to strip it.

### Where the ordering lives

**On the store, beside today's ordering.** The abstraction litmus test asks
whether a store that is not a filesystem could implement this. It could: a
tracker query can order by created date, priority, a mapped effort field or
summary. So ordering is part of the model, not a filesystem trick.

- A pure function in `tcw/store/base.py`, next to `priority_order` and
  `topo_order`, takes a list of `WorkItem`s, a key and an optional direction
  (`asc`, `desc`, or none for the key's default) and returns them in that
  order. It works on `WorkItem` fields only; it never reads folders or files.
- `WorkStore.board` gains optional `sort` and `order` parameters. With no
  `sort` it returns exactly what it returns today. With a `sort` it returns
  `query(status)` in the chosen order, without `topo_order`. A future store
  backed by a tracker may override `board` to ask the tracker to do the
  ordering; the filesystem store inherits the concrete method.
- The valid keys and directions are tuple constants beside `WORK_LEVELS`,
  which the CLI's `choices` read, so the parser and the model cannot disagree.

The CLI passes the options through `_visible_board_items` to `board`. Filters
keep working on the ordered list, and `_render_board` already preserves order
within each sibling group, so nesting in the single-node view needs no change.
In the `-i` view, items from all nodes are put in the chosen order once, before
per-owner child lists are built, so siblings from different nodes are
interleaved correctly; node sections themselves stay in registered order.

### Where the limiting lives

**In the CLI, not the store — and the store interface does not change at all.**

The litmus test asks whether a non-filesystem store could implement the
operation. Here the better question is whether it is a store operation, and it
is not: limiting is how the CLI renders a result set it has already been given,
in the same layer that decides row format, indentation and headings. Nothing
about it is filesystem-specific, so nothing has to be pushed into the adapter
either; a tracker-backed store reaches exactly the same code.

Pushing `limit` down into `board()` and the two `list_all()`s was considered
and rejected on its own merits: a heading must print `<total>`, so the full
count is needed whatever happens. A store-side limit would therefore force a
second count query per section to recover the number it had just discarded —
more interface surface, more work for a remote store, and a new way for the two
numbers to disagree. Keeping the store returning whole result sets keeps
`<emitted>` and `<total>` derived from one list.

A new module `tcw/listing.py` holds the shared mechanism as pure functions over
a list of already-formatted rows — no store access, no I/O, no printing:

- a limit-and-count function returning the rows to print and how many were
  withheld;
- a heading builder producing `# <label> (<counts>)` from a label, the emitted
  count and the total;
- the withheld-rows note's wording, in one place, so every command says it
  identically.

Each command's renderer then groups its rows into sections, and for each one
prints the heading, the kept rows, and the note. Six commands across three
subcommand groups share it, which is the point of the requester's choice of one
mechanism over six.

### Harness compatibility

Both halves are CLI options. Claude and Codex users reach them identically, and
the guarantee lives in the `tcw` CLI rather than in any injected context or
hook, so a Codex agent gets the same behavior. The skill documents only describe
them.

**The procedures that read these lists must be updated in the same change.**
A default limit changes what an agent following TCW's own instructions sees, and
those instructions draw conclusions from absence. Specifically:
`skills/work-create/references/find-overlap.md:14-17`, whose candidate search
must pass `--limit 0` so `no overlap` keeps meaning what it says, and
`skills/work/references/commands.md:6,8`, whose command forms gain the option.

### Shared contract with the timestamps item

This item and
`2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`
must agree on how a stored timestamp is read:

- A stored value is either a date alone (`2026-09-15`) or a full ISO 8601
  timestamp (the international date-and-time text format) with a timezone
  offset (`2026-09-15T14:03:22-07:00`, or `…Z` for UTC).
- A date alone is read as 12:00 (noon) UTC on that date.
- The value may arrive as a string, a `datetime.date` or a `datetime.datetime`,
  because YAML turns unquoted dates and timestamps into those types.
- **The timestamps item owns one function** that turns such a value into a
  timezone-aware `datetime`. Sorting by `created` must go through that
  function, not a second parser. If this item is implemented first, it adds
  that function under the name and module the timestamps item's plan names, so
  the timestamps item reuses it rather than adding another.
- An unreadable value must not take down the board. The timestamps item's spec
  settles the function as `read_timestamp(value) -> datetime` in
  `tcw/timestamps.py`, raising `ValueError` for anything it cannot read; this
  item catches that and treats the value as unset.

**Not blocked on the timestamps item.** Every stored `created` today is a date
alone, which the contract already covers, so sorting works now; ties within a
day fall back to slug, which is reasonable. Once times are recorded, the same
code orders within a day with no further change.

### Comparing values

- **priority:** the integer. Descending by default. Unset (`None`) last.
  A non-integer value from a hand-edited file counts as unset.
- **effort:** its position in `WORK_LEVELS`. Ascending by default. Unset
  (`""`) or any value not in `WORK_LEVELS` counts as unset.
- **title:** `title.casefold()` (Python's case-insensitive form of a string).
  An empty title sorts as an empty string, not as unset, since the loader
  already falls back to the slug when a title is missing
  (`tcw/store/fs.py:4253`). Ascending by default.
- **created:** the timezone-aware moment returned by the shared function above.
  Descending by default. A missing, empty or unreadable value counts as unset.
- **ties:** slug, A to Z, in either direction. Unset items are ordered among
  themselves by slug, A to Z, and stay last.

### What a row is, when rows nest

In `tcw work list`, a child prints indented beneath its parent. The limit counts
**printed rows**, children included, and stops at the next row whatever its
depth — so a family can be cut part-way through, and the withheld count includes
its remaining children. Counting whole families instead was rejected: it makes
the limit approximate (a family of 30 would blow past any cap, or be dropped
whole), and the number in the heading would then not be the number of lines on
screen, which is the one thing a reader can verify at a glance.

## Acceptance criteria

Each is checked against a test store built in the test suite unless it says
otherwise.

### Ordering

1. `tcw work list --sort created` lists an item created `2026-09-15` above one
   created `2026-09-09`; so does `--order desc`; with `--order asc`, below it.
2. Given `created` values `'2026-09-15'` (date alone, read as noon UTC) and
   `'2026-09-15T10:00:00-07:00'` (17:00 UTC), `--sort created` lists the second
   above the first. Given `'2026-09-15T13:00:00+02:00'` (11:00 UTC) instead, it
   lists the first above it.
3. An item whose `state.yaml` has an unquoted `created: 2026-09-15` (loaded as
   a `datetime.date`) sorts the same as one with the quoted string, and does not
   raise.
4. An item whose `created` is missing or is `not-a-date` is listed after every
   item with a readable `created`, under `--order asc` and `--order desc`
   alike, and the command exits 0.
5. `--sort priority` lists priority 50 above 40 above 10, then every item with
   no priority; with `--order asc`, 10 above 40 above 50, and the unset items
   are still last.
6. `--sort effort` lists `low`, `medium`, `high`, `very-high`, then unset;
   `--order desc` lists `very-high` first and unset still last. An item with
   `effort: huge` in its `state.yaml` is listed with the unset items.
7. `--sort title` lists `apple`, `Banana`, `cherry` in that order (upper and
   lower case ignored); `--order desc` lists `cherry`, `Banana`, `apple`.
8. Two items with equal priority are listed in slug order A to Z under
   `--sort priority --order asc` and `--sort priority --order desc` alike.
9. Item B is blocked by item A, and B has the higher priority.
   `tcw work list` (no sort) lists A above B, as today.
   `tcw work list --sort priority` lists B above A.
10. A parent with three children: under `--sort title` the children print
    indented directly beneath the parent, in title order among themselves, and
    the parent is placed by its own title among the top-level items.
11. In the `-i` view, an epic with initiative children in two different nodes
    prints those children beneath the epic in the chosen order across both
    nodes; node section headers stay in registered order.
12. `--sort priority --status backlog --tag cli` shows only backlog items tagged
    `cli`, in priority order. `--sort title --all` includes completed and
    discarded items, in title order.
13. `tcw work list --sort size` exits with status 2 and its error names the
    valid keys. `tcw work list --sort title --order up` exits with status 2 and
    names `asc` and `desc`. `tcw work list --order asc` exits with status 2 and
    says `--order needs --sort`.
14. With no `--sort`, item *order* is unchanged: the existing
    `tests/test_work.py` board-order tests (`test_topo_order_*`,
    `test_priority_order_*`) pass without being edited, and
    `WorkStore.board(status)` with no sort still equals
    `topo_order(priority_order(query(status)))`.

### Limiting

15. With 25 backlog items and `--limit 10`, `tcw work list` prints 10 rows on
    stdout, its heading reads `# board (10 of 25)`, and stderr contains
    `and 15 additional rows`.
16. With 5 items and `--limit 10`, it prints 5 rows, its heading reads
    `# board (5)` — one number, not `5 of 5` — and stderr contains no
    `additional rows` note.
17. `--limit 0` prints all 25 rows, its heading reads `# board (25)`, and
    stderr contains no note.
18. With 25 items and no `--limit`, 20 rows print and the heading reads
    `# board (20 of 25)`, pinning the default.
19. In the `-i` view with two nodes holding 25 items each and `--limit 10`,
    **each** node section prints 10 rows and each heading reads
    `# <label> (10 of 25)`; stderr carries a note for each. This is the
    criterion that proves the limit is per-section, not per-command.
20. `tcw work list --sort title --limit 3` prints the 3 alphabetically first
    titles — the limit keeps the first rows of the chosen order, not of
    today's.
21. `tcw work inbox list --limit 1` with 3 entries prints 1 row, heading
    `# inbox (1 of 3)`, and `and 2 additional rows` on stderr.
22. `tcw taxonomy list` with local and inherited entries prints one heading per
    origin, each with its own counts, and `--limit 1` shortens **each** origin
    to one row.
23. `tcw capabilities list --limit 2` and `tcw capabilities search <q> --limit 2`
    each print 2 rows under a counted heading, with the note on stderr.
24. `tcw taxonomy search <q> --limit 2` does the same.
25. `tcw work list --limit -1` and `--limit abc` each exit with status 2.
26. Rows themselves are byte-identical to today's: for every command in scope,
    a run with `--limit 0` produces stdout equal to today's output with the
    heading line prepended and nothing else changed.
27. `tests/test_work.py:1757` (`test_list_without_flag_has_no_node_headers`)
    passes **unedited** — the flat board's heading is `# board`, so `# .` is
    still absent from it.
28. `tcw serve`'s work payload is unchanged in both order and length: it calls
    `board()` with no sort and does not limit.
29. `--help` for each command in scope shows `--limit` and states the default;
    `tcw work list --help` also shows `--sort` with its four keys and `--order`
    with `asc`, `desc` and each key's default.
30. `skills/work-create/references/find-overlap.md` passes `--limit 0` on every
    command in its candidate search, so an agent following it still sees the
    whole board.
31. The five capability descriptions named under **Capability changes** state
    the new options, and the item's `capabilities.yaml` lists all five under
    `changed:`.

## Risks

- **A default limit makes TCW's own procedures wrong if they are not updated.**
  `find-overlap.md` concludes `no overlap` from an empty search; a silently
  shortened board turns that into a false negative, and a duplicate work item is
  the result. AC30 exists for this, and it is the single highest-value
  criterion in the limiting half. The same reasoning is already written in the
  repository at `tcw/work/cli.py:2048-2049`.
- **Adding a heading changes stdout for commands that had none.** At least
  `test_inbox_list_still_shows_the_filename_label`
  (`tests/test_work.py:2533`) asserts `capsys.readouterr().out` as an exact
  string with no heading, and `tests/test_work.py:1676` asserts
  `out.index("# .\n")`, which the appended counts break. Implementation must
  sweep every exact-stdout assertion over a command in scope rather than fixing
  the two named here. AC26 bounds what may change; AC27 names the one that must
  not.
- **This collides with the sibling inbox item.**
  `2026-09-15-show-the-tracker-s-untriaged-tickets-on-tcw-work-inbox-list`
  gives `tcw work inbox list` its own two sections (`raw intake:` /
  `tracker tickets:`) and its spec says `tests/test_work.py:2533` "must keep
  passing unedited" — which this item breaks. Whichever lands second must adopt
  the other's section shape: two sections with `#`-style counted headings, not
  one scheme layered over the other. Neither blocks the other, but the second
  one's plan must re-read the first.
- **Two parsers for one format.** If the timestamps item and this one each add
  their own way to read `created`, they will drift. The shared contract above
  exists to prevent that; the plan must check the other item's folder at the
  start of implementation.
- **Differing sort defaults.** Without `--order`, `--sort created` and
  `--sort effort` run "opposite" ways. That is deliberate (the first row is the
  one most likely wanted) and matches `ls`; `--order` removes any doubt, and
  `--help` states each key's default.
- **Hiding a blocker relationship.** A chosen sort can list a blocked item above
  its blocker. The row still shows `blocked-by:`, so the information is there;
  only the position changes, which the requester confirmed.
- **The `-i` view's ordering is easy to get subtly wrong.** Sorting each node's
  list separately would keep cross-node siblings grouped by node rather than
  interleaved. AC11 exists to catch that, and AC19 to catch the matching
  mistake in limiting — a per-command cap that spends every row on the first
  node.
- **Mixed types in `created`.** A plain `sorted` over raw values would raise
  comparing a `str` to a `datetime.date`. Every value goes through the shared
  function, and anything it cannot read is unset.
- **A default of 20 is a guess.** It is a screenful, and this repository's own
  lists (53, 47 and 97 rows) all exceed it, so the truncation path is exercised
  in ordinary use rather than only in tests. Since the requester declined a
  configured default, changing it later means a code change and a release note.

## Notes

- **Considered and rejected: printing the heading only when a section is
  shortened.** It would keep every existing exact-stdout test passing. It was
  rejected because the output shape would then depend on the data, which is
  worse for the agents that read these lists than a heading they can always
  skip — and the requester asked for the count in the heading, not for a count
  when there happens to be one.
- **Considered and rejected: `--limit` on the store.** See Design § Where the
  limiting lives. The deciding argument is that the heading needs the total
  anyway.
- `WorkItem.created`'s `str` annotation is not accurate for hand-edited files
  (see Problem). This item does not change the annotation; it only reads the
  field defensively. If the timestamps item changes how `created` is loaded,
  the sort still goes through the shared function either way.
- Planning first proposed a `--reverse` switch and asked the requester to
  confirm each key's default direction. The requester answered that offering
  explicit ascending and descending sorts makes the defaults a non-issue, so
  the design uses `--order asc|desc` and keeps the per-key defaults for when it
  is left off.
- The requester's own framing was "a small change". The limiting half is small
  per command and made larger only by the count of commands; the shared module
  in `tcw/listing.py` is what keeps it from being six changes. If the item still
  reads as too large at `plan`, the natural cut is by subcommand group — work,
  then taxonomy and capabilities — not by feature.
