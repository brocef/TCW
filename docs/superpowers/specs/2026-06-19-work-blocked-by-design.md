# Work blocked-by relations — design

**Date:** 2026-06-19
**Component:** work (`tcw/store/base.py`, `tcw/store/fs.py`, `tcw/work/cli.py`)
**Status:** approved, pending plan

## Problem

Today "blocked" is a *status* (the `docs/work/blocked/` folder) reached via
`tcw work block` and left via `tcw work unblock`. This conflates two things:

- the **relation** "item A is blocked by item B" (data between items), and
- the **state** "this item is parked" (a board column).

Because `active` and `blocked` are mutually-exclusive folders, the model cannot
represent the common reality of *"I started this, then hit a wall"* — an item
is either in-progress or parked, never both. The relation is also weak: you can
only block from `active`, and only via the single `block --on` call.

## Decision

Decouple the blocked-by **relation** (data) from any blocked **status**.
"Blocked" becomes a *derived overlay* — an item with ≥1 non-completed blocker —
that sits on top of `inbox`/`backlog`/`active`. Remove the `blocked` status, the
`blocked/` folder, and the `block`/`unblock` commands. Manage the relation
directly with `edit`/`new` flags.

This passes the abstraction litmus test: a blocked-by list is just references
between items, and ordering / cycle-detection / gating are pure computation over
those references. All of it lives in the core (`WorkStore`); the FS adapter
stays a dumb effector. A `JiraWorkStore` would map `blocked_by` onto Jira's
"is blocked by" link type.

**Migration is a no-op:** `docs/work/blocked/` holds only `.gitkeep`, and no
`links.yaml` exists yet.

## Model (`tcw/store/base.py` — abstract spine)

- `WORK_STATUSES = ("inbox", "backlog", "active", "completed")`.
- `LEGAL_TRANSITIONS` drops the two `blocked` edges; keeps:
  - `("inbox", "active")`, `("backlog", "active")` — start
  - `("active", "completed")` — complete
- `WorkItem.blocked_on` → **`blocked_by: list[dict]`**, each entry
  `{"slug": …}` or `{"external": …}`, sourced from `state.yaml`.
- Drop the `link()` abstract primitive and the entire `links.yaml` concept;
  `set_field(slug, "blocked_by", …)` covers all writes. One fewer file per item,
  one fewer interface method.

### New concrete operations (depend only on `get` / `set_field`)

- **`add_blocker(slug, ref)`** — read-modify-write: `get(slug)`, copy its
  `blocked_by`, append, `set_field(slug, "blocked_by", new_list)`. Resolve `ref`:
  if it resolves to a work item, store `{"slug": ref}`, else `{"external": ref}`
  (keeps external/off-tracker waits). Refuse:
  - **self-block** (`ref == slug`);
  - any edge that would close a **cycle** — `_reaches(ref, slug)` walks `ref`'s
    blocker chain via `get`; if `slug` is reachable, refuse.
  - Idempotent: adding an entry already present is a no-op.
- **`remove_blocker(slug, ref)`** — read-modify-write dropping entries that match
  `ref` against their **stored** representation (no re-resolution):
  `entry.get("slug") == ref or entry.get("external") == ref`. Removing something
  not present is a silent no-op (idempotent, mirrors add).
- **Entry identity** (for dedup on add and matching on remove): two entries are
  the same iff they share the same `slug` value or the same `external` text. A
  `slug` entry and an `external` entry never collide, even on equal text.
- **`unresolved_blockers(item) -> list[str]`** — an entry is *unresolved* if
  it is `external`, or a slug whose item is not `completed`. A slug that no
  longer resolves counts as **resolved** (silently — the old vanished-blocker
  warning is dropped; rationale: a dropped blocker is gone, and re-`get`-ing it
  is the only way to know, so the warning added noise for a non-actionable
  state). An external wait is "resolved" by `--unblocked-by`-ing its text once
  it clears — there is no separate resolve step (matches keeping it lazy).
  Unlike `topo_order`, this uses `get`, so it *does* see cross-status blockers:
  a `--status active` board can annotate "blocked-by: <backlog-slug>" even though
  that edge didn't reorder the active items.
- **`board(status=None) -> list[WorkItem]`** — `query(status)` then
  `topo_order()`. `status=None` means all statuses (delegates to `query`'s
  existing all-statuses behavior).
- **`topo_order(items)`** (module-level pure function) — stable Kahn
  topological sort. An edge counts **only when both endpoints are in `items`**:
  a slug blocker outside the set (e.g. filtered out by `--status`, or external)
  is *not* a node and does not constrain ordering. Within that graph a blocker
  always precedes what it blocks; ties keep the input order (the status-grouped
  order `query` returns). Any residual cycle (only possible via hand-edited YAML,
  since writes refuse them) degrades gracefully: leftover nodes are appended in
  original order. (Implementation note: a board holds dozens of items, so a
  naive sort is fine — no perf work warranted.)

### Changed transitions (gating)

- **`start(slug, force=False)`** — refuse `inbox/backlog→active` when
  `unresolved_blockers` is non-empty, unless `force`. (`start` has no other
  gate, so the asymmetry with `complete` below is intentional.)
- **`complete(slug, resolution, dod_ack, force=False)`** — refuse when
  unresolved blockers remain, unless `force`. This is **in addition to** the
  existing DoD `--confirm` gate; the two are independent — `--force` bypasses
  *only* the blocker gate and never the DoD `--confirm`. CLI precedence: the CLI
  calls `unresolved_blockers` first, so a blocked complete fails fast on the
  blocker *before* the DoD checklist prints; `complete()` re-checks in the core
  as defense (and for non-CLI callers).

