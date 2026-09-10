# Spec — Record the branch a work item is being implemented on

## Capability changes

No new capabilities. Three existing entries change and are recorded in this
item's `capabilities.yaml`:

- `work/start-a-work-item` — a plain `tcw work start` now records the branch the
  work is being implemented on, not only the `--worktree` path.
- `work/read-a-work-item` — `tcw work show` displays `branch` and `worktree`.
- `work/view-the-board` — the board shows an item's branch, and
  `tcw work list --branch` filters on it.

Nothing here is removed, and no capability's `Status` moves: all three are
already `Supported` and stay so. `tcw capabilities check` passes on the tree as
it stands.

## Problem

`WorkItem` already carries `worktree` and `branch` (`tcw/store/base.py:1879-1880`),
`FsWorkStore._read_item` reads them back (`tcw/store/fs.py:3953-3954`), and
`WORK_ITEM_SCHEMA` already emits both (`tcw/work/projection.py:126-127`). The
model is not missing a field. Three things stop it from answering *where is this
work being done*.

**1. Only `--worktree` writes them.** `_start` sets `worktree` and `branch` at
`tcw/work/cli.py:790-791`, inside the `if not args.worktree: … return` guard's
far side. `WorkStore.start` (`tcw/store/base.py:2665`) writes `owner` and
`started` and nothing else, so an item started on an ordinary branch — the
common case — has `branch: ''`.

**2. Nothing displays them.** `_print_item` (`tcw/work/cli.py:128-163`) prints
nine fields and the body, and skips both. `_render_board_item`
(`tcw/work/cli.py:377-406`) prints owner and started for an active item and
skips both. `tcw work show --json` is the only surface that reveals either.

**3. Nothing filters on them.** The `list` parser takes `--status`, `--tag`,
`--all` and `--include-descendants` (`tcw/work/cli.py:1890-1898`).

A fourth problem is adjacent and this spec fixes it, because the change would
otherwise make it worse. `start` writes the claim as **two** separate
`set_field` calls — `tcw/store/base.py:2673-2674` on the takeover path and
`2692-2693` on the normal one. Each re-resolves the item's location, so a
transition landing between them writes `started` into a folder `owner` did not
go to. That is exactly the tear `_set_fields_at` says it exists to prevent:
*"Multi-key so a pair like `owner`/`started` cannot be torn across two locations
by a move landing between them"* (`tcw/store/fs.py:5539-5540`). The multi-key
write is reachable only through `_effect_transition`'s `fields` argument, and
`start` cannot use it: `transition` clears `owner` and `started` **over** any
caller-supplied fields on a move touching `active` (`tcw/store/base.py:2626-2629`),
by design. Adding `branch` as a third `set_field` call widens the window.

## Goals

- A plain `tcw work start` records the branch the work will be implemented on.
- `tcw work show` and the board reveal an item's branch and worktree.
- The board can be filtered to one branch.
- The claim and the branch are written by one store call, closing the existing
  two-write tear rather than widening it.

## Non-goals

- **No node configuration for any of this.** The original request paired the
  branch with an opt-out mechanism on the premise that a project may not want
  the field. `branch` is already in the model, already in the emitted schema,
  and already written on the `--worktree` path with no opt-out; adding one for
  the other write path would make the same field optional in one case and
  mandatory in the other. Nothing here reads a new config key.
- **No node-declared field vocabulary.** That is
  `2026-09-10-let-a-node-declare-its-own-work-item-state-fields`, and this item
  neither waits on it nor anticipates it.
- **No schema-version move.** Both fields are already in `WORK_ITEM_SCHEMA`;
  `SCHEMA_VERSION` stays 1 and the web client's item type is unchanged.
- **`rework` does not re-record the branch.** It is a transition, not a claim,
  and it deliberately leaves the item unclaimed; there is no claimant to
  attribute a branch to. The consequence is named under Risks.
- **A plain start records no `worktree`.** There is no worktree to name. The
  field is displayed, not written, outside `--worktree`.
- **Nothing cleans a branch up.** A completed item keeps the branch it was
  implemented on even after the branch is deleted, exactly as a `--worktree`
  item does today.

