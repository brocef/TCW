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

The blocker-write paths: `tcw work edit --blocked-by` and `--blocks`
(`tcw/work/cli.py:2587-2604`, via `check_blocker_edits` and `add_blocker`), and
`update_work` (`fs.py:7733`), which the web app's `PATCH` uses
(`tcw/serve/__init__.py:1266`), all reach `_check_new_blocker` and share the gap.
`create_work` (`fs.py:7586-7593`), used by `tcw work new --blocked-by`
(`cli.py:786`) and the web app's `POST` (`serve/__init__.py:969`), checks
nothing at all — and it *can* close a cycle: a blocker naming a slug that does
not exist yet is accepted as an `external` entry, slugs are predictable (date
plus title), so `b/y` may already wait on `a/<future-slug>` when that item is
created blocked by `b/y`. The same holds inside one node for a dangling
bare-slug `external` entry, which the base store already settles against a
local item (`external_blocker_state`, `base.py:4263-4283`) but the cycle walk
never follows.

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
3. Holds for every write path: `--blocked-by`, `--blocks`, `update_work`
   (web `PATCH`), and `create_work` (`tcw work new --blocked-by`, web `POST`).
4. The walk follows exactly the entries that can keep an item blocked — the
   ones `external_blocker_state` settles against an item — and no others.

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
  where a stored blocker entry points. The base answers `(self, slug)` for a
  slug entry, and for an `external` entry shaped like a slug
  (`[a-z0-9][a-z0-9-]*`) whether or not that item exists yet — the base
  `external_blocker_state` settles such an entry against the item of that name
  once there is one, so an entry naming a future slug is a real edge (criterion
  6). A name that matches no item is a dead end for the walk. Anything else is
  `None`. *(Corrected during implementation: the first wording required the
  item to exist, which criterion 6 contradicts.)*
- `FsWorkStore` extends it for an `external` entry of exactly
  `<project-id>/<slug>` shape. One private helper does the shape check and the
  `resolve_qualified_work_ref(self.node_root, …)` call, and both
  `_blocker_target` and `external_blocker_state` use it, so the cycle walk and
  the settling rule cannot drift apart. The entry is resolved from the node
  that **holds** it, as settling already does.
- `_reaches` walks pairs and compares them by store identity and slug. Store
  identity is a new `_store_key()`: `id(self)` in the base; in the filesystem
  adapter, the store root's folder identity (device and inode, as
  `_same_folder` compares with `samefile`), so two opens of one folder —
  including spellings that differ only in letter case — are one store. Each
  item is expanded through *its own* store's `_blocker_target`. Stores met
  during one walk are kept by key, first open wins.
- Anything that fails while expanding a pair — resolving it, or reading the
  item (an interrupted claim, an ambiguous slug), in this store or another —
  means that pair is not followed. The state of an item the edit does not name
  never makes the edit fail. *(Widened from "another store" after code review:
  otherwise `tcw work new` began failing on an unrelated local claim.)*
- `_check_new_blocker` and the `--blocks` half of `check_blocker_edits` go
  through `_blocker_target` instead of testing `"slug" in entry`.
- `create_work` checks each new blocker with `_check_new_blocker` once the slug
  is known and before anything is written. A qualified reference resolves to its
  store whether or not the slug exists yet (`fs.py:606-616`), so a waiting entry
  `a/<new-slug>` elsewhere is recognised as the new item.

**Known limit.** Two nodes whose `work.path` names one folder are one store, but
each would resolve a qualified entry from its own graph. The walk uses the node
that first opened the store. In a valid graph both nodes see the same projects,
so this only differs when the two nodes' graphs differ, which nothing in this
repository sets up.

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
5. `update_work`: the same edit as 1, made on `b`'s `FsWorkStore` with
   `update_work(y, blockers=["a/x"])`, raises `ValueError` matching `would
   create a blocking cycle`. It stands in for the web app's `PATCH`, which
   calls it.
6. `create_work`: `y` in `b` is blocked by `a/<slug>` for a slug `a` does not
   hold yet; `tcw work new "<title>" --blocked-by b/y` in `a`, where the title
   and today's date produce exactly that slug, is refused and creates nothing.
   The same inside one node, with a dangling bare-slug `external` entry.
7. No false refusals: a cross-node blocker with no cycle is accepted; an
   `external` blocker naming an unknown project (`zz/x`), a missing slug in a
   known project (`b/nosuch`), or free text (`vendor/legal review`) is accepted
   as today.
8. A stored cycle does not trap edits: with a cross-node cycle already stored
   (written directly to `state.yaml`), an unrelated blocker edit on one of its
   items finishes and is accepted, and the edit that removes a cycle edge is
   accepted.
9. One store, two spellings: with `b`'s board reached once as `pb` and once
   through a path differing only in letter case (on a case-insensitive disk;
   skipped elsewhere), the cycle of criterion 1 is still refused.
10. Another node's broken state does not fail an edit: with `b/y` mid-claim
    (an interrupted `start`), adding `b/y` as a blocker of `a/x` succeeds.
11. The existing blocker tests pass unchanged, and the full suite passes as CI
    runs it (bare `pytest`).

## Risks

- **Cost.** Each cross-node edge opens another store and resolves a registry.
  Only blocker writes walk.
- **A walk that never ends.** Pairs are marked seen, as slugs are today, so a
  stored cycle does not loop.
- **Resolution raising.** `resolve_qualified_work_ref` is wrapped as
  `_local_forms` wraps it (`fs.py:6056-6059`): a failure is "not followed".

## Notes

- Reviewed before planning by an Opus advisor (Codex was unavailable: usage
  limit). Accepted: follow what `external_blocker_state` settles, through one
  shared helper; compare stores by folder identity, not path text; check
  `create_work`, which can close a cycle; a failure in another store means
  "not followed"; sharper criteria 5-10. The two-nodes-one-folder case is
  recorded as a known limit rather than solved.
