# Outcome — The provisioning skip misses a reachable project

## What shipped

One task, as planned. `_provision_nodes` keeps the registry opened at the
starting node and asks `registry.get(project_id)` directly, plus the ids obtained
during the walk. The `current`/`ancestors()`/`descendants()` reconstruction is
gone, and the comment at the call site says why: a reconstruction can always miss
a relation nobody thought of, and this one missed the relation a workspace is
made of.

Changelog: the existing skip entry now records that the question is asked rather
than reconstructed, and names the relation the intermediate version missed.
Nothing else fired — the README and capability wording already said "a project
this checkout can already reach", which is what the code now implements.

## Tests

```
$ python -m pytest -q tests/ -p no:randomly
5 failed, 2310 passed in 351.61s (0:05:51)
```

The established environmental failures.

One new test in `tests/test_store_provisioning.py`: a four-node workspace where
the caller's grandparent declares a repository for a sibling project that is
present on disk, and another for one that is not. The present one is reported
available and never cloned; the absent one is obtained; exactly one cache
directory exists and it belongs to the absent repository.

### The real verification

`tcw provision --dry-run` in `apps/server` of the hierarchical workspace — every
repository on disk, which is the workstation layout:

```
  work: already available at …/mac/docs/proposit-server/work
  proposit-app: already available
  proposit-core: already available
  proposit-app-repo: already available
```

No cache directory is created. Before the fix, `proposit-core` read
`would obtain into …`.

## Corrections

- **The test's cache assertion was wrong before it was right.** It checked for
  the substring "sibling" in the cache directory names, which match either way
  because the directory name embeds the pytest node id — and the test name
  contains "sibling". It now asserts one directory and matches it against the
  absent repository's own cache key.

## Notes

This is the second defect in four hours in the same two lines, and both were
found by running against a real workspace rather than by a test. The first fix
was written against the case in front of it; the second replaced the enumeration
with a question. Worth remembering that "which relations count as here" was never
a question TCW needed to answer — the registry already did.
