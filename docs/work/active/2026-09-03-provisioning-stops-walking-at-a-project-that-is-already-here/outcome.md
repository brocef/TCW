# Outcome — Provisioning stops walking at a project that is already here

## What shipped

1. **`ProjectRegistry.projects()`** — every project in the graph, on the
   storage-neutral interface. `_declared_nodes_in_graph` used
   `current + ancestors + descendants`, which omits a sibling and a sibling of an
   ancestor: the shapes a workspace is actually made of, and the ones whose
   declarations were therefore never read. The docstring says why the set is not
   reconstructed from relations.
2. **A present project is still enqueued.** `resolved_outside` now returns
   *where* the project is rather than a boolean, and the skip branch enqueues it.
   Not fetching a project was never a reason to stop reading it — its own
   declarations are how the walk reaches anything beyond it.
3. **`--dry-run` no longer records a planned obtain as available.**
   `have.add(project_id)` moved after the dry-run return.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2317 passed in 356.15s (0:05:56)
```

The five environmental failures. (Re-run after the delete-safety item: 2322
passed.)

Two new tests in `tests/test_store_provisioning.py`: a three-node chain where the
middle project is present *and* declared, asserting the far project is still
obtained; and a project declared twice — as a parent and as a child, which is
what a parent and a grandparent both naming it looks like — asserting `--dry-run`
plans it rather than calling it available, and creates no cache directory.

### Against the real workspace

The steady state is the case this item exists for, so it was reproduced on the
real repositories rather than in a fixture. In a `proposit-app`-only checkout
with orchestration already provisioned:

```
$ rm -rf <cache>/*proposit-core*        # orchestration stays present
$ tcw provision
  proposit-app: already available at <cache>/…-proposit-orchestration-…
→ proposit-core: https://github.com/Proposit-App/proposit-core.git at main → …
  proposit-core: obtained at …
  proposit-app-repo: already available
```

`proposit-core` is reachable only through the declaration on the orchestration
node, which is present. Before this change that node was skipped and never read,
so `proposit-core` was silently never obtained.

## Autonomous decisions

Codex is unavailable in this container; the advisor consulted for this run was a
single Opus subagent, on the delete-safety item. No checkpoint on this item
needed one: the finding named the defect and the fix follows from it.

1. **Whether to add `projects()` to the abstract interface or reach the graph
   another way.** Decided alone. `registry.get(id)` already answers per-project,
   so the set is information the registry has and no caller should rebuild.
   Adding it to `ProjectRegistry` rather than only `FsProjectRegistry` keeps the
   question storage-neutral — a tracker adapter answers it as easily.
2. **Whether to enqueue a present project or rely on `projects()` alone.** Both.
   `projects()` covers everything present at the start; the enqueue covers a
   project that becomes present *during* the walk, and a graph reached through a
   node obtained mid-run. Either alone leaves a hole.

## Notes

The defect and its predecessor were both in the same two lines, and both were
found by running against a real workspace rather than by a test. The first fix
enumerated three relations; this one asks the registry. That is the same
correction the delete-safety item made in a different file on the same day —
enumerating causes where a single question was available.
