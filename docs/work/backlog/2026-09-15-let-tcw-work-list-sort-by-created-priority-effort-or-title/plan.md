# Plan: Let tcw work list sort by created, priority, effort or title

Implements `spec.md`. Each task ends with the full suite green, run the way CI
runs it (bare `pytest` from the checkout root, not `python -m pytest`), and is
committed on its own.

**No blocker on the timestamps item.** Every stored `created` today is a date
alone, which the shared contract already covers, so this item can be built and
shipped first. The one piece the two items share is the timestamp-reading
function, and Task 1 decides who writes it at the moment implementation starts.

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

1. Beside `WORK_LEVELS` (`:852`) add
   `WORK_SORT_KEYS = ("created", "priority", "effort", "title")`.
2. Beside `priority_order` (`:2577`) add
   `order_by(items: list[WorkItem], key: str, reverse: bool = False) -> list[WorkItem]`.
   It reads only `WorkItem` fields. Behavior, exactly:
   - A value per item, or "unset":
     - `created`: `read_timestamp(created)`; a raised `ValueError` means
       unset.
     - `priority`: the value if it is an `int` and not a `bool`; else unset.
     - `effort`: `WORK_LEVELS.index(effort)` if it is in `WORK_LEVELS`; else
       unset.
     - `title`: `str(title).casefold()`; never unset.
   - Newest/highest first by default for `created` and `priority`; lowest
     first for `effort` and `title`. `reverse` flips that.
   - Ties by slug A to Z, flipped by `reverse`. Do it with two stable sorts:
     sort the items that have a value by slug (descending when `reverse`),
     then sort that list by value with `reverse=` set to the key's effective
     direction. Python's sort is stable even with `reverse=True`, so equal
     values keep the slug order from the first pass.
   - Unset items follow, sorted by slug A to Z, whatever `reverse` is.
   - An unknown `key` raises `ValueError` naming `WORK_SORT_KEYS`.
3. Change `WorkStore.board` (`:3207`) to
   `board(self, status=None, sort=None, reverse=False)`: with `sort is None`,
   return `topo_order(priority_order(self.query(status)))` exactly as today
   (and ignore `reverse`); otherwise return `order_by(self.query(status), sort,
   reverse)`. Extend its docstring to say a store backed by a tracker may
   override it to have the tracker do the ordering.

Tests, new section `# ── order_by / board(sort=) ──` in `tests/test_work.py`,
building items with `st.create(..., created=…)` and adjusting fields with
`st.set_field(slug, key, value)`:

- **AC1** created: `2026-09-15` above `2026-09-09`; reversed below.
- **AC2** created mixed forms: date alone `'2026-09-15'` vs
  `'2026-09-15T10:00:00-07:00'` (the second first); vs
  `'2026-09-15T13:00:00+02:00'` (the first first).
- **AC3** `set_field(slug, "created", datetime.date(2026, 9, 15))` sorts with
  the quoted equivalent and does not raise.
- **AC4** `created` set to `'not-a-date'`, and another set to `''` (what the
  loader gives for a missing key, `tcw/store/fs.py:4255`), both last with and
  without `reverse`.
- **AC5** priority 50, 40, 10, then unset; reversed 10, 40, 50, unset last.
- **AC6** effort low, medium, high, very-high, unset; reversed very-high first,
  unset last; `effort: huge` (via `set_field`) is with the unset ones.
- **AC7** titles `apple`, `Banana`, `cherry`; reversed `cherry`, `Banana`,
  `apple`.
- **AC8** two items with equal priority: slug A to Z; reversed Z to A.
- **AC9 (model half)** B blocked by A, B higher priority: `board()` gives A
  first; `board(sort="priority")` gives B first.
- **AC14 (model half)** `board(status)` equals
  `topo_order(priority_order(query(status)))` for a store with blockers and
  mixed priorities; `order_by(items, "size")` raises `ValueError`.

**Files:** `tcw/store/base.py`, `tests/test_work.py`. **Proves it:** the tests
above, and the existing `test_topo_order_*`, `test_priority_order_*` and
`test_cli_new_and_edit_priority_reorders_list` passing unedited.

## Task 3 — The CLI: `--sort` and `--reverse` on `tcw work list`

In `tcw/work/cli.py`:

1. Parser (`:2792-2800`): add
   `--sort` with `choices=WORK_SORT_KEYS` (import it from `tcw.store.base`),
   help `"order the board by this key instead of priority and blockers
   (created and priority: newest/highest first; effort: least first; title:
   A-Z; unset values last)"`; and `--reverse`, `action="store_true"`, help
   `"flip the --sort direction (unset values stay last)"`.
2. `_list` (`:642`): if `args.reverse` and not `args.sort`, print
   `tcw work list: --reverse needs --sort` to stderr and return 2. Otherwise
   pass `args.sort` and `args.reverse` to both renderers.
3. `_visible_board_items` (`:506`): take `sort=None, reverse=False` and call
   `st.board(status=status, sort=sort, reverse=reverse)`. Filters are
   unchanged and keep the order they are given.
4. `_render_board` (`:552`): take and pass through `sort`/`reverse`. Nothing
   else changes; it already keeps the incoming order inside each sibling group.
5. `_render_descendant_boards` (`:571`): take and pass through
   `sort`/`reverse`. When `sort` is set, after `entries` is built (`:588-592`)
   and before the ownership pass, put `entries` into one cross-node order:
   `rank = {id(it): n for n, it in enumerate(order_by([e[2] for e in entries],
   sort, reverse))}` then `entries.sort(key=lambda e: rank[id(e[2])])`. Node
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
  `main(["work", "list", "--reverse"])` returns 2 and stderr contains
  `--reverse needs --sort`.
