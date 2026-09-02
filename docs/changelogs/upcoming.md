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

- **`tcw work tombstone add` refused the case it exists for.** It rejected any
  slug `get()` could find, but `get()` answers for `completed/` and `discarded/`
  too — so on the machine an adopter actually backfills from, where the resolved
  folder is still on disk, the documented migration path refused itself with
  "it is a live work item … resolve the item instead" of an item already
  resolved. Now refuses only a genuinely live status.
- **A second `tombstone add` for the same slug silently replaced its record.**
  `_write_tombstone` assigns the entry outright, which is right for a transition
  and wrong for a backfill: re-running the command without `--resolution` wrote
  an empty resolution and today's date over a good record and reported success.
  With no `tombstone rm`, the only repair was the hand-edit the graveyard exists
  to avoid. An existing record is now left alone.
- **Resolving transitions were not serialized against each other.** The
  cleanliness check ran before the move, the write after it and the commit after
  that, with nothing holding the three together — so two agents resolving
  different items in one working tree could interleave. Worst case was silent: a
  lost graveyard entry left an item resolved with no tombstone, which
  `_unique_slug` then could not protect against. A `flock` on a temp-dir path
  keyed to the store now spans check, write and commit. Also fixed the refusal
  message that told the user another agent's in-flight record was a stray edit
  to "commit or discard" — following that advice destroyed it.
- **`tcw://W/completed/<slug>` still failed in other checkouts.** The
  status-path spelling returned before the tombstone was consulted, keeping the
  exact per-machine behaviour the bare spelling was fixed for. It now falls
  through to the record, verifying the status segment against the resolution
  where one was kept and allowing it where none was.
- **`tcw work tombstone add` committed but never published.** On a provisioned
  store the record sat on the machine that wrote it until some later transition
  happened to push it — the one thing a record whose purpose is reaching other
  clones must not do. It now refreshes first and publishes after, like a
  transition, with its own failure message (nothing moved, so the transition
  wording would have been false).
- **`tombstone add` accepted any string as a slug**, so an empty or path-shaped
  key could be written and committed permanently. Blank and path-shaped are
  refused; nothing stricter, since a backfilled slug may predate today's
  `slugify`. `--resolved` is also normalized now, not merely validated —
  `20260601` passed `date.fromisoformat` and was stored in that shape.
- **`tombstone()` promised more tolerance than it had.** `_safe_yaml` catches a
  YAML syntax error and nothing else, so an unreadable or non-UTF-8 graveyard
  raised out of `_unique_slug` and turned `tcw work new` into a traceback about
  a file the user never touched.
- The viewer described a tombstone with no recorded resolution as "completed
  work", which is wrong for a discarded item.

### Internal

- The graveyard lock lives in the system temp directory, keyed to the store
  path, not in the store: the graveyard is replaced atomically so a lock on it
  protects nothing, and a lock file inside a tracked store root would sit in
  `git status` forever. `flock` over a lock directory because the kernel
  releases it on process death — a stale directory lock would wedge every future
  resolution. Degrades to no locking where `fcntl` is absent, which is the
  behaviour every caller had before. Cross-machine concurrency is out of scope
  and ends in a plain YAML merge conflict, as designed.
- Three hand-maintained test lists did not cover the new command and have no
  completeness check of their own: the "every public CLI write" list in
  `test_non_git_writes.py`, `TRANSITIONS` in `test_store_publication.py`, and
  the mutator name prefixes in `test_stage_verb.py` (`record_tombstone` matched
  none of them, so the no-mutation guard silently skipped it).
- The graveyard write hooks `_effect_transition`, the one primitive every
  resolving route passes through — `transition()` and the backlog-epic bypass
  that calls it directly. Read-modify-write, not append: one file serves the
  whole store.
- A resolving transition **refuses** when `graveyard.yaml` is unparseable, is
  not a mapping, or holds uncommitted changes TCW did not make, rather than
  absorbing someone else's edit. Skipped when `auto-commit-transitions` is off,
  where an uncommitted graveyard is the expected steady state. This narrows the
  hole a shared path opens in the scoped-commit promise; the lock above is what
  closes it, and the two are not the same thing.
- `tcw/refs.py`'s docstring recorded that it added no store-interface method.
  That stopped being true and is corrected in place rather than left to age.
- Sweep, recorded so it is not redone: `unresolved_blockers`
  (`base.py:2118-2142`) already fails open on a slug that no longer resolves and
  is unaffected; `tcw work list` excludes resolved statuses and is unaffected.
  **The sweep was not complete, though it was recorded as such.** Adversarial
  review found a third caller with the identical defect —
  `_shipped_but_missing` (`capabilities/cli.py`) decides "did this ship?" from
  `get()`, so `tcw capabilities drift` reports drift for whoever completed the
  work and reports none in every other clone, failing in the silent direction.
  Filed as its own item rather than fixed here, since it changes what a
  different command reports.
