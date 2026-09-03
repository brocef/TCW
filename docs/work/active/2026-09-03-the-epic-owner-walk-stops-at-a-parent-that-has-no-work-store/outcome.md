# Outcome — The epic owner walk stops at a parent that has no work store

## What shipped

Six planned tasks, in three commits — the fixture landed with the code it
proves rather than as its own commit, see Corrections.

1-3. **`nearest_work_ancestor` and the walks.** A registry `ancestors()`
   traversal that no filter can truncate, used by `FsWorkStore.initiative_epic`,
   the descendant board's ownership walk (`tcw/work/cli.py`), and `escalate`.
   `initiative_children` moved from `child_nodes` to `descendant_nodes`, so the
   downward direction crosses a routing node exactly as the registry's own
   descendant walk already did. `parent_node` is unchanged and still answers the
   direct question.
4-5. **`registered_parent`** exposes the direct parent without the store filter.
   `tcw work nodes` prints `parent: <id> (no work store)`, and `escalate` refuses
   with "no registered ancestor keeps a work store" instead of claiming the node
   is the root.
6. **Documentation:** README, release notes, changelog, the cross-node skill
   reference, and the `work/inspect-the-node-topology` and
   `work/escalate-a-request-to-the-parent-node` capability bodies.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2271 passed in 350.06s (0:05:50)
```

Four environmental failures as established previously, plus
`test_a_grandchild_does_not_survive_the_timeout`, which is timing-sensitive
under load and passes on a quiet run — it also fails at `v1.2.3`.

Eight new tests in `tests/test_multiproject.py`, built on a `_routing_graph`
fixture: A → B → C where B is registered, reciprocal, `tcw validate`-clean, and
keeps no work store.

- the graph is legal today (so the defect is behavioral, not a rejected config);
- an epic in A resolves from a slice in C;
- `initiative_children` in A finds the slice in C, asserted by count as well as
  presence so a duplicate from the wider walk would fail;
- `escalate` from C lands in A's inbox;
- an ancestry with no board at all refuses with the new wording and *not* with
  "this is the root";
- `tcw work nodes` distinguishes the two cases.

## Corrections

- **The fixture is not its own commit.** Task 1 called for writing it first with
  assertions against the broken behavior, then inverting them in task 2. The
  fixture is in the same commit as the fix. The reproduction still happened —
  the walk was confirmed to stop at B before the change — but the plan's stated
  artifact, a commit containing a red test, does not exist. Recorded rather than
  glossed: the plan asked for something this implementation did not deliver.
- **`escalate`'s refusal needed a second message, not just a different target.**
  The plan said "refuse only when the walk finds nothing". Doing that alone would
  have kept telling a user with a registered parent that they were at the root.
- **Task 6's timing check was not run.** See Notes.

## Notes

**This ships unproven against a real graph, and that was known at planning time.**
No node in this repository or in `proposit-app` is a routing node today; every
criterion above is a fixture. The first real exercise will be the `proposit-app`
repository-root node, which is consumer-side work outside this item. The
verification section's outstanding real-world check therefore remains
outstanding, deliberately.

The plan also asked for a before/after timing of `tcw work reconcile` on this
repository's board, since `initiative_children` widened from direct children to
all descendants. It was not run: this node has no registered children at all, so
the walk it widens does not execute here and a measurement would have compared
two identical empty loops. On a graph where it does run, the widening is bounded
by the same `registry.descendants()` the board already walks for `-i`.
