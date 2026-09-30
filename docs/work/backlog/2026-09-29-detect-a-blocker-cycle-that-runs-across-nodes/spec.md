# Spec — Detect a blocker cycle that runs across nodes

## Capability changes

- **changed:** `work/manage-blocking-relations` — the cycle guard covers cycles
  that run through items in other connected projects, not only this one.

## Problem

Every blocker write is checked by one rule, `WorkStore._check_new_blocker`
(`tcw/store/base.py:4113-4120`): a self-block, or a cycle, found by
`_reaches` (`base.py:4091-4111`). `_reaches` expands only entries stored as
`{"slug": …}` (`base.py:4110`). A blocker naming an item in another node is
stored as `{"external": "<project-id>/<slug>"}` (`_entry_for`,
`base.py:4062-4066`), so the walk stops there. The same limit applies to the
`--blocks` half of `check_blocker_edits` (`base.py:4156-4157`, `"slug" in e`).

So with `x` in project `a` blocked by `b/y`, running `tcw work edit y
--blocked-by a/x` in `b` is accepted. Each now waits on the other; neither
settles (`external_blocker_state`, `tcw/store/fs.py:6064-6097`, reports each
open), and `start` needs `--force`.

All three blocker-write paths reach the same rule, so all three have the gap:
`tcw work edit --blocked-by` and `--blocks` (`tcw/work/cli.py:2587-2604`, via
`check_blocker_edits` and `add_blocker`), and `update_work`
(`fs.py:7733`), which the web app's `PATCH` uses. Creating an item with
blockers (`create_work`, `fs.py:7620`) cannot close a cycle — nothing refers
to a slug before it exists.

Sweep: the other cycle checks in the repository are the `parent` cycle guard
(`base.py:4494`), which is local by construction (a parent is always in the
same store), and the project-graph and inheritance cycle checks in
`tcw/store/fs.py` (`~365`, `~1503`), which are about projects, not items.
Nothing else follows `blocked_by`.

## Goals

1. A blocker write that would close a cycle through items in any number of
   connected projects is refused with the existing message, `<ref> → <slug>
   would create a blocking cycle`, and writes nothing.
2. Each `external` entry is followed only when it names a work item that can
   be resolved: `<project-id>/<slug>`, resolved **from the node that holds the
   entry** — the qualifier means what it meant to whoever stored it.
3. Holds for all three write paths: `--blocked-by`, `--blocks`, and
   `update_work`.

## Non-goals

- Reporting that a cycle check could not see through something (an
  unreachable project, an unreadable `state.yaml`). The next item in this run
  (`2026-09-29-see-a-blocker-cycle-that-runs-through-an-item-whose-state-yaml-cannot-be-read`)
  owns that; this item leaves an unresolvable entry exactly as today: not
  followed, write accepted.
- Detecting or repairing cycles already stored. As today, an item already in a
  cycle stays saveable, including by the edit that breaks it
  (`fs.py:7729-7730`).
- Any change to how blockers are stored, displayed or settled.

## Design

The walk moves from slugs to *(store, slug)* pairs.

- A new `WorkStore` hook, `_blocker_target(entry) -> (WorkStore, slug) | None`:
  where a stored blocker entry points, if at a work item this store can reach.
  The base answers `(self, entry["slug"])` for a slug entry and `None`
  otherwise, which is today's behavior for any store that does not override it.
- `FsWorkStore` overrides it for an `external` entry of exactly
  `<project-id>/<slug>` shape, resolving it with `resolve_qualified_work_ref`
  from its own `node_root` — the rule `external_blocker_state` already applies
  to settle the same entry. Anything that does not resolve answers `None`.
- `_reaches` walks pairs, compares them by store identity (a new
  `_store_key()`: `id(self)` in the base, the resolved store root in the
  filesystem adapter, so two opens of one store are one) and slug, and
  expands each item through *its own* store's `_blocker_target`. Stores
  opened during one walk are cached by key.
- `_check_new_blocker` and the `--blocks` half of `check_blocker_edits` go
  through `_blocker_target` instead of testing `"slug" in entry`.

Litmus test: "could a non-filesystem store implement this?" Yes — a tracker
store resolves a qualified reference to another project's issue the same way.
The hook is in the model; only the resolution of `<project-id>/<slug>` is the
filesystem adapter's.

## Acceptance criteria

In a scratch graph: root `r` with children `a`, `b`, `c`, each keeping a board.

1. `x` in `a` is blocked by `b/y`. In `b`, `tcw work edit y --blocked-by a/x`
   exits non-zero with `would create a blocking cycle`, and `y`'s `state.yaml`
   is byte-for-byte unchanged.
2. Three nodes: `a/x` blocked by `b/y`, `b/y` blocked by `c/z`; `tcw work edit
   z --blocked-by a/x` in `c` is refused the same way.
3. Edited from another node: `tcw work edit b/y --blocked-by a/x`, run in `a`,
   is refused as in 1.
4. `--blocks`: `a/x2` is blocked by `b/y`, `b/y` by `a/x`; in `a`, `tcw work
   edit x2 --blocks x` is refused, and neither `x` nor `x2` changes.
5. `update_work`: the same edit as 1, made with `FsWorkStore.update_work(y,
   blockers=["a/x"])`, raises `would create a blocking cycle`.
6. No false refusals: a cross-node blocker with no cycle is accepted; an
   `external` blocker naming an unknown project, a missing slug, or free text
   (`vendor/legal review`) is accepted as today.
7. The existing blocker tests pass unchanged, and the full suite passes as CI
   runs it (bare `pytest`).

## Risks

- **Cost.** Each cross-node edge opens another store and resolves a registry.
  Only blocker writes walk, and the cache bounds opens to one per store.
- **A walk that never ends.** Pairs are marked seen, as slugs are today, so a
  stored cycle does not loop.
- **Resolution raising.** `resolve_qualified_work_ref` is wrapped as
  `_local_forms` wraps it (`fs.py:6056-6059`): a failure is "not followed".
