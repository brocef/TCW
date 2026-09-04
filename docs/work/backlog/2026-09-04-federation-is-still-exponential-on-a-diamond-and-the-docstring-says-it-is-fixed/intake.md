Found by an adversarial review of the federation work, 2026-09-04. Reproduced
and measured.

`seen_nodes` is a per-*path* set, so it terminates a cycle but does not memoise a
shared node. Any DAG where two extended projects reach a common ancestor rebuilds
that whole subtree once per route. On a graph of depth N with two nodes per level,
each extending both nodes of the next level, `_extended_component_stores` is
entered exactly 2^N − 1 times:

| levels | constructions | elapsed |
| ------ | ------------- | ------- |
| 4      | 15            | 0.09 s  |
| 6      | 63            | 0.48 s  |
| 8      | 255           | 2.55 s  |
| 10     | 1023          | 12.59 s |

`_inherited_stores()` de-duplicates afterwards (18 distinct stores at depth 10),
so the results are right and the cost is not.

Each rebuild is now *more* expensive than before this work, because it goes
through `.open()` → `resolve_store` → `FsProjectRegistry.open(...).require_valid()`
— a full graph walk per construction, unconditionally, even for an empty
`extends`.

Not a regression in shape: the previous code was per-edge too. What is new is the
constant factor and a docstring that claims the problem is solved — *"it is also
what made federation exponential, since each edge built the same subtree twice"*.
The test kept for it, `test_federation_stays_linear_in_chain_depth`, measures a
*linear chain*, where the shape never appears.

Related, from the same review: `FsTaxonomyStore.__init__` and
`FsCapabilitiesStore.__init__` still take `_seen: set[Path] | None`, which no
caller passes any more — recursion now goes through `_extended_component_stores`
→ `open()`. `seen` is therefore always `{self.root}` and the
`if store.root.resolve() not in seen` filter can only fire for a self-extend the
identity check already refused.
