# Outcome — tcw validate reports a work store on a node that keeps no board

## What shipped

`_components_to_check` appended `"work"` when the store failed to open and
either `docs/work` existed *or* `tcw-config.yaml` existed. The second disjunct is
true of every node, so a node that keeps no board — a repository root registered
purely so its packages can reach each other — was checked anyway and reported its
default `docs/work` as a missing directory.

The fallback's intent is kept unchanged: a node that *claims* a work store and
cannot open one must say why rather than being silently skipped. What changed is
the test for "claims one". `_claims_work` reads the config and answers yes for a
`work.path` or a `work.repository`; a `work:` section carrying only tags or
documentation entries is not a claim about where a store is, and a config too
broken to parse answers no — the graph check reports that long before this, and
answering yes would bury it behind a second, worse message.

## Tests

Three new tests in `tests/test_validate.py`, over a `_bare_node` fixture (`init`
cannot produce one: an empty component list means "the usual three"):

- a node with no components validates clean — fails before the change;
- a node declaring `work.path: nowhere` still reports it — passes before and
  after, which is the half a narrowing fix can silently lose;
- a node whose `work:` section carries only tags validates clean — fails before.

```
$ python -m pytest -q -p no:randomly tests/
5 failed, 2343 passed in 352.99s (0:05:52)
```

Four environmental (three `chmod` tests that cannot fail as root, one wheel
build). The fifth, `test_generate_hook.py::test_a_grandchild_does_not_survive_the_timeout`,
is a timing-sensitive test that passes on its own and did not appear in the two
preceding full runs of this branch.

### Against the real workspace

The defect was found by running `tcw validate` in `proposit-app`, whose root node
`proposit-app-repo` is exactly this shape. Before: one problem, naming
`docs/work` under a repository that has never had one. After: `validate OK`, with
the three package nodes still `validate OK` individually.

## Autonomous decisions

Codex is not installed in this container; no advisor was consulted. The finding
came from running the tool against the real repositories rather than from a
review, and the fix follows from the config the feature itself introduced.

1. **What counts as claiming a board.** Decided alone: a `path` or a
   `repository`. Tags and documentation entries live under `work:` too and say
   nothing about location — treating the section's mere presence as a claim would
   have reintroduced the same over-reach one level down.

## Notes

Pre-existing on `main` and harmless there: before this work there was no reason
to register a node that keeps no board. The routing node is what turns it into a
defect, which is why it belongs with this work rather than after it.
