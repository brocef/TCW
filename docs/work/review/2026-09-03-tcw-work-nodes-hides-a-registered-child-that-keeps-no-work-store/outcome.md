# Outcome — `tcw work nodes` hides a registered child that keeps no work store

## What shipped

Two tasks, one commit.

`registered_children(root)` beside `registered_parent`, returning the registry's
direct children unfiltered. `_nodes` lists all of them, marking each whose board
is unusable here — and distinguishing the two reasons, which the plan did not
ask for. See Corrections.

Documentation: the routing-node changelog entry gains the children half; the
`work/inspect-the-node-topology` capability body drops "is also omitted" for the
listing and says which entries mean "reachable by cross-node commands".

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2311 passed in 347.67s (0:05:47)
```

The established environmental failures.

One new test in `tests/test_multiproject.py` over the routing-node fixture, and
one existing test in `tests/test_store_provisioning.py` updated — see
Corrections.

### The real verification

`tcw work nodes` at the orchestration root of the hierarchical workspace:

```
node:   proposit-app
parent: (none — root)
children:
  proposit-core  (no work store)
  proposit-app-repo  (no work store)
```

Before: `children: (none — leaf)`.

## Corrections

- **The marker distinguishes two situations, which the plan treated as one.**
  `test_a_parent_still_lists_its_topology_when_a_child_is_unprovisioned` asserted
  that an unprovisioned child "says so by absence" — the contract this item calls
  a defect — and updating it forced the question of what the marker should say. A
  child with a declared-but-unobtained store is not a child with no store: only
  the first is something the reader can act on. So `(no work store)` and
  `(work store not provisioned here)` are separate, and that test now asserts the
  second.
- **`tcw work nodes` refuses at a routing node itself**, because it is a work
  subcommand and the node has no work store. Existing behaviour, out of scope,
  and recorded in the test rather than asserted away — but it means the topology
  of a routing node can only be seen from its parent or its children.

## Notes

The updated test is the only pre-existing assertion this whole run has reversed
rather than extended. Its stated rationale was that omission communicates the
absence; the reproduction here is a case where omission communicates something
false instead.
