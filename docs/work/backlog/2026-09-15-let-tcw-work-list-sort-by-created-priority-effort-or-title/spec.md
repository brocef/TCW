# Spec: Let tcw work list sort by created, priority, effort or title

## Capability changes

- **changed:** `work/view-the-board` — its description gains the sort option:
  which keys exist, `--order asc|desc` and each key's default, where unset values
  go, and that a chosen sort replaces the blocker ordering while children stay
  nested. No new capability: choosing the board's order is part of viewing the
  board, not a separate thing a user does.

No taxonomy change. The capability's `Feature` and `Subject` (`work-item`) are
unaffected. Records are written at implementation (the item's
`capabilities.yaml` sidecar, a file beside the item's documents that lists the
capabilities it changes) and the description is updated at completion.

## Problem

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
  `-i`/`--incl-desc`/`--include-descendants` (`tcw/work/cli.py:2792-2800`).
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

## Goals

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
7. With no `--sort`, the output of every existing `tcw work list` form is
   exactly what it is today.
8. `--sort` and `--order` combine with `--status`, `--tag` and `--all`, which
   decide *which* items appear, while the sort decides *their order*.
9. Sorting by `created` reads each value through the shared timestamp-reading
   function described in Design, so date-only values and full timestamps
   compare correctly against each other.

## Non-goals

- **Sorting in `tcw serve` or the web app.** The web client already sorts its
  work tree itself, by name or last-modified time, and does not use the server's
  order for that (`sortWorkTree`, `web/client/src/model/tree.ts:105-145`).
  `tcw serve` keeps calling `board()` with no sort (`tcw/serve/__init__.py:495`).
  Adding `created`, `priority` or `effort` to the web app's sort control is a
  separate change.
- **More keys** (complexity, status, modified, started) and **sorting by more
  than one key.** The request asks for four keys to start with.
- **Short flags** for `--sort` or `--order`, and a `--reverse` switch. Easy to
  add later; not asked for.
- **Sorting other lists** (`tcw work inbox list`, `tcw work tracker list`,
  `tcw capabilities list`, `tcw taxonomy list`). The repository-wide sweep for
  sibling lists found these, and each has its own order; the request names
  `tcw work list` only.
- **Changing what `created` records.** Adding a time of day is
  `2026-09-15-record-a-time-of-day-and-timezone-offset-in-every-timestamp-tcw-writes`.
- **Remembering a preferred sort** in configuration.
- **Validating stored values.** A `state.yaml` with a nonsense effort or
  `created` is `tcw validate`'s concern; the board only has to not crash on it.

## Design

### Command-line syntax

`tcw work list --sort {created,priority,effort,title} [--order {asc,desc}]`

Why this spelling, from how common tools do it:

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

### Comparing values

- **priority:** the integer. Descending by default. Unset (`None`) last.
  A non-integer value from a hand-edited file counts as unset.
- **effort:** its position in `WORK_LEVELS`. Ascending by default. Unset
  (`""`) or any value not in `WORK_LEVELS` counts as unset.
- **title:** `title.casefold()` (Python's case-insensitive form of a string).
  An empty title sorts as an empty string, not as unset, since the loader
  already falls back to the slug when a title is missing
  (`tcw/store/fs.py:4253`). Ascending by default.
- **created:** the timezone-aware moment returned by the shared function below.
  Descending by default. A missing, empty or unreadable value counts as unset.
- **ties:** slug, A to Z, in either direction. Unset items are ordered among
  themselves by slug, A to Z, and stay last.

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
code orders within a day with no further change. There is no concrete reason
to make one wait for the other; the only shared piece is the function above,
and the rule for whichever lands first handles that.

### Harness compatibility

This is a CLI option. Claude and Codex users reach it identically; the skill
documents only describe it.

## Acceptance criteria

Each is checked against a test store built in the test suite unless it says
otherwise.

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
14. With no `--sort`, output is unchanged: the existing `tests/test_work.py`
    board-order tests (`test_topo_order_*`, `test_priority_order_*`) and every
    other existing `tcw work list` test pass without being edited, and
    `WorkStore.board(status)` with no sort still equals
    `topo_order(priority_order(query(status)))`.
15. `tcw serve`'s work payload order is unchanged (it calls `board()` with no
    sort).
16. `tcw work list --help` shows `--sort` with its four keys, and `--order` with
    `asc`, `desc` and each key's default.
17. The `work/view-the-board` capability description states the keys,
    `--order` and the defaults, unset-last and the blocker/nesting rules,
    and the item's `capabilities.yaml` lists it under `changed:`.

## Risks

- **Two parsers for one format.** If the timestamps item and this one each add
  their own way to read `created`, they will drift. The shared contract above
  exists to prevent that; the plan must check the other item's folder at the
  start of implementation.
- **Differing defaults.** Without `--order`, `--sort created` and
  `--sort effort` run "opposite" ways. That is deliberate (the first row is the
  one most likely wanted) and matches `ls`; `--order` removes any doubt, and
  `--help` states each key's default.
- **Hiding a blocker relationship.** A chosen sort can list a blocked item above
  its blocker. The row still shows `blocked-by:`, so the information is there;
  only the position changes, which the requester confirmed.
- **The `-i` view's ordering is easy to get subtly wrong.** Sorting each node's
  list separately would keep cross-node siblings grouped by node rather than
  interleaved. Acceptance criterion 11 exists to catch that.
- **Mixed types in `created`.** A plain `sorted` over raw values would raise
  comparing a `str` to a `datetime.date`. Every value goes through the shared
  function, and anything it cannot read is unset.

## Notes

- `WorkItem.created`'s `str` annotation is not accurate for hand-edited files
  (see Problem). This item does not change the annotation; it only reads the
  field defensively. If the timestamps item changes how `created` is loaded,
  the sort still goes through the shared function either way.
- Planning first proposed a `--reverse` switch and asked the requester to
  confirm each key's default direction. The requester answered that offering
  explicit ascending and descending sorts makes the defaults a non-issue, so
  the design uses `--order asc|desc` and keeps the per-key defaults for when it
  is left off.