## Design

**D1 — the branch is the code node's checked-out branch, or the empty string.**
A new concrete method `WorkStore.current_branch() -> str` returns `""`.
`FsWorkStore` overrides it with `git_current_branch(self.node_root) or ""`
(`tcw/store/fs.py:726-733`). The **code** node, not the store: `branch` records
where the implementation lives, and `--worktree` proves it — `add_worktree`
creates `work/<slug>` in `st.node_root` (`tcw/store/fs.py:761-766`, called from
`tcw/work/cli.py:833`). A detached HEAD, or a code node outside a repository,
yields `""` and never raises; a start must not fail because of where HEAD is.

An **unborn** branch — a repository with no commit yet — is a third case, and it
is why *when* the branch is read matters. `git rev-parse --abbrev-ref HEAD`
exits 128 there, so `git_current_branch` returns `None` and the branch would be
recorded empty. `current_branch()` is therefore called **after** the transition,
not before: the transition's own auto-commit is what gives the repository its
first commit, so by the time the claim is written HEAD is born and names a real
branch. Reading it earlier would make the first start in a fresh repository the
one start that records nothing.

The method is concrete with a `""` default rather than abstract, so an adapter
written against the current interface keeps working. That is the degradation
`registered_tags` already documents for an adapter with no configuration
surface.

**D2 — `start` records the branch in the same write as the claim.**
A new abstract `WorkStore.set_fields(slug, fields: dict)` carries a whole field
map; `set_field` (`tcw/store/base.py:2242`) becomes a one-key call through it,
and `FsWorkStore` implements it as the already-existing `_set_fields_at`
(`tcw/store/fs.py:5530-5547`). `start` then builds one map — `branch` always,
`owner` and `started` only when an owner was supplied — and writes it once.
Writing the map when it holds only `branch` is what makes an unclaimed start
record one: `tcw serve` starts items with no owner
(`tcw/serve/__init__.py:870`), and the current `if owner:` guard would skip the
write entirely.

**D3 — `branch` is written on a claim and on a takeover, and by nothing else.**
Both paths in `start` write it, because a takeover is a new claimant who may be
on a different branch. It is written **unconditionally**, including as `""`: the
field means *the branch this claim is on*, and a claim that cannot name one must
not inherit the last one. No other transition writes or clears it — `submit`,
`rework` and `complete` must leave it alone, since `complete`'s worktree
merge-back reads it and `_warn_off_trunk` compares against it
(`tcw/store/fs.py:5673-5695`).

**D4 — `--worktree` still wins.** `_start` overwrites `branch` with
`work/<slug>` after `st.start(...)` returns (`tcw/work/cli.py:790-791`). That
ordering is correct — the item will be implemented on the worktree branch, not
on whatever was checked out when the command ran — and this spec pins it rather
than changing it.

**D5 — `show` and the board display both fields when non-empty.**
`_print_item` gains a `branch:` line and a `worktree:` line after `started:`,
each printed only when the field is non-empty, matching every other optional
line in that function. `_render_board_item` appends a `| branch: <name>` segment
whenever `item.branch` is non-empty, placed immediately before the claim
segment. The rule is status-independent on purpose: a `review` item is live work
whose branch is worth finding, and the two resolved statuses are hidden from the
default board anyway.

**D6 — `tcw work list --branch <name>` filters, mirroring `--tag`.**
Repeatable, match-any, exact and case-sensitive, since git branch names are
case-sensitive. The filter is applied where the tag filter already is, in
`_visible_board_items`, over items `query()` already returned — no new store
operation. `--branch` takes a required value; there is no bare form meaning "the
branch I am on", because a flag whose meaning changes with the checkout is a
surprise in a saved command.

## Abstraction litmus test

