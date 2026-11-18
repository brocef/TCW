# Spec — The web app's taxonomy and capabilities trees ignore a record's parent field

## Capability changes

- **changed** `tcw.capabilities/web`: its description says the Taxonomy and
  Capabilities trees nest each entry under the entry its `parent:` names,
  and under a label naming that parent when the parent is not listed.

No taxonomy terms are added or changed.

## Reproduction

1. In a project `app` whose parent project `core` has a taxonomy term
   `core.taxonomy/billing`, run
   `tcw taxonomy add Refund --parent core.taxonomy/billing`. The CLI prints
   `not nested:` and makes the folder `refund` at the top of `app`'s store,
   with `parent: core.taxonomy/billing` (behavior described in
   `docs/guide/taxonomy-and-capabilities.md:55-62`).
2. Run `tcw serve` in `app` and open the Taxonomy tab.

**What happens:** `refund` is a top-level row of the tree, beside every other
top-level term, under any scope. **What should happen:** it sits under
`billing`, which itself sits under the `core.taxonomy` label.

The same happens to an entry made with `--flat` under one of `app`'s own
terms (`tcw taxonomy add Receipt --parent invoice --flat`: shown at the top,
not under `invoice`), and to capabilities made the same ways.

## Problem

- The taxonomy and capabilities trees are built by `buildPathTree`
  (`web/client/src/model/tree.ts:7-37`), called from
  `web/client/src/ui/app.tsx:671-673` with only each record's route key. It
  places a node under the node whose path is its own path minus the last
  segment (`tree.ts:30-35`). The record's `parent` is never read.
- The server does send `parent`: `jsonable` in `tcw/serve/records.py:32-44`
  writes it, as the text of a full identifier, on every term and capability.
  `TaxonomyItem` declares it (`web/client/src/model/types.ts:217`);
  `CapabilityItem` does not declare it but carries it as a `JsonRecord`.
- Selecting a record expands its ancestors through `pathAncestors(key)`
  (`app.tsx:618`, `tree.ts:169-174`), which is path-based too, so even once
  the tree nests by `parent`, selecting a nested record from a link would
  leave its tree parent collapsed.
- Where a folder is made for `--parent`: inside the parent's folder only when
  the parent is one of this project's own (or, for a capability, an
  inherited one this project overrides at its path); at the top of the store
  otherwise, and always with `--flat`
  (`docs/guide/taxonomy-and-capabilities.md:55-62, 130-139`). So the path
  and `parent` disagree exactly in the cases the report describes.

**Sweep.** `buildPathTree` is the only tree builder for these two axes
(`grep -rn buildPathTree web/client/src`: one caller). The work tree
(`buildWorkTree`, `tree.ts:42-80`) already nests by `parent` and is out of
scope. The CLI's `tcw taxonomy list` and `tcw capabilities list` are flat
lists and show no hierarchy, so they have no counterpart defect.

## Goals

1. A taxonomy or capability record whose `parent:` names a listed record is
   shown under that record's row.
2. A record whose `parent:` names a record that is not listed is shown under
   a non-selectable label for the parent, built the way the tree already
   labels another project's entries: a `<project>.<namespace>` label, then
   one label per part of the parent's id-path (or, for one of this project's
   own records, its id-path parts alone).
3. Selecting a record (from the tree, a link or the address bar via
   navigation) expands every row above it in this hierarchy.
4. Records with no `parent:`, or whose `parent:` is already their folder's
   parent, appear exactly where they do today.

## Non-goals

- The work tree.
- Any server, store, CLI or file-format change.
- Showing the absent parent's own details; the label is not a link.

## Design

All of it is in the web client's tree model, plus one call site.

- `buildPathTree(items, keyOf, parentKeyOf?)` gains an optional third
  argument returning the **route key** of the record's declared parent, or
  `null`. A node's `path` stays what it is today, its route key's segments
  joined by `/`, so selection, expansion state saved in local storage, and
  every existing caller are unchanged.
