# Spec — Match an epic's children by the epic's node as well as its slug

## Capability changes

None. This changes how an existing field is written and matched; it adds no
capability.

## Reproduction

1. Set up two nodes, `root` with a child node `kid`. Each node holds an epic
   with the same slug: same date and same title, so the slug
   `2026-01-01-epic` is identical in both.
2. `kid` holds an open item with `initiative: 2026-01-01-epic`. It was meant
   for `kid`'s own epic.
3. `root`'s epic has one resolved slice.

`FsWorkStore.open(root).initiative_children("2026-01-01-epic")` includes
`kid`'s item, so `root`'s epic refuses to complete. The ready-to-close hint and
`reconcile` count that item too.

A second path to the same failure: `tcw work delegate kid "Slice" --initiative
2026-01-01-epic` from `root` writes that bare slug into `kid`'s inbox, and
`kid` resolves it to its own epic.

## Problem

`initiative` holds only a slug, and a slug is unique only within one node.

- **Matching down.** `FsWorkStore.initiative_slices` (tcw/store/fs.py:6219)
  and `_graveyard_initiative` (fs.py:6201) count any item or record in this
  node, or in any node below it, whose value equals the slug.
- **Matching up.** `initiative_epic` (fs.py:6172), used by the start gate,
  takes the nearest node at or above the item that holds the slug.
- **Indentation in the list.** The list view (`_render_descendant_boards`,
  tcw/work/cli.py:1025) has a third, similar rule of its own.

The two directions can disagree: an item can start under one epic and be
counted toward another. And no rule based only on slugs can express the case
where a request is delegated into a node that already holds an epic with the
same slug.

## Goals

The user chose option A on 2026-09-29: record the epic's node with the
reference.

1. **Format.** `initiative` is either `<slug>` or `<project-id>/<slug>`, the
   same shape cross-node blockers and `tcw://` references already use.
   Parsing and project lookup go through `resolve_qualified_work_ref`.
2. **Writers record the node whenever the epic is elsewhere.**
   - **Plain `new` and `edit`.** `create_work`, `update_work`, inbox accept,
     `tracker import` and the web app all store through
     `qualify_initiative`. A bare slug that resolves to an epic on this board
     stays bare. One that resolves to another node is stored as
     `<that-id>/<slug>`. One that resolves nowhere is stored unchanged, as
     happens today.
   - **`delegate`.** It always writes the qualified form, resolving from the
     sending node (at or above it). A bare slug that resolves nowhere is
     refused, and the refusal says to pass `<project-id>/<slug>`.
   - **`escalate`.** It qualifies relative to the receiving parent.
   - **Graveyard records** copy the item's value, so they inherit the
     qualified form.
3. **One rule for matching, in both directions.** The rule is
   `_initiative_holder(value)`:
   - a qualified value names that project's board;
   - a bare value names the nearest board, at or above the item's node, that
     holds a live item with that slug.

   `initiative_epic`, `initiative_slices`, `resolved_initiative_children` and
   the list's indentation all use it. An item is a slice of epic E in node N
   exactly when its value resolves to (N, E).
4. **Amended at review — only here or above.** A qualified value names an
   epic only in the item's own project or in one above it, because that is
   as far as an epic's walk down can reach.
   - Writers refuse any other value.
   - The holder rule reads one written by hand as naming nothing, so the
     start gate refuses the item rather than letting it start as a slice its
     epic never counts.
   - `delegate` also checks a qualified value, from the child's side.
5. **Amended at review — a record also holds a slug.** A graveyard record
   counts as holding a slug for the bare rule. Without that, a bare value
   written for a node's own epic would fall through to an epic of the same
   name further up once the resolved epic's folder is missing, as it is on
   every other clone.
6. **No migration.** Existing bare values keep their current meaning under
   the nearest-holder rule. Only the case this item reports, a node holding
   its own same-slug epic, changes answer: that node's own epic now wins.

## Non-goals

- **Rewriting stored bare values.**
- **The legacy hazard left by a dropped epic.** If a same-slug descendant
  epic is later *dropped* (which leaves no record), its children with bare
  values fall through to the ancestor's epic. A resolved epic keeps its
  children through its graveyard record (Goal 5).
- **Delegating the child's own epic** now needs `<child-id>/<slug>`, since a
  bare slug is resolved from the sending node.
- **Extra ways a read can raise.** Resolving can now call `get`, which can
  raise `MultipleMatch` or report an interrupted claim, and the registry
  check on the list and completion paths. Left for a separate change.
- **Type checks.** Checking that the item a reference resolves to is an epic.
  `initiative_epic` does not check this today.
- **The `--initiative` flag.** It accepts both forms; no new flag.

## Design

- **The abstract store** gains `qualify_initiative(value) -> str`. By default
  it returns the value unchanged.
- **The filesystem store:**
  - `_initiative_holder(value) -> (FsWorkStore, slug) | None` handles the
    qualified form through `resolve_qualified_work_ref`, and the bare form
    through the existing upward walk (moved here from `initiative_epic`).
  - `initiative_epic` becomes a thin wrapper around it.
  - `initiative_slices` and `_graveyard_initiative` first skip, cheaply, any
    value that is not the slug and does not end in `/<slug>`. They resolve the
    rest, memoizing each (store, value) pair within one call, and keep a match
    when the holder's board is this store's board.
  - `_graveyard_initiative` returns `(slug, value)` pairs, so its caller can
    do the resolving.
- **The list view** resolves through the item's store, then looks the
  resolved key up among the visible entries. As before, an owner that is not
  an epic is ignored.
- **The `tracker import` re-run check** (cli.py:2789) compares the qualified
  forms.
- **The resolved-item check** in `update_work` (fs.py:7572) qualifies before
  comparing.

## Abstraction litmus test

A tracker can qualify a reference by project just as well, so
`qualify_initiative` belongs on the abstract store, with the identity
function as its default. Holder resolution depends on the project graph,
which is a filesystem concern, so it stays in the filesystem adapter, as
`resolve_qualified_work_ref` already does.

## Acceptance criteria

1. **The reproduction.** `root`'s epic does not count `kid`'s item, and
   completes. `kid`'s epic does count it.
2. **The same, with a record.** It also holds for a `kid` graveyard record
   whose `initiative` is the bare slug.
3. **Delegation.** `delegate` from `root`, with `--initiative
   2026-01-01-epic`, writes `initiative: root/2026-01-01-epic`. After
   `inbox accept` in `kid`, the item counts toward `root`'s epic and not
   toward `kid`'s. It also resolves through `initiative_epic`, so the start
   gate reads `root`'s epic. Delegating a slug held nowhere is refused.
4. **Old data still works.** A bare-valued slice in `kid`, where `kid` holds
   no epic with that slug, still counts toward `root`'s epic.
5. **`new` in a child node.** `tcw work new --initiative <root-epic>` in `kid`
   stores `root/<slug>`. Run in the epic's own node, it stores the bare slug.
6. **`tcw work list`** from `root` nests a qualified slice in `kid` under
   `root`'s epic.
7. **The full suite passes.**

## Risks

- **Scripts that read `initiative` see a new spelling.** An external script
  comparing the value to a bare slug now sees `<id>/<slug>` for cross-node
  slices. The `show` output and the rollup print the value as stored.
- **Cost.** Resolving a bare value walks up the registry. The cheap slug
  check limits this to candidate items, and each value is resolved once per
  call.
