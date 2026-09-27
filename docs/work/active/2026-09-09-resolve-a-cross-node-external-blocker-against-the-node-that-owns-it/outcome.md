# Outcome — Resolve a cross-node external blocker against the node that owns it

## What changed

- `WorkStore.external_blocker_state(text) -> (resolved, why)` (base.py). The
  base answers the case every store can: a bare slug this store holds or once
  held (an older entry written before a tombstoned local item was recorded as
  `slug:`) — the live item wins, then the tombstone. Anything else keeps
  blocking.
- `FsWorkStore` override adds exactly `<project-id>/<slug>`, through
  `resolve_qualified_work_ref` across the registered graph; live item, then
  tombstone. A qualifier the graph does not declare is prose and keeps blocking
  with no reason; a declared but absent project keeps blocking with the reason
  from `qualified_work_ref_problem`. Never raises.
- `unresolved_blockers` uses it, so `start` (both), `complete`, `list`, the
  strict tracker check and `reconcile` agree.
- `_entry_for` records a ref to a tombstoned local item as `slug:`.
  `_without` also accepts a label copied from `list` with its reason.
- `reconcile`: `_ready` asks each row's own store and labels other nodes' rows
  `<id>/<slug>`; it had keyed bare slugs across nodes and ignored local `slug:`
  blockers outside the epic.
- Docs: `skills/work/references/cross-node-deltas.md` (step 6),
  `docs/guide/work.md`, changelog, release notes.
- Tests: `tests/test_cross_node_blockers.py` (12 tests, 17 cases). All but the
  "still blocks" cases fail on the old code; the three review tests fail on the
  first version.

## Differences from the spec

- **Goal 4's note** ("the blocker is already resolved" when `--blocked-by` names
  a tombstoned item) is not printed. The entry is recorded as `slug:` and does
  not block, which `list` shows; a note would need a new return path from the
  store for one message.
- **Goal 5's caching** is not implemented. The reviewer measured about 5 ms per
  qualified external blocker on a 7-node graph — about 0.5 s for 100 such
  blockers on one `list`. Free text costs under 0.1 ms. Add a per-command cache
  when a real board shows the cost.

## Autonomous decisions

- **Shape** — Codex and Opus: option 2, keep `external:` and resolve
  `<project-id>/<slug>` exactly; reuse `resolve_qualified_work_ref` (Opus); a
  store method overridden by the FS store, not a callback (Opus); readiness
  from each row's own store (both). Taken.
- **An unreachable declared project** keeps blocking with a reason (both
  advisors left it to a person; the safe default).
- **Old bare `external:` entries naming a finished local item** resolve on read
  (Opus) rather than only being reported by `validate` (Codex): it fixes
  entries stuck today and rewrites nothing.
- **Review, accepted**: the bare-slug case answered differently on the machine
  that still has the folder (live item now wins; test added); the prose check
  compared an error message's text and leaked a reason onto URLs and
  multi-slash text (now asks the registry; tests added); a copied `list` label
  could not be removed (accepted now; test added); `_render`'s `stores` is
  required; the bare-slug case moved to the base store (it uses only the store
  interface — the abstraction test).
- **Review, separate change**: self-blocks and cycles through a qualified ref,
  and status-path blockers — filed as
  `2026-09-27-refuse-a-blocker-that-names-its-own-item-by-qualified-ref-and-settle-status-path-blockers`.
- **Rejected**: none.