- **AC16** `--help` output (via `SystemExit` from `main(["work", "list",
  "--help"])`) contains `--sort`, `{created,priority,effort,title}` and
  `--reverse`.

**Files:** `tcw/work/cli.py`, `tests/test_work.py`. **Proves it:** the tests
above; every existing `list` and `--include-descendants` test in
`tests/test_work.py`, `tests/test_work_tags.py` and
`tests/test_project_overrides.py` passing unedited (**AC14**); and
`tests/test_serve_descendants.py` plus the other `tests/test_serve*.py` passing
unedited, since `tcw serve` still calls `board()` with no sort (**AC15**).

## Task 4 — Capability record

1. Create the item's `capabilities.yaml` sidecar (in the folder
   `tcw work path 2026-09-15-let-tcw-work-list-sort-by-created-priority-effort-or-title`
   prints) containing:
   ```yaml
   changed:
       - work/view-the-board
   ```
2. Edit the capability's `description.md` (in the folder under
   `tcw capabilities path`, at `work/view-the-board/`; the body has no CLI
   verb). After the sentence ending "…is how I look at what was closed.", add:
   "With `--sort created|priority|effort|title` I choose the board's order
   instead: newest first, highest priority first, least effort first, or titles
   A to Z ignoring case, and `--reverse` flips it. Items with no value for the
   key stay last either way, and items that compare equal are ordered by slug.
   A chosen sort replaces the usual rule that lists a blocker above what it
   blocks; child items still print beneath their parent or epic, in the chosen
   order among themselves."
3. `tcw capabilities check` exits 0.

**Files:** the item's `capabilities.yaml`,
`docs/capabilities/work/view-the-board/description.md`. **Proves it (AC17):**
`tcw capabilities show work/view-the-board` shows the new sentences;
`tcw capabilities check` exits 0.

## Documentation Sync

One pass over the finished diff, after Tasks 1–4, committed together before
`outcome.md` is written. Predicted triggers:

- `README.md` **[Public-API] — fires** (new public CLI options). In the "Board
  and items" table, change the `tcw work list` row to: "shows the board;
  completed and discarded items only when asked; `--sort` orders it by created
  date, priority, effort or title".
- `docs/release-notes/upcoming.md` **[Public-API] — fires.** A short
  plain-language entry: `tcw work list --sort` with the four keys and their
  default directions, `--reverse`, unset values last, children still nested.
- `docs/changelogs/upcoming.md` **[Any-Code-Change] — fires.** Under **Added**:
  `tcw work list --sort {created,priority,effort,title}` and `--reverse`;
  `WORK_SORT_KEYS`, `order_by`, and `WorkStore.board(sort=, reverse=)` in
  `tcw/store/base.py`; the timestamp-reading function if Task 1 added it. Under
  **Changed**: `-i` orders entries across nodes before building child lists
  when a sort is chosen.
- `skills/<component>/SKILL.md` **[Skill-Driven-Component] — fires** for
  `tcw-work` (its CLI surface changed). `skills/tcw-work/SKILL.md` itself
  mentions only `tcw work list --status active` (`:44`) and needs no change;
  the option list lives in its reference
  `skills/tcw-work/references/commands.md:8`, whose "the board" row becomes
  `tcw work list [--status <s>] [--tag|--tags <t[,t]>] [--all] [-i] [--sort
  created|priority|effort|title [--reverse]]` — hides resolved; `-i` adds
  descendant boards; `--sort` replaces priority-and-blocker order.
- `docs/guide/jira.md` **[Tracker-Change] — does not fire** (no tracker
  behavior changes).
- `skills/tcw-configure/references/<document>.md` **[Configuration-Key-Change]
  — does not fire** (no configuration key).
- Not a declared entry, but the full reference README points to:
  `docs/guide/work.md:241-247` lists every `tcw work list` form. Add
  `tcw work list --sort created           # newest first; also priority, effort, title; --reverse flips`
  and change the comment on `:241` to say the plain board is priority first,
  then blocker order, unless `--sort` is given.

## Verification

What the suite cannot check, done by hand at the end of implementation:

1. **Unchanged default output on a real board.** Before Task 2, from the
   checkout implementation runs in, save `tcw work list`, `tcw work list --all`
   and `tcw work list -i` to files in the session's scratchpad directory. After
   Task 3, with no work-item files changed in between (check
   `git status docs/work`), run the same three and `diff` each against its
   saved copy: all three diffs must be empty.
2. **Reads well on this repository's board:** `tcw work list --sort created`
   (today's items at the top), `--sort effort` (low effort first, unset at the
   bottom), `--sort title --reverse`, and `-i --sort priority`. Look for rows
   that are out of order or children detached from parents.
3. **`--help` reads clearly**: `tcw work list --help` shows both options with
   the direction wording.
4. **Bare `pytest`** from the checkout root passes, the way CI runs it.

## Notes

- Questions for the user carried from `spec.md` (defaults are chosen and the
  plan follows them): effort sorts least effort first; `created` sorts newest
  first. Changing either is a one-word change to the default-direction mapping
  in `order_by`, the help text, and the capability sentence.
- `WorkItem.created` stays annotated `str` although YAML can hand it a
  `datetime.date` or `datetime.datetime`; this item reads it through the shared
  function instead of changing the loader. That is the timestamps item's
  territory.
- The web app keeps its own client-side sort (`web/client/src/model/tree.ts:105`);
  offering these keys there would be a separate item, not filed here.
