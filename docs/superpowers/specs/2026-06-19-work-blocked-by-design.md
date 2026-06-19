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

- **`add_blocker(slug, ref)`** — resolve `ref`: if it resolves to a work item,
  store `{"slug": ref}`, else `{"external": ref}` (keeps external/off-tracker
  waits). Refuse:
  - **self-block** (`ref == slug`);
  - any edge that would close a **cycle** — `_reaches(ref, slug)` walks `ref`'s
    blocker chain via `get`; if `slug` is reachable, refuse.
  - Idempotent: adding an entry already present is a no-op.
- **`remove_blocker(slug, ref)`** — drop the entry matching `ref` by slug or
  external text.
- **`_unresolved_blockers(item) -> list[str]`** — an entry is *unresolved* if
  it is `external`, or a slug whose item is not `completed`. A slug that no
  longer resolves counts as **resolved** (silently — the old vanished-blocker
  warning is dropped).
- **`board(status=None) -> list[WorkItem]`** — `query(status)` then
  `topo_order()`.
- **`topo_order(items)`** (module-level pure function) — stable Kahn
  topological sort over the slug edges *present in `items`*: a blocker always
  precedes what it blocks; ties keep the input order (which is the status-grouped
  order `query` returns). External entries are not nodes. Any residual cycle
  (only possible via hand-edited YAML, since writes refuse them) degrades
  gracefully: leftover nodes are appended in original order.
  - `# ponytail:` re-sort the ready set each step — O(n²) is fine for a board's
    worth of items; swap to a heap if it ever holds thousands.

### Changed transitions (gating)

- **`start(slug, force=False)`** — refuse `inbox/backlog→active` when
  `_unresolved_blockers` is non-empty, unless `force`.
- **`complete(slug, resolution, dod_ack, force=False)`** — refuse when
  unresolved blockers remain, unless `force`. This is **in addition to** the
  existing DoD `--confirm` gate (two independent gates).

## Adapter (`tcw/store/fs.py`)

- Drop `"blocked"` from the module-level `WORK_STATUSES` and from `init()`'s
  scaffold leaves (no more `docs/work/blocked/`).
- `get()` reads `blocked_by` from `state.yaml`; remove the `links.yaml` read and
  the `link()` method.
- `create()` unchanged (new items get blockers via `add_blocker` after creation;
  a brand-new item can never be in a cycle).

## CLI (`tcw/work/cli.py`)

- Remove `block` and `unblock` (and from `SUBCOMMANDS` / help / the `init` help
  string).
- **`tcw work edit <slug> [--blocked-by a,b] [--blocks c] [--unblocked-by d]`** —
  values comma-separated. `--blocked-by`/`--unblocked-by` act on `<slug>`'s list;
  `--blocks=c` is `add_blocker(c, <slug>)` (reverse direction). Cycle / self-block
  errors surface here. `edit` only handles blocking flags for now.
- **`tcw work new "<title>" [--blocked-by a,b]`** — create, then `add_blocker`
  per entry.
- **`tcw work start <slug> [--force]`**, **`tcw work complete … [--force]`**.
- **`list`** uses `board()`; appends `blocked-by: a,b` for items with unresolved
  blockers.
- **`show`** renames its `blocked_on:` line to `blocked_by:`.

## Tests (`tests/test_work.py`)

- blocked-by add/remove round-trip; `--blocks` reverse direction;
- cycle refusal — direct (A↔B) and transitive (A→B→C→A);
- self-block refusal;
- external blocker stored and counted unresolved;
- `start` and `complete` gated on unresolved blockers; `--force` overrides each;
- `topo_order` places a blocker before what it blocks and is stable on ties;
- vanished slug-blocker treated as resolved.

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
