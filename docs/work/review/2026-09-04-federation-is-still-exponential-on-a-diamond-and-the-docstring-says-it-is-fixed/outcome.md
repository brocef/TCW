# Outcome — Federation is still exponential on a diamond, and the docstring says it is fixed

## What shipped

**`_FederationWalk`** replaces the bare `_seen_nodes` set threaded through the
`extends` walk. It carries two things, and the reason they cannot be one set is
that they have different lifetimes:

- `seen` — the projects on *this* path, copied at every descent. It is what
  detects a cycle, and it has to be per-path: a project is a back edge only
  relative to the route that reached it.
- `built` — shared by the whole walk, keyed by `(component, node root)`. It is
  what stops a shared subtree being rebuilt once per route.

The previous shape had only the first, so it terminated a cycle and memoised
nothing. Any DAG where two extended projects reach a common ancestor rebuilt that
whole subtree per route, and each rebuild is *more* expensive than before this
branch, because it now goes through `open()` → `resolve_store` →
`FsProjectRegistry.open(...).require_valid()` — a full graph walk per
construction. Measured on `levels` pairs of nodes, each extending both nodes of
the next:

| levels | before | after |
| ------ | ------ | ----- |
| 4      | 15     | 7     |
| 6      | 63     | 11    |
| 8      | 255    | 15    |
| 10     | 1023 (12.1 s) | 19 |
| 12     | —      | 23    |

Exactly 2^levels − 1 before, 2·levels − 1 after.

**Only a subtree that truncated nothing is cached.** A store built with a cycle
truncated in it is correct for the path that built it and wrong for any other,
since a back edge is a property of the route. A cycle-free subtree is
path-independent and can be reused anywhere — and that is the common case, which
is where the cost was. The reasoning for why this is sufficient is worth stating:
if a cached store's subtree reaches a project that is *also* above it on a later
path, then that project's subtree reaches the store, and building it would have
truncated — so it would not have been cached.

`_federation_cycles()` memoises its answer, because the walk now asks it of every
store it builds and recomputing it there would trade one quadratic for another.
The `extends` tree is fixed once construction returns, so the memo cannot go
stale.

**The docstring claiming this was already fixed is corrected.** The earlier work
removed a *double* build per edge; it did not memoise, and saying so left the
next reader with no reason to look.

**The dead `_seen` parameter is gone** from both tree-store constructors. Nothing
had passed it since recursion moved into `_extended_component_stores`, so `seen`
was always `{self.root}` and the filter it fed could only fire for a self-extend
the identity check already refuses by project id. Removing it also removed the
second filtering of `built`, which is now assigned to `self.extends` directly.

## Tests

`tests/test_capabilities_federation.py::test_a_shared_subtree_is_built_once`
counts constructions rather than seconds, because the count is the property and
the seconds are the machine. It asserts a linear bound on an eight-level diamond;
against the previous code it counts 255.

The `_diamond` helper routes every `connected-projects` relation through one hub,
because a node may declare only one parent — the `extends` edges are what form
the DAG. The first draft declared two parents per node and was refused by the
config parser, which is a useful reminder that the connected graph and the
federation graph are not the same graph.

```
$ python -m pytest -q -p no:randomly tests/
5 failed, 2364 passed in 357.14s (0:05:57)
```

Four environmental. The fifth,
`test_an_unusable_local_layout_falls_through_to_the_provisioned_store`, belongs
to a sibling item still under advisement and is expected to be red until that
one settles.

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted on this item.

1. **Whether to make the cycle guard global instead of per-path.** No. A global
   guard would report a cycle for a diamond, which is not one. The two states are
   genuinely different and the fix is to carry both, not to merge them.
2. **Whether to cache every built store or only cycle-free ones.** Only
   cycle-free. Caching a truncated subtree makes the cached answer depend on
   which route happened to build it first — a correctness bug traded for a
   performance one, in the rarer case.
3. **Whether to bundle the walk state in an object or thread a second keyword.**
   An object. `seen` is copied per branch and `built` is shared, and a
   `descend()` that does exactly that is one place where the distinction is
   written down, rather than twelve call sites that each have to get it right.

## Notes

The dead `_seen` parameter is the same class of thing this branch has been fixing
all along: a mechanism that stopped being reachable when the recursion moved, and
that nobody removed, so the code read as if two guards were in force when only
one was.
