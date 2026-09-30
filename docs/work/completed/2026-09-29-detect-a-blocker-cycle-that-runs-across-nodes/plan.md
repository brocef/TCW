# Plan — Detect a blocker cycle that runs across nodes

Worktree: `.worktrees/<slug>` on `work/<slug>`, run through the scratch venv
re-pointed at the worktree. Every task commits on its own; the suite is green
at each commit.

## Task 1 — Failing tests

**Creates** `tests/test_cross_node_blocker_cycles.py`, reusing the graph shape
of `tests/test_cross_node_blockers.py` (a `node()` helper copied, not imported;
root `r` with children `a`, `b`, `c`, each keeping a board).

One test per acceptance criterion 1-10: CLI cases through `tcw work …` in a
subprocess, store cases through `FsWorkStore`. Criterion 8 writes the stored
cycle into `state.yaml` directly; criterion 9 opens `b`'s board through a
letter-case variant of its path and is skipped when the disk is
case-sensitive; criterion 10 leaves `y` in `.claiming/` as
`tests/test_child_status.py:88-89` does. Run: 1-6 and 9 fail; 7, 8 and 10 pass
(they guard against over-refusal and must stay green). Committed with the
failing ones marked `xfail(strict=True)` so the suite stays green; Task 3
removes the marks.

## Task 2 — The walk over (store, slug) pairs, in the model

**Modifies** `tcw/store/base.py`.

- `WorkStore._store_key()` → `id(self)`.
- `WorkStore._blocker_target(entry)` → `(self, slug)` for `{"slug": s}`; for
  `{"external": t}` shaped like a slug, `(self, t)` whether or not the item
  exists (see the spec's corrected Design bullet); otherwise `None`.
- `_reaches(start, target, *, settled)`: `start` a `(store, slug)` pair,
  `target` and `settled` slugs of `self` (as shipped — the goal is always in
  the store doing the edit). Keyed by `(store._store_key(), slug)`; stores met
  are kept in a dict by key, first open wins; `get` on any store is wrapped
  — any exception means not followed.
- `_check_new_blocker(slug, entry, ref)`: `target = self._blocker_target(entry)`;
  `None` → return; `target` equal to `(self, slug)` → self-block; `_reaches`
  from `target` to `(self, slug)` → cycle.
- `check_blocker_edits`, `--blocks` half: expand `proposed` through
  `_blocker_target` rather than `"slug" in e`.

Existing blocker tests prove nothing regressed locally
(`tests/test_work.py -k block`, `tests/test_local_qualified_blockers.py`,
`tests/test_cross_node_blockers.py`, `tests/test_edit_refusal.py`).

## Task 3 — The filesystem adapter

**Modifies** `tcw/store/fs.py`, `tests/test_cross_node_blocker_cycles.py`.

- `FsWorkStore._qualified_target(text)` → `(store, slug) | None`: the shape
  check now inline in `external_blocker_state` (`fs.py:6077-6080`), the
  registry probe, and `resolve_qualified_work_ref(self.node_root, text)`;
  never raises. `external_blocker_state` uses it for resolution, keeping its
  reason strings.
- `_blocker_target` override: base answer, else `_qualified_target` for an
  external entry containing `/`; a result whose store is this folder maps to
  `self`.
- `_store_key()` override: `(st_dev, st_ino)` of `self.root.stat()`, falling
  back to the resolved path string if `stat` fails.
- `create_work`: after `_unique_slug`, before any write, `_check_new_blocker`
  for each `(ref, entry)`.
- Remove the `xfail` marks. **Proves** criteria 1-10.

## Task 4 — Documentation Sync

- `docs/changelogs/upcoming/<slug>.md` [Any-Code-Change]: Fixed.
- `docs/release-notes/upcoming/<slug>.md` [Public-API]: one Fixes entry.
- `docs/guide/work.md` [Guide-Topic-Change]: the `--blocked-by
  other-node/its-slug` comment (`~284`) gains "a cycle through other projects
  is refused as one within this project is".
- `docs/capabilities/work/manage-blocking-relations/description.md` and the
  item's `capabilities.yaml` (`changed:`).
- `skills/work/SKILL.md` [Skill-Driven-Component]: checked for a statement of
  what the cycle guard covers; updated only if it states the local-only rule.
- README, jira guide, configure references: not triggered (no CLI surface,
  tracker or configuration change) — confirmed by grep for "cycle".

## Task 5 — Full suite

Bare `pytest` from the worktree root, as CI runs it. **Proves** criterion 11.

## Verification

- By hand in a scratch graph: the refusal message for the CLI cases in 1 and 6,
  read as a user would see it, and the item files unchanged afterwards.
- `tcw serve` in the scratch root: `PATCH` making the cycle of criterion 1
  answers an error and writes nothing.
