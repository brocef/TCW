# Spec — Refuse a blocker that names its own item by qualified reference, and settle status-path blockers

## Capability changes

None.

## Reproduction

Scratch node `pa` with items `alpha` and `beta` (released CLI):

- `tcw work edit alpha --blocked-by pa/alpha` → "edited"; `state.yaml` holds
  `external: pa/2026-09-29-alpha`; the board shows alpha blocked by itself.
  Should refuse: "an item cannot block itself".
- `tcw work edit beta --blocked-by backlog/alpha` → stored as
  `external: backlog/2026-09-29-alpha`. Should be stored as `slug: …alpha`.

## Problem

`WorkStore._entry_for` (`tcw/store/base.py:3916`) records `{slug}` only when the
normalized ref is a bare slug this store holds or once held; anything else is
`{external}`. `_normalize_ref` (base.py:3903) strips only an `external:` label.
`_check_new_blocker` (base.py:3956) and `_reaches` compare `slug` entries only,
so an own-qualified or status-path ref escapes both checks. At read time
`FsWorkStore.external_blocker_state` (`tcw/store/fs.py:5863`) resolves
`<project-id>/<slug>` through the graph — own id included — so a self-reference
is settled against the item itself and blocks forever; a `<status>/<slug>`
qualifier is explicitly returned as unresolved text (fs.py:5878).

**Sibling sweep, repo-wide** (`grep -n "_entry_for\|_normalize_ref" tcw/`): every
blocker write — `edit --blocked-by`, `--blocks`, `new --blocked-by`, the web
app's blockers — goes through `_entry_for` and `_check_new_blocker`; one fix
there covers them all. Existing entries already stored as such text are not
rewritten (non-goal); `external_blocker_state` keeps settling them as today.

## Goals

1. A blocker ref qualified with this node's own project id is recorded as the
   bare local slug when that item exists here (live or tombstoned).
2. A blocker ref of the form `<status>/<slug>`, `<status>` one of the work
   statuses, is recorded as the bare slug when that item exists here.
3. Both then go through the existing self-block and cycle checks.

## Non-goals

- Detecting a cycle across nodes (filed as a follow-up).
- Rewriting blocker entries already stored as external text.
- A full filesystem path (what `tcw work path` prints) as a blocker.

## Design

- Base store: `_normalize_ref` also strips a leading `<status>/` when the
  remainder is a single segment and `<status>` is in `WORK_STATUSES` — status
  names are part of the model, so any store can do this.
- `_entry_for` asks a new overridable `_local_slug(ref) -> str | None` for the
  local item a qualified ref names; the base answer is `None`. `FsWorkStore`
  answers through `resolve_qualified_work_ref`: when it resolves to this store
  (same root), the bare slug.

## Abstraction litmus test

`_local_slug` is "does this reference, qualified by project, name an item in
this store?" — any store that knows its own project identity can answer it, so
it is a store method; the FS adapter implements it through the node graph. The
status-prefix normalization is pure model vocabulary.

## Acceptance criteria

1. In node `pa`, `edit alpha --blocked-by pa/alpha` exits 1 with "an item cannot
   block itself" and records nothing.
2. `edit beta --blocked-by pa/alpha` records `slug: <alpha>`.
3. `edit beta --blocked-by backlog/alpha` records `slug: <alpha>`; with alpha
   completed and tombstoned, `completed/alpha` does too.
4. `edit alpha --blocked-by beta` then `edit beta --blocked-by pa/alpha` is
   refused as a cycle.
5. `vendor/legal-review` and `other-node/x` (a project not this one) are still
   recorded as external text.
6. The full test suite passes.

## Risks

- A node whose id equals a status name (`active`) would see `active/<slug>`
  read as a status path. Both readings name a local item, so the result is the
  same.