- Placement of a record's node: when `parentKeyOf` gives a key other than
  its own, the node goes under the node at that key's path, creating
  placeholder nodes along that key's segments if it is not listed (exactly
  the placeholders the path tree already makes for folder segments with no
  record). Otherwise it goes under its folder's parent, as today.
  Placeholders go under their folder's parent.
- A cycle of `parent` links (two records naming each other) is broken the way
  `buildWorkTree` breaks one: a node not reachable from a root is put back
  under its folder's parent (or made a root), and the check repeats until
  every node is reachable. Since a folder parent's path is strictly shorter,
  this ends.
- `parent` text that is not a valid full identifier (`parseFullId` returns
  `null`) is ignored, and the record is placed by its folder.
- The parent's route key is `routeKey(parent, projectId)`, so a parent this
  project owns maps to its id-path and another project's to its full
  identifier — the same keys the tree's other nodes use.
- A new `pathTreeAncestors(nodes, path)` returns the paths of the nodes above
  the node with that path in a built tree, outermost first, or `[]` when it
  is not found. `navigateTo` uses it, on the tree built for the axis being
  navigated to, in place of `pathAncestors`.
- `CapabilityItem` gains `parent?: string | null`; `TaxonomyItem.parent`
  becomes `string | null`, which is what the server sends.

## Abstraction litmus test

No new operation. This is a display change in the web client; it reads the
`parent` field the server already sends and touches no backend or store
operation.

## Use cases

- **UC-1** (single project): a `--flat` child of one of its own terms now
  nests under that term. No cost: no configuration, no new reads.
- **UC-2, UC-3, UC-4, UC-7** (a project reading a parent's taxonomy or
  capabilities): the reported case. A child of an inherited record nests
  under it when the scope lists the parent, and under a label for it when
  the scope shows only this project.
- **UC-6** (related project not on this machine): its records are not
  listed, so a child of one nests under a label — no read is attempted.
- **S-3**: unaffected; taxonomy and capabilities are files in both modes.
- **S-9**: no file format or key changes.

Checklist: 1 — locates nothing new. 2 — changes nothing. 3 — reads only the
`parent` text already in each record; no new cross-project read. 4 — no
backend involvement. 5, 6, 7 — not applicable (no lifecycle or agent
behavior). 8 — no cost to UC-1. 9 — no format change. 10 — the unit tests
build trees with records of two projects, both listed and not.

## Acceptance criteria

1. `buildPathTree` with records `core.taxonomy/billing` and `refund` (parent
   `core.taxonomy/billing`, route key of parent `core.taxonomy/billing`)
   returns one root `core.taxonomy` whose child `core.taxonomy/billing` has
   the child `refund`. No root named `refund` exists.
2. With only `refund` listed, the result is root `core.taxonomy` (no item) →
   `core.taxonomy/billing` (no item) → `refund` (the record).
3. A local `--flat` record `receipt` with parent key `invoice`, beside
   `invoice`, is a child of `invoice`.
4. Records with no parent, or whose parent key equals their folder parent,
   produce exactly today's tree (the existing `path tree` tests pass
   unchanged).
5. Two records naming each other as parent both appear in the tree exactly
   once, and the call returns.
6. A record whose `parent` is not a valid full identifier is placed by its
   folder.
7. `pathTreeAncestors` returns `["core.taxonomy", "core.taxonomy/billing"]`
   for `refund` in the tree of criterion 1.
8. In the running app (`tcw serve`), a taxonomy term and a capability whose
   parent is another project's record appear under that parent's row (or its
   label), and opening such a record by its URL shows its row with the rows
   above it expanded.
9. The web client's unit tests, type check, lint and the built bundle check
   (`scripts/check_web_build.mjs`) pass, and the built bundle in
   `tcw/serve/dist/client` is rebuilt from the changed source.

## Risks

- **A record shown in two places, or lost.** Each record has one node, and
  the reachability pass guarantees every node is reachable once; criterion 5
  covers the cycle.
- **Saved expansion state.** Node paths are unchanged, so a saved set still
  matches; a newly nested record's new parent row is expanded on first sight
  by the existing effect (`app.tsx:710-729`).
- **Filtering.** `pruneTree` works on any tree shape, so a match under a
  re-parented row still forces its ancestors open.
