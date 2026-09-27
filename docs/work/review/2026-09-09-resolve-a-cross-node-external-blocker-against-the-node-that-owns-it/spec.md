# Spec: resolve a cross-node external blocker against the node that owns it

## Capability changes

None to the ledger: blockers that name finished work stop blocking.

## Problem

`WorkStore.unresolved_blockers` (`tcw/store/base.py`) counts every `external:`
entry as unresolved; `_ready` in `tcw/work/recursion.py` does the same
independently, keys its set by bare slug across nodes (so equal slugs in two
nodes collide), and treats a local `slug:` blocker outside the epic as not
blocking — already disagreeing with `start`. `WorkStore._entry_for` writes a ref
to a local item that is resolved and tombstoned as `external:`, which then never
resolves.

## Goals

1. `WorkStore.external_blocker_state(text)` → resolved, open, or unresolvable
   with a reason. The base default is unresolvable (a store that cannot see
   other projects keeps blocking, as today). `FsWorkStore` implements it:
   - `<project-id>/<slug>` exactly, via `resolve_qualified_work_ref` over every
     project registered in the graph (ancestors, siblings, descendants), then
     the target store's live item or tombstone; resolved when that item's
     status is resolved;
   - a bare slug that is a local tombstone (an existing stuck entry) resolves
     the same way;
   - anything else — free text, an unknown project or slug, a project declared
     but not in this checkout (reason from `qualified_work_ref_problem`), any
     error — stays unresolved and blocking.
2. `unresolved_blockers` asks it for each `external:` entry; an unresolvable
   one's message says why when a reason is known.
3. `_ready` asks each row's own node store for `unresolved_blockers(item)`, so
   `reconcile`'s Next line and `start` always agree, and rows are qualified by
   node.
4. `_entry_for` writes `slug:` for a ref to a tombstoned local item, with a note
   that the blocker is already resolved.
5. The registry and opened stores are reused within one command.

## Non-goals

- A new `work:` blocker kind (option 1): existing stuck entries would need a
  migration.
- `delegate`/`escalate` recording blockers.
- Stale references on resolved items.

## Acceptance criteria

1. The request's repro (nodes A and B; A's item blocked by
   `external: B/<slug>`): after B's item completes, `start` in A succeeds;
   before, it refuses naming the blocker.
2. `reconcile` names that item under Next once B's item is complete; with a
   slug shared by two nodes, only the right node's row is affected.
3. `external: <free text>` and `external: B/<unknown>` keep blocking; a
   reference to a declared project not in this checkout keeps blocking and
   says why.
4. `--blocked-by <tombstoned local slug>` writes `slug:` and does not block; an
   existing `external: <tombstoned local slug>` no longer blocks;
   `--unblocked-by` still removes either.
5. `list`'s blocked column agrees with `start`.
6. Full suite passes.

## Notes

- Advisors (2026-09-27) agreed on option 2 and on reuse over a new resolver.
  Opus: a store method the FS store overrides (the `initiative_children`
  pattern), not a callback; `_ready` from each row's own store. Codex: exact
  `<id>/<slug>` matching only; resolve from all reachable projects. Two points
  both left to a person, taken here with the safer defaults and recorded: an
  unreachable declared project blocks with a reason; an old bare `external:`
  naming a local tombstone resolves on read (Opus) rather than only being
  reported (Codex) — it fixes entries stuck today.
- GitHub #28 closes only after publication; the earlier reply there needs
  correcting then, with the exact text approved first.