| Operation | Verdict |
| --- | --- |
| `WorkStore.current_branch()` | **Store interface.** Any backend can answer, and one with no view of a working copy returns `""` — the same degradation `registered_tags` gives an adapter with no configuration surface. |
| `WorkStore.set_fields(slug, fields)` | **Store interface.** A field-map update is the shape every tracker's issue-update endpoint already takes; the filesystem adapter has had it privately as `_set_fields_at` all along. |
| `start` recording `branch` with the claim | **Model.** `start` is already a model operation writing model fields; this adds one more to the same write. |
| `git rev-parse --abbrev-ref HEAD` | **Filesystem-adapter private detail.** Already there as `git_current_branch`; nothing above it knows how the answer was obtained. |
| `show` / board display, `list --branch` | **No new operation.** Presentation and a client-side predicate over `query()`, exactly as `--tag` is. |

## Acceptance criteria

1. `tcw work start <slug>` run in a repository with `feature-x` checked out
   leaves `branch: feature-x` in the item's `state.yaml`.
2. `tcw work start <slug>` on a detached HEAD exits 0, moves the item to
   `active`, and leaves `branch` empty.
3. Starting an item that already records `feature-a`, while `feature-b` is
   checked out, leaves `branch: feature-b`.
4. `tcw work start <slug> --worktree` leaves `branch: work/<slug>`, not the
   branch checked out when the command ran.
5. A start carrying no owner — `WorkStore.start(slug, force=...)`, the call
   `tcw serve` makes — records the branch, and leaves `owner` and `started`
   empty.
6. `tcw work start <slug> --take-over --owner <id>` leaves `owner`, `started`
   and `branch` all rewritten.
7. `WorkStore.set_fields` exists on the abstract store, `set_field` delegates to
   it, and `start` reaches the store exactly once per claim rather than twice.
8. `tcw work show <slug>` prints a `branch:` line and a `worktree:` line when
   those fields are non-empty, and neither line when they are empty.
9. A board row for an item with a branch carries a `| branch: <name>` segment;
   a row for an item without one carries no such segment.
10. `tcw work list --branch feature-x` lists only items whose branch is exactly
    `feature-x`; `--branch a --branch b` lists items on either; an unknown
    branch lists nothing and exits 0; `--branch feature-x` does not list an item
    on `Feature-X`.
11. `submit`, `rework` and `complete` leave `branch` unchanged, and a
    `--worktree` item still merges back on `complete`.
12. The first `tcw work start` in a repository that has no commit yet still
    records a branch, because the transition's own commit lands before the
    claim is written.
13. `tcw work show --json` reports `"schema": 1` and validates against
    `WORK_ITEM_SCHEMA`; `tcw validate` reports no new problem on a node whose
    configuration did not change.

### Coverage

Criteria against the six numbered design rules. A cell is the test that
exercises that criterion against that rule, or `n/a` with the line that makes it
so.

