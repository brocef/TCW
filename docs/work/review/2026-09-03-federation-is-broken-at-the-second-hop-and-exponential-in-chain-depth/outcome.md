# Outcome — Federation is broken at the second hop and exponential in chain depth

## What shipped

All four findings resolve to one change: **the store built while resolving an
`extends` edge is the store that gets used.**

`_extended_component_roots` opened the sibling's store — the whole point of the
preceding item, since the ladder is what knows about a moved `<component>.path`
or a provisioned checkout — read `.root` off it, threw it away, and let the
caller reconstruct it as `FsCapabilitiesStore(ext, _seen=seen)`. That
reconstruction had no `node_root`, so `FsTreeStore.__init__` fell back to
`root.parent.parent`: correct for `docs/<component>` and nothing else. It also
dropped `_seen_nodes`, resetting the node-level cycle guard every hop. The
function is now `_extended_component_stores` and returns the stores.

1. **The hop past a moved tree works.** A sibling with `capabilities.path: caps`
   got a node root two levels above its own repo, so its own `extends` was
   resolved against the wrong project graph and reported the next project as
   "not reachable through connected-projects". The one-hop case the previous
   item fixed worked; the transitive case it enabled did not.

2. **Federation is linear again.** Each edge built the sibling's entire subtree
   twice — once to read `.root`, once in the caller. Measured on a linear chain,
   before → after: depth 5, 0.24 s → 0.03 s; depth 8, 1.95 s → 0.06 s; depth 11,
   15.7 s → 0.10 s; depth 14, unmeasured → 0.19 s.

3. **A sibling's own error is quoted.** Every generic `ValueError` from opening
   the sibling was rewritten as `project '<id>' has no <component> component`,
   with `from None` — so a legacy `extends` map, a failed `require_valid()` and
   a self-extend all told the reader to create a store that already existed.
   `StoreNotProvisioned`, `StoreDeclarationError` and `ValueError` now each
   carry the sibling's own words behind a `project '<id>':` prefix. The one case
   that really is "no component" — the ladder's rule 4 resolving to a path that
   is simply not there — keeps that message.

4. **An `extends` cycle is reported.** Three comments claimed `check()` reported
   it; `FsProjectRegistry.check()` only ever knew about `connected-projects`,
   which is a different graph — two projects can be legitimately connected and
   still extend each other in a loop. The edge that closes a cycle is now
   recorded by the store that truncates it, and the `_FederationCycles` mixin
   gathers the record up the tree, so `check()` reports the cycle from wherever
   it is run rather than only from the deepest store, which nobody is holding.
   The two hand-rolled `_cycles` walkers this replaces are deleted; they
   recomputed the same resolution with `taxonomy_root.parent.parent` as the node
   root — the same wrong assumption, in the code whose job was to catch it.

The cycle guard sits on **project node roots**, checked before any store is
opened, because resolving an edge now opens a store and opening a store resolves
its own `extends`: a guard placed after the open recurses forever. Project
identity is known before any store is touched, which is what makes the guard
possible — and a cycle in `extends` is a cycle among projects, so it is also the
honest place to detect one.

## Tests

```
$ python -m pytest -q -p no:randomly tests/
6 failed, 2329 passed in 349.45s (0:05:49)
```

Four environmental (three `chmod` tests that cannot fail as root, one wheel
build that this container's patched setuptools refuses); two were the sibling
item's tests against a partially reverted tree and pass now.

New tests, each confirmed to fail against the reconstruct-from-root shape before
being kept:

- `tests/test_taxonomy.py::test_transitive_extends_crosses_a_second_hop_through_a_moved_tree`
  — the second hop, where transitive federation is the promise. `bravo` moves
  its tree to `ledger`; `charlie`'s terms must still reach `alpha`, with the
  right origins and the right validation resources.
- `tests/test_capabilities_federation.py::test_a_moved_sibling_that_extends_further_still_resolves`
  — the same shape for capabilities, which flattens one hop by design, so what
  it asserts is that the moved sibling resolves *at all* rather than raising
  `no tcw-config.yaml here` from a node root above its repo.
- `…::test_a_broken_sibling_reports_its_own_error` — a legacy `extends` map in
  the sibling, asserting its words survive and the "has no capabilities
  component" wording does not appear.
- `…::test_a_cycle_is_reported_from_the_top_of_the_chain` — `check()` run on the
  store a person is actually holding.
- `…::test_federation_stays_linear_in_chain_depth` — a fourteen-link chain under
  a generous bound. What it guards is the shape, not the number.

## Autonomous decisions

Codex is unavailable in this container, so the skill's two-advisor rule could not
be met on this item; no external consult was made. Both checkpoints below were
decided alone and are recorded so a reader does not assume otherwise.

1. **Where the cycle guard belongs.** Moving it from store roots to project node
   roots was forced: the first attempt kept it on store roots and recursed
   infinitely, because the guard could not run until the store it was guarding
   had been opened. Node identity is available earlier, and it is the graph the
   cycle actually lives in.
2. **What the capabilities second-hop test should assert.** The first draft
   asserted `n1/n2/deep/thing` reached the top of a capabilities chain and
   failed — correctly: capabilities federation flattens one hop by design, while
   taxonomy flattens transitively via `_inherited_stores`. Rather than change
   the behaviour to match the test, the second-hop assertion moved to the
   taxonomy suite where transitivity is the promise, and the capabilities test
   was narrowed to what that component does guarantee. A test that had to assert
   the difference is what surfaced it.

## Notes

The exponential blowup and the broken second hop were the same line, and so was
the misleading error: resolving something and then discarding it forces the
caller to reconstruct from whatever fragment survived. The deleted `_cycles`
walkers are the third copy of the same reconstruction, each with the
`parent.parent` assumption written out by hand.