## Adapter (`tcw/store/fs.py`)

- Drop `"blocked"` from `WORK_STATUSES` — note it is **duplicated** at
  `base.py:154` and `fs.py:25` and must change in lockstep; `init()` (fs.py:85)
  derives its scaffold leaves from the fs.py copy, so it follows automatically
  (no more `docs/work/blocked/`).
- `get()` reads `blocked_by` via `list(state.get("blocked_by") or [])` — an
  absent key means `[]`, which is exactly why `create()` needs no change. Remove
  the `links.yaml` read and the `link()` method, and drop the now-stale "links"
  mention from `_safe_yaml`'s docstring.
- `create()` unchanged (new items get blockers via `add_blocker` after creation;
  a brand-new item can never be in a cycle).

## CLI (`tcw/work/cli.py`)

- Remove `block` and `unblock` (and from `SUBCOMMANDS` / help / the `init` help
  string).
- **`tcw work edit <slug> [--blocked-by a,b] [--blocks c] [--unblocked-by d]`**:
  - Each flag value is comma-split with the existing repo idiom
    `(s.strip() for s in val.split(",") if s.strip())` — empty/whitespace tokens
    and a trailing comma are dropped; duplicates collapse via add idempotency.
  - `--blocked-by` → `add_blocker(<slug>, t)` per token; `--unblocked-by` →
    `remove_blocker(<slug>, t)`; `--blocks c` → `add_blocker(c, <slug>)` (reverse
    direction — here `c` is the item being mutated and **must resolve**, so an
    unknown `c` errors `no such work item: c`, it is *not* taken as external).
  - **Validation:** `<slug>` and every `--blocks` target are checked to exist up
    front (no writes if any is missing). Edges then apply left-to-right via
    `add_blocker`/`remove_blocker`, which re-check self-block and cycles against
    live state — so a cycle is **always refused and never persisted**. Full
    transactional rollback is *not* attempted: if a later token in the same
    command fails, earlier valid edges stay applied (the store is plain files
    with no transactions, and the only way to trip this is contradictory
    single-command input, e.g. `--blocked-by B --blocks B`). The integrity
    guarantee that matters — no cycles, ever — holds regardless.
  - `edit` only handles blocking flags for now.
- **`tcw work new "<title>" [--blocked-by a,b]`** — create, then `add_blocker`
  per token (same comma rules). A brand-new item can't cycle, but an unknown
  token still becomes an `external` entry, consistent with `--blocked-by`.
- **`tcw work start <slug> [--force]`**, **`tcw work complete … [--force]`**.
- **`list`** uses `board()`; appends `blocked-by: a, b` (comma-joined slugs /
  external texts) for items with unresolved blockers.
- **`show`** — rename the `blocked_on:` line to `blocked_by:` and format it as a
  comma list of slugs / external texts, not the raw dict `repr` (`_print_item`,
  cli.py:43-44, currently prints the list repr).

## Tests (`tests/test_work.py`)

**First rewrite/remove the existing tests that won't import once `block`/`unblock`
and the `blocked` status are gone:**

- `test_init_gitkeep_persistence` — drop `"blocked"` from its status loop.
- `test_legal_transition_lifecycle` — replace the `st.block`/`st.unblock` leg
  with the new `inbox/backlog→active→completed` path.
- `test_illegal_transitions_refused` — drop the `st.block` setup; assert the new
  illegal set (e.g. `backlog→completed`, `completed→*`).
- `test_unblock_refuses_unresolved_passes_on_dropped` and
  `test_unblock_passes_when_blocker_completed` — re-home as the new `start`/
  `complete` gating tests; the old `warnings` assertion goes away (vanished
  blocker is now silent).

**Then add:**

- blocked-by add/remove round-trip; `--blocks` reverse direction;
- `--blocks` against a nonexistent target errors `no such work item`;
- comma-list parsing (`a, ,b` → `[a, b]`, trailing comma, duplicate token);
- `edit` atomicity — a bad token aborts the whole command, nothing written;
- `remove_blocker` of an absent entry is a no-op;
- cycle refusal — direct (A↔B) and transitive (A→B→C→A);
- self-block refusal;
- external blocker stored and counted unresolved; `--unblocked-by <text>` clears it;
- `start` and `complete` gated on unresolved blockers; `--force` overrides each;
  `complete --force` still requires `--confirm` (DoD independent);
- `topo_order` places a blocker before what it blocks, is stable on ties, and
  ignores a blocker filtered out of the set;
- vanished slug-blocker treated as resolved (silently).

## Docs to sync (CLAUDE.md Documentation Sync)

- `docs/plan/phase-5-work.md` — rewrite the block/unblock spec sections, the
  `links.yaml` description, the CLI table, and the transition diagram.
- `README.md` — CLI surface (`edit`, `new --blocked-by`, `start/complete
  --force`; no `block`/`unblock`).
- `docs/release-notes/upcoming.md` — user-facing summary.
- `docs/changelogs/upcoming.md` — Added/Changed/Removed with commit range.
- `docs/capabilities/work/` — reconcile the work user stories.

## Out of scope

- Cycle detection as a separate `tcw work check` (handled inline at write time).
- An explicit `--external` flag (a non-resolving value is taken as external).
- `edit --title` / `--phase` and a `--unblocks` reverse-removal flag.
- Concurrency / file locking — `tcw` is a single-process CLI; `set_field`'s
  read-modify-write assumes no concurrent writer (unchanged from today).