| # | D1 branch source | D2 one write | D3 claim-only | D4 worktree wins | D5 display | D6 filter |
| - | ---------------- | ------------ | ------------- | ---------------- | ---------- | --------- |
| 1 | `test_start_records_current_branch` | `test_start_writes_claim_and_branch_once` | `test_start_records_current_branch` | n/a — plain start, `tcw/work/cli.py:783-787` returns before the `--worktree` block | n/a — asserts `state.yaml`, not output | n/a — no `--branch` passed |
| 2 | `test_start_on_detached_head_records_no_branch` | `test_start_writes_claim_and_branch_once` | `test_start_on_detached_head_records_no_branch` | n/a — plain start, `tcw/work/cli.py:783-787` | n/a — asserts `state.yaml` | n/a |
| 3 | `test_restart_replaces_recorded_branch` | `test_start_writes_claim_and_branch_once` | `test_restart_replaces_recorded_branch` | n/a — plain start, `tcw/work/cli.py:783-787` | n/a — asserts `state.yaml` | n/a |
| 4 | `test_worktree_start_records_work_branch` | `test_worktree_start_records_work_branch` | `test_worktree_start_records_work_branch` | `test_worktree_start_records_work_branch` | n/a — asserts `state.yaml` | n/a |
| 5 | `test_unowned_start_records_branch` | `test_unowned_start_records_branch` | `test_unowned_start_records_branch` | n/a — `tcw/serve/__init__.py:870` passes no `--worktree` | n/a — asserts `state.yaml` | n/a |
| 6 | `test_take_over_rewrites_claim_and_branch` | `test_take_over_rewrites_claim_and_branch` | `test_take_over_rewrites_claim_and_branch` | n/a — takeover never reaches the worktree block, `tcw/work/cli.py:777` | n/a — asserts `state.yaml` | n/a |
| 7 | n/a — counts store calls, does not read a branch | `test_start_writes_claim_and_branch_once` | `test_start_writes_claim_and_branch_once` | n/a — abstract-store test, no CLI | n/a — no output | n/a |
| 8 | n/a — fixture sets the fields directly | n/a — read-only | n/a — read-only | n/a — fixture, not a start | `test_show_prints_branch_and_worktree`, `tests/fixtures/show_baseline/` | n/a |
| 9 | n/a — fixture sets the fields directly | n/a — read-only | n/a — read-only | n/a — fixture, not a start | `test_board_row_shows_branch` | n/a — no `--branch` passed |
| 10 | n/a — fixture sets the fields directly | n/a — read-only | n/a — read-only | n/a — fixture, not a start | n/a — asserts which rows appear, not their content | `test_list_filters_by_branch`, `test_list_branch_filter_is_exact_and_cased` |
| 11 | n/a — no start involved | n/a — no claim written | `test_transitions_preserve_branch`, scenario 09 | `test_transitions_preserve_branch` | n/a — asserts `state.yaml` | n/a |
| 12 | `test_start_in_an_unborn_repo_records_the_branch` | `test_start_in_an_unborn_repo_records_the_branch` | `test_start_in_an_unborn_repo_records_the_branch` | n/a — plain start, `tcw/work/cli.py:783-787` | n/a — asserts `state.yaml` | n/a |
| 13 | n/a — schema shape, not a branch value | n/a — no write | n/a — no write | n/a — no start | `test_show_json.py` (unchanged) | n/a |

Two whole columns read `n/a` for the display and filter criteria (8-10) against
D1-D4, and that is the finding the table is meant to surface: those criteria are
checked against fixtures that set `branch` by hand, so none of them would catch a
`start` that recorded the wrong value. Criteria 1-6 are what cover that, and
they assert on `state.yaml` rather than on rendered output for the same reason
in reverse.

## Risks

- **A reworked item keeps a stale branch.** `rework` sends `review` → `active`
  without a claim, so the branch its last start recorded stays until someone
  runs `--take-over`. The field then names a branch the current work may not be
  on. Accepted: the alternative is writing `branch` from inside `transition`,
  which would also fire on `submit` and `complete` and break the worktree
  merge-back that reads it. Named here so it is a known limit rather than a
  surprise.
- **Two golden fixtures move.** `tests/fixtures/show_baseline/` pins `show`
  output line for line and `tests/fixtures/non_git_reads/work-list.txt` pins a
  board listing. Both have to be regenerated deliberately, and a regeneration
  that silently absorbs an unrelated diff is the failure mode to watch.
- **`set_fields` is a new abstract method.** Any adapter outside this repository
  implementing `WorkStore` breaks until it adds one. `FsWorkStore` is the only
  implementation here (`tcw/store/fs.py:3304`), so the cost is external and
  currently hypothetical — but it is a real interface change, unlike
  `current_branch`, which defaults.
- **The board line grows.** `_render_board_item` already emits up to six
  segments; a branch segment makes long rows longer on a narrow terminal. The
  alternative — showing it only under `--status active` — was rejected because a
  `review` item is exactly the "active but not yet completed" work the request
  wants to find.

## Notes

- The claim-tear fix (D2) is repaired here rather than filed, because this
  change is what would otherwise make it worse: a third `set_field` call widens
  a window whose own docstring says it should not exist. It is a behaviour-
  preserving repair to a path this item is already rewriting, not a separate
  sweep.
- A repo-wide sweep for the sibling defect — a multi-key state write issued as
  several single-key calls — found no second site. `set_field`'s only other
  callers are `add_blocker` and `remove_blocker`
  (`tcw/store/base.py:2558`, `2573`), each writing one field, and the
  `--worktree` pair at `tcw/work/cli.py:790-791`, which runs after the item has
  stopped moving.
