# Upcoming

Developer changelog for the next version. Technical and precise; grouped by
category.

### Added

- **`WorkStore.tombstone(slug)` and `WorkStore.record_tombstone(...)`** — two
  abstract reads/writes answering "did this store ever hold this id?", a
  question `get()` cannot answer because a store whose resolved items leave it
  returns `None` for finished work and for a typo alike. Abstract rather than a
  filesystem check: an adapter whose resolved items stay retrievable by `get()`
  can answer without storing anything.
- **`Tombstone`** (`slug`, `resolution`, `resolved`). No locator field, by
  decision: a recorded commit is a retrievability promise that does not survive
  a squash-merge, a rebase, or a shallow clone.
- **`FsWorkStore` graveyard** at `<store>/graveyard.yaml` — one sorted mapping
  for the whole store. Reads tolerate every degraded shape (absent, unparseable,
  non-mapping, malformed entry) because `resolve_tcw_ref` is contractually
  barred from propagating store exceptions; a present-but-damaged entry still
  answers that the slug existed.
- **`tcw work tombstone add <slug> [--resolution] [--resolved]`** — backfill for
  items resolved before any record was kept, without which the feature is inert
  for every existing repository. Validates through `resolution_status`, refuses
  a live slug, and commits its write under `auto-commit-transitions`.
- **`ResolveResult.archived` / `.resolution`**, and `reason: "archived"` from
  `/api/resolve`. No SPA change needed: its unrecognized-reason branch already
  neutralizes the anchor and shows `detail`.

### Fixed

- **`tcw validate` was not reproducible across checkouts.** Completion *moves*
  an item into the gitignored `completed/` rather than deleting it, so it
  survived for whoever ran the transition and reached no other clone —
  `validate OK` there, `no such work item` everywhere else, at the same commit.
  Wired as a `complete` pre-hook, that made completion impossible in a fresh
  checkout, which is how this repository's own `complete` transition became
  unusable.
- **`_unique_slug` could reassign a resolved item's slug.** It loops over live
  items only, so in a clone without the ignored folder a matching date and title
  got the very slug a resolved item used, silently repointing every existing
  reference to a different item. Now also consults the graveyard. Forward-only:
  slugs are assumed unique to date, so there is no audit or repair pass.

### Internal

- The graveyard write hooks `_effect_transition`, the one primitive every
  resolving route passes through — `transition()` and the backlog-epic bypass
  that calls it directly. Read-modify-write, not append: one file serves the
  whole store.
- A resolving transition **refuses** when `graveyard.yaml` is unparseable, is
  not a mapping, or holds uncommitted changes TCW did not make — closing the one
  hole a shared path opens in the scoped-commit promise, rather than absorbing
  someone else's edit. Skipped when `auto-commit-transitions` is off, where an
  uncommitted graveyard is the expected steady state.
- `tcw/refs.py`'s docstring recorded that it added no store-interface method.
  That stopped being true and is corrected in place rather than left to age.
- Sweep, recorded so it is not redone: `unresolved_blockers`
  (`base.py:2118-2142`) already fails open on a slug that no longer resolves and
  is unaffected; `tcw work list` excludes resolved statuses and is unaffected.
